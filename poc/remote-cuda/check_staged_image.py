"""Re-pulled image qualification: CPU only, no service proof/GPU/provider job."""
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from common import sha
from staged_policy import ROOT,CUDA,SCOPE

APP_FILES=('common.py','worker.py','staged_archive.py','staged_policy.py','staged_child.py','staged_worker.py','staged_service.py')


def check(image):
    env={k:v for k,v in os.environ.items() if k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}
    def docker(*args):return subprocess.check_output(['docker','--host=unix:///var/run/docker.sock',*args],env=env,text=True,timeout=90)
    code="from pathlib import Path;import json;from staged_policy import check;from common import sha;p=Path('/opt/kpi/staged-tn10');m=check(p,cuda=True);print(json.dumps({'policy':m,'policySha256':sha((p/'staged-policy.json').read_bytes()),'application':{n:sha((Path('/opt/kpi/app')/n).read_bytes()) for n in "+repr(APP_FILES)+"},'reviewedRunnerSha256':sha(Path('/opt/kpi/private-native-tn10/run_stage.py').read_bytes())}))"
    report=json.loads(docker('run','--rm','--entrypoint','python3',image,'-c',code))
    identity=json.loads((ROOT/'poc/staged-tn10-service/evidence/package-identity.json').read_text())
    assert report['policySha256']==identity['files']['staged-policy.json']
    for name,h in report['application'].items():assert sha((Path(__file__).parent/name).read_bytes())==h,name
    assert report['reviewedRunnerSha256']==sha((ROOT/'poc/private-native-tn10/run_stage.py').read_bytes())
    metadata=json.loads(docker('run','--rm','--entrypoint','cat',image,'/opt/kpi/package/cuda-build.json'))
    assert metadata['binarySha256']==CUDA and metadata['features']==['cuda','disable-dev-mode'] and metadata['nvccFlags']=='-arch=sm_89'
    assert 'not found' not in docker('run','--rm','--entrypoint','ldd',image,'/opt/kpi/staged-tn10/bin/kpi-private-native-tn10')
    linked=docker('run','--rm','--entrypoint','ldd',image,'/opt/kpi/bin/r0vm-cuda')
    assert all(x.strip()=='libcuda.so.1 => not found' for x in linked.splitlines() if 'not found' in x)
    assert json.loads(docker('image','inspect',image,'--format','{{json .Config.Cmd}}'))==['python3','staged_service.py']
    name='kpi-staged-smoke-'+uuid.uuid4().hex[:10];token='synthetic-cpu-image-token-not-a-credential-000000000'
    try:
        docker('run','-d','--name',name,'--mount','type=volume,dst=/workspace','-p','127.0.0.1::8080','-e','RUNPOD_POD_ID=unittest123','-e','KPI_GPU_TOKEN='+token,image)
        port=int(docker('port',name,'8080/tcp').strip().rsplit(':',1)[1])
        def http(method,path,value=None,auth=token):
            c=HTTPConnection('127.0.0.1',port,timeout=3)
            c.request(method,path,None if value is None else json.dumps(value),{'Authorization':'Bearer '+auth,'Content-Type':'application/json'})
            r=c.getresponse();result=r.status,json.loads(r.read());c.close();return result
        def wait():
            for _ in range(100):
                try:return http('GET','/v1/status')
                except (ConnectionError,OSError):time.sleep(.1)
            raise AssertionError('CPU image service did not start')
        assert wait()[1]['state']=='unconfigured'
        assert http('GET','/v1/status',auth='wrong')[0]==401
        now=time.time();lease={'podId':'unittest123','createdUnix':now-1,'stopUnix':now+7199,'gpuCount':1,'gpuType':'NVIDIA L40S',
            'actualGpuHourlyUsd':'1.09','actualStorageHourlyUsd':'0.014','stoppedStorageHourlyUsd':'0.0028','retentionHours':24,
            'serviceUrl':'https://unittest123-8080.proxy.runpod.net','workloadScope':SCOPE,
            'trial':report['policy']['trial'],'packagePolicySha256':report['policySha256']}
        assert http('POST','/v1/configure',lease)[0]==200
        status=http('GET','/v1/status')[1];assert status['scope']==SCOPE and status['state']=='idle' and status['ledger'] is None and not status['guardHeartbeatFresh']
        target={'trial':lease['trial'],'stage':'deposit','targetSha256':'00'*32}
        assert http('POST','/v1/targets',target)[0]==200
        assert http('POST','/v1/configure',lease|{'stopUnix':now+7198})[0]==409
        docker('restart',name)
        port=int(docker('port',name,'8080/tcp').strip().rsplit(':',1)[1])
        after=wait()[1];assert after['approved']==status['approved']|{'deposit':'00'*32} and after['ledger'] is None and not after['guardHeartbeatFresh']
        assert http('POST','/v1/targets',target|{'targetSha256':'11'*32})[0]==409
    finally:
        subprocess.run(['docker','--host=unix:///var/run/docker.sock','rm','-fv',name],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
    # Verify the actual retained receipts with the binary recovered from image.
    # These are historical fixture expectations, not new chain inputs/proofs.
    from test_staged import fixture
    from staged_policy import CASES
    rows={}
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)
        for stage in CASES:
            assets=root/stage;assets.mkdir();files,target_sha=fixture(report['policy'],stage)
            (assets/'target.json').write_bytes(files['target.json'])
            receipt=ROOT/'poc/private-native-proof/gpu-2026-10-18-02/evidence/returned/proofs'/stage/'receipt.bin'
            (assets/'receipt.bin').write_bytes(receipt.read_bytes())
            docker('run','--rm','--user',f'{os.getuid()}:{os.getgid()}','--mount',f'type=bind,src={root},dst=/cpu',
                '--entrypoint','/opt/kpi/staged-tn10/bin/kpi-private-native-tn10',image,'verify',f'/cpu/{stage}/target.json',target_sha,f'/cpu/{stage}/receipt.bin',f'/cpu/{stage}/verified')
            rows[stage]=json.loads((assets/'verified/verification.json').read_text())
    report.update(scope='STAGED_IMAGE_CPU_QUALIFICATION_RETAINED_FIXTURES_ONLY',cudaBuild=metadata,
        imageId=docker('image','inspect',image,'--format','{{.Id}}').strip(),
        retainedCpuReceiptChecks=rows,persistentAuthenticatedStartup=True,unguardedJobsStarted=0,
        proofJobStarted=False,providerCalled=False,cudaExecutionQualified=False)
    return report


if __name__=='__main__':print(json.dumps(check(sys.argv[1]),indent=2))
