#!/usr/bin/env python3
"""Retain the single approved attempt, including concrete failures if any."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

root = Path(__file__).resolve().parents[2]
local = root / '.local/outer-proof-128m'
old = root / '.local/accelerated-bn254'
original = root / '.local/groth16-comparison'
output = root / 'poc/outer-proof-128m/evidence'
output.mkdir(exist_ok=True)
archive_path = output / 'local-outer-proof-artifacts.tar.gz'
assert not archive_path.exists()
resource = json.loads((local / 'proof-job.resources.json').read_text())
qualification = json.loads((local / 'qualification/qualification.json').read_text())
assert qualification['passed'] and len(qualification['cases']) == 24
source = json.loads((local / 'source-and-inputs.json').read_text())
complete_path = local / 'proof-output/proof-complete.json'
verification_path = local / 'verification/verification.json'
complete = json.loads(complete_path.read_text()) if complete_path.exists() else None
verification = json.loads(verification_path.read_text()) if verification_path.exists() else None
if complete:
    assert resource['exitCode'] == 0 and resource['limitExceeded'] is None
    assert verification and verification['exactExpectedJournalVerified']
    assert verification['wrongExpectedImageCryptographicallyRejected']
    assert verification['tamperedJournalOffsetsCryptographicallyRejected'] == [0, 32, 44, 76, 166]
    assert verification['noUnresolvedAssumptions'] and not verification['developmentMode']
    assert verification['expectedProgramImage'] == source['expectedProgramImage']
    assert (local / 'proof-output/classifier-receipt.bin').read_bytes()
else:
    assert resource['exitCode'] != 0 or resource['limitExceeded'] is not None
    assert verification is None  # Never report artifact checks as receipt verification.

files = {}


def add(name, path):
    assert path.is_file() and not path.is_symlink()
    assert name not in files and not name.startswith('/') and '..' not in Path(name).parts
    assert 'proving-parameters' not in name
    files[name] = path.read_bytes()


for folder in ['expectations', 'qualification', 'proof-output', 'verification']:
    for path in sorted((local / folder).rglob('*')):
        if path.is_file():
            add('local/' + path.relative_to(local).as_posix(), path)
for pattern in ['proof-job.*', 'verify-job.*', 'build.*', 'watchdog-check.*', 'source-and-inputs.json',
                'qualification-summary.json', 'proof-os-snapshots.jsonl', 'hardware.json', 'proof-cpu.*',
                'rust-tests.log', 'adapter-tests.log', 'fast-checks-final.log']:
    for path in sorted(local.glob(pattern)):
        add('local/' + path.relative_to(local).as_posix(), path)
for path in sorted((old / 'programs-final').glob('*')):
    add('unchanged-classifier/' + path.name, path)
for folder, patterns in [('fixtures-reviewed', ['*']),
                         ('wallet-01', ['*-proof.bin', '*-operation.bin']),
                         ('setup-01', ['vk.bin', 'pvk.bin', 'pvk-uncompressed.bin'])]:
    for pattern in patterns:
        for path in sorted((original / folder).glob(pattern)):
            add('reused/' + path.relative_to(original).as_posix(), path)
tracked = subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines()
extra = {'poc/accelerated-bn254/host.rs', 'poc/takeover/host/src/main.rs',
         'poc/takeover/Cargo.lock', 'poc/takeover/host/Cargo.toml',
         'docs/adr/0010-approved-128m-outer-proof.md', 'scripts/ci_fast.sh'}
for name in tracked:
    if (name.startswith('poc/outer-proof-128m/') and '/evidence/' not in name) or name in extra:
        add('source/' + name, root / name)
manifest = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in sorted(files.items())}
summary = {
    'scope': 'LOCAL_UNFUNDED_APPROVED_128M_OUTER_CLASSIFICATION_PROOF_EXPERIMENT',
    'sourceSnapshotCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    'runtimeSourceAndInputs': source,
    'qualifiedExistingCases': 24,
    'executedMainProfile': json.loads((local / 'proof-output/profile-complete.json').read_text()),
    'hardwareAndLimits': json.loads((local / 'hardware.json').read_text()),
    'proofAttemptCount': 1,
    'proofJobResourceReport': resource,
    'processGroupCpuSampling': json.loads((local / 'proof-cpu.summary.json').read_text()),
    'proofCompleted': complete is not None,
    'proofCompletion': complete,
    'separateProcessReceiptVerification': verification,
    'proofFailure': json.loads((local / 'proof-output/prover-error.json').read_text())
    if (local / 'proof-output/prover-error.json').exists() else
    (None if complete else {'resourceLimitExceeded': resource['limitExceeded'],
                           'processExitCode': resource['exitCode'],
                           'details': 'See retained process logs and resource report; no completed receipt.'}),
    'lastCompletedHostStage': 'proof-complete' if complete else
    ('candidate-receipt-returned' if (local / 'proof-output/candidate-receipt.bin').exists() else
     ('execution-profile-complete' if (local / 'proof-output/profile-complete.json').exists() else 'job-started')),
    'archiveManifest': manifest,
}
with tarfile.open(archive_path, 'w:gz') as archive:
    for name, data in sorted(files.items()):
        item = tarfile.TarInfo(name)
        item.size = len(data)
        item.mode = 0o644
        item.mtime = 0
        archive.addfile(item, io.BytesIO(data))
with tarfile.open(archive_path, 'r:gz') as archive:
    assert len(archive.getmembers()) == len(manifest)
    for item in archive.getmembers():
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        data = archive.extractfile(item).read()
        assert len(data) == manifest[item.name]['bytes']
        assert hashlib.sha256(data).hexdigest() == manifest[item.name]['sha256']
summary['archiveBytes'] = archive_path.stat().st_size
summary['archiveSha256'] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
with (output / 'comparison.json').open('x') as target:
    target.write(json.dumps(summary, indent=2) + '\n')
print(json.dumps({key: summary[key] for key in ['proofCompleted', 'archiveBytes', 'archiveSha256']}, indent=2))
print('Read-back verified members:', len(manifest))
