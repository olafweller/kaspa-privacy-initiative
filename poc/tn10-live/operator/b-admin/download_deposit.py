import sys,json,os,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-staged-tn10/remote-cuda')
from common import json_request,request,atomic,sha
from watchdog import save_archive
from staged_verify import verify
root=Path('/var/lib/kpi-cuda-guard/tn10-live-20261019');package=Path('/opt/kpi-staged-tn10/package');lease=json.loads((root/'lease.json').read_text());stage='deposit'
s=json_request(lease['serviceUrl']+'/v1/status',os.environ['KPI_GPU_TOKEN'])
assert s['state'] in ('waiting','completed','failed','interrupted'),'stage still running'
data=request(lease['serviceUrl']+'/v1/artifacts',os.environ['KPI_GPU_TOKEN']);assert sha(data)==s['artifact']['sha256'] and len(data)==s['artifact']['bytes']
directory=root/'downloads'/stage;directory.mkdir(parents=True);save_archive(directory,data)
archive=directory/(sha(data)+'.tar.gz');out=root/'verified'/stage;out.parent.mkdir(exist_ok=True)
r=verify(package,archive,root/'targets-index.json',out)
result={'stage':stage,'archiveSha256':sha(data),'archiveBytes':len(data),'archivePath':str(archive),'verification':r,'status':s,'retrievedUnix':time.time()}
atomic(root/(stage+'-result.json'),result);print(json.dumps(result,indent=2))
