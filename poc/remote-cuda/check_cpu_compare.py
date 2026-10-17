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
        def invoke(path, partial=False):
            result = subprocess.run([str(host.resolve()), 'phase-diagnostics',
                'compare-partial' if partial else 'compare', str(path)],
                env=os.environ | {'RISC0_PROVER': 'ipc'}, capture_output=True, timeout=30)
            assert result.returncode >= 0, 'signal/resource failure cannot count as rejection'
            return result.returncode
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
        partial = Path(directory)/'one-returned-receipt'
        shutil.copytree(baseline, partial)
        (partial/'cpu-comparison.json').unlink()
        for phase in CLAIMS:
            if phase != 'segment-24':
                (partial/(phase+'.bin')).unlink()
        assert invoke(partial) != 0, 'strict five-receipt comparison accepted an incomplete run'
        assert invoke(partial, True) == 0
        report = __import__('json').loads((partial/'cpu-comparison.json').read_text())
        assert report['receiptsVerified'] == 1 and not report['allFiveSealsVerified']
        (partial/'cpu-comparison.json').unlink()
        data = bytearray((partial/'segment-24.bin').read_bytes())
        data[8] ^= 1
        (partial/'segment-24.bin').write_bytes(data)
        assert invoke(partial, True) != 0
    print('Actual CPU seals pass; valid foreign claims and altered seals rejected; incomplete verification reports only returned receipts.')


if __name__ == '__main__':
    check(Path(sys.argv[1]))
