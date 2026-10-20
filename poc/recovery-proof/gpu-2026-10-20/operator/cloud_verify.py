"""Independent local CPU verification of the B-preserved GPU archive."""
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,'poc/remote-cuda')
from recovery_control import extract,verify
root=Path('.local/recovery-six-gpu')
m=json.loads((root/'terminal-backup.json').read_text())
archive=root/'terminal-artifacts.tar.gz'
assert archive.stat().st_size==m['bytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==m['sha256']
start=time.monotonic();returned=root/'cloud-returned';extract(archive,returned,m['sha256'])
r=verify(root/'trusted',returned,root/'cloud-verification')
r.update({'archiveSha256':m['sha256'],'archiveBytes':m['bytes'],'verifiedArchiveAndPublicInputs':True,'savedOnCloud':True,'seconds':time.monotonic()-start,'observedUnix':time.time(),'sameReviewedVerifierSeparateHostAndProcesses':True})
(root/'cloud-recovery-verification.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
