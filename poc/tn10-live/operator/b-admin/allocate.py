"""B-only one-shot allocation under the owner's explicit single-attempt TN10 release."""
import datetime,hashlib,json,os,pwd,grp,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda')
from common import atomic,json_request,lease_check
from provider import provider_request,created_unix
root=Path('/var/lib/kpi-cuda-guard/tn10-live-20261019')
image='ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:fa4f72f0e060325a951eac33ea01ef00d3593ffe68531d69cf6a8b09daf41aa1'
name='kpi-tn10-live-20261019'
unit='kpi-cuda-guard.service'
assert (root/'targets/deposit.json').exists()
assert (root/'quote.json').exists()
sys.path.insert(0,'/opt/kpi-staged-tn10/remote-cuda')
from staged_policy import check
policy=check(Path('/opt/kpi-staged-tn10/package'))
assert os.geteuid()==0 and os.environ['RUNPOD_API_KEY'] and len(os.environ['KPI_GPU_TOKEN'])>=32
assert subprocess.check_output(['hostname','-f'],text=True).strip()=='vmi3641034.contaboserver.net'
assert subprocess.check_output(['timedatectl','show','--value','--property=NTPSynchronized'],text=True).strip()=='yes'
assert shutil.disk_usage(root).free>10*1024**3
for n,h in {'common.py':'5ed5815ae1177f5915852477d270110f3768bd6b61ff5ebd5833b62526e549c3','provider.py':'9e1a65b68da2cff78d3549b6b72c83a6bcbf8a7a540fa7aa1d6faafbebe7380f','watchdog.py':'f057acefdd5d7c54075711228ae5490b5252bb610605837c74b244c1261ed9d0'}.items():
 assert hashlib.sha256((Path('/opt/kpi-remote-cuda')/n).read_bytes()).hexdigest()==h,n
assert not (root/'lease.json').exists() and not (root/'allocation-intent.json').exists()
assert 'ActiveState=inactive' in subprocess.check_output(['systemctl','show',unit,'--property=ActiveState'],text=True)
query='query($input: GpuLowestPriceInput!) { gpuTypes(input: {id: "NVIDIA L40S"}) { id securePrice lowestPrice(input: $input) { gpuTypeId uninterruptablePrice minMemory minVcpu } } }'
q=json_request('https://api.runpod.io/graphql',os.environ['RUNPOD_API_KEY'],'POST',{'query':query,'variables':{'input':{'gpuCount':1,'minMemoryInGb':32,'minVcpuCount':4,'secureCloud':True,'totalDisk':100}}})
assert not q.get('errors'), 'provider catalog query failed'
gpus=q['data']['gpuTypes'];assert len(gpus)==1 and gpus[0]['id']=='NVIDIA L40S'
available=gpus[0]['lowestPrice'];assert available and available['gpuTypeId']=='NVIDIA L40S'
hourly=float(available['uninterruptablePrice']);assert (hourly+.014)*2+.0028*24<=5
pods=json_request('https://rest.runpod.io/v1/pods',os.environ['RUNPOD_API_KEY']);assert isinstance(pods,list)
assert not any(p.get('name')==name for p in pods),'existing matching allocation; do not allocate twice'
intent={'unixSeconds':time.time(),'name':name,'imageName':image,'ownerAuthorization':'Explicit consent in Chat, 2026-10-19; one bounded actual-TN10 attempt','gpuQuote':gpus[0],'gpuCount':1,'gpuType':'NVIDIA L40S','activeStorageHourlyUsd':.014,'stoppedStorageHourlyUsd':.0028,'planningTotalWith24hRetentionUsd':(hourly+.014)*2+.0028*24,'wholeProofSecondsLimit':3600,'rentalSecondsLimit':7200,'existingPodCount':len(pods)}
with (root/'allocation-intent.json').open('x') as f:
 json.dump(intent,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
fd=os.open(root,os.O_RDONLY);os.fsync(fd);os.close(fd)
request={'name':name,'computeType':'GPU','cloudType':'SECURE','gpuTypeIds':['NVIDIA L40S'],'gpuCount':1,'gpuTypePriority':'availability','imageName':image,'containerDiskInGb':90,'volumeInGb':10,'volumeMountPath':'/workspace','minRAMPerGPU':32,'minVCPUPerGPU':4,'ports':['8080/http'],'env':{'KPI_GPU_TOKEN':os.environ['KPI_GPU_TOKEN'],'NVIDIA_DRIVER_CAPABILITIES':'compute,utility'}}
pod_id=None
try:
 try:
  p=json_request('https://rest.runpod.io/v1/pods',os.environ['RUNPOD_API_KEY'],'POST',request)
  pod_id=p['id']
 except Exception as error:
  atomic(root/'allocation-response-error.json',{'errorType':type(error).__name__,'httpCode':getattr(error,'code',None),'unixSeconds':time.time(),'creationMustNotBeRetried':True})
  # Reconcile the sole request by its unique intent, without repeating creation.
  for attempt in range(4):
   candidates=[p for p in json_request('https://rest.runpod.io/v1/pods',os.environ['RUNPOD_API_KEY']) if p.get('name')==name and p.get('imageName')==image]
   assert len(candidates)<=1,'ambiguous allocation identity'
   if candidates:
    p=candidates[0];pod_id=p['id'];break
   if attempt<3:time.sleep(5)
  if pod_id is None:raise RuntimeError('Allocation response failed; no matching Pod found; no retry permitted') from error
 atomic(root/'allocated-pod.json',{k:p.get(k) for k in ['id','name','createdAt','desiredStatus','costPerHr','imageName','gpuCount','volumeInGb','containerDiskInGb']})
 p=provider_request('https://rest.runpod.io/v1/pods/'+pod_id,os.environ['RUNPOD_API_KEY'])
 created=created_unix(p['createdAt'])
 assert created>=intent['unixSeconds']-60,'provider creation predates this attempt'
 lease={'podId':pod_id,'gpuCount':1,'gpuType':'NVIDIA L40S','createdUnix':created,'stopUnix':created+7200,'serviceUrl':'https://'+pod_id+'-8080.proxy.runpod.net','actualGpuHourlyUsd':str(p['costPerHr']),'actualStorageHourlyUsd':'0.014','stoppedStorageHourlyUsd':'0.0028','retentionHours':24,'workloadScope':policy['scope'],'trial':policy['trial'],'packagePolicySha256':hashlib.sha256(Path('/opt/kpi-staged-tn10/package/staged-policy.json').read_bytes()).hexdigest()}
 lease_check(lease)
 path=root/'lease.json';atomic(path,lease);os.chown(path,pwd.getpwnam('kpi-cuda-guard').pw_uid,grp.getgrnam('kpi-cuda-guard').gr_gid);os.chmod(path,0o600)
 shared=Path('/var/lib/kpi-cuda-guard');old=shared/'lease.json';backup=shared/'lease.before-tn10-live-20261019.json'
 if old.exists():assert not backup.exists();old.rename(backup)
 atomic(old,lease);os.chown(old,pwd.getpwnam('kpi-cuda-guard').pw_uid,grp.getgrnam('kpi-cuda-guard').gr_gid);old.chmod(0o600)
 artifacts=shared/'artifacts'
 if artifacts.exists():artifacts.rename(shared/'artifacts.before-tn10-live-20261019')
 artifacts.mkdir(mode=0o750);os.chown(artifacts,pwd.getpwnam('kpi-cuda-guard').pw_uid,grp.getgrnam('kpi-cuda-guard').gr_gid)
 subprocess.run(['systemctl','enable','--now',unit],check=True,capture_output=True)
 valid=(p['gpuCount']==1 and p['gpuTypeId']=='NVIDIA L40S' and p['imageName']==image and p['memoryInGb']>=32 and p['vcpuCount']>=4 and p['volumeInGb']==10 and p['containerDiskInGb']==90 and p['volumeMountPath']=='/workspace')
 public={k:p.get(k) for k in ['id','name','createdAt','desiredStatus','gpuCount','gpuTypeId','costPerHr','imageName','memoryInGb','vcpuCount','volumeInGb','containerDiskInGb','volumeMountPath']}
 atomic(root/'provider-allocation-readback.json',public)
 assert valid,'actual Pod does not match the approved configuration'
 service=subprocess.check_output(['systemctl','show',unit,'--property=ActiveState','--property=SubState','--property=MainPID'],text=True)
 assert 'ActiveState=active' in service
 result={'provider':public,'lease':lease,'leaseDigest':lease_check(lease),'guardUnit':unit,'guardService':service.splitlines(),'proofStarted':False,'plannedMaxCostWith24hRetentionUsd':(float(p['costPerHr'])+.014)*2+.0028*24}
 atomic(root/'allocation-complete.json',result)
 print(json.dumps(result,indent=2))
except Exception as error:
 atomic(root/'allocation-failure.json',{'unixSeconds':time.time(),'podId':pod_id,'errorType':type(error).__name__,'noRetry':True})
 if pod_id:
  confirmed=False
  for attempt in range(7):
   try:
    p=provider_request('https://rest.runpod.io/v1/pods/'+pod_id,os.environ['RUNPOD_API_KEY'])
    if p.get('desiredStatus')!='EXITED':json_request('https://rest.runpod.io/v1/pods/'+pod_id+'/stop',os.environ['RUNPOD_API_KEY'],'POST')
    p=provider_request('https://rest.runpod.io/v1/pods/'+pod_id,os.environ['RUNPOD_API_KEY']);confirmed=p.get('desiredStatus')=='EXITED'
    if confirmed:break
   except Exception:pass
   if attempt<6:time.sleep(5)
  atomic(root/'allocation-failure-stop.json',{'podId':pod_id,'providerDesiredExitedConfirmed':confirmed,'unixSeconds':time.time()})
 raise
