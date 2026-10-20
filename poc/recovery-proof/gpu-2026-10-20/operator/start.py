import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda')
from common import atomic,json_request,lease_check
from provider import provider_request,created_unix
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01')
lease=json.loads((root/'lease.json').read_text())
image='ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:442bc15d6d4cece6e0cd28b30862a0a9c15c64c67a637275fd45ea648600a628'
p=provider_request('https://rest.runpod.io/v1/pods/'+lease['podId'],os.environ['RUNPOD_API_KEY'])
assert p['id']==lease['podId'] and p['desiredStatus']=='RUNNING' and p['imageName']==image
assert p['gpuCount']==1 and p['gpuTypeId']=='NVIDIA L40S' and p['memoryInGb']>=32 and p['vcpuCount']>=4
assert p['containerDiskInGb']==90 and p['volumeInGb']==10 and p['volumeMountPath']=='/workspace'
assert abs(created_unix(p['createdAt'])-lease['createdUnix'])<=1 and lease['stopUnix']==lease['createdUnix']+7200
assert time.time()+3960<lease['stopUnix'],'need full hour plus 300s transfer margin before guard stop at lease minus 60s'
g=json.loads((root/'artifacts/guard.json').read_text());assert time.time()-g['heartbeatUnix']<30 and g['leaseDigest']==lease_check(lease)
s=json_request(lease['serviceUrl']+'/v1/status',os.environ['KPI_GPU_TOKEN'])
assert s['state']=='idle' and s['scope']=='FIXED_RECOVERY_SIX_SUCCINCT_RECEIPTS' and s['guardHeartbeatFresh'] and s['leaseDigest']==lease_check(lease) and s['podId']==lease['podId']
atomic(root/'pre-start-readback.json',{'unixSeconds':time.time(),'providerImageReference':p['imageName'],'scope':s['scope'],'provider':{k:p.get(k) for k in ['id','createdAt','desiredStatus','costPerHr','gpuCount','gpuTypeId','memoryInGb','vcpuCount','containerDiskInGb','volumeInGb','volumeMountPath']},'guard':g,'service':s,'remainingSeconds':lease['stopUnix']-time.time()})
with (root/'start-intent.json').open('x') as f:
 json.dump({'unixSeconds':time.time(),'podId':lease['podId'],'attempt':1,'proofSecondsLimit':3600,'cycleLimitPerBatch':160000000,'orderedBatches':['deposit','credit-transfer','bob-exit','bob-reconcile','alice-exit','alice-reconcile'],'effectiveGuardStopUnix':lease['stopUnix']-60,'scope':s['scope']},f,indent=2);f.flush();os.fsync(f.fileno())
r=json_request(lease['serviceUrl']+'/v1/start',os.environ['KPI_GPU_TOKEN'],'POST',{})
atomic(root/'start-response.json',r)
assert r.get('alreadyStarted') is False,'server reported an old attempt; do not accept/retry'
print(json.dumps({'startResponse':r,'providerImageReference':p['imageName'],'scope':s['scope'],'remainingSeconds':lease['stopUnix']-time.time(),'stopUnix':lease['stopUnix']},indent=2))
