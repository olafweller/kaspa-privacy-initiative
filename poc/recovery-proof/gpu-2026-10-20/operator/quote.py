import json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda')
from common import atomic,json_request
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01')
assert (root/'package-qualified.json').exists()
assert subprocess.check_output(['hostname','-f'],text=True).strip()=='vmi3641034.contaboserver.net'
query='query($input: GpuLowestPriceInput!) { gpuTypes(input: {id: "NVIDIA L40S"}) { id securePrice lowestPrice(input: $input) { gpuTypeId uninterruptablePrice minMemory minVcpu } } }'
response=json_request('https://api.runpod.io/graphql',os.environ['RUNPOD_API_KEY'],'POST',{'query':query,'variables':{'input':{'gpuCount':1,'minMemoryInGb':32,'minVcpuCount':4,'secureCloud':True,'totalDisk':100}}})
assert not response.get('errors'),'provider catalog query failed'
gpus=response['data']['gpuTypes'];assert len(gpus)==1 and gpus[0]['id']=='NVIDIA L40S'
price=gpus[0]['lowestPrice'];assert price and price['gpuTypeId']=='NVIDIA L40S'
hourly=float(price['uninterruptablePrice']);estimate=(hourly+.014)*2+.0028*24;assert estimate<=5
pods=json_request('https://rest.runpod.io/v1/pods',os.environ['RUNPOD_API_KEY']);assert isinstance(pods,list)
assert not any(p.get('name')=='kpi-recovery-six-20261020-01' for p in pods)
result={'observedUnix':time.time(),'quote':gpus[0],'activeStorageHourlyUsdUpperBound':.014,'stoppedStorageHourlyUsdUpperBound':.0028,'storagePricingBasis':'90GB container + 10GB local volume; USD0.10/GB/month active, USD0.20/GB/month stopped volume, 720h/month; rounded upward','storagePricingSource':'https://docs.runpod.io/pods/pricing','planningTotalIncluding24hRetentionUsd':estimate,'planningLimitUsd':5,'existingPodCount':len(pods),'providerMutation':False}
atomic(root/'quote.json',result);print(json.dumps(result,indent=2))
