"""Bounded G5 accepted-spend lookup hint; immutable archive remains authoritative."""
import hashlib,json,sqlite3,zlib
from capture import Archive as CoreArchive,canonical
SCHEMA='''CREATE TABLE IF NOT EXISTS recovery_index_progress(id INTEGER PRIMARY KEY CHECK(id=1),seq INTEGER NOT NULL,cursor TEXT NOT NULL,digest TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recovery_index_chain(position INTEGER PRIMARY KEY,hash TEXT UNIQUE NOT NULL,page_seq INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS recovery_acceptance_lookup ON acceptance(accepting_hash,page_seq,full_hash);
CREATE INDEX IF NOT EXISTS recovery_funding_lookup ON bodies(txid);
'''
def require(v,m):
 if not v:raise ValueError(m)
def schema(db):db.executescript(SCHEMA);db.commit()
def meta(db,key):
 r=db.execute('select value from metadata where key=?',(key,)).fetchone();return json.loads(r[0]) if r else None
def begin(db):
 cp=meta(db,'checkpoint');require(cp and cp.get('hash'),'index origin missing')
 db.execute('insert into recovery_index_progress values(1,0,?,?)',(cp['hash'],'0'*64))
 if meta(db,'horizon_state') is not None or db.execute('select 1 from active_chain where hash=?',(cp['hash'],)).fetchone():db.execute('insert into recovery_index_chain values(0,?,0)',(cp['hash'],))
def apply(db,seq):
 old=db.execute('select seq,cursor,digest from recovery_index_progress where id=1').fetchone();require(old and seq==old[0]+1 and 0<seq<2**63,'index page gap/bound')
 row=db.execute('select start,cursor,response_sha,response,previous_digest,digest,horizon from pages where seq=?',(seq,)).fetchone();require(row is not None,'index missing immutable page')
 start,cursor,check,blob,prev,digest,horizon=row;raw=zlib.decompress(blob)
 require(start==old[1] and prev==old[2] and hashlib.sha256(raw).hexdigest()==check,'index cursor/checksum gap')
 require(hashlib.sha256(canonical({'start':start,'cursor':cursor,'horizon':horizon,'response_sha':check,'previous_digest':prev})).hexdigest()==digest,'index digest mismatch')
 response=json.loads(raw);chain=list(db.execute('select hash,page_seq from recovery_index_chain order by position'));hashes=[x[0] for x in chain];removed=response['removedChainBlockHashes'];added=response['addedChainBlockHashes'];groups=response['chainBlockAcceptedTransactions']
 require(len(set(removed))==len(removed) and len(set(added))==len(added) and len(added)==len(groups),'index duplicate/missing group')
 if removed:
  require(set(removed)<=set(hashes),'index unknown removal');first=min(hashes.index(h) for h in removed);require(set(hashes[first:])==set(removed),'index noncontiguous removal');chain=chain[:first]
 require(not set(added)&{x[0] for x in chain},'index active group replay')
 for h,g in zip(added,groups):require(g['chainBlockHeader']['hash']==h,'index reordered acceptance group')
 prefix=len(chain);db.execute('delete from recovery_index_chain where position>=?',(prefix,));db.executemany('insert into recovery_index_chain values(?,?,?)',[(prefix+i,h,seq) for i,h in enumerate(added)])
 require((added[-1] if added else chain[-1][0] if chain else meta(db,'checkpoint')['hash'])==cursor,'index projected cursor mismatch')
 db.execute('update recovery_index_progress set seq=?,cursor=?,digest=? where id=1',(seq,cursor,digest))
def ensure_current(db):
 if db.execute('select 1 from recovery_index_progress where id=1').fetchone() is None:
  with db:begin(db)
 progress=db.execute('select seq,cursor,digest from recovery_index_progress where id=1').fetchone();last=meta(db,'last_commit')
 require(last and progress[0]<=last['seq'],'index ahead of archive')
 if progress[0]<last['seq']:
  # One pass over only the existing bounded run log, without native replay.
  with db:
   for seq in range(progress[0]+1,last['seq']+1):apply(db,seq)
 progress=db.execute('select seq,cursor,digest from recovery_index_progress where id=1').fetchone()
 require(progress==(last['seq'],last['cursor'],last['digest']),'index/archive progress mismatch')
 want=list(db.execute('select hash from active_chain order by position'));got=list(db.execute('select hash from recovery_index_chain order by position'));require(got==want,'index/current acceptance projection mismatch')
 return {'seq':progress[0],'cursor':progress[1],'digest':progress[2]}
class Archive(CoreArchive):
 def __init__(self,path,reference_binary=None):
  super().__init__(path,reference_binary=reference_binary);schema(self.db)
  if self.meta('last_commit'):ensure_current(self.db)
 def setmeta(self,key,value):
  super().setmeta(key,value)
  if key=='last_commit':
   if not self.db.execute('select 1 from recovery_index_progress where id=1').fetchone():begin(self.db)
   if value['seq']>0:apply(self.db,value['seq'])

def hint(db,locator,checkpoint,run_id):
 last=ensure_current(db);cp=db.execute('select cursor,digest from pages where seq=?',(checkpoint['seq'],)).fetchone()
 require(cp==(checkpoint['cursor'],checkpoint['digest']),'index checkpoint not retained')
 tid=locator['s0_txid_hex'];index=int(locator['s0_index'])
 def refs(sql,args):
  result=[]
  for seq,h,pos,txid,full,bodysha in db.execute(sql,args):
   require(seq>checkpoint['seq'],'relevant acceptance predates fresh checkpoint')
   result.append({'page_seq':seq,'accepting_hash':h,'transaction_position':pos,'txid':txid,'full_hash':full,'body_sha256':bodysha})
  return result
 join=' from acceptance a join recovery_index_chain c on c.hash=a.accepting_hash and c.page_seq=a.page_seq join bodies b on b.full_hash=a.full_hash '
 cols='select a.page_seq,a.accepting_hash,a.position,a.txid,a.full_hash,b.sha256 '
 funding=refs(cols+join+'where a.txid=? order by c.position,a.position',(tid,))
 spenders=refs(cols+join+'join spends s on s.full_hash=a.full_hash where s.previous_txid=? and s.previous_index=? order by c.position,a.position',(tid,index))
 require(len(funding)==1,'missing/duplicate funding lookup');require(len(spenders)==1,'missing/duplicate/conflicting spender lookup')
 return {'schema':'kpi-bounded-S0-spend-hint/v1','run_id':run_id,'checkpoint_seq':checkpoint['seq'],'checkpoint_cursor':checkpoint['cursor'],'checkpoint_digest':checkpoint['digest'],'commit':last,'S0_outpoint':[tid,index],'funding':funding[0],'spender':spenders[0]}
