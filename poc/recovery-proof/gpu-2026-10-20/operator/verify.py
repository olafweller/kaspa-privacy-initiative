"""Independently audit returned public receipts on B using only the trusted package."""
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda/recovery-six-client-20261020-archive-fix/poc/remote-cuda')
from common import atomic,lease_check
from recovery_control import extract,verify
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01')
package=Path('/opt/kpi-remote-cuda/recovery-six-proof-20261020-01')
m=json.loads((root/'artifacts/terminal-backup.json').read_text());lease=json.loads((root/'lease.json').read_text());assert m['leaseDigest']==lease_check(lease)
p=root/'artifacts'/(m['sha256']+'.tar.gz');assert p.stat().st_size==m['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
out=root/'results';out.mkdir(exist_ok=True);returned=out/'returned'
extracted=extract(p,returned,m['sha256'])
start=time.monotonic();result=verify(package,returned,out/'independent-verification')
assert p.stat().st_size==m['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
r={'scope':'INDEPENDENT_B_SIX_RECOVERY_RECEIPT_AUDIT_NOT_TN10','unixSeconds':time.time(),'seconds':time.monotonic()-start,'archiveSha256':m['sha256'],'archiveBytes':m['bytes'],'extracted':extracted,'archiveAndPublicInputsVerified':True,'result':result,'cryptographicSuccess':result['allSixFinalReceiptsVerified'],'actualTN10Broadcast':False}
for n in ('aggregate.resources','hardware','cuda-by-batch','complete','pipeline-complete','progress'):
 f=returned/(n+'.json')
 if f.exists():r[n]=json.loads(f.read_text())
r['stages']=[json.loads(f.read_text()) for f in sorted((returned/'stages').glob('*.json'))]
atomic(out/'b-verification.json',r);print(json.dumps(r,indent=2))
