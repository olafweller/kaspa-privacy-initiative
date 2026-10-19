import json,os,subprocess,sys,time,shutil
from pathlib import Path
sys.path.insert(0,'/opt/kpi-staged-tn10/remote-cuda')
from common import atomic,json_request
root=Path('/var/lib/kpi-cuda-guard/tn10-live-20261019')
root.mkdir(mode=0o750,exist_ok=False)
assert subprocess.check_output(['timedatectl','show','--value','--property=NTPSynchronized'],text=True).strip()=='yes'
assert shutil.disk_usage(root).free>10*1024**3
assert subprocess.check_output(['hostname','-f'],text=True).strip()=='vmi3641034.contaboserver.net'
assert subprocess.run(['systemctl','is-active','kpi-cuda-guard'],capture_output=True,text=True).stdout.strip()=='inactive'
import staged_policy
policy=staged_policy.check(Path('/opt/kpi-staged-tn10/package'))
assert policy['trial']=='fb82dcc105bc33efaef6e20c28144f871204e16fce531ed2e643e90f91a9977a'
query='query($input: GpuLowestPriceInput!) { gpuTypes(input: {id: "NVIDIA L40S"}) { id securePrice lowestPrice(input: $input) { gpuTypeId uninterruptablePrice minMemory minVcpu } } }'
r=json_request('https://api.runpod.io/graphql',os.environ['RUNPOD_API_KEY'],'POST',{'query':query,'variables':{'input':{'gpuCount':1,'minMemoryInGb':32,'minVcpuCount':4,'secureCloud':True,'totalDisk':100}}})
assert not r.get('errors'),'catalog query failed'
g=r['data']['gpuTypes'];assert len(g)==1 and g[0]['id']=='NVIDIA L40S'
p=g[0]['lowestPrice'];assert p and p['gpuTypeId']=='NVIDIA L40S'
hourly=float(p['uninterruptablePrice']);estimate=(hourly+.014)*2+.0028*24;assert estimate<=5
pods=json_request('https://rest.runpod.io/v1/pods',os.environ['RUNPOD_API_KEY']);assert isinstance(pods,list)
r={'unixSeconds':time.time(),'quote':g[0],'activeStorageHourlyUsdUpperBound':.014,'stoppedStorageHourlyUsdUpperBound':.0028,'storagePricingBasis':'90GB container + 10GB local volume; USD0.10/GB/month active, USD0.20/GB/month stopped volume, 720h/month; rounded upward','storagePricingSource':'https://docs.runpod.io/pods/pricing','maxRentalHours':2,'retentionHoursBudgeted':24,'planningCostUsd':estimate,'limitUsd':5,'existingPodCount':len(pods),'matchingExistingPods':[{'id':p['id'],'name':p.get('name'),'status':p.get('desiredStatus')} for p in pods if p.get('name','').startswith('kpi-tn10-live-')],'credentialValuesPrinted':False,'providerMutation':False}
assert not r['matchingExistingPods']
atomic(root/'quote.json',r);print(json.dumps(r,indent=2))

import pwd,grp
os.chown(root,pwd.getpwnam('kpi-cuda-guard').pw_uid,grp.getgrnam('kpi-cuda-guard').gr_gid)
