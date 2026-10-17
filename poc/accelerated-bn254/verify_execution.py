#!/usr/bin/env python3
"""Separate-process artifact consistency checks. No receipt/proof verification."""
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
import sys
import tarfile


programs, run, original, expected_image, output = sys.argv[1:]
programs, run, original = map(Path, (programs, run, original))
identity = json.loads((programs / 'identity.json').read_text())
assert identity['expectedProgramImage'] == expected_image
command = ['.local/ci-target/release/kpi-takeover-host', 'wallet-image',
           str(programs / 'classifier.program.bin')]
sdk = subprocess.run(command, check=True, text=True, capture_output=True)
words = json.loads(re.search(r'WALLET_IMAGE: \[u32; 8\] = (\[.*\]);', sdk.stdout)[1])
assert struct.pack('<8I', *words).hex() == expected_image

expected = json.loads((original / 'fixtures-reviewed/expected.json').read_text())
journal = (run / 'journal.bin').read_bytes()
assert len(journal) == 44 + 3 * 41
assert journal[:32].hex() == expected['orderedRoot']
assert struct.unpack('<QI', journal[32:44]) == (1_000_000_000, 3)
for i in range(3):
    record = journal[44 + i * 41:44 + (i + 1) * 41]
    assert record[:32].hex() == expected['operations'][i]['nativeId']
    assert record[32] == expected['outcomes'][i]
    assert struct.unpack('<Q', record[33:])[0] == expected['balances'][i]

# Compare retained input bytes to the previously published PR37 archive, not
# merely to another regenerated copy. Never extract untrusted archive paths.
reused = {}
with tarfile.open('poc/groth16-comparison/evidence/local-groth16-artifacts.tar.gz', 'r:gz') as archive:
    paths = list((original / 'fixtures-reviewed').glob('*'))
    paths += list((original / 'wallet-01').glob('*-proof.bin'))
    paths += list((original / 'wallet-01').glob('*-operation.bin'))
    paths += [original / 'setup-01' / name for name in
              ('vk.bin', 'pvk.bin', 'pvk-uncompressed.bin')]
    for path in sorted(p for p in paths if p.is_file()):
        name = path.relative_to(original).as_posix()
        member = archive.getmember(name)
        assert member.isfile()
        data = path.read_bytes()
        assert archive.extractfile(member).read() == data
        reused[name] = hashlib.sha256(data).hexdigest()

result = {'scope': 'SEPARATE_PROCESS_EXECUTION_ARTIFACT_CONSISTENCY_NOT_A_PROOF',
          'expectedProgramImage': expected_image, 'sdkRecomputedImageMatches': True,
          'originalRootIdsOutcomesBalancesMatch': True,
          'reusedInputsMatchPublishedPr37Archive': reused,
          'receipt': None, 'developmentMode': False}
with Path(output).open('x') as f:
    f.write(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items()
                  if k != 'reusedInputsMatchPublishedPr37Archive'}, indent=2))
