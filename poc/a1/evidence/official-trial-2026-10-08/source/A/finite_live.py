"""Concrete future live CLI: prepare -> one funding -> volatile continuation.
Requires later externally hash-bound exact user authority, installed bindings,
checklist and fixed terms. Never powers off A. No action runs at import.
"""
import argparse,copy,hashlib,json,os,pathlib,secrets,subprocess,time
import finite_launch as startup
from launcher_common import E,BASE,NODE,SDK,read,sha,durable,clean_env,remote
import controller_access as ca
from fixed_terms import u64
HERE=pathlib.Path(__file__).resolve().parent

def require(v,m):
 if not v:raise ValueError(m)
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def child(name,timeout):
 allowed={'plan_funding_live.mjs','review_funding_live.mjs','submit_funding_ready.mjs','start_worker.py','qualify_sandbox.py','confirm_S0.py'}
 require(name in allowed,'fixed executable phase only');exe=str(NODE) if name.endswith('.mjs') else '/usr/bin/python3';v=subprocess.run([exe,str(HERE/name)],env=clean_env(),capture_output=True,timeout=timeout);require(v.returncode==0,'phase halted: '+name);return v.stdout

def remote_put(role,path,value,mode=0o600,gid=None):
 raw=value if type(value) is bytes else encode(value)
 code='PATH='+repr(path)+'\nRAW='+repr(raw)+'\nMODE='+repr(mode)+'\nGID='+repr(gid)+'\n'+r'''
import pathlib,os,json,hashlib
p=pathlib.Path(PATH);assert p.is_absolute() and '..' not in p.parts and not p.is_symlink() and p.parent.is_dir()
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,MODE)
if GID is not None:os.fchown(fd,0,GID)
os.fchmod(fd,MODE)
with os.fdopen(fd,'wb') as f:f.write(RAW);f.flush();os.fsync(f.fileno())
fd=os.open(p.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd);print(json.dumps({'sha256':hashlib.sha256(RAW).hexdigest()}))
'''
 result=json.loads(remote.run(role,code,30));require(result['sha256']==hashlib.sha256(raw).hexdigest(),'exact retained remote bytes')

def activation(role,m,cfg,a,check,b):
 host='@C_SSH_HOST@' if role=='C' else '@B_SSH_HOST@';admin=b['live'][role]
 for name,value in [('config.json',cfg),('activation-manifest.json',m),('authority.json',a),('checklist.json',check)]:remote_put(host,admin['state_root']+'/'+name,value,mode=0o640 if name=='config.json' else 0o600,gid=(986 if role=='C' else 988) if name=='config.json' else None)
 paths={n:admin['state_root']+'/'+n+'.json' for n in ['config','authority','checklist']};paths['manifest']=admin['state_root']+'/activation-manifest.json'
 args=[]
 for n,v in [('manifest',m),('config',cfg),('authority',a),('checklist',check)]:args+=['--'+n,paths[n],'--'+n+'-sha256',hashlib.sha256(encode(v)).hexdigest()]
 code='P='+repr(admin['activation_helper'])+'\nPIN='+repr(admin['activation_helper_sha256'])+'\nSUPPORT='+repr(admin['activation_support_pins'])+'\nARGS='+repr(args)+'\n'+r'''
import pathlib,hashlib,subprocess,json
p=pathlib.Path(P);assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==PIN
for name,pin in SUPPORT.items():
 child=p.parent/name;assert child.is_file() and not child.is_symlink() and child.stat().st_uid==0 and not child.stat().st_mode&0o022 and hashlib.sha256(child.read_bytes()).hexdigest()==pin
v=subprocess.run(['/usr/bin/python3',P,*ARGS],capture_output=True,timeout=500)
for name,raw in [('activation.stdout',v.stdout),('activation.stderr',v.stderr)]:
 fd=__import__('os').open(pathlib.Path(ARGS[ARGS.index('--config')+1]).parent/name,__import__('os').O_WRONLY|__import__('os').O_CREAT|__import__('os').O_EXCL|__import__('os').O_NOFOLLOW,0o600)
 with __import__('os').fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();__import__('os').fsync(stream.fileno())
assert v.returncode==0,'finite role activation halted; exact private output retained';print(v.stdout.decode())
'''
 return json.loads(remote.run(host,code,510))

def prepare(cfg,b,a,check,ownership=None):
 # Reject every host AF_UNIX route before the one-run claim or remote mutation.
 from finite_install import unix_path
 unix_path(b['C']['socket_root']+'/control.sock')
 unix_path(b['live']['C']['activation_manifest']['socket_root']+'/control.sock')
 unix_path(ca.worker_channel(cfg['run_id'])['intent_socket'])
 # Fresh E is the durable one-run claim; an interrupted run is never resumed.
 E.mkdir(mode=0o700,exist_ok=False)
 if ownership is not None:ownership['claimed']=True
 durable(E/'owner-live-authorization.json',a);durable(E/'installed-runtime-binding.json',b);durable(E/'frozen-live-checklist.json',check);durable(E/'fixed-terms.json',check['fixed_terms'])
 require(sha(E/'fixed-terms.json')==check['fixed_terms_sha256'],'frozen extracted terms bytes')
 ready=startup.startup(cfg,b);durable(E/'startup-receipt.json',ready)
 from endpoint_readiness import check as endpoint
 ep=endpoint(cfg['run_id'],b);durable(E/'endpoint-before-fee.json',ep)
 from fee_refresh import run as fee
 fee(E/'installed-runtime-binding.json',sha(E/'installed-runtime-binding.json'));report=read(HERE/'fresh-fee-mechanism-report.json');require(report['passed'] and report['run_id']==cfg['run_id'],'one fresh fixed-fee preflight');durable(E/'latest-fee-mechanism-report.json',report)
 location=read(HERE/'live-candidate-run-location.private.json');durable(E/'run-location.private.json',location);public=pathlib.Path(location['path'])/'public';manifest=read(public/'manifest.json');require(sha(public/'manifest.json')==cfg['manifest_sha256']==check['manifest_sha256'],'actual exact native BASE')
 # Existing wallet, read-only C node context and fixed one-input SDK construction.
 env={}
 import re
 wallet_env=BASE.parent.parent/'.env.tn10.local';require(wallet_env.stat().st_mode&0o777==0o600,'wallet context private file')
 for line in wallet_env.read_text().splitlines():
  found=re.match(r'^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$',line)
  if found:env[found[1]]=found[2].strip('"\'')
 require(env['KASPA_NETWORK']=='tn10','test KAS only')
 installed=b['C'];code='INSTALLED='+repr(installed)+'\nADDRESS='+repr(env['KPI_FUNDING_ADDRESS'])+'\n'+r'''
import sys,pathlib,json,hashlib
root=pathlib.Path(INSTALLED['source_root'])
for n,h in INSTALLED['source_pins'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h
raw=pathlib.Path(INSTALLED['config_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==INSTALLED['config_sha256'];cfg=json.loads(raw);sys.path.insert(0,str(root));from finite_runtime import settings,node_binding;settings(cfg);node_binding(cfg);from rpc_local import RPC
r=RPC();r.METHODS=set(r.METHODS)|{'getFeeEstimate'}
try:v={'server':r.call('getServerInfo',{}),'dag':r.call('getBlockDagInfo',{}),'utxos':r.call('getUtxosByAddresses',{'addresses':[ADDRESS]}),'fees':r.call('getFeeEstimate',{})};assert v['server']['networkId']=='testnet-10' and v['server']['isSynced'] and len(v['utxos']['entries'])<=32
finally:r.close()
print(json.dumps(v))
'''
 wallet=json.loads(remote.run('@C_SSH_HOST@',code,30));durable(E/'wallet-context-refreshed.json',wallet);child('plan_funding_live.mjs',120);request=read(E/'funding-full-request.json');tx=read(E/'funding-transaction.json');entry=request['entry']
 durable(E/'funding-generic-context.json',{'entries':[{'amount':u64(entry['amount']),'blockDaaScore':int(entry['blockDaaScore']),'covenantId':None,'isCoinbase':False,'outpoint':tx['inputs'][0]['previousOutpoint'],'scriptPublicKeyHex':entry['scriptPublicKey']}],'virtualDaaScore':int(wallet['dag']['virtualDaaScore']),'pastMedianTime':int(wallet['dag']['pastMedianTime'])});child('review_funding_live.mjs',120);review=read(E/'funding-review.json')
 live=copy.deepcopy(b['C']['config']);live.update(run_id=cfg['run_id'],base_instance_id=cfg['base_instance_id'],execution_authorized=True,terminal_execution_authorized=True,funding_authorized=True,poweroff_authorized=False,checkpoint={},locator={},authorized_clean_run_id=b['standby_run_id'],execution_checklist_sha256=a['checklist_sha256'])
 admin=b['live']['C'];live['finite']['root']=admin['state_root']+'/finite-runs';live['terminal_policy'].update(run_id=live['run_id'],execution_checklist_sha256=a['checklist_sha256']);live['terminal_policy']['fee_sompi']=manifest['branches']['s1_terminal']['fee'];live['terminal_policy']['exact_payout']=u64(manifest['branches']['s1_terminal']['outputs'][0]['value'])
 # Independently fixed planned-run paths are supplied by inspected role manifests.
 for role in ['C','B']:
  root=b['live'][role]['state_root'];code='ROOT='+repr(root)+'\n'+r'''
import pathlib,os
p=pathlib.Path(ROOT);assert p.is_absolute() and not p.exists() and not p.is_symlink();parent=p.parent;gid=986 if ROLE=='C' else 988
assert str(parent)==('/opt/kpi-finite-live' if ROLE=='C' else '/srv/kpi-recovery/finite-live') and not parent.is_symlink()
if not parent.exists():parent.mkdir(mode=0o750);os.chown(parent,0,gid);os.chmod(parent,0o750)
assert parent.is_dir() and parent.stat().st_uid==0 and parent.stat().st_gid==gid and parent.stat().st_mode&0o777==0o750
p.mkdir(mode=0o750);os.chown(p,0,gid);os.chmod(p,0o750)
'''.replace('ROLE',repr(role));remote.run('@C_SSH_HOST@' if role=='C' else '@B_SSH_HOST@',code,15)
 draft=admin['state_root']+'/prefunding-draft.json';remote_put('@C_SSH_HOST@',draft,live)
 code='ROOT='+repr(b['C']['source_root'])+'\nCONFIG='+repr(draft)+'\nPIN='+repr(hashlib.sha256(encode(live)).hexdigest())+'\n'+r'''
import sys,pathlib,json,hashlib
raw=pathlib.Path(CONFIG).read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN;cfg=json.loads(raw);sys.path.insert(0,ROOT);from finite_capture import select_recent_anchor,prefunding;from rpc_local import RPC
r=RPC()
try:anchor=select_recent_anchor(r,80)
finally:r.close()
cfg['finite']['origin_hash']=anchor['hash'];cp=prefunding(cfg);run=pathlib.Path(cfg['finite']['root'])/cfg['run_id'];print(json.dumps({'config':cfg,'checkpoint':cp,'anchor':anchor,'prefund_sha256':hashlib.sha256((run/'PREFUND.json').read_bytes()).hexdigest(),'prefund_seal_sha256':hashlib.sha256((run/'PREFUND-SEAL.json').read_bytes()).hexdigest()}))
'''
 capture_script=admin['state_root']+'/prefund-capture.py';remote_put('@C_SSH_HOST@',capture_script,code.encode())
 bounded='SCRIPT='+repr(capture_script)+'\nPIN='+repr(hashlib.sha256(code.encode()).hexdigest())+'\nUNIT='+repr('kpi-finite-prefund-'+live['run_id'])+'\nROOT='+repr(admin['state_root'])+'\n'+r'''
import pathlib,hashlib,subprocess,json,os
p=pathlib.Path(SCRIPT);assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==PIN
args=['systemd-run','--quiet','--wait','--collect','--pipe','--unit='+UNIT,'--property=RuntimeMaxSec=1800','--property=TimeoutStopSec=5','--property=KillMode=control-group','--property=MemoryHigh=3G','--property=MemoryMax=4G','--property=CPUQuota=250%','--property=TasksMax=64','--property=Restart=no','--property=LimitCORE=0','--property=NoNewPrivileges=yes','/usr/bin/python3',SCRIPT]
v=subprocess.run(args,capture_output=True,timeout=1860)
# Retain exact capture output privately before parsing/rejection and full-stop check.
for n,raw in [('prefund-cgroup.stdout',v.stdout),('prefund-cgroup.stderr',v.stderr)]:
 fd=os.open(pathlib.Path(ROOT)/n,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
stop=subprocess.run(['systemctl','show',UNIT+'.service','--property=MainPID,ControlPID,ActiveState,SubState,LoadState'],capture_output=True,text=True,timeout=5);props=dict(x.split('=',1) for x in stop.stdout.splitlines());assert props.get('MainPID','0')=='0' and props.get('ControlPID','0')=='0' and props.get('ActiveState','inactive') in ['inactive','failed']
cgroup=pathlib.Path('/sys/fs/cgroup/system.slice')/(UNIT+'.service');assert not cgroup.exists() or not (cgroup/'cgroup.procs').read_text().strip()
assert v.returncode==0,'bounded finite prefunding halted';result=json.loads(v.stdout);result['bounded_capture']={'unit':UNIT+'.service','runtime_max_seconds':1800,'memory_max':'4G','CPU_percent':250,'full_stop_verified':True};print(json.dumps(result))
'''
 pref=json.loads(remote.run('@C_SSH_HOST@',bounded,1900));durable(E/'C-prefunding-checkpoint-acquisition.json',pref);live=pref['config'];cp=pref['checkpoint'];durable(E/'pre-funding-checkpoint.json',cp)
 loc={'artifact_index_sha256':cfg['inventory_sha256'],'genesis_hex':manifest['genesis_hex'],'instance_hex':manifest['instance_hex'],'network':'testnet-10','s0_amount':manifest['states']['s0']['R'],'s0_covenant':None,'s0_index':'0','s0_spk_hex':manifest['states']['s0']['spk_hex'],'s0_txid_hex':review['txid'],'scan_start_blue_score':cp['blue_score'],'scan_start_daa_score':cp['daa_score'],'scan_start_hash':cp['cursor']};live.update(locator=loc,checkpoint=cp);durable(E/'old-S0-locator.json',loc);durable(E/'live-config.json',live)
 m=copy.deepcopy(admin['activation_manifest']);m.update(config=admin['state_root']+'/config.json',config_sha256=sha(E/'live-config.json'),prefund_sha256=pref['prefund_sha256'],prefund_seal_sha256=pref['prefund_seal_sha256']);cr=activation('C',m,live,a,check,b);require(cr['prepared'] and cr['collector_started_before_funding'] and cr['S1_pointer_supplied'] is False,'actual original C prepared/collector before funding');durable(E/'C-live-prepared.json',cr)
 # Keep credential namespace, independently update its exact new forced-run bytes.
 current=copy.deepcopy(b);current['current_run_id']=live['run_id'];current['C'].update(config=live,config_path=m['config'],config_sha256=m['config_sha256'],socket_root=m['socket_root']);current['A_controller_route'].update(run_id=live['run_id'],config_sha256=m['config_sha256'],forced_command_sha256=next(x['forced_command_sha256'] for x in cr['routes']['routes'] if x['role']=='controller'));durable(E/'current-runtime-binding.json',current)
 builder=pathlib.Path(b['B_expectations_builder']);require(sha(builder)==b['B_expectations_builder_sha256'],'independent B expectations builder pin');import importlib.util
 spec=importlib.util.spec_from_file_location('finite_builder',builder);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);Bcfg=copy.deepcopy(b['B']['config']);Bcfg.update({k:v for k,v in live.items() if k not in {'manifest','terminal_sdk_directory','terminal_wire_node','terminal_wire_node_sha256','qualification_role','native_directory'}});Bcfg['finite_expected']=module.build(live,{'run_id':live['run_id'],'checkpoint':cp});Bcfg['manifest']='/instances/'+cfg['base_instance_id']+'/public/manifest.json';Bcfg['B_locator_path']='/work/final-qualification/autonomous-results/'+live['run_id']+'/old-S0-locator.json';Bcfg['B_checkpoint_path']='/work/final-qualification/autonomous-results/'+live['run_id']+'/pre-funding-checkpoint.json';Bcfg['B_recovery_output']='/work/finite-recovery/'+live['run_id']
 badmin=b['live']['B'];bm=copy.deepcopy(badmin['activation_manifest']);bm.update(config=badmin['state_root']+'/config.json',config_sha256=hashlib.sha256(encode(Bcfg)).hexdigest());br=activation('B',bm,Bcfg,a,check,b);require(br['B_started_before_funding'] and br['unarmed'],'actual B before funding');durable(E/'B-live-deployed.json',br)
 durable(E/'authorization.json',{'run_id':live['run_id'],'checklist_sha256':a['checklist_sha256'],'owner_authorization_sha256':sha(E/'owner-live-authorization.json')});durable(E/'worker-channel.private.json',ca.worker_channel(live['run_id']));durable(E/'pre-funding-autonomy-receipt.json',{'run_id':live['run_id'],'passed':True,'at':time.time(),'C_live_prepared':True,'B_started_before_funding':True,'terminal_broadcast_authorized':True})
 return live,current

def fund(live,current):
 # Original helper claims funding before one send and rejects any replay/ambiguity.
 child('submit_funding_ready.mjs',65);deadline=time.monotonic()+600
 while time.monotonic()<deadline:
  child('confirm_S0.py',min(95,deadline-time.monotonic()))
  if (E/'S0-confirmation.json').exists():return read(E/'S0-confirmation.json')
  time.sleep(2)
 raise TimeoutError('independent durable native S0 deadline; never resubmit')

def continuation(live,current,s0):
 require(s0['ready'] and s0['receipt']['run_id']==live['run_id'],'exact independent S0 receipt');entry=dict(s0['receipt']['durable_historical_native_entry']);spk=entry['scriptPublicKey'];entry['scriptPublicKey']=spk if type(spk) is str else format(int(spk['version']),'04x')+spk['script'];entry['amount']=u64(entry['amount']);entry['blockDaaScore']=int(entry['blockDaaScore']);require(entry['scriptPublicKey']==live['locator']['s0_spk_hex'] and entry['amount']==u64(live['locator']['s0_amount']),'exact S0 input')
 channel=read(E/'worker-channel.private.json');runtime=pathlib.Path(channel['runtime']);runtime.mkdir(mode=0o700,exist_ok=False);require(subprocess.check_output(['findmnt','-no','FSTYPE','-T',str(runtime)],text=True).strip()=='tmpfs','volatile worker RAM filesystem');durable(E/'worker-config.private.json',{'run_id':live['run_id'],'mode':'live','S0_request':{'txid':live['locator']['s0_txid_hex'],'index':'0','entry':entry},'S0_locator_sha256':sha(E/'old-S0-locator.json'),'inventory_sha256':live['inventory_sha256'],'worker_source_sha256':live['worker_source_sha256'],'attempt_nonce':secrets.token_hex(16)})
 subprocess.run(['systemd-run','--user','--quiet','--unit='+channel['broker_unit'],'--property=StandardOutput=null','--property=StandardError=null','--setenv=PYTHONPATH='+str(HERE)+':'+str(BASE),'/usr/bin/python3',str(HERE/'intent_broker.py')],env=clean_env(),check=True,capture_output=True,timeout=15);child('start_worker.py',15);child('qualify_sandbox.py',30)
 deadline=time.monotonic()+3900
 while time.monotonic()<deadline:
  status=startup.query(live,'status',binding=current);require(not status['faulted'] and status['terminal_result'] is None,'C fault before whole-A boundary')
  code='RUN='+repr(live['run_id'])+'\n'+r'''
import pathlib,json
p=pathlib.Path('/srv/kpi-recovery/jail/work/final-qualification/autonomous-results')/RUN;v=json.loads((p/'controller.json').read_bytes());print(json.dumps({'events':[x['kind'] for x in v['events']],'failed':any((p/n).exists() for n in ['result.json','boundary-error.json','C-delivery-failed.json'])}))
'''
  b=json.loads(remote.run('@B_SSH_HOST@',code,20));require(not b['failed'],'B acceptance/ARM guard failed')
  if len(status['events'])==4 and b['events']==['B_CONTROLLER_STARTED_BEFORE_ACCEPTANCE','B_ARMED_AFTER_C_RECEIPT']:
   outcome=read(runtime/'submission-outcome.json');require(outcome['attempts']==1,'exact one volatile continuation')
   from finite_final_check import check as final_check
   final=final_check(live,current);require(final['passed'],'fresh original native/current/ARM gates')
   handoff={'schema':'kpi-finite-rehearsal-A-route-handoff/v1','run_id':live['run_id'],'at':time.time(),'C_events':status['events'],'B_events':b['events'],'C_independent_acceptance_and_B_ARMED':True,'A_accepted_S1_exported':False,'minimum_off_seconds':0,'terminal_policy_sha256':hashlib.sha256(encode(live['terminal_policy'])).hexdigest(),'poweroff_performed':False};durable(E/'whole-A-poweroff-handoff.json',handoff)
   Ctarget=live['finite']['root']+'/'+live['run_id']+'/POWER-OFF-HANDOFF.json';Btarget='/srv/kpi-recovery/jail/work/final-qualification/autonomous-results/'+live['run_id']+'/POWER-OFF-HANDOFF.json'
   remote_put('@C_SSH_HOST@',Ctarget,handoff);remote_put('@B_SSH_HOST@',Btarget,handoff);durable(E/'poweroff-handoff-durability.json',{'matching_B_C_durable_handoff':True,'sha256':sha(E/'whole-A-poweroff-handoff.json'),'poweroff_performed':False});return handoff
  time.sleep(2)
 raise TimeoutError('C complete receipt/B ARM deadline')

def funding_may_have_happened(stage):
 # Durable intent precedes the only RPC submit. Missing/lost RPC responses never
 # justify stopping the independent backing/recovery processes or re-submitting.
 markers=[]
 try:
  for name in ['funding-submission-intent.json','funding-submission-response.json','funding-ambiguous-response.json','S0-confirmation.json']:
   item=E/name
   if item.exists() or item.is_symlink():markers.append(name)
 except OSError:return True,['funding-marker-inspection-uncertain']
 return bool(markers) or stage=='volatile-continuation-and-handoff',markers

def fail_closed(cfg,b,stage,exc,claimed):
 result={'schema':'kpi-finite-live-fail-closed/v1','run_id':cfg.get('run_id'),'stage':stage,'exception_type':type(exc).__name__,'claims_retained':True,'resume_or_resubmit_allowed':False,'poweroff_performed':False,'keep_A_on':True,'cleanup':{},'cleanup_certain':False,'at':time.time()}
 if not claimed:return result
 # Do not touch an existing invocation when a replay failed E's exclusive claim.
 durable(E/'failure-context.json',result)
 channel=ca.worker_channel(cfg['run_id'])
 try:
  units=[channel['unit'],channel['broker_unit']];v=subprocess.run(['systemctl','--user','stop',*units],env=clean_env(),capture_output=True,timeout=30)
  props={u:subprocess.check_output(['systemctl','--user','show',u,'--property=MainPID,ControlPID,ActiveState'],env=clean_env(),text=True,timeout=5) for u in units}
  certain=all('MainPID=0' in x and 'ControlPID=0' in x and ('ActiveState=inactive' in x or 'ActiveState=failed' in x) for x in props.values());result['cleanup']['A']={'certain':certain,'stop_exit_code':v.returncode,'units':units}
 except BaseException as failure:result['cleanup']['A']={'certain':False,'exception_type':type(failure).__name__}
 preserve,markers=funding_may_have_happened(stage)
 if preserve:
  result.update(funding_may_have_happened=True,funding_markers=markers,independent_runtime_preserved=True,authorization_routes_preserved=True,manual_reconciliation_required=True)
  for role in ['B','C']:result['cleanup'][role]={'certain':True,'stop_attempted':False,'runtime_preserved':True}
  result['cleanup_certain']=result['cleanup'].get('A',{}).get('certain') is True;durable(E/'failure-cleanup-receipt.json',result);return result
 for role in ['B','C']:
  try:
   unit=b['live'][role]['activation_manifest']['unit'];require(unit=='kpi-finite-'+role.lower()+'-'+cfg['run_id']+'.service','only exact new live unit cleanup');units=([ 'kpi-finite-prefund-'+cfg['run_id']+'.service','kpi-finite-collector-'+cfg['run_id']+'.service',unit] if role=='C' else [unit])
   code='UNITS='+repr(units)+'\n'+r'''
import subprocess,json
v=subprocess.run(['systemctl','stop',*UNITS],capture_output=True,timeout=210)
props={u:dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show',u,'--property=MainPID,ControlPID,ActiveState'],text=True,timeout=5).splitlines()) for u in UNITS}
certain=all(p['MainPID']==p['ControlPID']=='0' and p['ActiveState'] in ['inactive','failed'] for p in props.values());print(json.dumps({'certain':certain,'stop_exit_code':v.returncode,'units':UNITS}))
'''
   result['cleanup'][role]=json.loads(remote.run('@B_SSH_HOST@' if role=='B' else '@C_SSH_HOST@',code,240))
  except BaseException as failure:result['cleanup'][role]={'certain':False,'exception_type':type(failure).__name__}
 result['cleanup_certain']=all(result['cleanup'].get(role,{}).get('certain') is True for role in ['A','B','C']);durable(E/'failure-cleanup-receipt.json',result);return result

def main():
 parser=argparse.ArgumentParser()
 for key in ['runtime-binding','runtime-binding-sha256','authority','authority-sha256','checklist','checklist-sha256']:parser.add_argument('--'+key,required=True)
 parser.add_argument('action',choices=['start']);a=parser.parse_args();os.umask(0o077);cfg={};b={};ownership={'claimed':False};stage='authorization'
 try:
  cfg=startup.config();require(sha(a.checklist)==a.checklist_sha256,'external reviewed checklist hash');check=read(a.checklist);b=startup.binding(a.runtime_binding,a.runtime_binding_sha256,cfg);authority=startup.authority(a.authority,a.authority_sha256,cfg,b,a.checklist);require(authority['checklist_sha256']==a.checklist_sha256,'one exact checklist')
  stage='preparation';live,current=prepare(cfg,b,authority,check,ownership);stage='funding';s0=fund(live,current);stage='volatile-continuation-and-handoff';value=continuation(live,current,s0);print(json.dumps(value,sort_keys=True));return 0
 except BaseException as exc:
  failure=fail_closed(cfg,b,stage,exc,ownership['claimed']);print(json.dumps({'failed_closed':True,'run_id':cfg.get('run_id'),'stage':stage,'cleanup_certain':failure['cleanup_certain'],'keep_A_on':True,'poweroff_performed':False,'resume_or_resubmit_allowed':False}));return 1
if __name__=='__main__':raise SystemExit(main())
