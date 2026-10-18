"""Independent CPU verification of a returned complete classifier receipt."""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

from common import sha


def verify(package, downloaded, host, expected_host_sha):
    assert sha(host.read_bytes()) == expected_host_sha, 'untrusted CPU verifier binary'
    policy = json.loads((package/'full-workload.json').read_text())
    assert policy['scope'] == 'FIXED_FULL_CLASSIFIER_ONE_SUCCINCT_RECEIPT'
    for name, spec in policy['inputs'].items():
        local = (package/'inputs'/name).read_bytes()
        remote = (downloaded/'assets'/name).read_bytes()
        assert len(local) == spec['bytes'] and sha(local) == spec['sha256']
        assert remote == local, 'returned public input differs from trusted package'
    output = downloaded/'independent-cpu-verification'
    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (12*1024**3, 12*1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    env = {k:os.environ[k] for k in ['PATH','HOME','LD_LIBRARY_PATH'] if k in os.environ}
    env['RISC0_PROVER'] = 'ipc'
    result = subprocess.run([str(host.resolve()), 'outer-proof-128m', 'verify',
        str((package/'inputs/expectations').resolve()), str((downloaded/'proof').resolve()),
        str(output.resolve())], env=env, stdin=subprocess.DEVNULL,
        capture_output=True, timeout=90, preexec_fn=limits)
    (downloaded/'independent-verify.stdout.log').write_bytes(result.stdout)
    (downloaded/'independent-verify.stderr.log').write_bytes(result.stderr)
    assert result.returncode == 0, 'independent CPU receipt verification failed'
    report = json.loads((output/'verification.json').read_text())
    assert report['expectedProgramImage'] == policy['expectedProgramImage']
    for key in ['exactExpectedJournalVerified','wrongExpectedImageCryptographicallyRejected',
                'corruptedSealCryptographicallyRejected','noUnresolvedAssumptions']:
        assert report[key] is True
    assert report['tamperedJournalOffsetsCryptographicallyRejected'] == [0,32,44,76,166]
    assert report['developmentMode'] is False
    return report


if __name__ == '__main__':
    assert sys.argv[1] == 'verify'
    print(json.dumps(verify(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]),indent=2))
