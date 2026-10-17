#!/usr/bin/env python3
"""Package explicitly scoped public local experiment files; never read environment."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import subprocess
import tarfile
import sys


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    root = Path(__file__).resolve().parents[2]
    local = Path(sys.argv[1]).resolve()
    evidence = root / 'poc/proof-classification/evidence'
    evidence.mkdir(exist_ok=True)
    read = lambda p: json.loads(p.read_text())
    fixture = read(local / 'fixture-complete/fixture.json')
    profile = read(local / 'profile-4b-result/report.json')
    baseline = read(local / 'baseline-result/report.json')
    assert profile['scope'] == baseline['scope'] == 'EXECUTION_ONLY_NOT_PROOF'
    assert profile['outcomes'] == [0, 3, 0]
    assert profile['balances'] == [600_000_000, 600_000_000, 500_000_000]
    assert profile['userCycles'] == 870_829_938 and len(profile['segments']) == 880
    assert sum(1 << n for n in profile['segments']) == 921_960_448
    negatives = {p.parent.name[7:]: read(p) for p in local.glob('result-*/report.json')}
    assert len(negatives) == 18
    assert sum('authenticationAbort' in v for v in negatives.values()) == 5
    for name, result in negatives.items():
        if 'authenticationAbort' not in result:
            assert result['outcomes'] == ([0, 4, 0] if name == 'replay' else [0, 2, 0])
            assert result['balances'] == profile['balances']
    wallets = {name: read(local / 'fixture-complete' / f'{name}-report.json')
               for name in ['wallet-a', 'wallet-c']}
    for name, result in wallets.items():
        assert result['scope'] == 'REAL_SUCCINCT_PROOF' and not result['developmentMode']
        assert result['assumptionsSupplied'] == 0
        a = (local / 'fixture-final' / f'{name}-receipt.bin').read_bytes()
        b = (local / 'fixture-complete' / f'{name}-receipt.bin').read_bytes()
        assert a == b
    files = {}
    dirs = ['fixture-complete', 'profile-4b-result', 'baseline-result',
            'malformed-fixtures', 'check-final', 'check-review', 'invalid-unspent-result', 'final-replay-result', 'source-files', 'source-final-files', 'source-review-files',
            'programs-06', 'fixture-01', 'programs-02']
    dirs += [p.name for p in local.glob('result-*') if p.is_dir()]
    for dirname in dirs:
        for p in sorted((local / dirname).rglob('*')):
            if p.is_file():
                files[str(p.relative_to(local))] = p.read_bytes()
    for pattern in ['*.resources.json', '*.stdout.log', '*.stderr.log', 'source*.json',
                    '*tests-final.log', 'fast-final.log', 'rebuild.log']:
        for p in local.glob(pattern):
            files[p.name] = p.read_bytes()
    for p in (root / 'poc/proof-classification').rglob('*'):
        if p.is_file() and 'evidence' not in p.parts and '__pycache__' not in p.parts:
            files['current-source/' + str(p.relative_to(root))] = p.read_bytes()
    files['current-source/poc/takeover/host/src/main.rs'] = (root / 'poc/takeover/host/src/main.rs').read_bytes()
    assert not any(n.endswith(('.key', '.pem', '.env')) for n in files)
    assert not any(n.endswith('classifier-receipt.bin') for n in files)
    for snapshot in ['source', 'source-final', 'source-review']:
        manifest = read(local / f'{snapshot}.json')
        directory = {'source': 'source-files', 'source-final': 'source-final-files',
                     'source-review': 'source-review-files'}[snapshot]
        for name, expected in manifest['sha256'].items():
            assert digest((local / directory / name).read_bytes()) == expected
    manifest = {n: {'bytes': len(b), 'sha256': digest(b)} for n, b in sorted(files.items())}
    files['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    archive = evidence / 'local-classification-artifacts.tar.gz'
    with archive.open('wb') as f, gzip.GzipFile(fileobj=f, mode='wb', mtime=0, filename='') as z:
        with tarfile.open(fileobj=z, mode='w') as t:
            for name, raw in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size, member.mode = len(raw), 0o644
                t.addfile(member, io.BytesIO(raw))
    # Read back the archive rather than trusting the construction pass.
    with tarfile.open(archive) as t:
        for name, expected in manifest.items():
            raw = t.extractfile(name).read()
            assert len(raw) == expected['bytes'] and digest(raw) == expected['sha256']
    result = {
        'scope': 'LOCAL_GUEST_EXECUTION_AND_REAL_WALLET_PROOFS_NOT_OUTER_PROOF_OR_TN10',
        'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'baseMain': '42c98654d38c8e86c6b0d58837bb134752439bec',
        'nativePin': '01b532e8b553523216471682649693af92f0fd16',
        'vprogsPin': 'f9b84a863a7c7c20586a9cf947550475e894f72e',
        'sdk': '3.0.3', 'zkpHost': '3.0.4', 'zkpGuest': '3.0.5',
        'newTN10Broadcasts': 0, 'actualPrivacyPayment': False, 'fundedTrialReady': False,
        'realOuterClassificationReceipt': False, 'outerProvingSeconds': None,
        'outerProvingMemory': None, 'realWalletReceiptsInFixture': 2,
        'diagnosticWalletReceipts': 1, 'walletProofs': wallets,
        'walletGenerationThenMassFailureResources': read(local / 'prepare-final.resources.json'),
        'fixture': fixture, 'profile': profile, 'baseline': baseline,
        'profileResources': read(local / 'profile-4b.resources.json'),
        'unspentInvalidThenValidControl': read(local / 'invalid-unspent-result/report.json'),
        'finalSourceReplay': read(local / 'final-replay-result/report.json'),
        'initialProfileLimitFailure': read(local / 'profile-main.resources.json'),
        'executionCeilingCycles': 4_294_967_296, 'maxReceiptBytes': 240_000,
        'maxOperationBytes': 250_000, 'negativeExecutionControls': negatives,
        'realReceiptHostMutations': read(local / 'check-final/checks.json'),
        'sourceSnapshots': [read(local / f'{name}.json') for name in ['source', 'source-final', 'source-review']],
        'programSha256': {p.name: digest(p.read_bytes()) for p in (local / 'programs-06').glob('*.program.bin')},
        'hardware': {'cpuQuota': Path('/sys/fs/cgroup/cpu.max').read_text().strip(),
                     'memoryLimitBytes': int(Path('/sys/fs/cgroup/memory.max').read_text()),
                     'walletProvingThreads': 4, 'r0vmVersion': '3.0.3',
                     'r0vmSha256': digest(Path('/workspace/scratch/kpi-lane-tools/r0vm').read_bytes())},
        'blockers': ['ordinary succinct verification requires 880 segments in this proxy',
                     'no produced outer classifier proof or actual accepted-lane binding',
                     'complete private relation, delivery, current nullifiers and native integration unimplemented',
                     'proxy payload already consumes 89.7 percent of pinned block transient limit'],
        'artifactArchive': {'path': archive.name, 'bytes': archive.stat().st_size,
                            'sha256': digest(archive.read_bytes()), 'manifestEntries': len(manifest)},
    }
    (evidence / 'classification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['artifactArchive'], indent=2))


if __name__ == '__main__':
    main()
