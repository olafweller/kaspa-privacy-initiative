"""Reviewed-stage only: dedicated B -> C fresh BASE public inventory, never active paths."""
from pathlib import Path
import sys,json,os,hashlib
O=Path(__file__).resolve().parent
Q=Path('@KPI_REPO@/.local/g5-preparation/orchestrator-dedicated-B-fresh-preparation-20261007T045400Z')
sys.path.insert(0,str(Q));import dedicated_remote,remote_safety
PLAN=json.loads((O.parent/'package-standby-cwd/STAGE-PLAN.json').read_bytes())
BROOT=PLAN['B_root']+'/transfer'
CROOT=PLAN['C_root']+'/transfer'
BASE=Path(PLAN['public_export']['public_path']).parent
INVENTORY=json.loads((BASE/'public/inventory.json').read_bytes())
SDK={x['path']:x['sha256'] for x in INVENTORY['files']}|{'inventory.json':hashlib.sha256((BASE/'public/inventory.json').read_bytes()).hexdigest()}
NODE={}
PUBLIC_DEST=PLAN['C_root']+'/public'
PUBLIC_TAR_SHA=PLAN['public_export']['public_tar_sha256']
def run(role,code,timeout=30):
 label='@B_SSH_HOST@' if role=='B' else '@C_SSH_HOST@'
 return json.loads(dedicated_remote.run(label,remote_safety.wrap(code,role,'public-transfer'),timeout))
def save(name,v):
 p=O/(name+'.private.json');p.write_text(json.dumps(v,indent=2)+'\n');p.chmod(0o600)
def execute():
 if not (O/'ROOT-STANDBY-CWD-RELEASE.json').is_file():raise RuntimeError('Root reviewed stage release required')
 release=json.loads((O/'ROOT-STANDBY-CWD-RELEASE.json').read_bytes())
 if release.get('plan_sha256')!=hashlib.sha256((O.parent/'package-standby-cwd/STAGE-PLAN.json').read_bytes()).hexdigest():raise RuntimeError('Plan digest mismatch')
 if release.get('transfer_source_sha256')!=hashlib.sha256(Path(__file__).read_bytes()).hexdigest():raise RuntimeError('Review source digest mismatch')
 btarget=dedicated_remote.binding()['SSH_target'];ctarget=dedicated_remote.target_C();cip=ctarget.split('@')[-1]
 import ipaddress
 ipaddress.ip_address(cip)
 key=None;line=None;setup_attempted=False;key_attempted=False
 try:
  key_attempted=True
  key=run('C','R='+repr(CROOT)+'\n'+r'''
import pathlib,subprocess,json,os
r=pathlib.Path(R);assert r.is_dir() and r.stat().st_uid==0 and r.stat().st_mode&0o777==0o700
assert not (r/'node_pull_key').exists()
subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(r/'node_pull_key'),'-C','kpi-finite-standby-credit-public-20261007T101055Z'],check=True,capture_output=True,timeout=10)
print(json.dumps({'public':(r/'node_pull_key.pub').read_text().strip()}))
''')
  line='restrict,from="'+cip+'",command="/usr/bin/timeout 180s /usr/bin/cat '+BROOT+'/public-node-sdk.tar" '+key['public']+'\n'
  setup_attempted=True
  host=run('B','R='+repr(BROOT)+'\nPINS='+repr(SDK)+'\nNODE='+repr(NODE)+'\nLINE='+repr(line)+'\nPUBLIC_TAR_SHA='+repr(PUBLIC_TAR_SHA)+'\n'+r'''
import pathlib,hashlib,json,os,tarfile
r=pathlib.Path(R);assert r.is_dir() and r.stat().st_uid==0 and r.stat().st_mode&0o777==0o700
bundle=r/'public-node-sdk.tar'
assert bundle.stat().st_size<=160*1024*1024 and hashlib.sha256(bundle.read_bytes()).hexdigest()==PUBLIC_TAR_SHA
a=pathlib.Path('/root/.ssh/authorized_keys');before=a.read_bytes();assert not before or before.endswith(b'\n');assert LINE.encode() not in before
with (r/'authorized_keys.runtime-transfer.preimage').open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(before);f.flush();os.fsync(f.fileno())
with a.open('ab') as f:f.write(LINE.encode());f.flush();os.fsync(f.fileno())
print(json.dumps({'hostkey':pathlib.Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().strip(),'bundle_sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'bundle_bytes':bundle.stat().st_size,'auth_preimage_sha256':hashlib.sha256(before).hexdigest()}))
''',35)
  # The exact B host key returned above must match the already-qualified local key.
  import subprocess
  binding=dedicated_remote.binding();known=Path(binding['known_hosts_file']).read_text().splitlines();hk=host['hostkey'].split()[:2]
  if not any(hk[0]+' '+hk[1] in row for row in known):raise RuntimeError('B host key does not match qualified known_hosts')
  value=run('C','R='+repr(CROOT)+'\nTARGET='+repr(btarget)+'\nHOSTKEY='+repr(' '.join(hk))+'\nPIN='+repr(host['bundle_sha256'])+'\nPINS='+repr(SDK)+'\nNODE='+repr(NODE)+'\nPUBLIC_DEST='+repr(PUBLIC_DEST)+'\n'+r'''
import pathlib,subprocess,hashlib,json,os,tarfile,time
r=pathlib.Path(R);known=r/'B-runtime-known_hosts'
with known.open('x') as f:os.fchmod(f.fileno(),0o600);f.write(TARGET.split('@')[-1]+' '+HOSTKEY+'\n')
args=['ssh','-T','-F','/dev/null','-i',str(r/'node_pull_key'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known),'-o','HostKeyAlgorithms=ssh-ed25519','-o','ForwardAgent=no','-o','ClearAllForwardings=yes','-o','ConnectTimeout=10',TARGET]
archive=r/'public-node-sdk.tar';started=time.monotonic()
with archive.open('xb') as f:
 os.fchmod(f.fileno(),0o600);result=subprocess.run(args,stdout=f,stderr=subprocess.PIPE,timeout=180);f.flush();os.fsync(f.fileno())
assert result.returncode==0 and hashlib.sha256(archive.read_bytes()).hexdigest()==PIN
expected=PINS;destroot=pathlib.Path(PUBLIC_DEST);destroot.mkdir(mode=0o700,exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert {m.name for m in members}==set(expected) and len(members)==len(expected)
 for m in members:
  assert m.isfile() and m.size<=100000000
  raw=tar.extractfile(m).read();assert hashlib.sha256(raw).hexdigest()==expected[m.name]
  dest=destroot/m.name;assert pathlib.Path(m.name).name==m.name
  with dest.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
assert hashlib.sha256((destroot/'inventory.json').read_bytes()).hexdigest()==PINS['inventory.json']
print(json.dumps({'direct_dedicated_B_to_C':True,'public_files_sha256':PINS,'bundle_sha256':PIN,'seconds':time.monotonic()-started,'active_paths_modified':False}))
''',195)
  save('C-standby-credit-public-transfer',value)
  return value
 finally:
  errors=[]
  if setup_attempted:
   try:
    v=run('B','R='+repr(BROOT)+'\nLINE='+repr(line)+'\nPUBLIC_TAR_SHA='+repr(PUBLIC_TAR_SHA)+'\n'+r'''
import pathlib,os,json,hashlib
r=pathlib.Path(R);a=pathlib.Path('/root/.ssh/authorized_keys');raw=a.read_bytes();target=LINE.encode();lines=raw.splitlines(keepends=True);count=lines.count(target);assert count<=1
if count:
 with a.open('wb') as f:f.write(b''.join(x for x in lines if x!=target));f.flush();os.fsync(f.fileno())
assert target not in a.read_bytes()
pre=r/'authorized_keys.runtime-transfer.preimage'
print(json.dumps({'temporary_exact_sender_line_removed':True,'auth_preimage_preserved':pre.exists(),'auth_equals_preimage':pre.exists() and a.read_bytes()==pre.read_bytes()}))
''');save('B-standby-credit-transfer-auth-cleanup',v)
   except Exception as exc:errors.append('B exact-line revocation '+type(exc).__name__)
  if key_attempted:
   try:
    v=run('C','R='+repr(CROOT)+'\n'+r'''
import pathlib,json
r=pathlib.Path(R)
for n in ['node_pull_key','node_pull_key.pub']:
 p=r/n
 if p.exists():p.unlink()
assert not (r/'node_pull_key').exists();print(json.dumps({'private_transfer_key_removed':True}))
''');save('C-standby-credit-transfer-key-cleanup',v)
   except Exception as exc:errors.append('C private-key cleanup '+type(exc).__name__)
  if errors:raise RuntimeError('; '.join(errors))
if __name__=='__main__':print(json.dumps(execute()))
