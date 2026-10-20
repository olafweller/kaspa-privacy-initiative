"""Export explicitly allowlisted public evidence; never credentials or wallet data."""
import hashlib,io,json,tarfile,time
from pathlib import Path
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01')
files={}
for n in ('package-qualified.json','quote.json','allocation-intent.json','allocated-pod.json','lease.json','provider-allocation-readback.json','allocation-complete.json','pre-start-readback.json','start-intent.json','start-response.json','deletion-intent.json','results/provider-stop-observation.json','results/provider-deletion.json','results/cloud-recovery-verification.json'):
 p=root/n
 if p.exists():files[n]=p
for folder in ('artifacts','results'):
 for p in (root/folder).rglob('*'):
  if p.is_file() and not p.is_symlink() and (p.suffix in ('.json','.jsonl','.bin','.log') or p.name=='native-identities-and-negatives.json'):
   files[p.relative_to(root).as_posix()]=p
m=json.loads((root/'artifacts/terminal-backup.json').read_text());p=root/'artifacts'/(m['sha256']+'.tar.gz')
assert p.stat().st_size==m['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
files['terminal-artifacts.tar.gz']=p
unit=Path('/etc/systemd/system/kpi-cuda-recovery-six-20261020-01.service');files['guard.service']=unit
assert all(not p.is_symlink() and p.stat().st_size<=32*1024**2 for p in files.values())
records={n:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for n,p in files.items()}
export=root/'public-evidence.tar.gz'
with tarfile.open(export,'w:gz') as tar:
 for n,p in sorted(files.items()):
  data=p.read_bytes();item=tarfile.TarInfo(n);item.size=len(data);item.mode=0o644;tar.addfile(item,io.BytesIO(data))
 data=(json.dumps({'scope':'PUBLIC_GPU_RUN_EXPORT','files':records},indent=2)+'\n').encode();item=tarfile.TarInfo('b-export-manifest.json');item.size=len(data);item.mode=0o644;tar.addfile(item,io.BytesIO(data))
print(json.dumps({'export':str(export),'bytes':export.stat().st_size,'sha256':hashlib.sha256(export.read_bytes()).hexdigest(),'fileCount':len(files),'observedUnix':time.time()}))
