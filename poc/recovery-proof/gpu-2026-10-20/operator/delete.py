"""Remove only this lease after confirmed stop and verified external preservation."""
import hashlib,json,os,subprocess,sys,time,urllib.error
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda')
from common import atomic,json_request
from provider import provider_request,created_unix
root=Path('/var/lib/kpi-cuda-guard/recovery-six-20261020-01');lease=json.loads((root/'lease.json').read_text());base='https://rest.runpod.io/v1/pods/'+lease['podId']
m=json.loads((root/'artifacts/terminal-backup.json').read_text());archive=root/'artifacts'/(m['sha256']+'.tar.gz')
assert archive.stat().st_size==m['bytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==m['sha256']
b=json.loads((root/'results/b-verification.json').read_text());cloud=json.loads((root/'results/cloud-recovery-verification.json').read_text());stop=json.loads((root/'results/provider-stop-observation.json').read_text())
assert b['archiveAndPublicInputsVerified'] and cloud['verifiedArchiveAndPublicInputs'] and cloud['savedOnCloud']
assert b['archiveSha256']==cloud['archiveSha256']==m['sha256'] and b['archiveBytes']==cloud['archiveBytes']==m['bytes']
assert b['result']['verifiedCount']==cloud['verifiedCount']
assert b['result']['verifiedReceipts']==cloud['verifiedReceipts']
assert b['result']['allSixFinalReceiptsVerified']==cloud['allSixFinalReceiptsVerified']
assert stop['providerDesiredExitedConfirmed'] and stop['guardStop']['providerDesiredExitedConfirmed']
p=provider_request(base,os.environ['RUNPOD_API_KEY']);assert p['id']==lease['podId'] and p['desiredStatus']=='EXITED';assert abs(created_unix(p['createdAt'])-lease['createdUnix'])<=1
assert p['name']=='kpi-recovery-six-20261020-01' and p.get('networkVolumeId') is None
intent={'unixSeconds':time.time(),'podId':lease['podId'],'providerDesiredStatus':p['desiredStatus'],'verifiedBAndCloudArchiveSha256':m['sha256'],'archiveBytes':m['bytes'],'receiptCount':cloud['verifiedCount'],'cryptographicSuccess':cloud['allSixFinalReceiptsVerified'],'deletePodLocalVolumeGb':p['volumeInGb'],'networkVolumeId':None}
with (root/'deletion-intent.json').open('x') as f:json.dump(intent,f,indent=2);f.flush();os.fsync(f.fileno())
fd=os.open(root,os.O_RDONLY);os.fsync(fd);os.close(fd)
json_request(base,os.environ['RUNPOD_API_KEY'],'DELETE')
confirmed=False
for attempt in range(7):
 try:provider_request(base,os.environ['RUNPOD_API_KEY'])
 except urllib.error.HTTPError as e:
  if e.code==404:confirmed=True;break
  raise
 if attempt<6:time.sleep(2)
assert confirmed,'provider has not confirmed deletion; reconcile read-only, do not repeat deletion blindly'
pods=json_request('https://rest.runpod.io/v1/pods',os.environ['RUNPOD_API_KEY']);assert isinstance(pods,list) and not any(p.get('id')==lease['podId'] for p in pods)
unit='kpi-cuda-recovery-six-20261020-01.service'
subprocess.run(['systemctl','disable','--now',unit],check=True,capture_output=True)
state=subprocess.check_output(['systemctl','show',unit,'--property=ActiveState','--property=SubState','--property=UnitFileState'],text=True);assert 'ActiveState=inactive' in state and 'UnitFileState=disabled' in state
r={'scope':'BOUNDED_SIX_RECOVERY_ATTEMPT_POD_AND_LOCAL_STORAGE_DELETED_AFTER_VERIFIED_EXTERNAL_PRESERVATION','deletedUnix':time.time(),'podId':lease['podId'],'providerGetStatus':404,'providerListStatus':200,'podAbsentFromList':True,'remainingPodCount':len(pods),'deletedPodVolumeGb':p['volumeInGb'],'deletedContainerDiskGb':p['containerDiskInGb'],'networkVolumeCreated':False,'bArchiveRevalidatedBeforeDelete':True,'cloudRecoveryVerified':True,'receiptCount':cloud['verifiedCount'],'cryptographicSuccess':cloud['allSixFinalReceiptsVerified'],'guardUnitState':state.splitlines(),'actualInvoiceChargesAvailable':False}
atomic(root/'results/provider-deletion.json',r);print(json.dumps(r,indent=2))
