"""Independent returned-artifact verification; never trusts a downloaded binary."""
import json
import os
from pathlib import Path
import subprocess
import sys
from common import sha
from private_package import BINS, INPUTS


def verify(package, downloaded, out):
    policy = json.loads((package/'private-workload.json').read_text())
    for name in BINS:
        assert sha((package/'bin'/name).read_bytes()) == policy['binaries'][name]['sha256']
    for name, (_, expected) in INPUTS.items():
        assert sha((downloaded/'assets'/name).read_bytes()) == expected
    # Expectations live in independently built local executables, not in the archive.
    out.mkdir()
    env = {key: os.environ[key] for key in ('PATH', 'HOME', 'LD_LIBRARY_PATH') if key in os.environ}
    receipt = (downloaded/'proof/classifier-receipt.bin').resolve()
    for binary, folder in [(BINS[1], 'cpu'), (BINS[2], 'native')]:
        subprocess.run([str((package/'bin'/binary).resolve()), 'verify-receipt', str(receipt), str((out/folder).resolve())],
                       env=env, stdin=subprocess.DEVNULL, check=True, timeout=120)
    return {'independentCpuAndNativeVerified': True, 'receiptSha256': sha(receipt.read_bytes()),
            'actualTN10Settlement': False}


if __name__ == '__main__':
    assert sys.argv[1] == 'verify' and len(sys.argv) == 5
    print(json.dumps(verify(*(Path(s) for s in sys.argv[2:])), indent=2))
