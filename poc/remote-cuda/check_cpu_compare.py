#!/usr/bin/env python3
"""Verify real retained CPU seals; reject valid but different substituted claims."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

from package import ARCHIVE_SHA, CLAIMS, INPUTS, ROOT, checked_archive, write


def check(host):
    contents = checked_archive(ROOT/'poc/proof-phase-diagnostics/evidence/local-phase-artifacts.tar.gz', ARCHIVE_SHA)
    with tempfile.TemporaryDirectory() as directory:
        baseline = Path(directory)/'baseline'
        for name in INPUTS+[phase+'.bin' for phase in CLAIMS]:
            write(baseline/name, contents['assets/'+name])
        def invoke(path):
            return subprocess.run([str(host.resolve()), 'phase-diagnostics', 'compare', str(path)],
                env=os.environ | {'RISC0_PROVER': 'ipc'}, capture_output=True, timeout=30).returncode
        assert invoke(baseline) == 0
        wrong = Path(directory)/'valid-seals-wrong-cpu-claim'
        shutil.copytree(baseline, wrong)
        (wrong/'cpu-comparison.json').unlink()
        data = bytearray((wrong/'segment-25.bin').read_bytes())
        index_offset = 8+4*struct.unpack_from('<Q', data)[0]
        assert struct.unpack_from('<I', data, index_offset)[0] == 25
        struct.pack_into('<I', data, index_offset, 24)  # Metadata is not the sealed claim.
        (wrong/'segment-24.bin').write_bytes(data)
        (wrong/'lift-24.bin').write_bytes((wrong/'lift-25.bin').read_bytes())
        assert invoke(wrong) != 0, 'valid foreign CPU claim was accepted'
        assert not (wrong/'cpu-comparison.json').exists()
        malformed = Path(directory)/'tampered-seal'
        shutil.copytree(baseline, malformed)
        (malformed/'cpu-comparison.json').unlink()
        data = bytearray((malformed/'join.bin').read_bytes())
        data[8] ^= 1
        (malformed/'join.bin').write_bytes(data)
        assert invoke(malformed) != 0
    print('Actual CPU seals pass; valid substituted claims and altered seals are rejected.')


if __name__ == '__main__':
    check(Path(sys.argv[1]))
