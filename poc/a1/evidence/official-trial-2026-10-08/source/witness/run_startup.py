"""One actual bounded false-authority startup attempt, then exact cleanup.
No finite_live/main, prepare, funding, continuation submission, ARM or terminal.
"""
from pathlib import Path
import sys,json,os,hashlib,subprocess,time,importlib.util,signal
W=Path(__file__).resolve().parent;T=W.parent;P=T/'package-standby-cwd';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,v):
 p=W/(name+'.json')
 with p.open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def module(name):
 p=W/(name+'.py');spec=importlib.util.spec_from_file_location('step2_'+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def child(args,label,timeout):
 began=time.monotonic()
 try:v=subprocess.run(args,capture_output=True,timeout=timeout)
 except subprocess.TimeoutExpired as exc:
  for suffix,raw in [('stdout',exc.stdout or b''),('stderr',exc.stderr or b'')]:
   with (W/(label+'.'+suffix+'.private')).open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
  save(label+'-deadline-failure',{'deadline_exceeded':True,'seconds':time.monotonic()-began,'stdout_bytes':len(exc.stdout or b''),'stderr_bytes':len(exc.stderr or b''),'funding':False,'submit':False});raise
 for suffix,raw in [('stdout',v.stdout),('stderr',v.stderr)]:
  with (W/(label+'.'+suffix+'.private')).open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
 receipt={'returncode':v.returncode,'seconds':time.monotonic()-began,'stdout_sha256':hashlib.sha256(v.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(v.stderr).hexdigest(),'stderr_bytes':len(v.stderr)}
 if v.returncode==0:receipt['result']=json.loads(v.stdout)
 save(label,receipt);assert v.returncode==0,label+' failed; exact output retained';return receipt

def cleanup(plan):
 out={}
 # Independently attempt each role; C auth restoration cannot be skipped by B.
 for role in ['B','C']:
  units=['kpi-finite-'+role.lower()+'-'+plan['standby_run_id']+'.service']
  if role=='C':units+=['kpi-fresh-prefund-a9f60e4f2a037353.service','kpi-fresh-collector-check-a9f60e4f2a037353.service']
  else:units+=['kpi-fresh-BASE-check-a9f60e4f2a037353.service']
  code='ROOT='+repr(plan[role+'_root'])+'\nCREDS='+repr(plan['B_credential_root'])+'\nROLE='+repr(role)+'\nUNITS='+repr(units)+'\nPRE='+repr(plan['C_authorized_keys_preimage_sha256'])+'\n'+r'''
import pathlib,hashlib,subprocess,json,os
P=pathlib.Path;r=P(ROOT);errors=[];authrestored=None
# Revoke only this attempt's exact forced rows before any stop-state assertions.
if ROLE=='C':
 a=P('/var/lib/kpi-history/.ssh/authorized_keys');pre=r/'state/authorized-keys.preimage'
 if pre.exists():
  before=pre.read_bytes();assert hashlib.sha256(before).hexdigest()==PRE;raw=a.read_bytes();pieces=raw.splitlines(keepends=True);targets=[x for x in pieces if ((' --bound-run '+r.name+' ').encode() in x)];assert len(targets)<=2;assert b''.join(x for x in pieces if x not in targets)==before;meta=a.stat();tmp=a.parent/('authorized_keys.'+r.name+'.cleanup');fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:os.fchown(f.fileno(),meta.st_uid,meta.st_gid);os.fchmod(f.fileno(),meta.st_mode&0o777);f.write(before);f.flush();os.fsync(f.fileno())
  os.replace(tmp,a);fd=os.open(a.parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 assert hashlib.sha256(a.read_bytes()).hexdigest()==PRE;authrestored=True
# Already unloaded transient units are accepted only with PID0 and no cgroup.
for u in UNITS:
 subprocess.run(['systemctl','stop',u],capture_output=True,timeout=200 if u.startswith('kpi-finite-') else 12)
props={};groups={}
for u in UNITS:
 v=subprocess.run(['systemctl','show',u,'--property=MainPID,ControlPID,LoadState,ActiveState,SubState'],capture_output=True,text=True,timeout=5);props[u]=dict(x.split('=',1) for x in v.stdout.splitlines());g=P('/sys/fs/cgroup/system.slice')/u;groups[u]={'exists':g.exists(),'procs':(g/'cgroup.procs').read_text() if (g/'cgroup.procs').exists() else None}
 if props[u].get('MainPID')!='0' or props[u].get('ControlPID')!='0' or props[u].get('ActiveState') not in ['inactive','failed'] or groups[u]['procs']:errors+=['unit-not-fully-stopped:'+u]
# Leave isolated inert evidence/credentials retained; exact auth is revoked.
print(json.dumps({'role':ROLE,'units':props,'cgroups':groups,'authorization_restored':authrestored,'cleanup_errors':errors,'cleanup_certain':not errors,'old_units_stopped':False}))
'''
  try:
   raw=dedicated_remote.run('@B_SSH_HOST@' if role=='B' else '@C_SSH_HOST@',remote_safety.wrap(code,role,'step2-cleanup'),250);out[role]=json.loads(raw);save(role+'-final-cleanup',out[role])
  except BaseException as exc:out[role]={'cleanup_certain':False,'exception':type(exc).__name__};save(role+'-final-cleanup-exception',out[role])
 return out

def wait_listener(expected):
 deadline=time.monotonic()+10;initial_pid=None;initial_restarts=None
 while time.monotonic()<deadline:
  p=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','--user','show','kpi-g5-prepared-funding-link.service','--property=MainPID,ControlPID,ActiveState,SubState,NRestarts'],text=True,timeout=3).splitlines());pid=p['MainPID']
  if pid!='0' and p['ActiveState']=='active' and p['SubState']=='running':
   if initial_pid is None:initial_pid=pid;initial_restarts=p['NRestarts']
   assert pid==initial_pid and p['NRestarts']==initial_restarts=='0','A tunnel replaced or restarted'
   actual=[x.decode() for x in Path('/proc',pid,'cmdline').read_bytes().split(b'\0') if x];assert actual==expected,'exact A SSH argv mismatch'
   listeners=subprocess.check_output(['ss','-ltnpH','( sport = :29211 )'],text=True,timeout=3).splitlines()
   if len(listeners)==1 and listeners[0].split()[3]=='127.0.0.1:29211' and ('pid='+pid+',') in listeners[0]:return {'properties':p,'listener':listeners[0],'exact_argv_verified':True,'at':time.time()}
  time.sleep(.1)
 raise TimeoutError('exact A-owned listener readiness deadline')
def execute():
 os.umask(0o077);release=json.loads((W/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes());assert release['driver_source_sha256']==sha(__file__);plan=json.loads((P/'STAGE-PLAN.json').read_bytes());assert release['plan_sha256']==sha(P/'STAGE-PLAN.json');result={'run_id':plan['standby_run_id'],'planned_live_run_id':plan['planned_live_run_id'],'funding':False,'prepare':False,'ARM':False,'submit':False,'poweroff':False,'full_startup_qualified':False};stage='initial';remote_started=False;tunnel_started=False;unit='kpi-g5-prepared-funding-link.service'
 before=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','--user','show',unit,'--property=MainPID,ControlPID,ActiveState,SubState,NRestarts'],text=True,timeout=5).splitlines());assert (before['MainPID']=='0' and before['ActiveState']=='inactive') or (before['MainPID']!='0' and before['ActiveState']=='active' and before['SubState']=='running');save('A-tunnel-before',before)
 try:
  stage='current-start';module('cold_bootstrap_gate').validate()
  def expiry(signum,frame):raise TimeoutError('bounded cold bootstrap deadline')
  signal.signal(signal.SIGALRM,expiry);signal.setitimer(signal.ITIMER_REAL,3725)
  stage='new-source-public-stage';remote_started=True;module('stage_fresh_sources_public').execute()
  stage='direct-B-to-C-public';module('transfer_fresh_public').execute()
  transferred=json.loads((W/'B-standby-credit-transfer-auth-cleanup.private.json').read_bytes());assert transferred['temporary_exact_sender_line_removed'] and transferred['auth_equals_preimage'],'B transfer auth preimage was not restored'
  assert json.loads((W/'C-standby-credit-transfer-key-cleanup.private.json').read_bytes())['private_transfer_key_removed']
  stage='actual-B-new-BASE';checked=module('check_credit_BASE_B').execute();assert checked['passed']
  stage='fresh-staged-native-fee';fee_input=W/'STAGED-FEE-INPUT.private.json';child(['/usr/bin/python3','-B',str(T/'package/A/fee_refresh.py'),'--runtime-binding',str(fee_input),'--runtime-binding-sha256',sha(fee_input)],'fresh-staged-native-fee',225)
  stage='credentials';module('prepare_credentials').execute();module('cold_bootstrap_gate').route_before_prefix()
  stage='prefund';pref=module('prefund_standby_cwd').execute();assert pref['passed'],'one actual C prefix failed'
  stage='bind';module('bind_standby_cwd').execute();module('cold_bootstrap_gate').route_after_bind()
  stage='install';module('install_standby_cwd').execute()
  stage='B-storage';code='ROOT='+repr(plan['B_root'])+'\nUNIT='+repr('kpi-finite-b-'+plan['standby_run_id']+'.service')+'\nPIN='+repr(plan['activation_admin_pins']['finite_live_activate.py'])+'\n'+"import pathlib,hashlib,sys,json;path=pathlib.Path(ROOT)/'admin/finite_live_activate.py';assert hashlib.sha256(path.read_bytes()).hexdigest()==PIN;sys.path.insert(0,str(path.parent));import finite_live_activate as helper;print(json.dumps(helper.qualify_B_recovery_storage(UNIT)))"
  result['B_recovery_storage_qualification']=json.loads(dedicated_remote.run('@B_SSH_HOST@',remote_safety.wrap(code,'B','new-standby-storage'),35));assert result['B_recovery_storage_qualification']['storage_ready'];save('B-current-actual-storage',result['B_recovery_storage_qualification'])
  stage='collector';collector=module('collector_standby_cwd_check').execute();assert collector['passed'],'actual bounded collector/funding-ready failed'
  stage='A-startup';binding=W/'STANDBY-CWD-INSTALL-BINDING.private.json';pin=sha(binding);result['A_startup']=child(['/usr/bin/python3','-B',str(T/'package/A/finite_launch.py'),'--runtime-binding',str(binding),'--runtime-binding-sha256',pin,'startup-check'],'A-actual-startup',55)
  stage='A-endpoint'
  if before['MainPID']=='0':tunnel_started=True;subprocess.run(['systemctl','--user','start',unit],check=True,capture_output=True,timeout=15)
  expected=json.loads((T/'package/A/qualified-funding-ssh-command.private.json').read_bytes())['argv'];result['A_listener_ready']=wait_listener(expected)
  result['A_endpoint']=child(['/usr/bin/python3','-B',str(T/'package/A/endpoint_readiness.py'),'--runtime-binding',str(binding),'--runtime-binding-sha256',pin,'--run-id',plan['planned_live_run_id'],'--output',str(T/'qualification/A-endpoint-actual.private.json')],'A-actual-endpoint',45)
  result['full_startup_qualified']=True;result['collector_qualified']=True;result['C_B_A_real_unarmed_startup']=True
 except BaseException as exc:
  result['failed_stage']=stage;result['exception_type']=type(exc).__name__;result['exception_message']=str(exc);save('startup-failure',result);raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  retain=result['full_startup_qualified'] is True and release['retain_success_for_current_new_trial_preparation'] is True
  result['cleanup']=cleanup(plan) if remote_started and not retain else {};result['cold_bootstrap_passed']=result['full_startup_qualified'];result['current_live_ready']=False;result['new_units_retained_active']=retain
  if tunnel_started and not retain:subprocess.run(['systemctl','--user','stop',unit],capture_output=True,timeout=15)
  after=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','--user','show',unit,'--property=MainPID,ControlPID,ActiveState,SubState,NRestarts'],text=True,timeout=5).splitlines());result['A_tunnel_final']=after;result['A_tunnel_prior_inactive_restored']=after['MainPID']==after['ControlPID']=='0' and after['ActiveState']=='inactive';result['prior_active_A_tunnel_preserved']=before['MainPID']!='0' and after==before;result['retained_for_current_authorized_live_run']=retain;save('FINAL-STARTUP-RESULT',result)
 print(json.dumps(result,indent=2))
if __name__=='__main__':execute()
