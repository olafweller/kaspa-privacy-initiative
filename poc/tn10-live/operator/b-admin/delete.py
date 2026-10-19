import json,os,sys,time,subprocess,hashlib,urllib.error
from pathlib import Path
sys.path.insert(0,'/opt/kpi-remote-cuda')
from common import atomic,json_request,lease_check
from provider import provider_request,created_unix
root=Path('/var/lib/kpi-cuda-guard/tn10-live-20261019');lease=json.loads((root/'lease.json').read_text());b=json.loads((root/'final-result.json').read_text());cloud=json.loads((root/'cloud-preservation.json').read_text());stop=json.loads((root/'provider-stop-readback.json').read_text())
assert b['verification']['allFourVerified'] and cloud['allFourCpuVerified'] and cloud['actualTN10LifecycleCompleted']
archive=Path(b['archivePath']);assert archive.stat().st_size==cloud['archiveBytes']==b['archiveBytes'] and hashlib.sha256(archive.read_bytes()).hexdigest()==cloud['archiveSha256']==b['archiveSha256']
assert {k:v['receiptSha256'] for k,v in b['verification']['results'].items()}==cloud['receiptHashes']
assert stop['providerDesiredExitedConfirmed'] and stop['guardStop']['providerDesiredExitedConfirmed']
base='https://rest.runpod.io/v1/pods/'+lease['podId'];p=provider_request(base,os.environ['RUNPOD_API_KEY']);assert p['desiredStatus']=='EXITED' and p['id']==lease['podId'] and abs(created_unix(p['createdAt'])-lease['createdUnix'])<=1 and p.get('networkVolumeId') is None
intent={'unixSeconds':time.time(),'podId':lease['podId'],'verifiedExternalArchiveSha256':b['archiveSha256'],'archiveBytes':b['archiveBytes'],'receiptCount':4,'volumeGb':p['volumeInGb'],'containerDiskGb':p['containerDiskInGb']}
with (root/'deletion-intent.json').open('x') as f:json.dump(intent,f);f.flush();os.fsync(f.fileno())
try:json_request(base,os.environ['RUNPOD_API_KEY'],'DELETE')
except Exception as e:atomic(root/'deletion-response-error.json',{'type':type(e).__name__,'httpCode':getattr(e,'code',None),'doNotRepeatMutation':True})
confirmed=False
for n in range(7):
 try:provider_request(base,os.environ['RUNPOD_API_KEY'])
 except urllib.error.HTTPError as e:
  if e.code==404:confirmed=True;break
  raise
 if n<6:time.sleep(2)
assert confirmed,'deletion outcome unresolved; read-only reconciliation required, no automatic second DELETE'
pods=json_request('https://rest.runpod.io/v1/pods',os.environ['RUNPOD_API_KEY']);assert not any(x.get('id')==lease['podId'] for x in pods)
subprocess.run(['systemctl','disable','--now','kpi-cuda-guard.service'],check=True,capture_output=True)
unit=subprocess.check_output(['systemctl','show','kpi-cuda-guard.service','--property=ActiveState','--property=SubState','--property=UnitFileState'],text=True);assert 'ActiveState=inactive' in unit and 'UnitFileState=disabled' in unit
r={'podId':lease['podId'],'deletedUnix':time.time(),'providerGetStatus':404,'podAbsentFromList':True,'remainingPodCount':len(pods),'deletedPodVolumeGb':p['volumeInGb'],'deletedContainerDiskGb':p['containerDiskInGb'],'networkVolumeCreated':False,'bArchiveRevalidatedBeforeDelete':True,'cloudRecoveryVerified':True,'receiptCount':4,'cryptographicSuccess':True,'actualTN10LifecycleCompleted':True,'guardUnitState':unit.splitlines(),'actualInvoiceAvailable':False}
atomic(root/'provider-deletion.json',r);print(json.dumps(r,indent=2))
