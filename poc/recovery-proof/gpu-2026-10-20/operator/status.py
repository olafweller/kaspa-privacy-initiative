import json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda')
from common import json_request
from provider import provider_request
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01');lease=json.loads((root/'lease.json').read_text())
p=provider_request('https://rest.runpod.io/v1/pods/'+lease['podId'],os.environ['RUNPOD_API_KEY'])
r={'observedUnix':time.time(),'provider':{k:p.get(k) for k in ('id','desiredStatus','createdAt','lastStatusChange')},'guardService':subprocess.check_output(['systemctl','show','kpi-cuda-recovery-six-20261020-01.service','--property=ActiveState','--property=SubState'],text=True).splitlines()}
for n in ('guard','latest-artifact','terminal-backup','stop','last-error'):
 path=root/'artifacts'/(n+'.json')
 if path.exists():r[n]=json.loads(path.read_text())
if p['desiredStatus']=='RUNNING':
 try:r['gpu']=json_request(lease['serviceUrl']+'/v1/status',os.environ['KPI_GPU_TOKEN'])
 except Exception as e:r['gpuError']={'type':type(e).__name__,'code':getattr(e,'code',None)}
print(json.dumps(r,indent=2))
