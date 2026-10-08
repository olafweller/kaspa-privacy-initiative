"""Exclusive reviewed standby files/public/backup stage; never starts services."""
from pathlib import Path
import sys,json,hashlib,base64,subprocess,os
W=Path(__file__).resolve().parent;T=W.parent;P=T/'package-standby-cwd';Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z');sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();plan=json.loads((P/'STAGE-PLAN.json').read_bytes())
def remote(role,code,timeout=30):return json.loads(dedicated_remote.run('@C_SSH_HOST@' if role=='C' else '@B_SSH_HOST@',remote_safety.wrap(code,role,'standby-stage'),timeout))
def save(name,v):
 p=W/(name+'.private.json');p.write_text(json.dumps(v,indent=2)+'\n');p.chmod(0o600)
def scp(source,target,timeout=1800):
 cmd=dedicated_remote.command('@B_SSH_HOST@');dest=cmd[-3];args=['scp',*cmd[1:-3],str(source),dest+':'+target];r=subprocess.run(args,capture_output=True,timeout=timeout);assert r.returncode==0,'authenticated B file transfer failed'
def execute():
 release=json.loads((W/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes());assert release['stage_source_sha256']==sha(__file__) and release['plan_sha256']==sha(P/'STAGE-PLAN.json')
 for role in ['B','C']:
  folder=P/role;assert sha(folder/'package-pins.json')==plan['package_ledger_sha256'][role];ledger=json.loads((folder/'package-pins.json').read_bytes());actual={str(x.relative_to(folder)) for x in folder.rglob('*') if x.is_file()};assert actual==set(ledger['files'])|{'package-pins.json'} and not any(x.is_symlink() for x in folder.rglob('*'))
  for name,h in ledger['files'].items():assert sha(folder/name)==h
  files={str(p.relative_to(folder)):{'sha256':sha(p),'base64':base64.b64encode(p.read_bytes()).decode()} for p in folder.rglob('*') if p.is_file()};assert sum(len(x['base64']) for x in files.values())<2*1024*1024
  root=plan[role+'_root'];code='ROOT='+repr(root)+'\nROLE='+repr(role)+'\nFILES='+repr(files)+'\n'+r'''
import pathlib,os,base64,hashlib,json
r=pathlib.Path(ROOT);assert not r.exists() and not r.is_symlink();parent=r.parent
if not parent.exists():parent.mkdir(mode=0o750 if ROLE=='C' else 0o700);os.chown(parent,0,986 if ROLE=='C' else 0)
assert parent.stat().st_uid==0 and not parent.stat().st_mode&0o022
if ROLE=='C':assert parent.stat().st_gid==986 and parent.stat().st_mode&0o777==0o750
r.mkdir(mode=0o750 if ROLE=='C' else 0o700);os.chown(r,0,986 if ROLE=='C' else 0);os.chmod(r,0o750 if ROLE=='C' else 0o700)
for name,x in FILES.items():
 p=pathlib.PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts;raw=base64.b64decode(x['base64'],validate=True);assert hashlib.sha256(raw).hexdigest()==x['sha256'];target=r/name
 target.parent.mkdir(mode=0o750 if ROLE=='C' else 0o755,parents=True,exist_ok=True)
 if ROLE=='C':os.chown(target.parent,0,986);os.chmod(target.parent,0o750)
 elif target.parent!=r:os.chmod(target.parent,0o755)
 with target.open('xb') as f:os.fchown(f.fileno(),0,986 if ROLE=='C' else 988);os.fchmod(f.fileno(),0o440 if ROLE=='C' else 0o444);f.write(raw);f.flush();os.fsync(f.fileno())
for name in ['state','transfer']:
 p=r/name;p.mkdir(mode=0o750 if ROLE=='C' and name=='state' else 0o700);os.chown(p,0,986 if ROLE=='C' and name=='state' else 0);os.chmod(p,0o750 if ROLE=='C' and name=='state' else 0o700)
if ROLE=='C':(r/'state/finite-runs').mkdir(mode=0o700)
# Credentials are separately and exclusively generated B-only later.
print(json.dumps({'role':ROLE,'root':ROOT,'source_files_staged':len(FILES),'service_started':False}))
''';v=remote(role,code);save(role+'-standby-credit-source-stage',v);print(json.dumps(v),flush=True)
 base=Path(plan['public_export']['public_path']).parent;B=plan['B_root'];scp(base/'public.tar',B+'/transfer/public-node-sdk.tar');scp(base/'backup/backup-package.json',B+'/transfer/backup-package.json');scp(base/'backup/unlock.key',B+'/transfer/unlock.key')
 inventory=json.loads((base/'public/inventory.json').read_bytes());expected={x['path']:x['sha256'] for x in inventory['files']}|{'inventory.json':sha(base/'public/inventory.json')};code='ROOT='+repr(B)+'\nBASE='+repr(plan['base_instance_id'])+'\nEXPECTED='+repr(expected)+'\nTAR_SHA='+repr(plan['public_export']['public_tar_sha256'])+'\nBACKUP_SHA='+repr(plan['public_export']['backup_package_sha256'])+'\n'+r'''
import pathlib,hashlib,tarfile,json,os,shutil,sys
r=pathlib.Path(ROOT);bundle=r/'transfer/public-node-sdk.tar';assert bundle.stat().st_size<=160*1024*1024 and hashlib.sha256(bundle.read_bytes()).hexdigest()==TAR_SHA
base=pathlib.Path('/srv/kpi-recovery/jail/instances')/BASE;assert not base.exists();base.mkdir(mode=0o750);os.chown(base,0,988);os.chmod(base,0o750);public=base/'public';public.mkdir(mode=0o750);os.chown(public,0,988);os.chmod(public,0o750)
with tarfile.open(bundle) as tar:
 members=tar.getmembers();assert len(members)==len(EXPECTED) and {m.name for m in members}==set(EXPECTED)
 for m in members:
  assert m.isfile() and pathlib.Path(m.name).name==m.name and m.size<=100000000;raw=tar.extractfile(m).read();assert hashlib.sha256(raw).hexdigest()==EXPECTED[m.name]
  with (public/m.name).open('xb') as f:os.fchown(f.fileno(),0,988);os.fchmod(f.fileno(),0o640);f.write(raw);f.flush();os.fsync(f.fileno())
backup=base/'backup';backup.mkdir(mode=0o700);os.chown(backup,999,988)
for n in ['backup-package.json','unlock.key']:
 src=r/'transfer'/n
 if n=='backup-package.json':assert hashlib.sha256(src.read_bytes()).hexdigest()==BACKUP_SHA
 dest=backup/n
 with dest.open('xb') as f:os.fchown(f.fileno(),999,988);os.fchmod(f.fileno(),0o600);f.write(src.read_bytes());f.flush();os.fsync(f.fileno())
 src.unlink()
sys.dont_write_bytecode=True;sys.path.insert(0,str(r/'software'));from a1_recovery_rehearsal import verify_inventory
verify_inventory(public,EXPECTED['inventory.json']);print(json.dumps({'role':'B','base_instance_id':BASE,'public_files':len(EXPECTED),'inventory_sha256':EXPECTED['inventory.json'],'sealed_backup_staged_B_only':True,'no_precomputed_proof_or_transaction':True}))
''';v=remote('B',code,45);save('B-standby-credit-new-BASE-stage',v);print(json.dumps(v),flush=True)
if __name__=='__main__':execute()
