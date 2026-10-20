import json,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda/recovery-six-client-20261020-archive-fix/poc/remote-cuda')
from recovery_control import extract
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01');m=json.loads((root/'artifacts/latest-artifact.json').read_text())
with tempfile.TemporaryDirectory(prefix='diagnostics-',dir=root) as tmp:
 out=Path(tmp)/'returned';extract(root/'artifacts'/(m['sha256']+'.tar.gz'),out,m['sha256'])
 r={'observedUnix':time.time()}
 for n in ('aggregate.stderr.log','aggregate.samples.jsonl'):
  p=out/n
  if p.exists():r[n]=p.read_text().splitlines()[-8:]
 print(json.dumps(r,indent=2))
