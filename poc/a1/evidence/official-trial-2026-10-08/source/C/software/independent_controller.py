"""C owns acceptance/loss decisions. A cannot arm loss or release recovery."""
import os,json,time,socket,struct,pathlib,hashlib,threading,sqlite3,zlib,urllib.request,uuid,subprocess,sys,signal
from boundary_job import Job
import recovery_errors as errors
JOB=None
import boundary_controller_v2 as native_fixture
from capture import canonical
from boundary_watch import validate_boundary
from rpc_local import RPC
from lease_state import read_state
import a1_recovery as recovery
from result_gate import validate as validate_result
ROOT=pathlib.Path('/var/lib/kpi-capture/boundary-final');SOCKET='/run/kpi-g5-independent/control.sock';LOCK=threading.RLock()
ORDER=['PREPARED','C_ACCEPTED_DURABLE','A_NO_DURABLE_S1_VERIFIED','A_LOSS_ARMED','A_LOSS_BOUNDARY','B_RECOVERY_STARTED']
def require(x,m):
 if not x:raise ValueError(m)
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def durable(path,data):native_fixture.durable(path,data)
def records(run):return native_fixture.events(run)
def append(run,kind,payload):return native_fixture.event(run,kind,payload)
def verify(rows):return native_fixture.verify_chain(rows)
def fault(run,message):
 if not (run/'FAULT.json').exists():durable(run/'FAULT.json',{'at':time.time(),'message':message,'scope':'independent C gate fails closed'})
def reject_restarted_active_boundary(run):
 if len(records(run))>=4 or (run/'validation-started.json').exists() and not (run/'validation-completed.json').exists():fault(run,'Observer restarted with an active boundary; recovery must stop and be independently requalified')
def sample():
 results=[]
 for kind,port in zip(['machine','KPI-availability'],CONFIG['probe_ports']):
  nonce=os.urandom(16).hex();observed={'endpoint':kind,'at':time.time(),'reachable':False,'identity_valid':False}
  try:
   # Any successful TCP connection is reachability, even with a silent or malformed HTTP peer.
   with socket.create_connection(('127.0.0.1',port),timeout=1):observed['reachable']=True
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/probe?nonce={nonce}',timeout=1) as reply:data=json.loads(reply.read(1025))
   observed['reachable']=True;require(data['nonce']==nonce and data['endpoint']==kind and data['liveness'] is True and data['boot_identity_sha256']==CONFIG['A_boot_identity_sha256'],'liveness identity mismatch');observed['identity_valid']=True
  except urllib.error.HTTPError:observed['reachable']=True
  except (ValueError,KeyError,json.JSONDecodeError):observed['reachable']=True
  except (ConnectionError,TimeoutError,OSError):pass
  results.append(observed)
 lease=read_state()
 results.append({'endpoint':'independently challenged SSH link','at':time.time(),'reachable':lease['state']=='reachable','identity_valid':lease['state']=='reachable','observer_certain':lease['certain'],'observer_state':lease})
 return {'at':time.time(),'endpoints':results,'any_reachable':any(x['reachable'] for x in results),'all_reachable':all(x['reachable'] and x.get('identity_valid',True) for x in results),'uncertain':not lease['certain']}

def capture_health():
 if CONFIG['mode']=='finite-live-native':
  from finite_runtime import health
  return health(CONFIG)
 rpc=RPC()
 try:info=rpc.call('getServerInfo',{})
 finally:rpc.close()
 db=sqlite3.connect('file:/var/lib/kpi-capture/history.sqlite?mode=ro',uri=True);m={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')};db.close();require(info['networkId']=='testnet-10' and info['isSynced'] and info['hasUtxoIndex'] and m['last_error'] is None and time.time()-m['last_commit']['at']<15,'C chain/capture health gate');return m['last_commit']
def ensure_live_acceptance(run):
 if CONFIG['mode']=='finite-live-native':
  if len(records(run))>=2:
   from finite_runtime import ensure_acceptance
   ensure_acceptance(CONFIG,run)
  return
 if CONFIG['mode']!='live' and not (CONFIG['mode']=='rehearsal' and CONFIG.get('rehearsal_workload')):return
 rows=records(run)
 if len(rows)<2:return
 intent=json.loads((run/'intent.json').read_text());db=sqlite3.connect('file:'+str(run/'history.sqlite' if CONFIG['mode']=='rehearsal' else pathlib.Path('/var/lib/kpi-capture/history.sqlite'))+'?mode=ro',uri=True)
 try:
  active=db.execute('SELECT 1 FROM acceptance a JOIN recovery_index_chain c ON c.hash=a.accepting_hash AND c.page_seq=a.page_seq WHERE a.txid=? AND a.full_hash=? LIMIT 1',(intent['intended_txid'],intent['full_hash'])).fetchone()
 finally:db.close()
 if active is None:fault(run,'Previously receipted continuation no longer actively accepted; requalify lineage after reorg');raise ValueError('stale/reorged acceptance')
def accepted_receipt(run):
 rows=records(run);require(len(rows)>=2,'independent acceptance not observed');v=rows[1];intent=json.loads((run/'intent.json').read_text());return {'run_id':CONFIG['run_id'],'acceptance_digest':v['digest'],'intent_digest':digest(intent),'at':v['at'],'S1_pointer_supplied':False,'authentication':'dedicated forced SSH/host-key verified C gateway'}
def fixture_data(run,name):
 initial=json.loads((run/'initial.json').read_text());accepted=json.loads((run/'accepted-native.json').read_text())
 import fixture_provenance as fp
 accepted=fp.stored(accepted,initial,CONFIG['fixture_header_adapter_sha256'],CONFIG['fixture_header_source_patch_sha256']);paths=accepted['accepted_path'];pages=[];cursor=initial.get('native_checkpoint',initial['checkpoint'])['synthetic_genesis_hash']
 for p in paths:pages.append(native_fixture.page(p['transaction'],p['accepting_block'],cursor,p));cursor=p['accepting_block']
 entries=json.loads((run/'historical-entries.json').read_text());require(entries==fp.entries(accepted),'stored fixture input entries changed');current=[];current_entries={}
 for point,entry in accepted['current_virtual_utxos']:
  current.append({'transaction_id':point['transactionId'],'index':str(point['index']),'value':str(entry['amount']),'spk_hex':entry['scriptPublicKey'],'covenant':entry['covenantId']});current_entries[point['transactionId']+':'+str(point['index'])]=entry
 return {'locator.json':initial['locator'],'pages.json':pages,'entries.json':entries,'current-utxos.json':current,'current-entries.json':current_entries,'source.json':{'horizon':cursor,'scope':'independently accepted native synthetic fixture; no public TN10 broadcast'}}[name]
def normalize_wire(wire):
 require(set(wire)=={'version','gas','lockTime','mass','storageMass','inputs','outputs','payload','subnetworkId','verboseData'},'SDK transport fields changed')
 require(wire['verboseData'] is None and wire['mass']==wire['storageMass'],'SDK cached metadata/mass mismatch')
 tx={k:wire[k] for k in ['version','subnetworkId','payload']};tx.update(lockTime=str(wire['lockTime']),gas=str(wire['gas']),storageMass=str(wire['storageMass']))
 tx['inputs']=[];tx['outputs']=[]
 for i in wire['inputs']:
  require(set(i)=={'computeBudget','previousOutpoint','sequence','sigOpCount','signatureScript','verboseData'} and i['verboseData'] is None,'wire input metadata')
  tx['inputs'].append({k:i[k] for k in ['computeBudget','previousOutpoint','sigOpCount','signatureScript']}|{'sequence':str(i['sequence'])})
 for o in wire['outputs']:
  require(set(o)=={'covenant','scriptPublicKey','value','verboseData'} and o['verboseData'] is None,'wire output metadata')
  tx['outputs'].append({'value':str(o['value']),'scriptPublicKey':recovery.rpc_spk(o['scriptPublicKey']).hex(),'covenant':o['covenant']})
 import tempfile
 with tempfile.TemporaryDirectory() as t:
  path=pathlib.Path(t)/'body.json';path.write_bytes(canonical(tx));p=subprocess.run([native_fixture.REF,'--body',str(path)],capture_output=True,check=True,text=True);h=json.loads(p.stdout)
 tx['id']=h['txid'];return tx

def check_intent(run,intent):
 required={'run_id','intended_txid','full_hash','compute_budget','native_masses','fee','manifest_sha256','inventory_sha256','scope','S0_locator_sha256','worker_source_sha256','attempt_nonce'}
 require(set(intent)==required,'intent fields not minimal/canonical');initial=json.loads((run/'initial.json').read_text());require(intent['run_id']==CONFIG['run_id'] and intent['S0_locator_sha256']==digest(initial['locator']),'wrong run/S0 intent');require(intent['manifest_sha256']==CONFIG['manifest_sha256'] and intent['inventory_sha256']==CONFIG['inventory_sha256'] and intent['worker_source_sha256']==CONFIG['worker_source_sha256'],'unfrozen source/artifacts');require(intent['native_masses']==CONFIG['qualified_masses'] and intent['compute_budget']==CONFIG['compute_budget'] and recovery.rpc_uint(intent['fee'])==recovery.rpc_uint(CONFIG['fee']),'mass/fee/budget changed')
 require(intent['scope']=='unaccepted candidate; no acceptance assertion, S1 index or body','intent scope not immutable')
 for key in ['intended_txid','full_hash']:
  require(isinstance(intent[key],str) and len(bytes.fromhex(intent[key]))==32,'invalid hash')
 require(len(bytes.fromhex(intent['attempt_nonce']))==16,'invalid nonce')
def dispatch(q):
 require(q.get('run_id')==CONFIG['run_id'],'wrong run');run=ROOT/CONFIG['run_id'];run.mkdir(mode=0o700,exist_ok=True);rows=records(run);verify(rows);op=q['op'];role=q['authenticated_role'];
 if op in ['terminal-submit','terminal-observe','terminal-status']:
  require(CONFIG['mode']=='finite-live-native' and role=='B','finite B-only terminal operation')
  def guard():
   with LOCK:return dispatch({'run_id':CONFIG['run_id'],'op':'guard','authenticated_role':'B'})
  guard()
  from terminal_runtime import dispatch as terminal_dispatch
  return terminal_dispatch(q,CONFIG,run,guard)
 if op=='funding-ready':
  require(CONFIG['mode']=='finite-live-native' and role=='controller','finite funding status credential')
  from finite_runtime import funding_ready
  return funding_ready(CONFIG)
 if op=='finite-checkpoint':
  require(CONFIG['mode']=='finite-live-native' and role=='controller','finite checkpoint credential')
  from finite_runtime import checkpoint
  return checkpoint(CONFIG)
 if op=='finite-read':
  require(CONFIG['mode']=='finite-live-native','finite read mode')
  from finite_runtime import read
  return read(q['request'],CONFIG,role,lambda:dispatch({'run_id':CONFIG['run_id'],'op':'guard','authenticated_role':'B'}))
 if op=='lineage-hint':
  require(role=='B','B-only hint');dispatch({'run_id':CONFIG['run_id'],'op':'guard','authenticated_role':'B'})
  from capture import canonical
  return json.loads((run/'lineage-hint.json').read_bytes())
 if op=='bounded-log-read':
  require(CONFIG['mode']=='live' and role=='B','live B-only run-log read');dispatch({'run_id':CONFIG['run_id'],'op':'guard','authenticated_role':'B'})
  from bounded_log_read import read
  return read(q['request'],run)
 if op=='rehearsal-read':
  from live_schema_rehearsal import read
  return read(q['request'],CONFIG,role,dispatch)
 if op=='result':
  require(role=='B','only B can finalize result');result=q['result'];validate_result(result,CONFIG,rows)
  target=run/'B-result.json'
  if target.exists():require(json.loads(target.read_text())==result,'conflicting/replayed result')
  else:
   if result['status']=='success':
    require(not (run/'FAULT.json').exists(),'faulted success forbidden');ensure_live_acceptance(run);require(LATEST is not None and not LATEST['any_reachable'] and not LATEST.get('uncertain',False) and time.time()-LATEST['at']<=5,'final absence guard');capture_health()
   if result['status']=='success':
    sdk_target=run/'terminal-sdk-receipt.json';sdk_result=result['terminal_sdk_receipt']
    if sdk_target.exists():require(json.loads(sdk_target.read_text())==sdk_result,'mixed/replayed SDK receipt')
    else:durable(sdk_target,sdk_result)
   durable(target,result)
   if result['status']=='failure':fault(run,'B autonomous recovery failed closed; no submission or recovery replay permitted')
  receipt={'run_id':CONFIG['run_id'],'status':result['status'],'result_sha256':digest(result),'at':time.time(),'durable_on_C':True,'broadcast':False}
  if result['status']=='success':receipt['terminal_sdk_receipt_sha256']=result['terminal_sdk_receipt_sha256']
  if not (run/'B-result-receipt.json').exists():durable(run/'B-result-receipt.json',receipt)
  return json.loads((run/'B-result-receipt.json').read_text())
 require(not (run/'FAULT.json').exists(),'independent gate faulted')
 if op=='prepare':
  require(role=='admin' and not rows,'prepare forbidden');require(sample()['all_reachable'],'A endpoints not independently baselined');require(CONFIG['mode'] in ['fixture','rehearsal'] or CONFIG.get('execution_authorized') is True,'live execution not authorized');native_fixture.CONFIG=CONFIG
  if CONFIG['mode'] in ['fixture','rehearsal']:return native_fixture.create_fixture(run)
  if CONFIG['mode']=='finite-live-native':
   from finite_runtime import checkpoint,database
   cp=checkpoint(CONFIG);locator=CONFIG['locator'];require(CONFIG['checkpoint']==cp and locator['scan_start_hash']==cp['cursor'] and locator['artifact_index_sha256']==CONFIG['inventory_sha256'],'finite locator/checkpoint binding')
   db=sqlite3.connect('file:'+str(database(CONFIG))+'?mode=ro',uri=True)
   require(db.execute('select cursor,digest from pages where seq=?',(cp['seq'],)).fetchone()==(cp['cursor'],cp['digest']) and db.execute('select 1 from bodies where txid=?',(locator['s0_txid_hex'],)).fetchone() is None,'finite checkpoint missing or funding predates preparation');db.close()
   durable(run/'initial.json',{'locator':locator,'checkpoint':cp})
   from finite_runtime import config_digest
   durable(run/'PREPARATION-FINAL-CONFIG.json',{'run_id':CONFIG['run_id'],'preparation_binding_sha256':config_digest(CONFIG),'final_config_sha256':digest(CONFIG),'checkpoint_sha256':digest(cp),'locator_sha256':digest(locator)})
   if CONFIG.get('terminal_execution_authorized') is True:
    from terminal_runtime import prepare
    prepare(CONFIG,run)
   append(run,'PREPARED',{'locator_sha256':digest(locator),'checkpoint_sha256':digest(cp),'execution_checklist_sha256':CONFIG['execution_checklist_sha256']});return {'prepared':True,'S1_pointer_supplied':False}
  locator=CONFIG['locator'];cp=CONFIG['checkpoint'];require(locator['scan_start_hash']==cp['cursor'] and locator['artifact_index_sha256']==CONFIG['inventory_sha256'],'live locator/checkpoint binding');db=sqlite3.connect('file:/var/lib/kpi-capture/history.sqlite?mode=ro',uri=True);retained=db.execute('SELECT cursor,digest FROM pages WHERE seq=?',(cp['seq'],)).fetchone();require(retained==(cp['cursor'],cp['digest']) and db.execute('SELECT 1 FROM bodies WHERE txid=?',(locator['s0_txid_hex'],)).fetchone() is None,'checkpoint missing or S0 already observed');db.close();durable(run/'initial.json',{'locator':locator,'checkpoint':cp});append(run,'PREPARED',{'locator_sha256':digest(locator),'checkpoint_sha256':digest(cp),'execution_checklist_sha256':CONFIG['execution_checklist_sha256']});return {'prepared':True,'S1_pointer_supplied':False}
 if op=='status':return {'run_id':CONFIG['run_id'],'mode':CONFIG['mode'],'events':[{'kind':x['kind'],'at':x['at'],'digest':x['digest']} for x in rows],'receipt':accepted_receipt(run) if len(rows)>=2 else None,'latest_probe':LATEST,'faulted':False,'sandbox_inspected':(run/'sandbox.json').exists(),'S1_pointer_supplied':False,'terminal_result':({'status':json.loads((run/'B-result.json').read_text())['status'],'sha256':digest(json.loads((run/'B-result.json').read_text()))} if (run/'B-result.json').exists() else None)}
 if op=='intent':
  require(role=='controller' and len(rows)==1 and not (run/'intent.json').exists(),'one-shot intent already spent/out of order');require(sample()['all_reachable'],'A not reachable before submit');check_intent(run,q['intent']);durable(run/'intent.json',q['intent']);return {'intent_committed':True,'intent_digest':digest(q['intent']),'live_authorized':CONFIG['mode'] in ['live','finite-live-native'] and CONFIG.get('execution_authorized') is True,'S1_pointer_supplied':False}
 if op=='fixture-submit':
  require(role=='controller' and CONFIG['mode'] in ['fixture','rehearsal'] and len(rows)==1 and (run/'intent.json').exists(),'synthetic submit forbidden/duplicate');require(not (run/'submission-claimed.json').exists(),'duplicate synthetic submit');durable(run/'submission-claimed.json',{'at':time.time(),'one_attempt':True});intent=json.loads((run/'intent.json').read_text());tx=normalize_wire(q['transaction']);require(tx['id']==intent['intended_txid'] and recovery.full_hash(tx)==intent['full_hash'],'fixture receipt does not match intended transaction');native_fixture.CONFIG=CONFIG;receipt=native_fixture.accepted_fixture(run,tx)
  if receipt is None:
   require(CONFIG['mode']=='rehearsal' and CONFIG.get('rehearsal_workload'),'unexpected pending acceptance')
   return {'transactionId':tx['id'],'scope':'native synthetic acceptance pending deployed C boundary Job; never public node'}
  require(receipt['range_complete'],'coverage incomplete');append(run,'C_ACCEPTED_DURABLE',receipt|{'intent_digest':digest(intent),'matched_intended_txid_and_full_hash':True});return {'transactionId':tx['id'],'scope':'native synthetic acceptance, never public node'}
 if op=='sandbox':
  require(role=='controller' and len(rows)<=2 and not (run/'sandbox.json').exists(),'sandbox stage/duplicate');p=q['receipt'];require(all(p.get(k) is True for k in ['all_persistent_mounts_read_only','work_is_tmpfs','swap_max_zero','stdout_stderr_null','core_disabled','actual_persistent_write_attempt_EROFS']),'durable S1 path remains');require(p['worker_source_sha256']==CONFIG['worker_source_sha256'],'worker source mismatch');durable(run/'sandbox.json',p);return {'sandbox_retained':True}
 if op=='arm':
  ensure_live_acceptance(run)
  require(role=='B' and len(rows)==2,'only independent B can arm after C acceptance');receipt=q['receipt'];require(receipt==accepted_receipt(run) and -2<=time.time()-receipt['at']<=120,'stale/replayed/mismatched receipt');require(sample()['all_reachable'],'A must still be independently reachable at arm');require((run/'sandbox.json').exists(),'sandbox not inspected');p=json.loads((run/'sandbox.json').read_text());append(run,'A_NO_DURABLE_S1_VERIFIED',p);armed=append(run,'A_LOSS_ARMED',{'acceptance_digest':receipt['acceptance_digest'],'intent_digest':receipt['intent_digest'],'controller':'B-owned restricted credential; decision on C'});return {'armed':True,'arm_digest':armed['digest'],'A_loss_decision_maker':'independent C observer'}
 if op in ['start','guard','fixture-data']:
  ensure_live_acceptance(run)
  require(role=='B' and len(rows)>=5,'B recovery before independently measured loss');require(LATEST is not None and not LATEST['any_reachable'] and not LATEST.get('uncertain',False) and time.time()-LATEST['at']<=5,'A reachable or stale observer');capture_health()
  if op=='start':require(len(rows)==5,'duplicate/replayed B start');x=append(run,'B_RECOVERY_STARTED',{'loss_digest':rows[4]['digest'],'observer_probe_digest':LATEST['digest']});return {'start_digest':x['digest'],'boundary_digest':rows[4]['digest'],'S1_pointer_supplied':False}
  require(len(rows)==6,'B not started')
  if op=='guard':return {'recovery_allowed':True,'run_id':CONFIG['run_id'],'boundary_digest':rows[4]['digest'],'probe_digest':LATEST['digest'],'at':LATEST['at'],'S1_pointer_supplied':False}
  require(CONFIG['mode']=='fixture' and q['name'] in ['locator.json','pages.json','entries.json','current-utxos.json','current-entries.json','source.json'],'fixture data forbidden');return {'data':fixture_data(run,q['name'])}
 raise ValueError('operation forbidden for independent gate')
def tick():
 global LATEST,ABSENT
 run=ROOT/CONFIG['run_id'];run.mkdir(mode=0o700,exist_ok=True);probe=sample();probe['seq']=PROBESEQ[0];PROBESEQ[0]+=1;probe['previous']=PROBEHASH[0];probe['digest']=digest(probe)
 with (run/'probes.jsonl').open('a') as f:f.write(canonical(probe).decode()+'\n');f.flush();os.fsync(f.fileno())
 PROBEHASH[0]=probe['digest'];LATEST=probe;rows=records(run)
 if not rows:return
 if (run/'FAULT.json').exists() or ((run/'B-result.json').exists() and CONFIG['mode']!='finite-live-native'):return
 if time.time()-rows[0]['at']>CONFIG.get('overall_timeout_seconds',5400):fault(run,'Overall autonomous experiment deadline exceeded');return
 ensure_live_acceptance(run)
 if probe.get('uncertain',False):
  ABSENT=[]
  if len(rows)>=4:fault(run,'Independent SSH observer uncertain after arming; fail closed')
  return
 if len(rows)<4:
  if probe['any_reachable']:ABSENT=[]
  else:
   ABSENT.append(probe)
   if len(ABSENT)>=CONFIG['absence_samples']:fault(run,'All A routes lost before independently armed boundary')
  return
 if probe['any_reachable']:
  ABSENT=[]
  if len(rows)>=5:fault(run,'A became reachable during recovery; abort recovery')
  return
 ABSENT.append(probe)
 if len(rows)==4 and len(ABSENT)>=CONFIG['absence_samples']:
  horizon=capture_health();append(run,'A_LOSS_BOUNDARY',{'controller':'independent C nonce/endpoint probes, not an A claim','arm_digest':rows[3]['digest'],'consecutive_absent_samples':len(ABSENT),'first_probe_at':ABSENT[0]['at'],'last_probe_at':probe['at'],'probe_chain_digest':probe['digest'],'healthy_C_horizon_digest':horizon['digest'],'whole_A_scope':'all configured experimental routes unavailable; physical power state not remotely attested','poweroff_mode':CONFIG['poweroff_mode']})
def observe_live():
 global JOB
 if CONFIG['mode']=='finite-live-native':return observe_finite()
 if CONFIG['mode']!='live' and not (CONFIG['mode']=='rehearsal' and CONFIG.get('rehearsal_workload')):return
 run=ROOT/CONFIG['run_id'];rows=records(run)
 if (run/'FAULT.json').exists():
  if JOB is not None:JOB.stop();JOB=None
  return
 if JOB is not None:
  result=JOB.poll()
  if result is None:return
  JOB=None
  require(len(rows)==1,'validation completion stage changed')
  if result.get('not_ready'):
   durable(run/'validation-completed.json',{'not_ready':True})
   fault(run,'Validation trigger did not establish a continuation; requalify rather than replay')
   return
  intent=json.loads((run/'intent.json').read_text())
  require(result['intent_digest']==digest(intent),'validation result intent mismatch')
  # Re-check current acceptance after off-lock validation. No stale worker can release B.
  db=sqlite3.connect('file:'+str(run/'history.sqlite' if CONFIG['mode']=='rehearsal' else pathlib.Path('/var/lib/kpi-capture/history.sqlite'))+'?mode=ro',uri=True)
  try:active=db.execute('SELECT 1 FROM acceptance a JOIN recovery_index_chain c ON c.hash=a.accepting_hash AND c.page_seq=a.page_seq WHERE a.txid=? AND a.full_hash=? LIMIT 1',(intent['intended_txid'],intent['full_hash'])).fetchone()
  finally:db.close()
  require(active is not None,'validation result no longer actively accepted');capture_health()
  receipt=result['receipt'];require(receipt['accepted_continuation_native_Full'] is True and receipt['range_complete'] is True and receipt['state_discovered']=='s1','incomplete validation result')
  append(run,'C_ACCEPTED_DURABLE',receipt|{'intent_digest':digest(intent),'matched_intended_txid_and_full_hash':True})
  durable(run/'validation-completed.json',{'at':time.time(),'acceptance_digest':records(run)[1]['digest']})
  return
 if len(rows)!=1 or not (run/'intent.json').exists():return
 # Indexed read only; expensive range traversal and native validation run in a child.
 initial=json.loads((run/'initial.json').read_text());loc=initial['locator']
 db=sqlite3.connect('file:'+str(run/'history.sqlite' if CONFIG['mode']=='rehearsal' else pathlib.Path('/var/lib/kpi-capture/history.sqlite'))+'?mode=ro',uri=True)
 try:found=db.execute('SELECT 1 FROM spends WHERE previous_txid=? AND previous_index=? LIMIT 1',(loc['s0_txid_hex'],int(loc['s0_index']))).fetchone()
 finally:db.close()
 if not found:return
 require(not (run/'validation-started.json').exists(),'one-shot validation already claimed')
 durable(run/'validation-started.json',{'at':time.time(),'run_id':CONFIG['run_id'],'intent_digest':digest(json.loads((run/'intent.json').read_text()))})
 JOB=Job(run,CONFIG)
def rpc_callback(request):
 method=request['method'];params=request.get('params',{});require(method in ['getServerInfo','getBlockDagInfo','submitTransaction'],'RPC method forbidden')
 if method=='submitTransaction' and CONFIG['mode']=='finite-live-native':
  return finite_submit_continuation(request)
 if method!='submitTransaction':
  require(params=={},'unexpected read parameters');rpc=RPC()
  try:result=rpc.call(method,{})
  finally:rpc.close()
 else:
  require(set(params)=={'transaction','allowOrphan'} and params['allowOrphan'] is False,'submit envelope/orphan policy')
  with LOCK:
   run=ROOT/CONFIG['run_id'];rows=records(run);require(len(rows)==1 and not (run/'FAULT.json').exists(),'submit not authorized/current stage')
   if CONFIG['mode'] in ['fixture','rehearsal']:result=dispatch({'run_id':CONFIG['run_id'],'op':'fixture-submit','authenticated_role':'controller','transaction':params['transaction']})
   else:
    require(CONFIG.get('execution_authorized') is True,'live submission disabled');require((run/'intent.json').exists() and not (run/'submission-claimed.json').exists(),'intent missing or duplicate')
    intent=json.loads((run/'intent.json').read_text());tx=normalize_wire(params['transaction']);require(tx['id']==intent['intended_txid'] and recovery.full_hash(tx)==intent['full_hash'],'body/hash differs from intent')
    initial=json.loads((run/'initial.json').read_text());db=sqlite3.connect('file:/var/lib/kpi-capture/history.sqlite?mode=ro',uri=True);loc=initial['locator'];entry=None
    for blob, in db.execute('SELECT response FROM utxo_observations WHERE page_seq>? ORDER BY seq DESC',(initial['checkpoint']['seq'],)):
     for item in json.loads(zlib.decompress(blob))['entries']:
      if item['outpoint']=={'transactionId':loc['s0_txid_hex'],'index':int(loc['s0_index'])}:entry=item['utxoEntry'];break
     if entry is not None:break
    db.close();require(entry is not None,'independently retained S0 native entry missing');entry=dict(entry);entry['scriptPublicKey']=recovery.rpc_spk(entry['scriptPublicKey']).hex();full=native_fixture.native('validate-body',{'transaction':tx,'entry':entry});require(full['full_valid'] and full['full_hash']==intent['full_hash'] and full['native_masses']==intent['native_masses'] and recovery.rpc_uint(full['fee'])==recovery.rpc_uint(intent['fee']),'C native Full/fee/mass mismatch');capture_health()
    durable(run/'submission-claimed.json',{'at':time.time(),'intent_digest':digest(intent),'one_upstream_call':True});rpc=RPC();rpc.METHODS=set(rpc.METHODS)|{'submitTransaction'}
    try:result=rpc.call('submitTransaction',params)
    finally:rpc.close()
 return {'id':request['id'],'method':method,'params':result}

def observe_finite():
 global JOB
 from finite_runtime import publish,database
 run=ROOT/CONFIG['run_id'];rows=records(run)
 if (run/'FAULT.json').exists():
  if JOB is not None:JOB.stop();JOB=None
  return
 if JOB is not None:
  result=JOB.poll()
  if result is None:return
  verification=JOB.publish_verification;JOB=None;require(len(rows)==1 and not result.get('not_ready'),'finite validation stage/result')
  publish(CONFIG,run,result,verification)
  intent=json.loads((run/'intent.json').read_bytes());receipt=result['receipt']
  append(run,'C_ACCEPTED_DURABLE',receipt|{'intent_digest':digest(intent),'matched_intended_txid_and_full_hash':True})
  durable(run/'validation-completed.json',{'at':time.time(),'acceptance_digest':records(run)[1]['digest']});return
 if len(rows)!=1 or not (run/'intent.json').exists() or not (run/'CAPTURE-STOP.json').exists():return
 require(not (run/'CAPTURE-FAULT.json').exists() and not (run/'validation-started.json').exists(),'faulted/replayed finite validation')
 durable(run/'validation-started.json',{'at':time.time(),'run_id':CONFIG['run_id'],'intent_digest':digest(json.loads((run/'intent.json').read_bytes()))})
 JOB=Job(run,CONFIG)

def safe_rpc_failure(exception, stage='rpc-callback'):
 # Never persist exception text/traceback, request, body, proof or locals.
 # Stage labels are source constants, not derived from RPC input.
 kind=type(exception).__name__
 if kind not in {'ValueError','TypeError','KeyError','FileNotFoundError','PermissionError','TimeoutError','CalledProcessError','OSError'}:kind='OtherException'
 errors.emit('rpc-callback-rejected',{'rpc_stage':stage,'exception_type':kind,'code':'RPC_REJECTED_NO_RETRY'})

def finite_submit_continuation(request):
 stage=['entry']
 try:return _finite_submit_continuation(request,stage)
 except Exception as exception:
  safe_rpc_failure(exception,stage[0]);raise

def _finite_submit_continuation(request, stage):
 from finite_runtime import current,database
 stage[0]='envelope'
 params=request.get('params',{});require(set(params)=={'transaction','allowOrphan'} and params['allowOrphan'] is False,'finite submit envelope')
 with LOCK:
  stage[0]='authorization'
  run=ROOT/CONFIG['run_id'];require(CONFIG.get('execution_authorized') is True and len(records(run))==1 and not (run/'FAULT.json').exists(),'finite continuation unauthorized/stage')
  stage[0]='intent-once'
  require((run/'intent.json').exists() and not (run/'submission-claimed.json').exists(),'finite duplicate continuation')
  stage[0]='normalize-wire'
  intent=json.loads((run/'intent.json').read_bytes());tx=normalize_wire(params['transaction']);stage[0]='intent-body-binding';require(tx['id']==intent['intended_txid'] and recovery.full_hash(tx)==intent['full_hash'],'finite continuation body differs from intent')
  stage[0]='current-native-observation'
  initial=json.loads((run/'initial.json').read_bytes());loc=initial['locator'];observed=current(CONFIG,run)
  from finite_runtime import funding_ready
  stage[0]='funding-ready'
  require(funding_ready(CONFIG)['funding_native_entry_retained'],'funding wait gate not ready')
  stage[0]='current-S0-entry'
  exact=[e for e in observed['utxos']['entries'] if e['outpoint']=={'transactionId':loc['s0_txid_hex'],'index':int(loc['s0_index'])}];require(len(exact)==1,'finite S0 current entry missing')
  db=sqlite3.connect(str(database(CONFIG)))
  from recovery_index import ensure_current
  stage[0]='durable-funding-index'
  commit=ensure_current(db)
  require(commit['seq']>initial['checkpoint']['seq'] and db.execute('select 1 from acceptance a join recovery_index_chain c on c.hash=a.accepting_hash and c.page_seq=a.page_seq where a.txid=?',(loc['s0_txid_hex'],)).fetchone(),'funding body not independently captured')
  entry=exact[0]['utxoEntry'];native_entry=dict(entry);native_entry['scriptPublicKey']=recovery.rpc_spk(entry['scriptPublicKey']).hex()
  stage[0]='native-Full'
  full=native_fixture.native('validate-body',{'transaction':tx,'entry':native_entry});stage[0]='native-Full-binding';require(full['full_valid'] and full['full_hash']==intent['full_hash'] and full['native_masses']==intent['native_masses'] and recovery.rpc_uint(full['fee'])==recovery.rpc_uint(intent['fee']),'finite native Full/fee/mass mismatch')
  stage[0]='durable-UTXO-observation'
  raw=canonical(observed['utxos']);db.execute('insert into utxo_observations(page_seq,at,horizon,addresses_sha,response_sha,response) values(?,?,?,?,?,?)',(commit['seq'],observed['observation_at'],commit['cursor'],digest(CONFIG['finite']['watch_addresses']),hashlib.sha256(raw).hexdigest(),zlib.compress(raw)));db.commit();db.close()
  stage[0]='A-reachability-and-capture-health'
  require(sample()['all_reachable'],'A lost before finite continuation submit');capture_health()
  stage[0]='submission-claim'
  durable(run/'submission-claimed.json',{'at':time.time(),'intent_digest':digest(intent),'one_upstream_call':True})
  rpc=RPC();rpc.METHODS=set(rpc.METHODS)|{'submitTransaction'}
  stage[0]='upstream-submit'
  try:result=rpc.call('submitTransaction',params)
  finally:rpc.close()
 return {'id':request['id'],'method':request['method'],'params':result}

def observer_loop():
 while True:
  try:
   with LOCK:tick();observe_live()
  except Exception as e:
   with LOCK:
    errors.capture(e);fault(ROOT/CONFIG['run_id'],'independent observer failure: '+type(e).__name__)
  time.sleep(2)
if __name__=='__main__':
 CONFIG=json.loads(pathlib.Path('/etc/kpi-g5-independent.json').read_text());
 if CONFIG['mode']=='finite-live-native':
  from finite_runtime import settings
  settings(CONFIG);ROOT=pathlib.Path(CONFIG['finite']['root']);native_fixture.BINARY=CONFIG['finite']['native']['path'];native_fixture.REF=CONFIG['finite']['reference']['path']
 if CONFIG['mode']=='rehearsal':
  from live_schema_rehearsal import require_rehearsal
  require_rehearsal(CONFIG)
 require(hashlib.sha256(pathlib.Path(CONFIG['manifest']).read_bytes()).hexdigest()==CONFIG['manifest_sha256'],'frozen manifest changed');native_fixture.CONFIG=CONFIG;ROOT.mkdir(mode=0o750,exist_ok=True);run=ROOT/CONFIG['run_id'];run.mkdir(mode=0o700,exist_ok=True);LATEST=None;ABSENT=[];PROBESEQ=[0];PROBEHASH=['0'*64]
 # Recovered probe journal must be validated; a controller restart never inherits absent samples.
 if (run/'probes.jsonl').exists():
  for line in (run/'probes.jsonl').read_text().splitlines():
   p=json.loads(line);h=p.pop('digest');require(p['seq']==PROBESEQ[0] and p['previous']==PROBEHASH[0] and digest(p)==h,'probe journal corrupt');PROBEHASH[0]=h;PROBESEQ[0]+=1
 errors.initialize(run/'errors');errors.stage('C-independent-control');reject_restarted_active_boundary(run)
 if pathlib.Path(SOCKET).exists():pathlib.Path(SOCKET).unlink()
 server=socket.socket(socket.AF_UNIX);server.bind(SOCKET);os.chmod(SOCKET,0o660);server.listen(8);threading.Thread(target=observer_loop,daemon=True).start()
 from ws_fixture import Server,Handler
 proxy=Server(('127.0.0.1',19410),Handler);proxy.callback=rpc_callback;proxy.failure_callback=safe_rpc_failure;proxy.requests=__import__('collections').deque(maxlen=1);threading.Thread(target=proxy.serve_forever,daemon=True).start()
 while True:
  conn,_=server.accept()
  try:
   _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12));require(uid in [0,CONFIG['gateway_uid']],'unexpected local peer');conn.settimeout(120)
   with conn.makefile('rb') as f:raw=f.readline(32769)
   require(len(raw)<=32768 and raw.endswith(b'\n'),'bounded request required');q=json.loads(raw);require(uid==0 or q['authenticated_role']!='admin','admin role forbidden')
   if CONFIG['mode']=='finite-live-native' and q.get('op') in ['terminal-submit','terminal-observe','terminal-status']:result=dispatch(q)
   else:
    with LOCK:result=dispatch(q)
  except Exception as e:
   errors.capture(e);result={'error':type(e).__name__+': '+str(e)}
  try:conn.sendall(canonical(result)+b'\n')
  except (BrokenPipeError,ConnectionResetError,TimeoutError):pass
  finally:conn.close()
