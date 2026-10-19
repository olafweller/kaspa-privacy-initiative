import json,os,sys,time,subprocess
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda')
from common import atomic
from provider import provider_request,created_unix
root=Path('/var/lib/kpi-cuda-guard/tn10-live-20261019');lease=json.loads((root/'lease.json').read_text());p=provider_request('https://rest.runpod.io/v1/pods/'+lease['podId'],os.environ['RUNPOD_API_KEY'])
assert p['id']==lease['podId'] and abs(created_unix(p['createdAt'])-lease['createdUnix'])<=1
stop=json.loads(Path('/var/lib/kpi-cuda-guard/artifacts/stop.json').read_text())
assert stop['providerDesiredExitedConfirmed'] and stop['podId']==lease['podId'] and p['desiredStatus']=='EXITED'
result={'observedUnix':time.time(),'providerDesiredExitedConfirmed':True,'provider':{k:p.get(k) for k in ['id','createdAt','desiredStatus','costPerHr','adjustedCostPerHr','lastStartedAt','lastStoppedAt','gpuCount','gpuTypeId','volumeInGb','containerDiskInGb','networkVolumeId']},'guardStop':stop,'guardService':subprocess.check_output(['systemctl','show','kpi-cuda-guard','--property=ActiveState','--property=SubState','--property=MainPID'],text=True).splitlines(),'invoiceAvailable':False}
atomic(root/'provider-stop-readback.json',result);print(json.dumps(result,indent=2))
