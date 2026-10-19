import sys,json,os,time,tarfile,hashlib
from pathlib import Path
sys.path.insert(0,'/opt/kpi-staged-tn10/remote-cuda')
from common import atomic,sha,lease_check
from staged_verify import verify
root=Path('/var/lib/kpi-cuda-guard/tn10-live-20261019');package=Path('/opt/kpi-staged-tn10/package');lease=json.loads((root/'lease.json').read_text());a=Path('/var/lib/kpi-cuda-guard/artifacts')
m=json.loads((a/'terminal-backup.json').read_text());assert m['leaseDigest']==lease_check(lease)
archive=a/(m['sha256']+'.tar.gz');assert archive.stat().st_size==m['bytes'] and sha(archive.read_bytes())==m['sha256']
with tarfile.open(archive) as tar:
 s=json.loads(tar.extractfile('service-state.json').read());ledger=json.loads(tar.extractfile('ledger.json').read());stats={stage:json.loads(tar.extractfile('stages/'+stage+'/proof/stats.json').read()) for stage in ('deposit','credit-transfer','exit','reconcile')}
assert s['state']=='completed' and ledger['completed']==['deposit','credit-transfer','exit','reconcile'] and ledger['attempted']==ledger['completed']
out=root/'verified/final';r=verify(package,archive,root/'targets-index.json',out);assert r['allFourVerified']
s['ledger']=ledger
result={'archivePath':str(archive),'archiveSha256':m['sha256'],'archiveBytes':m['bytes'],'verification':r,'status':s,'stats':stats,'retrievedUnix':time.time(),'backup':m}
atomic(root/'final-result.json',result);print(json.dumps(result,indent=2))
