import json,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda/recovery-six-client-20261020-archive-fix/poc/remote-cuda')
from recovery_control import extract
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01')
m=json.loads((root/'artifacts/latest-artifact.json').read_text())
with tempfile.TemporaryDirectory(prefix='progress-',dir=root) as tmp:
 out=Path(tmp)/'returned';extract(root/'artifacts'/(m['sha256']+'.tar.gz'),out,m['sha256'])
 result={'observedUnix':time.time(),'archive':m,'stages':[]}
 for p in sorted((out/'stages').glob('*.json')):
  r=json.loads(p.read_text());result['stages'].append({k:r.get(k) for k in ('case','kind','finished','exitCode','startedUnix','finishedUnix')})
 for n in ('complete','cuda-by-batch','aggregate.resources'):
  p=out/(n+'.json')
  if p.exists():result[n]=json.loads(p.read_text())
 print(json.dumps(result,indent=2))
