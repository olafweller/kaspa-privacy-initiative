#!/usr/bin/env python3
"""Publish only explicit public research artifacts; read back every member."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


root = Path(__file__).resolve().parents[2]
local = root / '.local/accelerated-bn254'
old = root / '.local/groth16-comparison'
output = root / 'poc/accelerated-bn254/evidence'
output.mkdir(exist_ok=True)
archive_path = output / 'local-backend-artifacts.tar.gz'
assert not archive_path.exists()
source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
files = {}


def add(name, path):
    assert not name.startswith('/') and '..' not in Path(name).parts
    assert path.is_file() and not path.is_symlink()
    assert 'proving-parameters' not in name
    assert name not in files
    files[name] = path.read_bytes()


for folder in ['programs-final', 'smoke-program', 'smoke-result', 'smoke-profile-result',
               'reference-final', 'practical-result', 'calibration-result',
               'practical-path-result']:
    for path in sorted((local / folder).glob('*')):
        add('local/' + path.relative_to(local).as_posix(), path)
for path in sorted(local.glob('result-*/*')):
    add('local/' + path.relative_to(local).as_posix(), path)
for pattern in ['smoke-build.*', 'smoke-build-feature.*', 'classifier-build-pinned.*',
                'classifier-build-final.*', 'build-final.*', 'host-build-v4.*',
                'smoke-execution.*', 'smoke-profile.*', 'practical.*', 'calibration.*',
                'practical-path-profile.*', 'control-*.*', 'rebuild.*', 'smoke-rebuild.*']:
    for path in sorted(local.glob(pattern)):
        add('local/' + path.relative_to(local).as_posix(), path)
for name in ['accelerated-path-observed.json', 'adversarial-controls.json',
             'separate-process-consistency.json', 'artifact-controls.json',
             'wrong-identity.stderr.log', 'tampered-journal.stderr.log',
             'rust-tests.log', 'adapter-tests.log', 'fast-checks-final.log', 'toolchain.json']:
    add('local/' + name, local / name)
for folder, patterns in [('fixtures-reviewed', ['*']),
                         ('wallet-01', ['*-proof.bin', '*-operation.bin']),
                         ('setup-01', ['vk.bin', 'pvk.bin', 'pvk-uncompressed.bin'])]:
    for pattern in patterns:
        for path in sorted((old / folder).glob(pattern)):
            add('reused-pr37/' + path.relative_to(old).as_posix(), path)
tracked = subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines()
extra = {'poc/takeover/Cargo.lock', 'poc/takeover/host/Cargo.toml',
         'poc/takeover/host/src/main.rs', 'poc/groth16-comparison/host.rs',
         '.github/workflows/code.yml', 'scripts/ci_fast.sh',
         'docs/adr/0009-accelerated-bn254-qualification.md'}
for name in tracked:
    if (name.startswith('poc/accelerated-bn254/') and '/evidence/' not in name) or name in extra:
        add('source/' + name, root / name)

practical = json.loads((local / 'practical-result/report.json').read_text())
calibration = json.loads((local / 'calibration-result/report.json').read_text())
controls = json.loads((local / 'adversarial-controls.json').read_text())
consistency = json.loads((local / 'separate-process-consistency.json').read_text())
assert practical['completed'] is False and practical['cycleBudget'] == 32_000_000
assert calibration['completed'] is True and calibration['cycleBudget'] == 128_000_000
assert calibration['userCycles'] == 117_473_222 and calibration['outcomes'] == [0, 3, 0]
assert calibration['balances'] == [600_000_000, 600_000_000, 500_000_000]
assert len(controls) == 13 and all(item['exitCode'] == 0 for item in controls)
assert consistency['receipt'] is None and consistency['sdkRecomputedImageMatches']
assert json.loads((local / 'accelerated-path-observed.json').read_text())['acceleratedPathObserved']
manifest = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            for name, data in sorted(files.items())}
summary = {
    'scope': 'LOCAL_UNFUNDED_EXECUTION_CALIBRATION_NOT_OUTER_PROOF',
    'sourceCommit': source,
    'executionSourceCommit': '76215dd537f1bec68439c502ffc40fd8c45b34ef',
    'predeclaredPlanCommit': 'bcc719d8b1f4f7d532a3c10bb93b6176622f7224',
    'mergedPr37Commit': 'a1d1b08dda867d9c0c8c47c16bddeece1d85dc76',
    'backendCommit': '22108fe8c6ea1ebc1358fc4fd6854a6bf46e3509',
    'originalPr37ArchiveSha256': hashlib.sha256((root / 'poc/groth16-comparison/evidence/local-groth16-artifacts.tar.gz').read_bytes()).hexdigest(),
    'expectedProgramImage': calibration['expectedProgramImage'],
    'practical': practical, 'calibration': calibration,
    'guestAuthenticationControls': 5, 'guestMalformedOnlyControls': 8,
    'fullReplayAtLargerBudgetQualified': False,
    'outerReceipt': None, 'outerProofAttempted': False,
    'outerProofSecondsBudget': 3600,
    'reasonOuterProofNotAttempted': '117.47M calibration does not meet predeclared 32M practical cap',
    'archiveManifest': manifest,
}
with tarfile.open(archive_path, 'w:gz') as archive:
    for name, data in sorted(files.items()):
        item = tarfile.TarInfo(name)
        item.size = len(data)
        item.mtime = 0
        item.mode = 0o644
        archive.addfile(item, io.BytesIO(data))
with tarfile.open(archive_path, 'r:gz') as archive:
    assert len(archive.getmembers()) == len(manifest)
    for member in archive.getmembers():
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        data = archive.extractfile(member).read()
        assert len(data) == manifest[member.name]['bytes']
        assert hashlib.sha256(data).hexdigest() == manifest[member.name]['sha256']
summary['archiveBytes'] = archive_path.stat().st_size
summary['archiveSha256'] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
with (output / 'comparison.json').open('x') as file:
    file.write(json.dumps(summary, indent=2) + '\n')
print(json.dumps({key: summary[key] for key in ['sourceCommit', 'expectedProgramImage',
                                             'archiveBytes', 'archiveSha256']}, indent=2))
print('Read-back verified members:', len(manifest))
