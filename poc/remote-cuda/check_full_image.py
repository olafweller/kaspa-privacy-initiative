"""CPU-only source/binary/input/startup validation; never starts a proof job."""
import json
import os
from pathlib import Path
import subprocess
import sys

from check_image import check
from common import sha
from full_package import HOST_SHA, CUDA_SHA


def full_check(image):
    result = check(image)
    result['scope'] = 'FULL_CLASSIFIER_CPU_ONLY_CONTAINER_CHECK_NO_PROOF'
    assert result['runtimeFilesSha256']['/opt/kpi/package/bin/kpi-takeover-host'] == HOST_SHA
    assert result['runtimeFilesSha256']['/opt/kpi/bin/r0vm-cuda'] == CUDA_SHA
    env = {k:v for k,v in os.environ.items() if k not in
           ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}
    code = '''import json;from pathlib import Path;from common import sha;from full_worker import check_inputs
p=Path('/opt/kpi/full');m=json.loads((p/'full-workload.json').read_text());check_inputs(p,m)
print(json.dumps({'workloadSha256':sha((p/'full-workload.json').read_bytes()),'application':{n:sha((Path('/opt/kpi/app')/n).read_bytes()) for n in ['full_worker.py','full_service.py']}}))'''
    extra = json.loads(subprocess.check_output(['docker','--host=unix:///var/run/docker.sock',
        'run','--rm','--entrypoint','python3',image,'-c',code],env=env,text=True,timeout=60))
    for name,digest in extra['application'].items():
        assert digest == sha((Path(__file__).parent/name).read_bytes())
    result.update(extra)
    return result


if __name__ == '__main__':
    print(json.dumps(full_check(sys.argv[1]),indent=2))
