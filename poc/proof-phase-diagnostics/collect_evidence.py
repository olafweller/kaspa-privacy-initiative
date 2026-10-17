#!/usr/bin/env python3
"""Whitelist and read back public diagnostics, including every failed stage."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

root = Path(__file__).resolve().parents[2]
local = root / '.local/proof-phase-diagnostics'
run = local / 'run-01'
assets = run / 'assets'
output = root / 'poc/proof-phase-diagnostics/evidence'
output.mkdir(exist_ok=True)
archive_path = output / 'local-phase-artifacts.tar.gz'
assert not archive_path.exists()
files = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def add(name, path):
    assert path.is_file() and not path.is_symlink()
    assert name not in files and not name.startswith('/') and '..' not in Path(name).parts
    files[name] = path.read_bytes()


for path in sorted(run.glob('*')):
    if path.is_file() and path.suffix in ('.json', '.jsonl', '.log'):
        add('attempt/' + path.name, path)
for path in sorted((run / 'preflight-repair').glob('*')):
    if path.is_file() and path.suffix in ('.json', '.jsonl', '.log'):
        add('attempt/preflight-repair/' + path.name, path)
allowed_assets = {
    'program.bin', 'input.bin', 'expected-journal.bin', 'session.json', 'session-claim.bin',
    'separate-verification.json', 'join-started.json', 'join.bin', 'join-verified.json',
}
for index in (24, 25):
    for stage in ('segment', 'lift'):
        allowed_assets.update({f'{stage}-{index}.bin', f'{stage}-{index}-started.json',
                               f'{stage}-{index}-verified.json'})
    add(f'assets/segments/{index}.bincode', assets / f'segments/{index}.bincode')
    add(f'old-temporary-traces/{index}.bincode', Path(f'/tmp/.tmpdSt2cX/{index}.bincode'))
for name in sorted(allowed_assets):
    path = assets / name
    if path.exists():
        add('assets/' + name, path)
for pattern in ('*build*.log', '*tests.log', '*runner*.log', 'retained-inspection.json',
                'fast-checks.log', 'hardware-and-sdk.json'):
    for path in sorted(local.glob(pattern)):
        add('local/' + path.name, path)
tracked = subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines()
extra = {'poc/outer-proof-128m/host.rs', 'poc/accelerated-bn254/host.rs',
         'poc/takeover/host/src/main.rs', 'poc/takeover/host/Cargo.toml',
         'poc/takeover/Cargo.lock', 'scripts/ci_fast.sh'}
for name in tracked:
    if (name.startswith('poc/proof-phase-diagnostics/') and '/evidence/' not in name) or name in extra:
        add('source/' + name, root / name)

session = json.loads((assets / 'session.json').read_text())
summary = json.loads((run / 'preflight-repair/summary.json').read_text())
assert summary['completedAllPhases']
assert summary['aggregateSecondsIncludingPreflightRepair'] < 3600
assert all(p['exitCode'] == 0 and p['limitExceeded'] is None for p in summary['phases'])
old_runtime = json.loads((root / '.local/outer-proof-128m/source-and-inputs.json').read_text())
new_runtime = json.loads((run / 'preflight-repair/attempt.json').read_text())
assert new_runtime['r0vmSha256'] == old_runtime['toolchain']['r0vmSha256']
for index in (24, 25):
    assert sha(files[f'assets/segments/{index}.bincode']) == session['segments'][index]['assetSha256']
verified = [name for name in allowed_assets if name.endswith('-verified.json') and (assets / name).exists()]
assert len(verified) == 5
assert json.loads((assets / 'separate-verification.json').read_text())['verified']
for name in verified:
    checkpoint = json.loads((assets / name).read_text())
    assert checkpoint['receiptSha256'] == sha(files['assets/' + name.replace('-verified.json', '.bin')])
manifest = {name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(files.items())}
old_archive = root / 'poc/outer-proof-128m/evidence/local-outer-proof-artifacts.tar.gz'
old_sha = sha(old_archive.read_bytes())
assert old_sha == 'eb39eb23d6dd7da2f55a45711fbcac2acaad844dee94e30e2a91d6f6705a1710'
result = {
    'scope': 'LOCAL_UNFUNDED_PARTIAL_PROOF_PHASE_DIAGNOSTICS_NOT_FULL_CLASSIFIER',
    'sourceSnapshotCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    'originalPr39ArchiveSha256': old_sha, 'expectedProgramImage': session['expectedProgramImage'],
    'predeclaredPlanCommit': '47ed371', 'selectedSegments': [session['segments'][i] for i in (24, 25)],
    'priorTraceByteMatches': sum(row['oldTraceByteMatch'] for row in session['segments']),
    'initialPreflightOutcome': json.loads((run / 'summary.json').read_text()),
    'diagnosticOutcome': summary, 'verifiedPartialCheckpoints': sorted(verified),
    'separateVerification': json.loads((assets / 'separate-verification.json').read_text())
        if (assets / 'separate-verification.json').exists() else None,
    'fullClassifierReceiptProduced': False, 'archiveManifest': manifest,
}
with tarfile.open(archive_path, 'w:gz') as archive:
    for name, data in sorted(files.items()):
        item = tarfile.TarInfo(name)
        item.size = len(data)
        item.mode = 0o644
        archive.addfile(item, io.BytesIO(data))
with tarfile.open(archive_path, 'r:gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(files)
    for member in members:
        assert member.isfile()
        data = archive.extractfile(member).read()
        assert len(data) == manifest[member.name]['bytes']
        assert sha(data) == manifest[member.name]['sha256']
result['archive'] = {'name': archive_path.name, 'bytes': archive_path.stat().st_size,
                     'sha256': sha(archive_path.read_bytes()), 'regularMembers': len(files)}
with (output / 'comparison.json').open('x') as out:
    json.dump(result, out, indent=2)
    out.write('\n')
print(json.dumps(result['archive']))
