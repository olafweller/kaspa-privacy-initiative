"""One actual B jail/UID999 PrivateNetwork public+sealed backup qualification."""
from pathlib import Path
import sys,json,hashlib,base64
W=Path(__file__).resolve().parent;P=W.parent/'package-standby-cwd';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def execute():
 rel=json.loads((W/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes());assert rel['B_check_source_sha256']==sha(__file__);assert sha(P/'STAGE-PLAN.json')==rel['plan_sha256'];plan=json.loads((P/'STAGE-PLAN.json').read_bytes());B=plan['B_root'];helper=P/'B/new_base_check.py';assert sha(helper)==rel['B_check_helper_sha256'];files={'new_base_check.py':helper.read_bytes(),'config.json':(P/'B/config.template.json').read_bytes()};pins={n:hashlib.sha256(raw).hexdigest() for n,raw in files.items()};payload={n:base64.b64encode(raw).decode() for n,raw in files.items()};unit='kpi-fresh-BASE-check-a9f60e4f2a037353'
 props={'User':'999','Group':'988','RootDirectory':'/srv/kpi-recovery/jail','PrivateNetwork':'yes','MountAPIVFS':'yes','CapabilityBoundingSet':'','RuntimeMaxSec':'1800','MemoryHigh':'3G','MemoryMax':'4G','CPUQuota':'250%','TasksMax':'64','KillMode':'control-group','Restart':'no','UMask':'0077','TimeoutStopSec':'5','NoNewPrivileges':'yes','PrivateTmp':'yes','ProtectSystem':'strict','ProtectHome':'yes','ReadWritePaths':'+/work','BindReadOnlyPaths':'/usr /lib /lib64 /bin '+B+'/qualification-files:/qualification'}
 for n in plan['source_pins']['B']:props['BindReadOnlyPaths']+=' '+B+'/software/'+n+':/software/'+n
 args=['systemd-run','--unit='+unit,'--wait','--collect','--pipe','--quiet']
 for k,v in props.items():args+=['--property='+k+'='+v]
 args+=['/usr/bin/python3','-I','/qualification/new_base_check.py','--config','/qualification/config.json','--config-sha256',pins['config.json']]
 code='ROOT='+repr(B)+'\nUNIT='+repr(unit)+'\nFILES='+repr(payload)+'\nPINS='+repr(pins)+'\nARGS='+repr(args)+'\n'+r'''
import pathlib,json,base64,hashlib,os,subprocess,signal,time
r=pathlib.Path(ROOT);d=r/'qualification-files';d.mkdir(mode=0o755,exist_ok=False);os.chmod(d,0o755)
for n,raw in FILES.items():
 data=base64.b64decode(raw,validate=True);assert hashlib.sha256(data).hexdigest()==PINS[n]
 with (d/n).open('xb') as f:os.fchmod(f.fileno(),0o444);f.write(data);f.flush();os.fsync(f.fileno())
started=time.monotonic();expired=False;out=r/'state/B-new-base-check.stdout';err=r/'state/B-new-base-check.stderr'
with out.open('xb') as stdout,err.open('xb') as stderr:
 os.fchmod(stdout.fileno(),0o600);os.fchmod(stderr.fileno(),0o600);child=subprocess.Popen(ARGS,stdout=stdout,stderr=stderr,start_new_session=True,env={'PATH':'/usr/bin:/bin'})
 try:
  try:rc=child.wait(timeout=1860)
  except subprocess.TimeoutExpired:expired=True;rc=-1
 finally:
  subprocess.run(['systemctl','stop',UNIT+'.service'],capture_output=True,timeout=10)
  try:os.killpg(child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  child.wait(timeout=10)
 stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
v={'passed':rc==0 and not expired,'exit_code':rc,'expired':expired,'seconds':time.monotonic()-started,'stdout_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256(err.read_bytes()).hexdigest(),'stderr_bytes':err.stat().st_size,'actual_UID':999,'PrivateNetwork':True,'funding':False,'submit':False}
if v['passed']:v['helper']=json.loads(out.read_bytes())
with (r/'state/B-new-base-check-process.json').open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(v,f);f.flush();os.fsync(f.fileno())
state=subprocess.run(['systemctl','show',UNIT+'.service','--property=MainPID,ActiveState,SubState,Result'],capture_output=True,text=True,timeout=5);props=dict(x.split('=',1) for x in state.stdout.splitlines() if '=' in x);v['transient_final']=props;assert (state.returncode!=0 and not props) or (props.get('MainPID')=='0' and props.get('ActiveState') in ['inactive','failed']);print(json.dumps(v))
''';v=json.loads(dedicated_remote.run('@B_SSH_HOST@',remote_safety.wrap(code,'B','new-base-check'),1900));p=W/'B-credit-BASE-check-actual.private.json';p.write_text(json.dumps(v,indent=2)+'\n');p.chmod(0o600);print(json.dumps(v));return v
if __name__=='__main__':execute()
