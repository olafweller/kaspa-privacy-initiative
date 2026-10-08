"""One reviewed bounded C prefix acquisition; never starts the standby observer."""
from pathlib import Path
import json,hashlib,sys
W=Path(__file__).resolve().parent;P=W.parent/'package-standby-cwd';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def execute():
 release=json.loads((W/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes());plan=json.loads((P/'STAGE-PLAN.json').read_bytes());assert release['prefund_source_sha256']==sha(__file__) and release['plan_sha256']==sha(P/'STAGE-PLAN.json');checked=json.loads((W/'B-credit-BASE-check-actual.private.json').read_bytes());assert checked['passed'] and checked['helper']['base_instance_id']==plan['base_instance_id'];fee=json.loads((W.parent/'package/A/fresh-fee-mechanism-report.json').read_bytes());assert fee['passed'] and fee['run_id']==plan['planned_live_run_id'] and fee['funding_authorized'] is False and sha(fee['receipt_path'])==fee['receipt_sha256'];root=plan['C_root'];unit='kpi-fresh-prefund-a9f60e4f2a037353'
 props={'User':'root','RuntimeMaxSec':'120','MemoryHigh':'3G','MemoryMax':'4G','CPUQuota':'250%','TasksMax':'64','KillMode':'control-group','Restart':'no','UMask':'0077','TimeoutStopSec':'5','NoNewPrivileges':'yes','PrivateTmp':'yes','ProtectSystem':'strict','ProtectHome':'read-only','ReadWritePaths':root+'/state','BindReadOnlyPaths':plan['C_source_root']+' '+root+'/config.template.json '+root+'/prefund_standby.py '+root+'/package-pins.json '+str(Path(json.loads((P/'C/config.template.json').read_bytes())['manifest']).parent)}
 args=['systemd-run','--unit='+unit,'--wait','--collect','--pipe','--quiet']
 for k,v in props.items():args+=['--property='+k+'='+v]
 args+=plan['C_prefund_command'];code='ROOT='+repr(root)+'\nUNIT='+repr(unit)+'\nARGS='+repr(args)+'\n'+r'''
import pathlib,json,hashlib,subprocess,os,signal,time
root=pathlib.Path(ROOT);out=root/'state/prefund-stdout.txt';err=root/'state/prefund-stderr.txt';started=time.monotonic();expired=False
with out.open('xb') as stdout,err.open('xb') as stderr:
 os.fchmod(stdout.fileno(),0o600);os.fchmod(stderr.fileno(),0o600);child=subprocess.Popen(ARGS,stdout=stdout,stderr=stderr,start_new_session=True,env={'PATH':'/usr/bin:/bin'})
 try:
  try:rc=child.wait(timeout=135)
  except subprocess.TimeoutExpired:expired=True;rc=-1
 finally:
  subprocess.run(['systemctl','stop',UNIT+'.service'],capture_output=True,timeout=10)
  try:os.killpg(child.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  child.wait(timeout=10)
 stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
v={'passed':rc==0 and not expired,'exit_code':rc,'expired':expired,'seconds':time.monotonic()-started,'stdout_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'stderr_sha256':hashlib.sha256(err.read_bytes()).hexdigest(),'stderr_bytes':err.stat().st_size,'funding':False,'submit':False,'observer_started':False}
if v['passed']:v['helper']=json.loads(out.read_bytes())
with (root/'state/prefund-process-receipt.json').open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(v,f);f.flush();os.fsync(f.fileno())
state=subprocess.run(['systemctl','show',UNIT+'.service','--property=MainPID,ActiveState,SubState,Result,MemoryPeak'],capture_output=True,text=True,timeout=5);props=dict(x.split('=',1) for x in state.stdout.splitlines() if '=' in x);v['transient_final']=props
assert (state.returncode!=0 and not props) or (props.get('MainPID')=='0' and props.get('ActiveState') in ['inactive','failed']);print(json.dumps(v))
''';v=json.loads(dedicated_remote.run('@C_SSH_HOST@',remote_safety.wrap(code,'C','standby-prefund'),165));p=W/'C-standby-cwd-prefund-actual.private.json';p.write_text(json.dumps(v,indent=2)+'\n');p.chmod(0o600);print(json.dumps(v));return v
if __name__=='__main__':execute()
