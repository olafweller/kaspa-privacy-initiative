"""Shared ordering gates; fixture acceptance uses isolated native TestConsensus.

No public-node transaction submission. Live acceptance callback only reads the
independent archive. Root/OS observation trust remains explicit.
"""
import json,os,time,socket,struct,hashlib,pathlib,subprocess,threading,uuid
from capture import canonical
from recovery_index import Archive
from boundary_watch import validate_boundary
import a1_recovery as r
import recovery_errors as errors
import fixture_provenance as fp
ROOT=pathlib.Path('/var/lib/kpi-capture/boundary-v2');SOCKET='/run/kpi-g5-boundary/control.sock';BINARY='/opt/kpi-g5-capture/kpi-poc-a1';REF='/opt/kpi-g5-capture/a1_reference'
def require(x,m):
 if not x:raise ValueError(m)
def durable(path,data):
 data=canonical(data);fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 d=os.open(path.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
def native(action,value):
 import tempfile
 with tempfile.TemporaryDirectory() as temp:
  request=pathlib.Path(temp)/'request.json';request.write_bytes(canonical(value))
  binary=BINARY
  if action=='native-path':
   require(CONFIG['mode'] in ['fixture','rehearsal'],'fixture adapter disabled for live')
   binary=CONFIG['fixture_header_adapter']
   require(pathlib.Path(binary).is_file() and not pathlib.Path(binary).is_symlink() and hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest()==CONFIG['fixture_header_adapter_sha256'],'fixture adapter pin mismatch')
  result=errors.command([binary,action,str(request)],timeout=120)
  if action=='native-path':result['fixture_provenance']=fp.bind(result,value,CONFIG['fixture_header_adapter_sha256'],CONFIG['fixture_header_source_patch_sha256'])
  return result
def events(run):
 p=run/'events.jsonl';return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def event(run,kind,payload):
 previous=events(run);record={'seq':len(previous),'kind':kind,'at':time.time(),'previous':previous[-1]['digest'] if previous else '0'*64,'scope':'unfunded-native-rehearsal' if CONFIG['mode'] in ['fixture','rehearsal'] else 'separately-authorized-live-archive-observation','payload':payload};record['digest']=hashlib.sha256(canonical(record)).hexdigest()
 with (run/'events.jsonl').open('a') as f:f.write(canonical(record).decode()+'\n');f.flush();os.fsync(f.fileno())
 d=os.open(run,os.O_DIRECTORY);os.fsync(d);os.close(d);return record
ORDER=['PREPARED','C_ACCEPTED_DURABLE','A_NO_DURABLE_S1_VERIFIED','A_LOSS_ARMED','A_LOSS_BOUNDARY','B_RECOVERY_STARTED']
def verify_chain(records):
 prev='0'*64
 for i,source in enumerate(records):
  record=dict(source);digest=record.pop('digest');require(record['seq']==i and record['kind']==ORDER[i] and record['previous']==prev and hashlib.sha256(canonical(record)).hexdigest()==digest,'corrupt/out-of-order controller journal');prev=digest
 return prev
def page(tx,accepting,start,item):
 require(item['transaction']==tx and item['accepting_block']==accepting,'fixture page body/header binding mismatch');accepting_header=fp.header(item)
 t=json.loads(json.dumps(tx));t['storageMass']=str(t.pop('mass'));t['verboseData']={'transactionId':t.pop('id'),'hash':r.full_hash(t)}
 return {'startHash':start,'response':{'removedChainBlockHashes':[],'addedChainBlockHashes':[accepting],'chainBlockAcceptedTransactions':[{'chainBlockHeader':accepting_header,'acceptedTransactions':[t]}]}}
def create_fixture(run):
 require(CONFIG['mode'] in ['fixture','rehearsal'],'fixture operation disabled for live run');manifest=json.loads(pathlib.Path(CONFIG['manifest']).read_text());state=manifest['states']['s0'];seed={'amount':int(state['R'])+1000000,'scriptPublicKey':'000051','blockDaaScore':0,'isCoinbase':False,'covenantId':None};outpoint={'transactionId':os.urandom(32).hex(),'index':7}
 tx={'version':1,'id':'00'*32,'inputs':[{'previousOutpoint':outpoint,'signatureScript':'','sequence':str(2**64-1),'sigOpCount':0,'computeBudget':1}],'outputs':[{'value':state['R'],'scriptPublicKey':state['spk_hex'],'covenant':None}],'lockTime':'0','subnetworkId':'00'*20,'gas':'0','payload':'','storageMass':'0'}
 prepared=native('prepare-body',{'transaction':tx,'entry':seed});checkpoint=native('native-checkpoint',{'initial_outpoint':outpoint,'initial_entry':seed});accepted=native('native-path',{'transactions':[prepared['transaction']],'initial_entry':seed});require(accepted['synthetic_genesis_hash']==checkpoint['synthetic_genesis_hash'],'native seed/checkpoint mismatch')
 first=accepted['accepted_path'][0];p=page(first['transaction'],first['accepting_block'],checkpoint['synthetic_genesis_hash'],first);workload=CONFIG.get('rehearsal_workload')
 if workload:
  from live_schema_rehearsal import initialize_workload_archive
  archive=initialize_workload_archive(CONFIG,run);p['startHash']=archive.meta('cursor')
 else:
  archive=Archive(run/'history.sqlite');archive.initialize({'hash':checkpoint['synthetic_genesis_hash']},{'scope':'isolated TestConsensus fixture, not live node'})
 archive.commit(p['startHash'],p['response'],first['accepting_block']);archive.db.close()
 point=prepared['transaction']['id'];entry={'amount':int(state['R']),'scriptPublicKey':state['spk_hex'],'blockDaaScore':0,'isCoinbase':False,'covenantId':None}
 # Exact authenticated entry comes from C's native current state, never synthesized.
 actual=[e for op,e in accepted['current_virtual_utxos'] if op['transactionId']==point and op['index']==0];require(len(actual)==1,'native S0 missing');entry=actual[0]
 locator={'network':'testnet-10','genesis_hex':manifest['genesis_hex'],'instance_hex':manifest['instance_hex'],'s0_txid_hex':point,'s0_index':'0','s0_amount':state['R'],'s0_spk_hex':state['spk_hex'],'s0_covenant':None,'scan_start_hash':checkpoint['synthetic_genesis_hash'],'scan_start_blue_score':'0','scan_start_daa_score':'0','artifact_index_sha256':CONFIG['inventory_sha256']}
 native_checkpoint=checkpoint
 if CONFIG['mode']=='rehearsal':
  from live_schema_rehearsal import checkpoint_metadata
  checkpoint=checkpoint_metadata(CONFIG,native_checkpoint)
 if workload:
  locator.update(scan_start_hash=checkpoint['cursor'],scan_start_blue_score=checkpoint['blue_score'],scan_start_daa_score=checkpoint['daa_score'])
 durable(run/'initial.json',{'prepared':prepared,'checkpoint':checkpoint,'native_checkpoint':native_checkpoint,'locator':locator,'S0_entry':entry,'fixture_provenance':accepted['fixture_provenance']});event(run,'PREPARED',{'native_checkpoint_sha256':hashlib.sha256(canonical(checkpoint)).hexdigest(),'S0_locator_sha256':hashlib.sha256(canonical(locator)).hexdigest(),'fixture_no_public_TN10':True});return {'locator':locator,'entry':entry,'scope':'old S0 only; native synthetic seed, no future TN10 funding'}
def accepted_fixture(run,tx):
 initial=json.loads((run/'initial.json').read_text());accepted=native('native-path',{'transactions':[initial['prepared']['transaction'],tx],'initial_entry':initial['prepared']['entry']});require(accepted['synthetic_genesis_hash']==initial.get('native_checkpoint',initial['checkpoint'])['synthetic_genesis_hash'],'native checkpoint changed');fp.stable_prefix(initial['fixture_provenance'],accepted['fixture_provenance'],CONFIG['fixture_header_adapter_sha256'],CONFIG['fixture_header_source_patch_sha256']);paths=accepted['accepted_path'];require(len(paths)==2,'accepted path incomplete');p=page(paths[1]['transaction'],paths[1]['accepting_block'],paths[0]['accepting_block'],paths[1]);a=Archive(run/'history.sqlite');a.commit(p['startHash'],p['response'],paths[1]['accepting_block']);a.db.close()
 entries={}
 for item in paths:
  inp=item['transaction']['inputs'][0]['previousOutpoint'];entries[inp['transactionId']+':'+str(inp['index'])]=item['input_entry']
 if CONFIG.get('rehearsal_workload'):
  durable(run/'accepted-native.json',accepted);durable(run/'historical-entries.json',entries)
  return None  # Same deployed asynchronous C Job performs full range validation.
 m=json.loads(pathlib.Path(CONFIG['manifest']).read_text());receipt=validate_boundary(run/'history.sqlite',m,initial['locator'],{'seq':0,'cursor':initial.get('native_checkpoint',initial['checkpoint'])['synthetic_genesis_hash'],'digest':'0'*64},CONFIG['inventory_sha256'],entries,BINARY,REF)
 durable(run/'accepted-native.json',accepted);durable(run/'historical-entries.json',entries);durable(run/'accepted-boundary.json',receipt);return receipt

def dispatch(request):
 require(request.get('run_id')==CONFIG['run_id'],'wrong run id');run=ROOT/CONFIG['run_id'];run.mkdir(mode=0o700,exist_ok=True);records=events(run);verify_chain(records);op=request['op'];role=request['authenticated_role']
 if op=='prepare':
  require(role=='admin' and not records,'prepare already happened/not admin')
  if CONFIG['mode']=='fixture':return create_fixture(run)
  require(CONFIG.get('execution_authorized') is True and len(CONFIG.get('immutable_checklist_sha256',''))==64,'separate live authorization required')
  locator=CONFIG['locator'];checkpoint=CONFIG['checkpoint'];require(locator['artifact_index_sha256']==CONFIG['inventory_sha256'] and locator['scan_start_hash']==checkpoint['cursor'],'pre-positioned locator/checkpoint mismatch')
  db=__import__('sqlite3').connect('file:/var/lib/kpi-capture/history.sqlite?mode=ro',uri=True);row=db.execute('SELECT cursor,digest FROM pages WHERE seq=?',(checkpoint['seq'],)).fetchone();require(row is not None and row==(checkpoint['cursor'],checkpoint['digest']),'unretained pre-funding checkpoint');require(db.execute('SELECT 1 FROM bodies WHERE txid=?',(locator['s0_txid_hex'],)).fetchone() is None,'S0 already observed before pre-funding marker');db.close();durable(run/'initial.json',{'locator':locator,'checkpoint':checkpoint});event(run,'PREPARED',{'immutable_checklist_sha256':CONFIG['immutable_checklist_sha256'],'S0_locator_sha256':hashlib.sha256(canonical(locator)).hexdigest()});return {'prepared':True,'S1_pointer_supplied':False}
 if op=='observe':
  require(role=='controller' and len(records)==1 and CONFIG['mode']=='live','live acceptance watcher stage invalid');initial=json.loads((run/'initial.json').read_text());db=__import__('sqlite3').connect('file:/var/lib/kpi-capture/history.sqlite?mode=ro',uri=True);entries={}
  import zlib
  for blob, in db.execute('SELECT response FROM utxo_observations WHERE page_seq>?',(initial['checkpoint']['seq'],)):
   for item in json.loads(zlib.decompress(blob))['entries']:
    point=item['outpoint'];key=point['transactionId']+':'+str(point['index']);entry=item['utxoEntry'];require(key not in entries or entries[key]==entry,'contradictory historical native entry');entries[key]=entry
  db.close();manifest=json.loads(pathlib.Path(CONFIG['manifest']).read_text());receipt=validate_boundary('/var/lib/kpi-capture/history.sqlite',manifest,initial['locator'],initial['checkpoint'],CONFIG['inventory_sha256'],entries,BINARY,REF);record=event(run,'C_ACCEPTED_DURABLE',receipt);return {'accepted_continuation_native_Full':True,'range_complete':True,'boundary_digest':record['digest'],'S1_pointer_supplied':False,'at':record['at']}
 if op=='status':return {'events':[{'kind':x['kind'],'digest':x['digest'],'at':x['at']} for x in records],'mode':CONFIG['mode'],'S1_pointer_supplied':False}
 if op=='submit':
  require(role=='controller' and len(records)==1,'continuation submission out of order');require(CONFIG['mode']=='fixture','no public broadcaster; live uses independent archive watcher');receipt=accepted_fixture(run,request['transaction']);record=event(run,'C_ACCEPTED_DURABLE',receipt);return {'accepted_continuation_native_Full':True,'range_complete':True,'boundary_digest':record['digest'],'S1_pointer_supplied':False,'at':record['at']}
 if op=='sandbox':
  require(role=='controller' and len(records)==2,'sandbox observation before acceptance/wrong stage');receipt=request['receipt'];require(receipt['all_persistent_mounts_read_only'] and receipt['work_is_tmpfs'] and receipt['swap_max_zero'] and receipt['stdout_stderr_null'] and receipt['core_disabled'],'A durable write path remains');require(receipt['worker_source_sha256']==CONFIG['worker_source_sha256'],'unreviewed worker');record=event(run,'A_NO_DURABLE_S1_VERIFIED',receipt);return {'sandbox_receipt_digest':record['digest'],'S1_pointer_supplied':False}
 if op=='arm':
  require(role=='controller' and len(records)==3,'loss action cannot arm before acceptance/sandbox observation');record=event(run,'A_LOSS_ARMED',{'accepted_digest':records[1]['digest'],'sandbox_digest':records[2]['digest']});return {'armed':True,'arm_digest':record['digest'],'mode':CONFIG['mode'],'S1_pointer_supplied':False}
 if op=='loss':
  require(role=='controller' and len(records)==4 and request['arm_digest']==records[3]['digest'],'unarmed/incorrect loss boundary');require(request['worker_inactive'] is True,'original worker still available');if_live = CONFIG['mode']!='fixture'
  if if_live:
   witness_path=CONFIG.get('independent_loss_witness_path');require(isinstance(witness_path,str),'independent live loss witness not configured')
   path=pathlib.Path(witness_path);require(path.is_file() and not path.is_symlink() and path.stat().st_uid==0 and path.stat().st_mode & 0o022==0,'loss witness must be independently root-owned and immutable to controller')
   witness=json.loads(path.read_text());require(witness.get('run_id')==CONFIG['run_id'] and witness.get('arm_digest')==records[3]['digest'] and witness.get('whole_A_unreachable') is True and witness.get('observed_at',0)>records[3]['at'],'independent loss witness invalid')
  record=event(run,'A_LOSS_BOUNDARY',{'arm_digest':records[3]['digest'],'worker_inactive':True,'whole_A_unreachable':True if if_live else False,'independent_witness_sha256':hashlib.sha256(path.read_bytes()).hexdigest() if if_live else None,'scope':'harmless simulated loss' if CONFIG['mode']=='fixture' else 'external whole-A isolation observation'});return {'loss_digest':record['digest'],'recovery_allowed':True}
 if op in ['start','fixture-data']:
  require(role=='B' and len(records)>=5,'B recovery forbidden before accepted/armed loss boundary')
  if op=='start':
   require(len(records)==5,'duplicate recovery start');record=event(run,'B_RECOVERY_STARTED',{'loss_digest':records[4]['digest'],'authentication':'dedicated restricted B SSH credential'});return {'start_digest':record['digest'],'boundary_digest':records[4]['digest'],'S1_pointer_supplied':False}
  require(len(records)==6 and CONFIG['mode']=='fixture','fixture unavailable/no authenticated B start');require(request['name'] in ['locator.json','pages.json','entries.json','current-utxos.json','current-entries.json','source.json'],'fixture name forbidden');initial=json.loads((run/'initial.json').read_text());accepted=json.loads((run/'accepted-native.json').read_text());accepted=fp.stored(accepted,initial,CONFIG['fixture_header_adapter_sha256'],CONFIG['fixture_header_source_patch_sha256']);paths=accepted['accepted_path'];pages=[];cursor=initial.get('native_checkpoint',initial['checkpoint'])['synthetic_genesis_hash']
  for item in paths:
   pages.append(page(item['transaction'],item['accepting_block'],cursor,item));cursor=item['accepting_block']
  entries=json.loads((run/'historical-entries.json').read_text());require(entries==fp.entries(accepted),'stored fixture input entries changed');current=[];current_entries={}
  for point,entry in accepted['current_virtual_utxos']:
   current.append({'transaction_id':point['transactionId'],'index':str(point['index']),'value':str(entry['amount']),'spk_hex':entry['scriptPublicKey'],'covenant':entry['covenantId']});current_entries[point['transactionId']+':'+str(point['index'])]=entry
  values={'locator.json':initial['locator'],'pages.json':pages,'entries.json':entries,'current-utxos.json':current,'current-entries.json':current_entries,'source.json':{'horizon':cursor,'scope':'C independently accepted synthetic native fixture; not public TN10'}};return {'data':values[request['name']]}
 raise ValueError('boundary operation forbidden')
if __name__=='__main__':
 CONFIG=json.loads(pathlib.Path('/etc/kpi-g5-boundary.json').read_text());require(hashlib.sha256(pathlib.Path(CONFIG['manifest']).read_bytes()).hexdigest()==CONFIG['manifest_sha256'],'frozen manifest changed');ROOT.mkdir(mode=0o750,exist_ok=True);p=pathlib.Path(SOCKET)
 if p.exists():p.unlink()
 s=socket.socket(socket.AF_UNIX);s.bind(SOCKET);os.chmod(SOCKET,0o660);s.listen(4)
 while True:
  conn,_=s.accept()
  try:
   _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12));require(uid in [0,CONFIG['gateway_uid']],'unexpected local peer');conn.settimeout(120);f=conn.makefile('rb');raw=f.readline(32769);require(len(raw)<=32768 and raw.endswith(b'\n'),'boundary request too large');request=json.loads(raw);require(uid==0 or request['authenticated_role']!='admin','admin role forbidden');result=dispatch(request)
  except Exception as e:result={'error':type(e).__name__+': '+str(e)}
  conn.sendall(canonical(result)+b'\n');conn.close()
