"""Finite C-native history collector, concrete read-only node CLI. No submit API.
Retains every complete original V2 page, including overshoot, and stops at a
fixed prefunding target or exact continuation. Old READY/capture paths unchanged.
"""
import argparse,fcntl,hashlib,json,os,pathlib,shutil,sqlite3,time
from rpc_local import RPC
from recovery_index import Archive,ensure_current
from capture import canonical
from seal_witness import durable_new,require,survival,digest,process_identity,hexhash,integer
from finite_runtime import settings,run_path,database,seal_record,node_binding

def pin_health(cfg,rpc):
 info=rpc.call('getServerInfo',{})
 require(info['networkId']=='testnet-10' and info['isSynced'] is True and info['hasUtxoIndex'] is True and info['serverVersion']==cfg['finite']['server_version'],'finite collector node health')
 node_binding(cfg)
 return info

def blue_score(header):
 value=header.get('blueScore')
 require(type(value) is int and 0<=value<2**64,'native header blue score uint64')
 return value

def select_recent_anchor(rpc,depth,clock=time.monotonic):
 """C-owned actual selected-parent walk, bounded, never caller-certified."""
 require(type(depth) is int and depth in (40,80),'fixed preparation anchor depth')
 began=clock();deadline=began+8
 def call(method,params):
  require(clock()<deadline,'anchor RPC start deadline');sock=getattr(rpc,'s',None);prior=sock.gettimeout() if sock is not None else None
  try:
   if sock is not None:sock.settimeout(max(.001,deadline-clock()))
   value=rpc.call(method,params);require(clock()<deadline,'anchor RPC completion deadline');return value
  finally:
   if sock is not None:sock.settimeout(prior)
 dag=call('getBlockDagInfo',{});sink=dag['sink']
 require(hexhash(sink),'selection sink hash')
 headers=[];seen=set();requested=sink;previous=None;snapshot_blue=None
 for step in range(129):
  require(clock()<deadline,'anchor selection deadline')
  block=call('getBlock',{'hash':requested,'includeTransactions':False})['block']
  require(clock()<deadline,'anchor selection completion deadline')
  header=block['header'];verbose=block['verboseData'];score=blue_score(header)
  require(header.get('hash')==requested and requested not in seen,'anchor header identity')
  if previous is not None:require(score<previous,'selected-parent blue score must decrease')
  if snapshot_blue is None:snapshot_blue=score
  headers.append(header);seen.add(requested)
  if snapshot_blue-score>=depth:
   require(verbose.get('isChainBlock') is True,'chosen anchor is not on current chain')
   rpc.METHODS=set(rpc.METHODS)|{'getVirtualChainFromBlock'}
   survival(call('getVirtualChainFromBlock',{'startHash':requested,'includeAcceptedTransactionIds':False,'minConfirmationCount':0}),requested)
   require(clock()<deadline,'anchor survival completion deadline')
   return {'hash':requested,'blue_score':score,'snapshot_sink':sink,'snapshot_blue_score':snapshot_blue,
           'minimum_blue_depth':depth,'selected_parent_steps':step,'path_headers':headers,'path_sha256':digest(headers),
           'selection_seconds':clock()-began,'max_steps':128,'max_seconds':8}
  parent=verbose.get('selectedParentHash');parents=header.get('parentsByLevel')
  require(hexhash(parent) and type(parents) is list and parents and type(parents[0]) is list and parent in parents[0],'selected parent/header membership')
  require(step<128,'anchor selected-parent step budget');previous=score;requested=parent
 raise ValueError('unreachable anchor selection budget')

def confirmation_count(tip_blue,cursor_blue):
 require(integer(tip_blue) and integer(cursor_blue) and tip_blue>=cursor_blue,'finite cursor/tip blue scores')
 return max(20,tip_blue-cursor_blue-64)

# Per-run physical storage, including WAL and rollback journal. The measured
# funded run reached 1.09 GB in about five minutes; 32 GiB leaves more than four
# times that rate extrapolated over the unchanged 1800-second lifetime. This is
# an experimental allocation, not a bound on future public-testnet growth.
CAPTURE_DISK_LIMIT=32*1024*1024*1024
CAPTURE_FREE_RESERVE=50*1024*1024*1024
CAPTURE_PAGE_LIMIT=512

def capture_resource_budget(cfg,archive):
 files=[database(cfg),pathlib.Path(str(database(cfg))+'-wal'),pathlib.Path(str(database(cfg))+'-journal')]
 sizes={p.name:p.stat().st_size if p.exists() else 0 for p in files}
 pages=archive.db.execute('select count(*) from pages').fetchone()[0]
 total=sum(sizes.values())
 # Inspect the capture's actual filesystem, not the root/home filesystem.
 free=shutil.disk_usage(database(cfg).parent).free
 if total>CAPTURE_DISK_LIMIT or pages>CAPTURE_PAGE_LIMIT or free<CAPTURE_FREE_RESERVE:
  # Numeric resource counters only; never export page bodies, entries or proofs.
  durable_new(run_path(cfg)/'CAPTURE-RESOURCE-FAULT.json',{'run_id':cfg['run_id'],'at':time.time(),'file_sizes_bytes':sizes,'total_bytes':total,'byte_limit':CAPTURE_DISK_LIMIT,'pages':pages,'page_limit':CAPTURE_PAGE_LIMIT,'filesystem_free_bytes':free,'filesystem_free_reserve_bytes':CAPTURE_FREE_RESERVE})
 require(total<=CAPTURE_DISK_LIMIT and pages<=CAPTURE_PAGE_LIMIT and free>=CAPTURE_FREE_RESERVE,'finite capture budget')
 return {'total_bytes':total,'pages':pages,'byte_limit':CAPTURE_DISK_LIMIT,'page_limit':CAPTURE_PAGE_LIMIT,'filesystem_free_bytes':free,'filesystem_free_reserve_bytes':CAPTURE_FREE_RESERVE}

def append_page(cfg,archive,rpc):
 # Refuse another page before collecting or writing if storage is already low;
 # recheck after the entire page commits. Never trim evidence to meet a budget.
 capture_resource_budget(cfg,archive)
 start=archive.meta('cursor');dag=rpc.call('getBlockDagInfo',{})
 cursor_header=rpc.call('getBlock',{'hash':start,'includeTransactions':False})['block']['header']
 tip_header=rpc.call('getBlock',{'hash':dag['sink'],'includeTransactions':False})['block']['header']
 require(cursor_header.get('hash')==start and tip_header.get('hash')==dag['sink'],'finite page cursor/tip header identity')
 request={'startHash':start,'dataVerbosityLevel':'Full','minConfirmationCount':confirmation_count(blue_score(tip_header),blue_score(cursor_header))}
 response=rpc.call('getVirtualChainFromBlockV2',request)
 require(len(canonical(response))<=64*1024*1024,'finite complete page size budget')
 require(type(response) is dict and set(response)=={'removedChainBlockHashes','addedChainBlockHashes','chainBlockAcceptedTransactions'} and all(type(response[k]) is list for k in response),'finite exact typed page arrays')
 require(not response['removedChainBlockHashes'],'finite historical removal; never requalify a removed prefix')
 if not response['addedChainBlockHashes']:
  require(not response['chainBlockAcceptedTransactions'],'empty confirmed page has acceptance groups')
  return False,response
 addresses=cfg['finite']['watch_addresses'];utxos=rpc.call('getUtxosByAddresses',{'addresses':addresses})
 require(type(utxos.get('entries')) is list and len(utxos['entries'])<=8,'finite UTXO cardinality')
 changed=archive.commit(start,response,dag['sink'],utxos,addresses,request)
 capture_resource_budget(cfg,archive)
 return changed,response

def prefunding(cfg,rpc_factory=RPC,clock=time.monotonic):
 settings(cfg);run=run_path(cfg);run.parent.mkdir(mode=0o700,parents=True,exist_ok=True);run.mkdir(mode=0o700,exist_ok=True)
 require(not database(cfg).exists() and not (run/'PREFUND.json').exists(),'new finite preparation required')
 archive=Archive(database(cfg),reference_binary=cfg['finite']['reference']['path']);rpc=rpc_factory();deadline=clock()+1800
 try:
  server=pin_health(cfg,rpc);selection=select_recent_anchor(rpc,40,clock);target=selection['hash']
  origin=rpc.call('getBlock',{'hash':cfg['finite']['origin_hash'],'includeTransactions':False})['block'];origin_blue=blue_score(origin['header'])
  require(origin['header'].get('hash')==cfg['finite']['origin_hash'] and origin['verboseData'].get('isChainBlock') is True and origin_blue<selection['blue_score'] and selection['snapshot_blue_score']-origin_blue>=80,'origin must be older than fixed target and at least80blue behind snapshot')
  survival(rpc.call('getVirtualChainFromBlock',{'startHash':cfg['finite']['origin_hash'],'includeAcceptedTransactionIds':False,'minConfirmationCount':0}),cfg['finite']['origin_hash'])
  node_binding(cfg);durable_new(run/'TARGET-SELECTION.json',selection)
  archive.initialize({'hash':cfg['finite']['origin_hash']},{'network':'testnet-10','server':server,'finite_target':target,'run_id':cfg['run_id'],'source_pins_sha256':digest(cfg['finite']['role_sources'])})
  archive.setmeta('last_error',None);archive.db.commit()
  while True:
   require(clock()<deadline,'finite prefunding capture deadline');changed,response=append_page(cfg,archive,rpc)
   require(changed,'no progress before fixed prefunding target')
   if target in response['addedChainBlockHashes']:break
  commit=ensure_current(archive.db);endpoint=commit['cursor'];block=rpc.call('getBlock',{'hash':endpoint,'includeTransactions':False})['block']
  rpc.METHODS=set(rpc.METHODS)|{'getVirtualChainFromBlock'}
  survival(rpc.call('getVirtualChainFromBlock',{'startHash':endpoint,'includeAcceptedTransactionIds':False,'minConfirmationCount':0}),endpoint)
  cp={'schema':'kpi-finite-prefunding-checkpoint/v1','seq':commit['seq'],'cursor':endpoint,'digest':commit['digest'],
      'blue_score':str(block['header']['blueScore']),'daa_score':str(block['header']['daaScore']),
      'network':'testnet-10','server_version':cfg['finite']['server_version'],'capture_state':'FINITE-SEALED',
      'sealed_at':time.time(),'funding_authorization':False,'scope':'finite independently retained native-node prefix plus sampled survival; distinct from READY'}
  chain=[x[0] for x in archive.db.execute('select hash from active_chain order by position')]
  seal=seal_record(cfg,commit,chain,cp,digest({'prefunding_commit':commit}),None,'pre-funding')
  durable_new(run/'PREFUND-SEAL.json',seal)
  durable_new(run/'PREFUND.json',{'run_id':cfg['run_id'],'fixed_target':target,'checkpoint':cp,'commit':commit,'seal_sha256':hashlib.sha256((run/'PREFUND-SEAL.json').read_bytes()).hexdigest()})
  return cp
 except BaseException as exc:
  if not (run/'CAPTURE-FAULT.json').exists():durable_new(run/'CAPTURE-FAULT.json',{'reason':type(exc).__name__,'at':time.time()})
  raise
 finally:rpc.close();archive.db.close()

def continuation(cfg,rpc_factory=RPC,clock=time.monotonic):
 settings(cfg);run=run_path(cfg);require(not (run/'CAPTURE-STOP.json').exists() and not (run/'CAPTURE-FAULT.json').exists(),'consumed/faulted finite collector')
 pref=json.loads((run/'PREFUND.json').read_bytes())
 require(cfg['checkpoint']==pref['checkpoint'],'finite continuation checkpoint mismatch')
 lock=os.open(run/'collector.lock',os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 archive=Archive(database(cfg),reference_binary=cfg['finite']['reference']['path']);rpc=rpc_factory();deadline=clock()+1800
 durable_new(run/'COLLECTOR-START.json',{'run_id':cfg['run_id'],'at':time.time(),'observer':process_identity(),'checkpoint_sha256':digest(pref['checkpoint'])})
 try:
  pin_health(cfg,rpc);rpc.METHODS=set(rpc.METHODS)|{'getVirtualChainFromBlock'}
  while True:
   require(clock()<deadline,'finite continuation capture deadline')
   survival(rpc.call('getVirtualChainFromBlock',{'startHash':pref['checkpoint']['cursor'],'includeAcceptedTransactionIds':False,'minConfirmationCount':0}),pref['checkpoint']['cursor'])
   append_page(cfg,archive,rpc)
   progress={'run_id':cfg['run_id'],'observer':process_identity(),'at':time.time(),'checkpoint_sha256':digest(pref['checkpoint']),'commit':ensure_current(archive.db)}
   temp=run/'collector-progress.tmp';temp.write_bytes(canonical(progress));temp.chmod(0o600)
   with temp.open('rb') as stream:os.fsync(stream.fileno())
   os.replace(temp,run/'COLLECTOR-PROGRESS.json')
   directory=os.open(run,os.O_DIRECTORY);os.fsync(directory);os.close(directory)
   if not (run/'intent.json').exists():
    time.sleep(.25);continue
   intent=json.loads((run/'intent.json').read_bytes());require(intent['run_id']==cfg['run_id'],'collector cross-run intent')
   match=archive.db.execute('select 1 from acceptance a join recovery_index_chain c on c.hash=a.accepting_hash and c.page_seq=a.page_seq where a.txid=? and a.full_hash=?',(intent['intended_txid'],intent['full_hash'])).fetchone()
   if match:
    commit=ensure_current(archive.db);archive.db.execute('PRAGMA wal_checkpoint(FULL)')
    durable_new(run/'CAPTURE-STOP.json',{'run_id':cfg['run_id'],'intent_digest':digest(intent),'commit':commit,'at':time.time(),'all_returned_overshoot_retained':True})
    return commit
   time.sleep(.25)
 except BaseException as exc:
  if not (run/'CAPTURE-FAULT.json').exists():durable_new(run/'CAPTURE-FAULT.json',{'reason':type(exc).__name__,'at':time.time()})
  raise
 finally:rpc.close();archive.db.close();os.close(lock)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',type=pathlib.Path,required=True);parser.add_argument('phase',choices=['prefunding','continuation']);args=parser.parse_args()
 cfg=json.loads(args.config.read_bytes());print(json.dumps((prefunding if args.phase=='prefunding' else continuation)(cfg)))
