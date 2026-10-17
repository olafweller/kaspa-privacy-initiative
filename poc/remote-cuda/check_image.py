#!/usr/bin/env python3
"""CPU-only container startup check. Never starts the proof workload or a Pod."""
from http.client import HTTPConnection
import json
import os
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
    docker('run', '--rm', '--entrypoint', 'python3', image, '-m', 'py_compile',
           '/opt/kpi/app/service.py', '/opt/kpi/app/worker.py', '/opt/kpi/app/common.py')
    linked = docker('run', '--rm', '--entrypoint', 'ldd', image, '/opt/kpi/bin/r0vm-cuda')
    assert 'not found' not in linked, linked
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
            'proverVersion': version, 'cudaBuild': metadata,
            'linkedLibrariesResolved': True, 'pythonCompilation': True,
            'authenticatedStartupAndLeaseBinding': True, 'unguardedStartRejected': True,
            'proofJobStarted': False, 'providerCalled': False, 'gpuExecutionQualified': False}


if __name__ == '__main__':
    print(json.dumps(check(sys.argv[1]), indent=2))
