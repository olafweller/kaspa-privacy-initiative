"""Concrete C-local finite history/current observation runtime; no submit API.
Only mode=finite-live-native selects this contract. Node assertions are sampled,
non-atomic and assume an honest pinned validating C node.
"""
import hashlib,json,os,pathlib,socket,sqlite3,threading,time
from seal_witness import Store,Sampler,BoundedRPC,durable_new,digest,canonical,require,hexhash
MODE='finite-live-native'
CRITICAL={'finite_runtime.py','finite_capture.py','seal_witness.py','independent_controller.py','gateway.py',
          'boundary_job.py','capture.py','a1_recovery.py','indexed_discovery.py','historical_context.py','history_chunks.py','recovery_index.py'}
_INSTANCE=None

def settings(cfg,source_directory=None):
 require(cfg.get('mode')==MODE,'finite mode required');f=cfg['finite']
 require(set(f)=={'root','genesis','server_version','origin_hash','watch_addresses','role_sources','native','reference','sdk','node_binding'},'finite settings fields')
 require(pathlib.Path(f['root']).is_absolute() and hexhash(f['origin_hash']) and hexhash(f['genesis']),'finite root/genesis/origin')
 require(isinstance(f['server_version'],str) and f['server_version'],'finite server pin')
 here=pathlib.Path(source_directory).resolve() if source_directory is not None else pathlib.Path(__file__).resolve().parent
 expected={p.name for p in here.iterdir() if p.suffix in ('.py','.mjs') and not p.name.startswith('test_')}
 require(set(f['role_sources'])==expected and expected>=CRITICAL,'complete executed C role tree freeze required')
 for name,record in f['role_sources'].items():
  require(pathlib.Path(name).name==name and pathlib.Path(record['path']).resolve()==here/name and set(record)=={'path','sha256'} and hexhash(record['sha256']),'role source pin fields')
  require(hashlib.sha256(pathlib.Path(record['path']).read_bytes()).hexdigest()==record['sha256'],'finite role source changed: '+name)
 for key in ['native','reference','sdk']:
  require(set(f[key])=={'path','sha256'} and hexhash(f[key]['sha256']) and hashlib.sha256(pathlib.Path(f[key]['path']).read_bytes()).hexdigest()==f[key]['sha256'],'finite native/reference/SDK pin')
 return f

def node_binding(cfg,proc_root=None):
 """Pinned local validating node identity substitutes for pruned genesis RPC.
 Exact upstream TN10 Params selects TESTNET_GENESIS (ADR source receipts).
 No B-supplied process/hash/network assertion is accepted.
 """
 from a1_check import GENESIS
 f=cfg['finite'];p=f['node_binding'];require(set(p)=={'pid','start_ticks','boot_id','binary_sha256','command_sha256','rpc_port'},'node identity fields')
 require(f['genesis']==GENESIS.hex() and p['rpc_port']==18210 and type(p['pid']) is int and p['pid']>0,'native TN10 genesis/port/PID')
 base=pathlib.Path('/proc') if proc_root is None else pathlib.Path(proc_root)
 proc=base/str(p['pid']);raw=(proc/'cmdline').read_bytes();argv=[x.decode() for x in raw.split(b'\0') if x]
 require(hashlib.sha256(raw).hexdigest()==p['command_sha256'] and '--testnet' in argv and not any(x=='--configfile' or x.startswith('--configfile=') for x in argv),'node argv/config binding')
 require(not any(x.startswith('--netsuffix') and x not in ('--netsuffix=10','--netsuffix') for x in argv),'node network suffix')
 if '--netsuffix' in argv:require(argv[argv.index('--netsuffix')+1]=='10','node suffix value')
 require((base/'sys/kernel/random/boot_id').read_text().strip()==p['boot_id'] and int((proc/'stat').read_text().rsplit(')',1)[1].split()[19])==p['start_ticks'],'node boot/start changed')
 require(hashlib.sha256((proc/'exe').read_bytes()).hexdigest()==p['binary_sha256'],'node binary changed')
 owned=set()
 for fd in (proc/'fd').iterdir():
  try:link=os.readlink(fd)
  except FileNotFoundError:continue
  if link.startswith('socket:['):owned.add(link[8:-1])
 listening=set()
 for table in ('tcp','tcp6'):
  for line in (base/'net'/table).read_text().splitlines()[1:]:
   fields=line.split()
   if fields[1].split(':')[1]==f'{18210:04X}' and fields[3]=='0A':
    require(fields[1].split(':')[0] in {'0100007F','00000000','00000000000000000000000000000000','00000000000000000000000001000000'}, 'unexpected native RPC listener address')
    listening.add(fields[9])
 require(bool(listening) and listening<=owned,'RPC listener not exclusively owned by pinned node')
 return dict(p)|{'genesis':GENESIS.hex(),'network':'testnet-10','binding':'pinned local node process + TN10 consensus params; sampled node trust'}

def run_path(cfg):return pathlib.Path(cfg['finite']['root'])/cfg['run_id']
def database(cfg):return run_path(cfg)/'capture.sqlite'
def node():return BoundedRPC(lambda timeout:socket.create_connection(('127.0.0.1',18210),timeout),deadline=8)
def config_digest(cfg):
 # Checkpoint/old locator are produced after prefunding; their exact bytes are
 # separately pinned in initial.json, seal and original indexed validator.
 return digest({k:v for k,v in cfg.items() if k not in {'checkpoint','locator'}})

def checkpoint(cfg):
 runtime=instance(cfg);runtime.health()
 record=json.loads((run_path(cfg)/'PREFUND.json').read_bytes())
 require(record['run_id']==cfg['run_id'],'prefunding run binding')
 return record['checkpoint']

def verify_publish(cfg,run,result):
 """Runs inside the worker after its durable native result and before child success;
 verify its durable output,
 complete original chunks, unchanged index/generation and exact native receipt.
 No request-supplied 'validated' boolean is accepted.
 """
 from history_chunks import iter_pages
 from recovery_index import ensure_current,meta
 f=settings(cfg);run=pathlib.Path(run)
 require(run==run_path(cfg) and not (run/'S1-SEAL.json').exists(),'one-shot seal location')
 require(json.loads((run/'validation-result.json').read_bytes())==result,'durable validator result mismatch')
 vc=json.loads((run/'validation-config.json').read_bytes());require(vc==cfg,'validator config changed')
 intent=json.loads((run/'intent.json').read_bytes());initial=json.loads((run/'initial.json').read_bytes())
 require(result['intent_digest']==digest(intent),'seal intent digest')
 r=result['receipt'];require(r['accepted_continuation_native_Full'] is True and r['range_complete'] is True and r['state_discovered']=='s1','native validator failed')
 frozen=sqlite3.connect('file:'+str(run/'history.sqlite')+'?mode=ro',uri=True)
 source=sqlite3.connect('file:'+str(database(cfg))+'?mode=ro',uri=True)
 try:
  commit=ensure_current(frozen);require(commit==ensure_current(source),'capture changed after freeze')
  require((r['C_commit_seq'],r['C_commit_digest'])==(commit['seq'],commit['digest']),'validator generation mismatch')
  stop=json.loads((run/'CAPTURE-STOP.json').read_bytes());require(stop['commit']==commit and stop['intent_digest']==digest(intent),'collector not frozen to intent')
  mp=run/'history-evidence/history-manifest.json';mraw=mp.read_bytes();m=json.loads(mraw)
  for _ in iter_pages(run/'history-evidence',initial['checkpoint'],cfg['run_id'],commit,hashlib.sha256(mraw).hexdigest()):pass
  match=frozen.execute('select a.accepting_hash from acceptance a join recovery_index_chain c on c.hash=a.accepting_hash and c.page_seq=a.page_seq where a.txid=? and a.full_hash=?',(intent['intended_txid'],intent['full_hash'])).fetchall()
  require(len(match)==1,'seal exact full body acceptance')
  chain=[x[0] for x in frozen.execute('select hash from active_chain order by position')]
  require(chain and chain[-1]==commit['cursor'],'seal chain endpoint')
  seal=seal_record(cfg,commit,chain,initial['checkpoint'],hashlib.sha256(mraw).hexdigest(),{'txid':intent['intended_txid'],'full_hash':intent['full_hash'],'accepting_hash':match[0][0]},'s1')
 finally:frozen.close();source.close()
 return seal

def read_verification(path):
 """Bounded C-owned one-shot worker artifact; never a request-provided witness."""
 import stat
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  st=os.fstat(fd);require(st.st_uid==os.getuid() and stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and 0<st.st_size<=3*1024*1024,'publication witness ownership/mode/size')
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(3*1024*1024+1)
 finally:os.close(fd)
 return json.loads(raw),hashlib.sha256(raw).hexdigest()

def verified_seal(cfg,run,result,verification):
 """Small parent checks after the exact waited worker completed every heavy check."""
 from recovery_index import ensure_current,meta
 settings(cfg);run=pathlib.Path(run)
 require(run==run_path(cfg) and not (run/'S1-SEAL.json').exists(),'one-shot seal location')
 require(type(verification) is dict and set(verification)=={'worker','witness_sha256'},'waited worker verification binding required')
 witness,pin=read_verification(run/'PUBLISH-VERIFIED.json')
 require(pin==verification['witness_sha256'] and witness['worker']==verification['worker'],'wrong publication worker/artifact')
 require(set(witness)=={'schema','run_id','worker','config_sha256','result_sha256','manifest_sha256','capture_stop_sha256','seal'} and witness['schema']=='kpi-C-child-publish-verification/v1' and witness['run_id']==cfg['run_id'],'publication witness fields/run')
 raw=(run/'validation-result.json').read_bytes();require(json.loads(raw)==result and witness['result_sha256']==hashlib.sha256(raw).hexdigest(),'durable validator result mismatch')
 vc=(run/'validation-config.json').read_bytes();require(json.loads(vc)==cfg and witness['config_sha256']==hashlib.sha256(vc).hexdigest(),'validator config changed')
 require(witness['manifest_sha256']==cfg['manifest_sha256'] and hashlib.sha256(pathlib.Path(cfg['manifest']).read_bytes()).hexdigest()==cfg['manifest_sha256'],'publication manifest changed')
 stopraw=(run/'CAPTURE-STOP.json').read_bytes();require(hashlib.sha256(stopraw).hexdigest()==witness['capture_stop_sha256'],'collector stop changed after worker')
 stop=json.loads(stopraw);seal=witness['seal'];r=result['receipt']
 require(seal['config_sha256']==config_digest(cfg) and seal['role_sources_sha256']==digest(cfg['finite']['role_sources']) and seal['checkpoint_sha256']==digest(json.loads((run/'initial.json').read_bytes())['checkpoint']),'publication config/source/checkpoint pins')
 require(seal['native_sha256']==cfg['finite']['native']['sha256'] and seal['sdk_sha256']==cfg['finite']['sdk']['sha256'] and seal['history_manifest_sha256']==hashlib.sha256((run/'history-evidence/history-manifest.json').read_bytes()).hexdigest(),'publication native/SDK/history pins')
 intent=json.loads((run/'intent.json').read_bytes());require(result['intent_digest']==digest(intent) and stop['intent_digest']==digest(intent),'publication intent changed')
 require(r['accepted_continuation_native_Full'] is True and r['range_complete'] is True and r['state_discovered']=='s1','native validator failed')
 require((r['C_commit_seq'],r['C_commit_digest'])==(stop['commit']['seq'],stop['commit']['digest']) and seal['prefix_sha256']==stop['commit']['digest'] and seal['endpoint']==stop['commit']['cursor'],'publication generation mismatch')
 require(seal['continuation']['txid']==intent['intended_txid'] and seal['continuation']['full_hash']==intent['full_hash'],'publication body mapping mismatch')
 for path in [run/'history.sqlite',database(cfg)]:
  db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
  try:
   last=meta(db,'last_commit');progress=db.execute('select seq,cursor,digest from recovery_index_progress where id=1').fetchone()
   # Never turn a supposedly frozen parent gate into a heavy reindex operation.
   require({k:last[k] for k in ('seq','cursor','digest')}==stop['commit'] and progress==(last['seq'],last['cursor'],last['digest']),'publication archive advanced/unindexed')
   require(ensure_current(db)==stop['commit'],'publication frozen/current generation mismatch')
  finally:db.close()
 return seal

def publish(cfg,run,result,verification):
 seal=verified_seal(cfg,run,result,verification)
 # A new genuine sample precedes publication; heavy work cannot lend old freshness.
 runtime=instance(cfg);runtime.current()
 durable_new(pathlib.Path(run)/'S1-SEAL.json',seal)
 runtime.activate(pathlib.Path(run)/'S1-SEAL.json','s1');runtime.current()
 return runtime.health()

def seal_record(cfg,commit,chain,cp,manifest_hash,continuation,phase):
 f=cfg['finite'];return {'schema':'kpi-C-native-validated-prefix-seal/v1','phase':phase,'run_id':cfg['run_id'],
  'network':'testnet-10','server_version':f['server_version'],'genesis':f['genesis'],'endpoint':commit['cursor'],
  'active_chain':chain,'continuation':continuation,'config_sha256':config_digest(cfg),
  'role_sources_sha256':digest(f['role_sources']),'native_sha256':f['native']['sha256'],'sdk_sha256':f['sdk']['sha256'],
  'checkpoint_sha256':digest(cp),'prefix_sha256':commit['digest'],'history_manifest_sha256':manifest_hash}

class Runtime:
 def __init__(self,cfg,rpc_factory=node):
  settings(cfg);self.cfg=json.loads(canonical(cfg));self.config_hash=config_digest(self.cfg);self.full_config_hash=digest(self.cfg);self.rpc_factory=rpc_factory;self.lock=threading.RLock();self.stop=threading.Event()
  run=run_path(cfg);require(not (run/'S1-SEAL.json').exists(),'active observer restart forbidden')
  self.activate(run/'PREFUND-SEAL.json','prefunding')
  self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
 def activate(self,path,phase):
  with self.lock:
   if hasattr(self,'store'):
    require(not self.stop.is_set(),'faulted prefunding observer cannot advance')
    previous=self.store.latest();require(self.store.seal['phase']=='pre-funding' and phase=='s1','one-shot seal transition')
   else:previous=None
   raw=path.read_bytes();seal=json.loads(raw)
   require(seal['config_sha256']==config_digest(self.cfg) and seal['role_sources_sha256']==digest(self.cfg['finite']['role_sources']) and seal['genesis']==self.cfg['finite']['genesis'] and seal['server_version']==self.cfg['finite']['server_version'], 'C-owned seal/config pins mismatch')
   new_store=Store(path.parent/('observer-'+phase),path,hashlib.sha256(raw).hexdigest(),os.getuid())
   if previous is not None:
    require(new_store.observer==self.store.observer,'observer changed across seal transition')
    durable_new(path.parent/'SEAL-TRANSITION.json',{'run_id':self.cfg['run_id'],'old_receipt_digest':previous['digest'],'old_seal_sha256':previous['seal_sha256'],'new_seal_sha256':new_store.seal_sha,'observer':new_store.observer,'at':time.time()})
   self.store=new_store
   self.sampler=Sampler(self.store,self.rpc_factory,self.cfg['finite']['watch_addresses'],genesis_verifier=lambda:node_binding(self.cfg));self.sampler.sample()
 def loop(self):
  while not self.stop.wait(2):
   try:
    with self.lock:self.sampler.sample()
   except BaseException as exc:
    self.stop.set()
    run=run_path(self.cfg)
    if not (run/'FAULT.json').exists():durable_new(run/'FAULT.json',{'at':time.time(),'message':'finite current observer failed: '+type(exc).__name__,'scope':'independent finite gate fails closed'})
    break
 def current(self):
  with self.lock:
   settings(self.cfg);require(digest(self.cfg)==self.full_config_hash and not self.stop.is_set(),'mutated/stopped finite runtime')
   self.sampler.sample()
   r=self.store.latest();o=r['observations']
   return {'receipt':r,'seal':self.store.seal,'server':o['server_after'],'dag':o['dag'],'utxos':o['utxos'],
     'observation_at':r['started_at'],'observation_age_seconds':time.time()-r['started_at'],
     'observation_horizon':self.store.seal['endpoint']}
 def health(self):
  with self.lock:
   settings(self.cfg);require(digest(self.cfg)==self.full_config_hash and not self.stop.is_set(),'mutated/stopped finite runtime')
   r=self.store.latest();s=self.store.seal
   return {'seq':r['seq'],'cursor':s['endpoint'],'digest':r['digest'],'at':r['started_at'],
    'frozen_history_digest':s['prefix_sha256'],'finite_seal_sha256':r['seal_sha256'],'observation_contract':'sampled fixed-endpoint native chain survival'}
 def acceptance(self,run):
  with self.lock:
   settings(self.cfg);require(digest(self.cfg)==self.full_config_hash and not self.stop.is_set(),'mutated/stopped finite runtime')
   self.store.latest();seal=self.store.seal;intent=json.loads((pathlib.Path(run)/'intent.json').read_bytes())
   require(seal['phase']=='s1' and seal['continuation']['txid']==intent['intended_txid'] and seal['continuation']['full_hash']==intent['full_hash'],'finite continuation seal mismatch')

def instance(cfg):
 global _INSTANCE
 if _INSTANCE is None:_INSTANCE=Runtime(cfg)
 require(_INSTANCE.cfg==cfg,'finite runtime config mutation');return _INSTANCE

def health(cfg):return instance(cfg).health()
def current(cfg,run):require(pathlib.Path(run)==run_path(cfg),'finite run mismatch');return instance(cfg).current()
def ensure_acceptance(cfg,run):return instance(cfg).acceptance(run)
def utxos(cfg,addresses):
 require(type(addresses) is list and addresses and set(addresses)<=set(cfg['finite']['watch_addresses']),'unbound finite watch set')
 r=current(cfg,run_path(cfg));r['utxos']={'entries':[e for e in r['utxos']['entries'] if e['address'] in addresses]}
 return r|{'finite_current_receipt':r['receipt'],'finite_seal':r['seal'],'scope':'fresh sampled finite-prefix C native UTXO bracket; non-atomic validating node assertion'}


def _fresh_collector_progress(cfg,run,*,_monotonic=None,_sleep=None):
 # A large page is published only after its complete durable commit. Wait for
 # the next completion instead of rejecting healthy ingestion between commits.
 # This changes latency only: the accepted heartbeat remains at most 5s old.
 monotonic=time.monotonic if _monotonic is None else _monotonic
 sleep=time.sleep if _sleep is None else _sleep
 deadline=monotonic()+30;initial_start=None
 while True:
  require((run/'COLLECTOR-START.json').exists() and not (run/'CAPTURE-FAULT.json').exists() and not (run/'CAPTURE-STOP.json').exists(),'finite funding collector not active')
  start=json.loads((run/'COLLECTOR-START.json').read_bytes());require(start['run_id']==cfg['run_id'] and start['checkpoint_sha256']==digest(cfg['checkpoint']),'collector start binding')
  if initial_start is None:initial_start=start
  require(start==initial_start,'collector start changed during bounded wait')
  identity=start['observer'];pid=identity['pid'];os.kill(pid,0)
  require(pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==identity['boot'] and int((pathlib.Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])==identity['start_ticks'],'collector process identity changed')
  try:progress=json.loads((run/'COLLECTOR-PROGRESS.json').read_bytes())
  except FileNotFoundError:progress=None
  if progress is not None:
   require(progress['run_id']==cfg['run_id'] and progress['observer']==identity and progress['checkpoint_sha256']==digest(cfg['checkpoint']),'collector heartbeat unbound')
   age=time.time()-progress['at'];require(age>=-2,'collector heartbeat future timestamp')
   if age<=5:
    require(monotonic()<=deadline,'collector fresh heartbeat arrived after bounded wait')
    return progress
  require(monotonic()<deadline,'collector heartbeat stale after bounded wait')
  sleep(.25)

def funding_ready(cfg):
 run=run_path(cfg);_fresh_collector_progress(cfg,run)
 observed=current(cfg,run);loc=cfg['locator'];point={'transactionId':loc['s0_txid_hex'],'index':int(loc['s0_index'])}
 entries=[e for e in observed['utxos']['entries'] if e['outpoint']==point]
 db=sqlite3.connect('file:'+str(database(cfg))+'?mode=ro',uri=True)
 try:
  found=db.execute('select 1 from acceptance a join recovery_index_chain c on c.hash=a.accepting_hash and c.page_seq=a.page_seq where a.txid=? and a.page_seq>?',(point['transactionId'],cfg['checkpoint']['seq'])).fetchone()
 finally:db.close()
 return {'run_id':cfg['run_id'],'funding_native_entry_retained':bool(found and len(entries)==1),'S1_pointer_supplied':False,'observation_at':observed['observation_at']}

def read(request,cfg,role,guard):
 require(role=='B','finite history B-only');guard();ensure_acceptance(cfg,run_path(cfg))
 from bounded_log_read import read as original_read
 if request['action']=='utxos':
  require(set(request)=={'action','addresses'},'finite UTXO request fields');return utxos(cfg,request['addresses'])
 result=original_read(request,run_path(cfg))
 if request['action']=='status':
  observer=instance(cfg)
  with observer.lock:
   current=observer.store.latest();result.update(finite_seal=observer.store.seal,finite_seal_sha256=current['seal_sha256'])
 return result


def readonly_current(cfg,run,directory):
 """New read-only lifetime on the unchanged C-owned S1 seal; same native sampler.
 Does not resume or mutate the stopped recovery observer, nor create authority.
 """
 run=pathlib.Path(run);require(run==run_path(cfg),'read-only finite run mismatch')
 historical=pathlib.Path(cfg['finite']['role_sources']['finite_runtime.py']['path']).parent
 settings(cfg,historical);seal_path=run/'S1-SEAL.json';raw=seal_path.read_bytes();seal=json.loads(raw)
 require(seal['phase']=='s1' and seal['run_id']==cfg['run_id'] and seal['config_sha256']==config_digest(cfg) and seal['role_sources_sha256']==digest(cfg['finite']['role_sources']),'historical S1 seal/config binding')
 require(seal['native_sha256']==cfg['finite']['native']['sha256'] and seal['sdk_sha256']==cfg['finite']['sdk']['sha256'],'historical native/SDK seal binding')
 store=Store(directory,seal_path,hashlib.sha256(raw).hexdigest(),os.getuid())
 sampler=Sampler(store,node,cfg['finite']['watch_addresses'],genesis_verifier=lambda:node_binding(cfg))
 def current(config,where):
  require(config==cfg and pathlib.Path(where)==run,'read-only current scope')
  settings(cfg,historical);sampler.sample();receipt=store.latest();o=receipt['observations']
  return {'receipt':receipt,'seal':store.seal,'server':o['server_after'],'dag':o['dag'],'utxos':o['utxos'],'observation_at':receipt['started_at'],'observation_age_seconds':time.time()-receipt['started_at'],'observation_horizon':store.seal['endpoint']}
 return current
