"""Root-reviewed smoke cleanup retention using the existing B transport.

Only called after exact successful no-submit smoke and B/C cleanup. Atomically
moves the sole new unfunded instance; historical receipts and bytes stay intact.
No import runs a remote command, and no private content leaves B.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,sys
W=Path(__file__).resolve().parent;P=W.parent/'package-standby-cwd'
BASE='unfunded-finite-credit-fee-23ec0276cb764ec4845aab53270b1e35'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def require(v,m):
    if not v:raise ValueError(m)
def execute():
    release=read(W/'ROOT-STANDBY-CWD-RELEASE.json');plan=read(P/'STAGE-PLAN.json');done=read(W/'FINAL-STARTUP-RESULT.json')
    require(release['smoke_retention_source_sha256']==sha(__file__) and release['plan_sha256']==sha(P/'STAGE-PLAN.json'),'exact reviewed smoke retention sources')
    require(release['preparation_smoke_authorized'] is True and release['funding_authorized'] is release['terminal_execution_authorized'] is False and plan['namespace_override'] is not None and plan['base_instance_id']==BASE,'sole new unfunded smoke scope')
    require(done['full_startup_qualified'] and done['cold_bootstrap_passed'] and not done['new_units_retained_active'] and not done['funding'] and not done['submit'],'successful unarmed stopped smoke')
    require(set(done['cleanup'])=={'B','C'} and all(v['cleanup_certain'] for v in done['cleanup'].values()),'both role cleanups certain')
    require(done['A_tunnel_prior_inactive_restored'] or done['prior_active_A_tunnel_preserved'],'exact prior A tunnel')
    cfg=read(P/'B/config.template.json')
    Q=next(p for p in W.parents if (p/'AGENTS.md').is_file())/'.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z'
    for name,pin in release['transport_source_pins'].items():require(sha(Q/name)==pin,'existing transport support pin')
    sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
    code='BASE='+repr(BASE)+'\nUNIT='+repr('kpi-finite-b-'+plan['standby_run_id']+'.service')+'\nROOT='+repr(plan['B_root'])+'\nMANIFEST='+repr(cfg['manifest_sha256'])+'\nINVENTORY='+repr(cfg['inventory_sha256'])+'\nBACKUP='+repr(cfg['backup_ciphertext_sha256'])+'\n'+r'''
import pathlib,json,hashlib,os,stat,subprocess,re
P=pathlib.Path;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=P('/srv/kpi-recovery/jail/instances')/BASE;root=P(ROOT);dest=root/'retained-smoke-instance'
assert root.is_dir() and not root.is_symlink() and root.resolve()==root and root.stat().st_uid==0
assert src.is_dir() and not src.is_symlink() and src.resolve()==src and not dest.exists() and not dest.is_symlink()
assert root.stat().st_dev==src.stat().st_dev,'atomic same-filesystem retention only'
assert sha(src/'public/manifest.json')==MANIFEST and sha(src/'public/inventory.json')==INVENTORY and sha(src/'backup/backup-package.json')==BACKUP
# Never read/export unlock/key plaintext. Atomic rename preserves the inodes.
names=['','public','backup','backup/unlock.key','backup/backup-package.json']
meta={n:(src/n).stat() for n in names}
assert (meta[''].st_uid,meta[''].st_gid,stat.S_IMODE(meta[''].st_mode))==(0,988,0o750)
assert (meta['backup'].st_uid,meta['backup'].st_gid,stat.S_IMODE(meta['backup'].st_mode))==(999,988,0o700)
assert (meta['backup/unlock.key'].st_uid,meta['backup/unlock.key'].st_gid,stat.S_IMODE(meta['backup/unlock.key'].st_mode))==(999,988,0o600)
def active():
 raw=subprocess.check_output(['systemctl','list-units','--type=service','--state=active','--no-legend','--plain'],text=True,timeout=5)
 units=[line.split()[0] for line in raw.splitlines() if line.strip()];snapshot={}
 for unit in units:
  raw=subprocess.check_output(['systemctl','show',unit,'--property=MainPID,ControlPID,ActiveState,BindReadOnlyPaths,Environment,ExecStart'],text=True,timeout=3)
  v=dict(x.split('=',1) for x in raw.splitlines() if '=' in x)
  if unit.startswith('kpi-'):snapshot[unit]=(v.get('MainPID'),v.get('ControlPID'),v.get('ActiveState'))
  assert BASE not in raw,'active unit property references new BASE'
  # Configs explicitly present in service argv/binds must not name the BASE.
  for name in re.findall(r'/[^\s:;={}]+\.json',raw):
   p=P(name)
   if p.is_file():
    assert p.stat().st_size<=2*1024*1024,'bounded active config inspection'
    assert BASE.encode() not in p.read_bytes(),'active unit config references new BASE'
  assert unit!=UNIT,'own smoke finite B must be inactive before retaining BASE'
 return snapshot
before=active();assert active()==before,'stable active unit process snapshot'
os.rename(src,dest)
for n,m in meta.items():
 z=(dest/n).stat();assert (z.st_dev,z.st_ino,z.st_mode,z.st_uid,z.st_gid,z.st_size)==(m.st_dev,m.st_ino,m.st_mode,m.st_uid,m.st_gid,m.st_size)
assert not src.exists() and not src.is_symlink()
for parent in [src.parent,dest.parent]:
 fd=os.open(parent,os.O_DIRECTORY);os.fsync(fd);os.close(fd)
print(json.dumps({'passed':True,'base_instance_id':BASE,'original_instance_path':str(src),'retained_instance_path':str(dest),'atomic_same_filesystem_move':True,'inode_mode_UID_private_bytes_preserved':True,'all_active_config_reference_scan_passed':True,'stable_KPI_unit_count':len(before),'production_BASE_namespace_absent':True,'funding':False,'submit':False,'private_contents_exported':False}))
'''
    result=json.loads(dedicated_remote.run('@B_SSH_HOST@',remote_safety.wrap(code,'B','cold-smoke-retain-new-unfunded'),60));require(result['passed'] and result['production_BASE_namespace_absent'],'exact smoke retention actual PASS')
    with (W/'SMOKE-INSTANCE-RETENTION.private.json').open('x') as f:os.fchmod(f.fileno(),0o600);json.dump(result,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return result
