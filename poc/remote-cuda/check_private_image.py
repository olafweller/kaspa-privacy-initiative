"""CPU startup and exact source/binary binding; never starts a proof."""
import json
import os
from pathlib import Path
import subprocess
import sys
from check_image import check
from common import sha
from private_package import ROOT


def private_check(image):
    result = check(image)
    result['scope'] = 'PRIVATE_NOTE_CPU_ONLY_CONTAINER_CHECK_NO_PROOF'
    env = {k: v for k, v in os.environ.items() if k not in
           ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')}
    def docker(*args):
        return subprocess.check_output(['docker', '--host=unix:///var/run/docker.sock', *args], env=env, text=True, timeout=60)
    code = '''import json;from pathlib import Path;from common import sha;from private_worker import check_inputs
p=Path('/opt/kpi/private-note');m=json.loads((p/'private-workload.json').read_text());check_inputs(p,m)
print(json.dumps({'workloadSha256':sha((p/'private-workload.json').read_bytes()),'application':{n:sha((Path('/opt/kpi/app')/n).read_bytes()) for n in ['private_package.py','private_worker.py','private_service.py','package.py']},'binaries':m['binaries']}))'''
    extra = json.loads(docker('run', '--rm', '--entrypoint', 'python3', image, '-c', code))
    identity = json.loads((ROOT/'poc/private-note-proof/evidence/package-identity.json').read_text())
    assert extra['workloadSha256'] == identity['policySha256']
    assert extra['binaries'] == identity['binaries']
    for name, digest in extra['application'].items():
        assert digest == sha((Path(__file__).parent/name).read_bytes())
    for name in extra['binaries']:
        linked = docker('run', '--rm', '--entrypoint', 'ldd', image, '/opt/kpi/private-note/bin/'+name)
        assert 'not found' not in linked, linked
    target = json.loads(docker('run', '--rm', '--entrypoint', '/opt/kpi/private-note/bin/kpi-private-note-producer',
                              image, 'check-target', '/opt/kpi/private-note/inputs'))
    assert target['fixedTargetVerified'] and not target['proofStarted']
    result.update(extra)
    result['fixedTarget'] = target
    return result


if __name__ == '__main__':
    print(json.dumps(private_check(sys.argv[1]), indent=2))
