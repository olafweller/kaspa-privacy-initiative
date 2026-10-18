"""CPU-only immutable-image package/startup checks. Never /v1/guard or /v1/start."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from http.client import HTTPConnection
from check_image import check as base_check
from common import sha
from lifecycle_package import ROOT, BINS, CASES, SCOPE

APP_FILES=('common.py','worker.py','service.py','package.py','lifecycle_package.py','lifecycle_runner.py','lifecycle_worker.py','lifecycle_service.py')


def check(image):
    result=base_check(image)
    env={k:v for k,v in os.environ.items() if k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}
    def docker(*args):return subprocess.check_output(['docker','--host=unix:///var/run/docker.sock',*args],env=env,text=True,timeout=60)
    code="from pathlib import Path;import json;from common import sha;from lifecycle_package import check;p=Path('/opt/kpi/private-native');m=check(p,cuda=True);print(json.dumps({'workloadSha256':sha((p/'lifecycle-workload.json').read_bytes()),'binaries':m['binaries'],'application':{n:sha((Path('/opt/kpi/app')/n).read_bytes()) for n in "+repr(APP_FILES)+"}}))"
    extra=json.loads(docker('run','--rm','--entrypoint','python3',image,'-c',code))
    identity=json.loads((ROOT/'poc/private-native-proof/evidence/package-identity.json').read_text())
    assert extra['workloadSha256']==identity['policySha256']
    for n,h in extra['application'].items():assert sha((Path(__file__).parent/n).read_bytes())==h,n
    assert extra['binaries']==identity['binaries']
    for n in BINS:assert 'not found' not in docker('run','--rm','--entrypoint','ldd',image,'/opt/kpi/private-native/bin/'+n)
    docker('run','--rm','--entrypoint','/usr/bin/timeout',image,'--version')
    targets=[]
    for case in CASES:
        text=docker('run','--rm','--entrypoint','/opt/kpi/private-native/bin/'+BINS[0],image,'check-target',case,'/opt/kpi/private-native/inputs')
        assert 'fixed public target verified; no proof started' in text;targets.append(case)
    assert json.loads(docker('image','inspect',image,'--format','{{json .Config.Cmd}}'))==['python3','lifecycle_service.py']
    name='kpi-lifecycle-smoke-'+uuid.uuid4().hex[:10];token='unit-only-not-a-real-token-00000000000000'
    try:
        docker('run','-d','--name',name,'-p','127.0.0.1::8080','-e','RUNPOD_POD_ID=unittest123','-e','KPI_GPU_TOKEN='+token,image)
        port=int(docker('port',name,'8080/tcp').strip().rsplit(':',1)[1])
        def http(method,path,value=None):
            c=HTTPConnection('127.0.0.1',port,timeout=2)
            c.request(method,path,None if value is None else json.dumps(value),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
            r=c.getresponse();v=r.status,json.loads(r.read());c.close();return v
        for attempt in range(100):
            try:
                assert http('GET','/v1/status')[0]==200;break
            except (ConnectionError,OSError):time.sleep(.1)
        now=time.time()
        lease={'podId':'unittest123','createdUnix':now,'stopUnix':now+7200,'gpuCount':1,'gpuType':'NVIDIA L40S','actualGpuHourlyUsd':'1.09','actualStorageHourlyUsd':'0.014','stoppedStorageHourlyUsd':'0.0028','retentionHours':24,'serviceUrl':'https://unittest123-8080.proxy.runpod.net'}
        assert http('POST','/v1/configure',lease)[0]==200
        status=http('GET','/v1/status')[1]
        assert status['scope']==SCOPE and status['state']=='idle' and not status['guardHeartbeatFresh']
    finally:
        subprocess.run(['docker','--host=unix:///var/run/docker.sock','rm','-f',name],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
    result.update(extra)
    result.update(scope='LIFECYCLE_CPU_IMAGE_QUALIFICATION_NO_PROVING',fixedTargetsChecked=targets,serviceScope=SCOPE,proofJobStarted=False,providerCalled=False,gpuExecutionQualified=False)
    return result


if __name__=='__main__':print(json.dumps(check(sys.argv[1]),indent=2))
