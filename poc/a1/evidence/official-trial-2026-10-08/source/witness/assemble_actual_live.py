"""Read-only installed-state attestation and fresh local child assembly; no authority."""
from pathlib import Path
import sys,json,hashlib,os,subprocess,copy
W=Path(__file__).resolve().parent;T=W.parent;A=T/'package/A';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def save(p,v):
 raw=json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 return hashlib.sha256(raw).hexdigest()
def execute():
 b=read(W/'STANDBY-CWD-INSTALL-BINDING.private.json');assert b['actual_installed'] is False;plan=read(T/'package-standby-cwd/STAGE-PLAN.json');final=read(W/'FINAL-STARTUP-RESULT.json');assert final['full_startup_qualified'] and final['retained_for_current_authorized_live_run'];authreceipt=read(W/'C-standby-cwd-forced-routes-installed.private.json');facts={}
 for role in ['B','C']:
  v=b[role];root=plan[role+'_root'];code='ROLE='+repr(role)+'\nROOT='+repr(root)+'\nBINDING='+repr(v)+'\nAUTH='+repr(b['C_authorized_keys_path'])+'\nAUTHSHA='+repr(authreceipt['authorized_keys_sha256'])+'\nLINES='+repr([x['forced_line'] for x in b['route_keys']])+'\n'+r'''
import pathlib,hashlib,subprocess,json
P=pathlib.Path;sha=lambda p:hashlib.sha256(P(p).read_bytes()).hexdigest();v=BINDING
props=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show',v['unit'],'--property=MainPID,ControlPID,ActiveState,SubState,NRestarts,FragmentPath'],text=True,timeout=5).splitlines())
assert props['ActiveState']=='active' and props['SubState']=='running' and props['MainPID']!='0' and props['ControlPID']=='0' and props['NRestarts']=='0'
assert sha(props['FragmentPath'])==v['unit_sha256'];cfg=P(ROOT)/'state/config.json';assert sha(cfg)==v['config_sha256'];c=json.loads(cfg.read_bytes());assert c['run_id']==v['run_id'] and all(c[k] is False for k in ['execution_authorized','terminal_execution_authorized','funding_authorized','poweroff_authorized']);assert all(sha(P(v['source_root'])/n)==h for n,h in v['source_pins'].items());assert sha(v['activation_helper'])==v['activation_helper_sha256'];assert all(sha(P(v['activation_helper']).parent/n)==h for n,h in v['activation_support_pins'].items())
out={'role':ROLE,'passed':True,'properties':props,'config_sha256':sha(cfg),'source_files_verified':len(v['source_pins']),'unit_sha256':sha(props['FragmentPath'])}
if ROLE=='C':
 a=P(AUTH);raw=a.read_bytes();assert hashlib.sha256(raw).hexdigest()==AUTHSHA and all(raw.splitlines(keepends=True).count(x.encode())==1 for x in LINES);out.update(authorized_keys_uid=a.stat().st_uid,authorized_keys_after_sha256=hashlib.sha256(raw).hexdigest())
print(json.dumps(out))
'''
  facts[role]=json.loads(dedicated_remote.run('@C_SSH_HOST@' if role=='C' else '@B_SSH_HOST@',remote_safety.wrap(code,role,'step3-actual-installed-readonly'),25));save(W/(role+'-current-installed-readonly.private.json'),facts[role])
 child=copy.deepcopy(b);child.update(actual_installed=True,C_authorized_keys_uid=facts['C']['authorized_keys_uid'],C_authorized_keys_after_sha256=facts['C']['authorized_keys_after_sha256']);bp=W/'ACTUAL-INSTALLED-DESCRIPTOR.private.json';save(bp,child)
 startup=read(W/'A-actual-startup.json')['result'];sp=W/'ACTUAL-STARTUP-SEMANTIC.private.json';save(sp,startup)
 old=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-finite-launch-preparation-20261007T101055Z');terms=T/'review/FRESH-NATIVE-FIXED-TERMS.json';sys.path.insert(0,str(A))
 from importlib.util import spec_from_file_location,module_from_spec
 spec=spec_from_file_location('new_run_fee_refresh',A/'fee_refresh.py');module=module_from_spec(spec);spec.loader.exec_module(module);module.run(bp,sha(bp));fee_report=read(A/'fresh-fee-mechanism-report.json');assert fee_report['run_id']==b['planned_live_run_id'] and sha(Path(fee_report['receipt_path']))==fee_report['receipt_sha256'];fee=A/'fresh-fee-mechanism-report.json';builder=Path('@KPI_REPO@/.local/worktrees/a1-finite-recovery/scripts/a1_runtime/build_finite_expectations.py')
 assert builder.is_file();endpoint=T/'qualification/A-endpoint-actual.private.json';args=['/usr/bin/python3','-B',str(A/'assemble_live_package.py')]
 for k,p in [('binding',bp),('terms',terms),('startup',sp),('endpoint',endpoint),('fee',fee)]:args+=['--'+k,str(p),'--'+k+'-sha256',sha(p)]
 args+=['--builder',str(builder.resolve()),'--builder-sha256',sha(builder),'--output',str((T/'live-package').resolve())];p=subprocess.run(args,capture_output=True,timeout=20)
 for n,raw in [('assembly.stdout.private',p.stdout),('assembly.stderr.private',p.stderr)]:
  fd=os.open(W/n,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 assert p.returncode==0,p.stderr.decode();save(W/'ACTUAL-LIVE-ASSEMBLY-RESULT.json',json.loads(p.stdout));print(p.stdout.decode())
if __name__=='__main__':execute()
