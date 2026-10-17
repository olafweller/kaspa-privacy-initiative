#!/usr/bin/env python3
"""Codex-side fixed HTTPS control and independent CPU artifact verification."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

from common import json_request, lease_check, request, sha
from package import checked_archive, write


def unpack(data, expected_sha, output):
    assert sha(data) == expected_sha
    output.mkdir()
    path = output/'download.tar.gz'
    write(path, data)
    for name, content in checked_archive(path, expected_sha).items():
        write(output/name, content)


def fetch(lease, output, token):
    lease_check(lease)
    status = json_request(lease['serviceUrl']+'/v1/status', token)
    data = request(lease['serviceUrl']+'/v1/artifacts', token)
    assert len(data) == status['artifact']['bytes'] and sha(data) == status['artifact']['sha256']
    unpack(data, status['artifact']['sha256'], output)
    write(output/'download-status.json', (json.dumps(status, indent=2)+'\n').encode())
    return {'downloaded': True, 'sha256': sha(data), 'cpuVerified': False}


def verify(package, downloaded, partial=False):
    policy = json.loads((package/'workload.json').read_text())
    host = package/'bin/kpi-takeover-host'
    assert sha(host.read_bytes()) == policy['cpuVerifierSha256']
    assets = downloaded/'assets'
    for name, spec in policy['inputs'].items():
        data = (assets/name).read_bytes()
        assert len(data) == spec['bytes'] and sha(data) == spec['sha256']
    remote_report = assets/'cpu-comparison.json'
    if remote_report.exists():
        remote_report.rename(downloaded/'remote-comparison-untrusted.json')
    def restrict():
        resource.setrlimit(resource.RLIMIT_AS, (12*1024**3, 12*1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    result = subprocess.run([str(host.resolve()), 'phase-diagnostics',
        'compare-partial' if partial else 'compare', str(assets.resolve())],
        env={key: os.environ[key] for key in ('PATH', 'HOME', 'LD_LIBRARY_PATH') if key in os.environ}
            | {'RISC0_PROVER': 'ipc'},
        stdin=subprocess.DEVNULL, capture_output=True, timeout=60, preexec_fn=restrict)
    assert result.returncode == 0, 'independent CPU verification failed'
    return json.loads((assets/'cpu-comparison.json').read_text())


if __name__ == '__main__':
    command = sys.argv[1]
    if command in ('verify', 'verify-partial'):
        print(json.dumps(verify(Path(sys.argv[2]), Path(sys.argv[3]), command == 'verify-partial'), indent=2))
    elif command == 'unpack':
        unpack(Path(sys.argv[2]).read_bytes(), sys.argv[3], Path(sys.argv[4]))
        print('Checked and unpacked archive; independent CPU verification still required.')
    else:
        lease = json.loads(Path(sys.argv[2]).read_text())
        lease_check(lease)
        token = os.environ['KPI_GPU_TOKEN']
        if command == 'status':
            print(json.dumps(json_request(lease['serviceUrl']+'/v1/status', token), indent=2))
        elif command == 'start':
            print(json.dumps(json_request(lease['serviceUrl']+'/v1/start', token, 'POST', {})))
        elif command == 'fetch':
            print(json.dumps(fetch(lease, Path(sys.argv[3]), token)))
        else:
            raise SystemExit('status LEASE | start LEASE | fetch LEASE NEW_DIRECTORY | unpack ARCHIVE SHA256 NEW_DIRECTORY | verify[-partial] PACKAGE DOWNLOADED')
