"""One bounded90s unfunded collector/funding-ready exercise using same real C observer."""
from pathlib import Path
import sys,json,hashlib
W=Path(__file__).resolve().parent;P=W.parent/'package-standby-cwd';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def execute():
 release=json.loads((W/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes());assert release['collector_source_sha256']==sha(__file__) and release['plan_sha256']==sha(P/'STAGE-PLAN.json');binding=json.loads((W/'STANDBY-CWD-INSTALL-BINDING.private.json').read_bytes());plan=json.loads((P/'STAGE-PLAN.json').read_bytes());root=plan['C_root'];unit='kpi-fresh-collector-check-a9f60e4f2a037353'
 props={'User':'root','RuntimeMaxSec':'90','MemoryHigh':'3G','MemoryMax':'4G','CPUQuota':'250%','TasksMax':'64','KillMode':'control-group','Restart':'no','TimeoutStopSec':'5','UMask':'0077','NoNewPrivileges':'yes','PrivateTmp':'yes','ProtectSystem':'strict','ProtectHome':'read-only','ReadWritePaths':root+'/state/finite-runs','StandardOutput':'append:'+root+'/state/collector.stdout','StandardError':'append:'+root+'/state/collector.stderr'}
 args=['systemd-run','--unit='+unit,'--collect','--quiet']
 for k,v in props.items():args+=['--property='+k+'='+v]
 args+=['/usr/bin/python3','-I',plan['C_source_root']+'/finite_capture.py','--config',root+'/state/config.json','continuation']
 # -I intentionally replaced below: original CLI imports exact sibling modules.
 args[args.index('-I')]='-B'
 code='ROOT='+repr(root)+'\nRUN='+repr(plan['standby_run_id'])+'\nUNIT='+repr(unit)+'\nSERVICE='+repr(binding['C']['unit'])+'\nARGS='+repr(args)+'\n'+r'''
import pathlib,json,socket,subprocess,time,os,hashlib
r=pathlib.Path(ROOT);cfg=json.loads((r/'state/config.json').read_bytes());assert all(cfg[k] is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']);run=r/'state/finite-runs'/RUN;assert not (run/'COLLECTOR-START.json').exists()
for n in ['collector.stdout','collector.stderr']:
 with (r/'state'/n).open('xb') as f:os.fchmod(f.fileno(),0o600)
before=subprocess.check_output(['systemctl','show',SERVICE,'--property=MainPID,NRestarts'],text=True,timeout=5);samples=[];began=time.monotonic();started=False;failure=None
def query():
 with socket.socket(socket.AF_UNIX) as s:
  s.settimeout(35);s.connect(str(r/'state/socket/control.sock'));s.sendall(json.dumps({'run_id':RUN,'op':'funding-ready','authenticated_role':'controller'}).encode()+b'\n');raw=s.makefile('rb').readline(262145)
 assert len(raw)<=262144 and raw.endswith(b'\n');return json.loads(raw)
def observation(label):
 p=run/'COLLECTOR-PROGRESS.json';progress=json.loads(p.read_bytes()) if p.exists() else None
 try:reply=query();error=None
 except Exception as e:reply=None;error=type(e).__name__+': '+str(e)
 item={'label':label,'at':time.time(),'elapsed':time.monotonic()-began,'progress':progress,'reply':reply,'transport_error':error};samples.append(item)
 with (r/'state'/('collector-'+label+'.json')).open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(item,f);f.flush();os.fsync(f.fileno())
try:
 subprocess.run(ARGS,check=True,capture_output=True,timeout=8);started=True
 while time.monotonic()-began<20 and not (run/'COLLECTOR-PROGRESS.json').exists() and not (run/'CAPTURE-FAULT.json').exists():time.sleep(.2)
 observation('first-progress')
 while time.monotonic()-began<25 and not (run/'CAPTURE-FAULT.json').exists():time.sleep(.2)
 observation('before-stop')
except Exception as e:failure=type(e).__name__+': '+str(e)
finally:
 stopped=subprocess.run(['systemctl','stop',UNIT+'.service'],capture_output=True,timeout=12)
after=subprocess.check_output(['systemctl','show',SERVICE,'--property=MainPID,NRestarts'],text=True,timeout=5);assert before==after
fault=json.loads((run/'CAPTURE-FAULT.json').read_bytes()) if (run/'CAPTURE-FAULT.json').exists() else None
observer=run/'observer-prefunding';files=sorted(observer.glob('[0-9][0-9][0-9][0-9][0-9][0-9].json'));last=json.loads(files[-1].read_bytes()) if files else None
passed=failure is None and fault is None and all(x['reply'] and x['reply'].get('funding_native_entry_retained') is False and x['reply'].get('S1_pointer_supplied') is False and 'error' not in x['reply'] for x in samples) and len(samples)==2
v={'passed':passed,'scope':'one bounded unfunded actual collector/progress exercise; not live near-tip activation or funding qualification','run_id':RUN,'seconds':time.monotonic()-began,'samples':samples,'collector_fault':fault,'failure':failure,'collector_stop_exit':stopped.returncode,'same_C_process_before_after':before==after,'C_process':before,'last_original_observer_receipt':last,'observer_samples':len(files),'funding':False,'intent_added':False,'prepared_events_added':False,'submit':False}
with (r/'state/collector-process-receipt.json').open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(v,f);f.flush();os.fsync(f.fileno())
state=subprocess.run(['systemctl','show',UNIT+'.service','--property=MainPID,ActiveState,SubState,Result'],capture_output=True,text=True,timeout=5);props=dict(x.split('=',1) for x in state.stdout.splitlines() if '=' in x);assert (state.returncode!=0 and not props) or (props.get('MainPID')=='0' and props.get('ActiveState') in ['inactive','failed']);v['collector_final_state']=props;print(json.dumps(v))
''';v=json.loads(dedicated_remote.run('@C_SSH_HOST@',remote_safety.wrap(code,'C','standby-collector-check'),110));p=W/'C-standby-cwd-collector-actual.private.json';p.write_text(json.dumps(v,indent=2)+'\n');p.chmod(0o600);print(json.dumps({k:v[k] for k in ['passed','scope','run_id','seconds','collector_fault','failure','observer_samples','same_C_process_before_after']}));return v
if __name__=='__main__':execute()
