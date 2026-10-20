import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda')
from provider import provider_request,created_unix
from common import atomic
r=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01');lease=json.loads((r/'lease.json').read_text())
p=provider_request('https://rest.runpod.io/v1/pods/'+lease['podId'],os.environ['RUNPOD_API_KEY'])
assert p['id']==lease['podId'] and abs(created_unix(p['createdAt'])-lease['createdUnix'])<=1
now=time.time();stop=r/'artifacts/stop.json';record=json.loads(stop.read_text()) if stop.exists() else None
public={k:p.get(k) for k in ['id','desiredStatus','createdAt','lastStatusChange','costPerHr','gpuCount','volumeInGb','containerDiskInGb','networkVolumeId']}
out={'observedUnix':now,'provider':public,'providerDesiredExitedConfirmed':p['desiredStatus']=='EXITED','guardStop':record,'actualInvoiceChargesAvailable':False}
if out['providerDesiredExitedConfirmed']:
 assert record and record['providerDesiredExitedConfirmed'],'provider stopped but independent guard record missing'
 atomic(r/'results/provider-stop-observation.json',out)
print(json.dumps(out,indent=2))
