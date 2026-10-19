import sys,json,os,time,subprocess
from pathlib import Path
sys.path.insert(0,'/opt/kpi-staged-tn10/remote-cuda')
from common import json_request,atomic
from provider import provider_request
root=Path('/var/lib/kpi-cuda-guard/tn10-live-20261019');lease=json.loads((root/'lease.json').read_text());pod=provider_request('https://rest.runpod.io/v1/pods/'+lease['podId'],os.environ['RUNPOD_API_KEY'])
s={'provider':{k:pod.get(k) for k in ['id','desiredStatus','imageName','createdAt','costPerHr','gpuCount','gpuTypeId']},'guardService':subprocess.check_output(['systemctl','show','kpi-cuda-guard','--property=ActiveState','--property=MainPID'],text=True).splitlines(),'nowUnix':time.time(),'lease':lease}
try:s['status']=json_request(lease['serviceUrl']+'/v1/status',os.environ['KPI_GPU_TOKEN'])
except Exception as e:s['serviceError']={'type':type(e).__name__,'code':getattr(e,'code',None)}
p=Path('/var/lib/kpi-cuda-guard/artifacts/guard.json')
if p.exists():s['guard']=json.loads(p.read_text())
atomic(root/'status05.json',s);print(json.dumps({'provider':s['provider'],'guard':s.get('guard'),'status':{k:s.get('status',{}).get(k) for k in ['state','phase','results','failureType','guardHeartbeatFresh']},'serviceError':s.get('serviceError')},indent=2))
