"""Bounded TN10 acceptance retention, not a cryptographic light client.

Uses unchanged pinned A1 canonical encoding and published upstream hash domains.
SQLite FULL/WAL atomically commits evidence and its cursor. Raw records are never
deleted by this program; current-chain projection is explicitly reversible.
"""
import argparse, hashlib, json, os, sqlite3, time, zlib, tempfile, subprocess
from pathlib import Path
from rpc_local import RPC
from a1_recovery import canonical_body, full_hash

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def txid(tx,reference_binary=None):
    pre=canonical_body(tx,False)
    if tx['version']==0:return hashlib.blake2b(pre,digest_size=32,key=b'TransactionID').hexdigest()
    if tx['version']!=1:raise ValueError('unsupported body version')
    # V1 uses upstream BLAKE3 domains. Reuse the pinned native reference rather
    # than adding a crypto implementation or a new Python dependency on C.
    with tempfile.TemporaryDirectory(prefix='kpi-public-body-') as d:
        p=Path(d)/'body.json';p.write_bytes(canonical(tx))
        result=subprocess.run([reference_binary or os.environ.get('KPI_REFERENCE','/opt/kpi-g5-capture/a1_reference'),'--body',str(p)],check=True,capture_output=True,text=True,timeout=15)
        hashes=json.loads(result.stdout)
        if hashes['full_hash']!=full_hash(tx):raise ValueError('Python/native full-hash disagreement')
        return hashes['txid']

def validate_page(start,response,chain,reference_binary=None):
    if set(response)!={'addedChainBlockHashes','removedChainBlockHashes','chainBlockAcceptedTransactions'}:raise ValueError('incomplete page fields')
    added=response['addedChainBlockHashes'];removed=response['removedChainBlockHashes'];groups=response['chainBlockAcceptedTransactions']
    if len(added)!=len(groups) or len(set(added))!=len(added) or len(set(removed))!=len(removed):raise ValueError('missing/duplicate acceptance groups')
    projected=list(chain)
    if removed:
        if not set(removed).issubset(projected):raise ValueError('removal beyond retained checkpoint')
        first=min(projected.index(h) for h in removed)
        if set(projected[first:])!=set(removed):raise ValueError('noncontiguous removal')
        projected=projected[:first]
    if set(added)&set(projected):raise ValueError('duplicate active accepting block')
    rows=[]
    for h,g in zip(added,groups):
        if len(h)!=64 or g.get('chainBlockHeader',{}).get('hash')!=h or not isinstance(g.get('acceptedTransactions'),list):raise ValueError('reordered/incomplete accepting group')
        for pos,t in enumerate(g['acceptedTransactions']):
            v=t.get('verboseData',{});tid=txid(t,reference_binary);full=full_hash(t)
            if v.get('transactionId')!=tid or v.get('hash')!=full:raise ValueError('native ID/full-hash mismatch')
            data=canonical(t);rows.append((h,pos,tid,full,sha(data),data,t))
    projected.extend(added)
    return projected,rows

SCHEMA='''
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pages(seq INTEGER PRIMARY KEY,start TEXT NOT NULL,cursor TEXT NOT NULL,horizon TEXT NOT NULL,response_sha TEXT NOT NULL,response BLOB NOT NULL,previous_digest TEXT NOT NULL,digest TEXT NOT NULL,at REAL NOT NULL,UNIQUE(start,response_sha));
CREATE TABLE IF NOT EXISTS bodies(full_hash TEXT PRIMARY KEY,txid TEXT NOT NULL,sha256 TEXT NOT NULL,body BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS acceptance(page_seq INTEGER NOT NULL,accepting_hash TEXT NOT NULL,position INTEGER NOT NULL,txid TEXT NOT NULL,full_hash TEXT NOT NULL,PRIMARY KEY(page_seq,accepting_hash,position));
CREATE TABLE IF NOT EXISTS spends(full_hash TEXT NOT NULL,input_index INTEGER NOT NULL,previous_txid TEXT NOT NULL,previous_index INTEGER NOT NULL,PRIMARY KEY(full_hash,input_index));
CREATE INDEX IF NOT EXISTS spender_lookup ON spends(previous_txid,previous_index);
CREATE TABLE IF NOT EXISTS active_chain(position INTEGER PRIMARY KEY,hash TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS utxo_observations(seq INTEGER PRIMARY KEY,page_seq INTEGER NOT NULL,at REAL NOT NULL,horizon TEXT NOT NULL,addresses_sha TEXT NOT NULL,response_sha TEXT NOT NULL,response BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,at REAL NOT NULL,kind TEXT NOT NULL,details TEXT NOT NULL);
'''
class Archive:
    def __init__(self,path,reference_binary=None):
        self.reference_binary=reference_binary
        self.db=sqlite3.connect(path,timeout=15);self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL');self.db.executescript(SCHEMA)
        if 'request' not in {x[1] for x in self.db.execute('PRAGMA table_info(pages)')}:
            self.db.execute('ALTER TABLE pages ADD COLUMN request TEXT');self.db.commit()
        for table in ['pages','bodies','acceptance','spends','utxo_observations','events']:
            for operation in ['UPDATE','DELETE']:
                self.db.execute(f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable archive record'); END")
        self.db.commit()
    def meta(self,key):
        r=self.db.execute('SELECT value FROM metadata WHERE key=?',(key,)).fetchone();return json.loads(r[0]) if r else None
    def setmeta(self,key,value):self.db.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',(key,canonical(value).decode()))
    def initialize(self,checkpoint,provenance):
        if self.meta('checkpoint') is not None:return
        with self.db:self.setmeta('checkpoint',checkpoint);self.setmeta('cursor',checkpoint['hash']);self.setmeta('provenance',provenance)
    def event(self,kind,details):
        with self.db:self.db.execute('INSERT INTO events(at,kind,details) VALUES(?,?,?)',(time.time(),kind,canonical(details).decode()))
    def commit(self,start,response,horizon,utxos=None,addresses=None,request=None):
        data=canonical(response);checksum=sha(data);cursor=self.meta('cursor');prior=self.db.execute('SELECT cursor FROM pages WHERE start=? AND response_sha=?',(start,checksum)).fetchone()
        if prior:
            if prior[0]!=cursor:raise ValueError('duplicate event conflicts with current cursor')
            self.event('duplicate-page-ignored',{'sha256':checksum});return False
        if start!=cursor:raise ValueError('cursor gap')
        chain=[r[0] for r in self.db.execute('SELECT hash FROM active_chain ORDER BY position')]
        projected,rows=validate_page(start,response,chain,reference_binary=self.reference_binary)
        new_cursor=projected[-1] if projected else self.meta('checkpoint')['hash']
        if not response['addedChainBlockHashes'] and not response['removedChainBlockHashes']:
            if cursor!=horizon:raise ValueError('no progress before horizon')
            return False
        previous=self.db.execute('SELECT digest FROM pages ORDER BY seq DESC LIMIT 1').fetchone();previous=previous[0] if previous else '0'*64
        digest=sha(canonical({'start':start,'cursor':new_cursor,'horizon':horizon,'response_sha':checksum,'previous_digest':previous}))
        with self.db:
            c=self.db.execute('INSERT INTO pages(start,cursor,horizon,response_sha,response,previous_digest,digest,at,request) VALUES(?,?,?,?,?,?,?,?,?)',(start,new_cursor,horizon,checksum,zlib.compress(data),previous,digest,time.time(),canonical(request).decode() if request else None));seq=c.lastrowid
            for h,pos,tid,full,check,body,tx in rows:
                old=self.db.execute('SELECT sha256,body FROM bodies WHERE full_hash=?',(full,)).fetchone()
                if old and old[0]!=check and canonical_body(json.loads(zlib.decompress(old[1])))!=canonical_body(tx):raise ValueError('same full hash with inconsistent retained body')
                self.db.execute('INSERT OR IGNORE INTO bodies VALUES(?,?,?,?)',(full,tid,check,zlib.compress(body)))
                self.db.execute('INSERT INTO acceptance VALUES(?,?,?,?,?)',(seq,h,pos,tid,full))
                for i,inp in enumerate(tx['inputs']):
                    op=inp['previousOutpoint'];self.db.execute('INSERT OR IGNORE INTO spends VALUES(?,?,?,?)',(full,i,op['transactionId'],int(op['index'])))
            self.db.execute('DELETE FROM active_chain')
            self.db.executemany('INSERT INTO active_chain VALUES(?,?)',enumerate(projected))
            if utxos is not None:self.db.execute('INSERT INTO utxo_observations(page_seq,at,horizon,addresses_sha,response_sha,response) VALUES(?,?,?,?,?,?)',(seq,time.time(),new_cursor,sha(canonical(addresses)),sha(canonical(utxos)),zlib.compress(canonical(utxos))))
            self.setmeta('cursor',new_cursor);self.setmeta('last_commit',{'seq':seq,'cursor':new_cursor,'queried_horizon':horizon,'digest':digest,'at':time.time()})
        return True
    def status(self):
        return {'checkpoint':self.meta('checkpoint'),'provenance':self.meta('provenance'),'cursor':self.meta('cursor'),'last_commit':self.meta('last_commit'),'pages':self.db.execute('SELECT COUNT(*) FROM pages').fetchone()[0],'bodies':self.db.execute('SELECT COUNT(*) FROM bodies').fetchone()[0],'acceptance_groups':self.db.execute('SELECT COUNT(DISTINCT accepting_hash) FROM acceptance').fetchone()[0],'version_counts':{str(v):n for v,n in self.version_counts()},'error':self.meta('last_error')}
    def version_counts(self):
        counts={}
        for body, in self.db.execute('SELECT body FROM bodies'):
            v=json.loads(zlib.decompress(body))['version'];counts[v]=counts.get(v,0)+1
        return counts.items()

def run(config):
    from capacity import Capacity
    capacity=Capacity(config)
    archive=Archive(config['database']);capacity.bind(archive.db);rpc=None;archive.event('capture-start',{'pid':os.getpid(),'source_sha256':sha(Path(__file__).read_bytes()),'configured_provenance':config['provenance']})
    while True:
        try:
            import shutil
            database=Path(config['database'])
            capacity.guard(archive.db)
            available=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
            if available<3*1024**3:raise ValueError('node-host memory reserve low; capture pauses')
            if rpc is None:rpc=RPC()
            info=rpc.call('getServerInfo',{})
            if info['networkId']!='testnet-10' or info['serverVersion']!='2.1.0' or not info['hasUtxoIndex'] or not info['isSynced']:raise ValueError('node provenance/sync/index qualification failed')
            dag=rpc.call('getBlockDagInfo',{})
            if archive.meta('checkpoint') is None:
                cursor=dag['sink']
                for _ in range(config.get('initial_ancestor_steps',2700)):
                    b=rpc.call('getBlock',{'hash':cursor,'includeTransactions':False})['block'];cursor=b['verboseData']['selectedParentHash']
                b=rpc.call('getBlock',{'hash':cursor,'includeTransactions':False})['block'];h=b['header']
                archive.initialize({'hash':cursor,'blue_score':str(h['blueScore']),'daa_score':str(h['daaScore']),'at':time.time(),'scope':'before-any-KPI-funding-public-TN10-only'},config['provenance']|{'server':info})
            cursor=archive.meta('cursor')
            # Upstream has no client batch-size parameter. Temporarily bound the
            # returned blue-score range using its documented strict-distance
            # filter, then lower it on subsequent pages until the head is covered.
            # This is pagination flow control, not a finality policy or skipped range.
            current_header=rpc.call('getBlock',{'hash':cursor,'includeTransactions':False})['block']['header']
            sink_header=rpc.call('getBlock',{'hash':dag['sink'],'includeTransactions':False})['block']['header']
            confirmation=max(0,int(sink_header['blueScore'])-int(current_header['blueScore'])-64)
            request={'startHash':cursor,'dataVerbosityLevel':'Full','minConfirmationCount':confirmation}
            page=rpc.call('getVirtualChainFromBlockV2',request)
            addresses=config.get('watch_addresses',[])
            # Full exact entries for declared reserves must be watched before funding.
            obs=rpc.call('getUtxosByAddresses',{'addresses':addresses}) if addresses else None
            capacity.guard(archive.db) # Recheck after bounded RPC; never advance at a failed capacity gate.
            changed=archive.commit(cursor,page,dag['sink'],obs,addresses,request)
            if changed:archive.db.execute('PRAGMA wal_checkpoint(PASSIVE)')
            capacity.publish(archive.db)
            with archive.db:archive.setmeta('last_error',None)
            if changed:print(json.dumps({'event':'commit','seq':archive.meta('last_commit')['seq'],'groups':len(page['addedChainBlockHashes']),'removed':len(page['removedChainBlockHashes'])}),flush=True)
            if confirmation==0:time.sleep(config.get('poll_seconds',3))
        except Exception as e:
            message=type(e).__name__+': '+str(e)
            with archive.db:archive.setmeta('last_error',{'at':time.time(),'message':message})
            archive.event('capture-error',{'message':message});capacity.publish(archive.db,error=message);print(json.dumps({'event':'error','message':message}),flush=True)
            if rpc:
                try:rpc.close()
                except Exception:pass
            rpc=None;time.sleep(10)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['run','status']);p.add_argument('--config',default='/etc/kpi-capture.json');a=p.parse_args();config=json.loads(Path(a.config).read_text())
    if a.action=='run':run(config)
    else:
        from capacity import Capacity
        db=sqlite3.connect('file:'+config['database']+'?mode=ro',uri=True)
        meta={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
        print(json.dumps({'metadata':meta,'capacity':Capacity(config).snapshot(db)},indent=2));db.close()
