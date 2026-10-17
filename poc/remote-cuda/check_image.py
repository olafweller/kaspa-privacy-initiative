#!/usr/bin/env python3
"""CPU-only container startup check. Never starts the proof workload or a Pod."""
from http.client import HTTPConnection
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


def check(image):
    env = {k: v for k, v in os.environ.items() if k not in
           ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')}
    def docker(*args):
        return subprocess.check_output(['docker', '--host=unix:///var/run/docker.sock', *args],
                                       env=env, text=True, timeout=60)
    metadata = json.loads(docker('run', '--rm', '--entrypoint', 'cat', image,
                                '/opt/kpi/package/cuda-build.json'))
    assert metadata['features'] == ['cuda', 'disable-dev-mode']
    assert metadata['sourceCommit'] == '14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6'
    assert metadata['nvccFlags'] == '-arch=sm_89'
    assert metadata['rustVersion'].startswith('rustc 1.89.0 ')
    files = json.loads(docker('run', '--rm', '--entrypoint', 'python3', image, '-c',
        'import hashlib,json; from pathlib import Path; '
        'paths=["/opt/kpi/app/"+n+".py" for n in ("common","worker","service")]+ '
        '["/opt/kpi/bin/r0vm-cuda","/opt/kpi/package/bin/kpi-takeover-host"]; '
        'print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}))'))
    for name in ('common', 'worker', 'service'):
        expected = hashlib.sha256((Path(__file__).parent/(name+'.py')).read_bytes()).hexdigest()
        assert files['/opt/kpi/app/'+name+'.py'] == expected, 'stale application source in image'
    assert files['/opt/kpi/bin/r0vm-cuda'] == metadata['binarySha256']
    policy = json.loads(docker('run', '--rm', '--entrypoint', 'cat', image,
                              '/opt/kpi/package/workload.json'))
    assert files['/opt/kpi/package/bin/kpi-takeover-host'] == policy['cpuVerifierSha256']
    docker('run', '--rm', '--entrypoint', 'python3', image, '-m', 'py_compile',
           '/opt/kpi/app/service.py', '/opt/kpi/app/worker.py', '/opt/kpi/app/common.py')
    linked = docker('run', '--rm', '--entrypoint', 'ldd', image, '/opt/kpi/bin/r0vm-cuda')
    missing = [line.strip() for line in linked.splitlines() if 'not found' in line]
    assert all(line == 'libcuda.so.1 => not found' for line in missing), linked
    version = None
    if not missing:
        version = docker('run', '--rm', '--entrypoint', '/opt/kpi/bin/r0vm-cuda', image, '--version').strip()
        assert '3.0.3' in version
    name = 'kpi-cuda-cpu-smoke-'+uuid.uuid4().hex[:10]
    token = 'unit-test-only-not-a-real-credential-00000000'
    try:
        docker('run', '-d', '--name', name, '-p', '127.0.0.1::8080',
               '-e', 'RUNPOD_POD_ID=unittest123', '-e', 'KPI_GPU_TOKEN='+token, image)
        port = int(docker('port', name, '8080/tcp').strip().rsplit(':', 1)[1])
        def http(method, path, value=None, auth=token):
            connection = HTTPConnection('127.0.0.1', port, timeout=2)
            connection.request(method, path, None if value is None else json.dumps(value),
                               {'Authorization': 'Bearer '+auth, 'Content-Type': 'application/json'})
            response = connection.getresponse()
            result = response.status, json.loads(response.read())
            connection.close()
            return result
        for attempt in range(100):
            try:
                status, body = http('GET', '/v1/status')
                break
            except (ConnectionError, OSError):
                time.sleep(0.1)
        else:
            raise AssertionError('container service did not start')
        assert status == 200 and body['state'] == 'unconfigured'
        assert http('GET', '/v1/status', auth='wrong')[0] == 401
        assert http('POST', '/v1/start', {})[0] == 409
        now = time.time()
        lease = {'podId': 'unittest123', 'createdUnix': now, 'stopUnix': now+7200,
                 'gpuCount': 1, 'gpuType': 'NVIDIA L40S', 'actualGpuHourlyUsd': '1.09',
                 'actualStorageHourlyUsd': '0.014', 'stoppedStorageHourlyUsd': '0.0028',
                 'retentionHours': 24, 'serviceUrl': 'https://unittest123-8080.proxy.runpod.net'}
        assert http('POST', '/v1/configure', lease)[0] == 200
        assert http('GET', '/v1/status')[1]['state'] == 'idle'
        assert http('POST', '/v1/start', {})[0] == 409  # Still no independent guard.
        assert http('POST', '/v1/configure', lease | {'stopUnix': now+7199})[0] == 409
    finally:
        subprocess.run(['docker', '--host=unix:///var/run/docker.sock', 'rm', '-f', name],
                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    return {'scope': 'CPU_ONLY_CONTAINER_SMOKE_NOT_CUDA_EXECUTION',
            'imageId': docker('image', 'inspect', image, '--format', '{{.Id}}').strip(),
            'imageBytes': int(docker('image', 'inspect', image, '--format', '{{.Size}}')),
            'proverVersion': version, 'cudaBuild': metadata, 'runtimeFilesSha256': files,
            'nonDriverLibrariesResolved': True, 'driverLibraryResolved': not missing,
            'driverNote': 'libcuda.so.1 must be injected by the NVIDIA GPU container runtime; no driver stub is bundled.',
            'pythonCompilation': True,
            'authenticatedStartupAndLeaseBinding': True, 'unguardedStartRejected': True,
            'proofJobStarted': False, 'providerCalled': False, 'gpuExecutionQualified': False}


if __name__ == '__main__':
    print(json.dumps(check(sys.argv[1]), indent=2))
