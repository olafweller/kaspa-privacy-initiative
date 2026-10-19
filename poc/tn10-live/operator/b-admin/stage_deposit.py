import sys,json,os,time,subprocess
from pathlib import Path
sys.path.insert(0,'/opt/kpi-staged-tn10/remote-cuda')
from common import json_request,atomic,sha
from staged_policy import check,unpack
root=Path('/var/lib/kpi-cuda-guard/tn10-live-20261019');package=Path('/opt/kpi-staged-tn10/package');lease=json.loads((root/'lease.json').read_text());policy=check(package)
stage='deposit';target=root/'targets'/f'{stage}.json';expected='685c2d754a5fa64b09102801a4e7f63a6a78f10722c25025c371ca62c6dec13e';archive=root/'public'/f'{stage}.tar.gz'
assert sha(target.read_bytes())==expected;unpack(archive.read_bytes(),expected,policy,stage)
s=json_request(lease['serviceUrl']+'/v1/status',os.environ['KPI_GPU_TOKEN'])
assert s['scope']==policy['scope'] and s['trial']==policy['trial'] and s['packagePolicySha256']==lease['packagePolicySha256']
assert s['state']=='idle' and s['ledger'] is None and not s['results'] and not s['received']
assert s['guardHeartbeatFresh'] and lease['stopUnix']-time.time()>3960
h=json.loads(Path('/var/lib/kpi-cuda-guard/artifacts/guard.json').read_text());assert time.time()-h['heartbeatUnix']<30 and h['leaseDigest']==s['leaseDigest']
atomic(root/'targets-index.json',{stage:{'targetPath':str(target),'targetSha256':expected}})
args=['/usr/bin/python3','/opt/kpi-staged-tn10/remote-cuda/staged_control.py']
common=['--lease',str(root/'lease.json'),'--package',str(package),'--stage',stage,'--expected-target-sha',expected]
subprocess.run(args+['approve',*common,'--target',str(target)],check=True)
subprocess.run(args+['submit',*common,'--archive',str(archive)],check=True)
