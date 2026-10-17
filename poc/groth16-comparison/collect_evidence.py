#!/usr/bin/env python3
"""Bundle public, explicitly scoped comparison artifacts, excluding proving parameters."""
from pathlib import Path
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    root = Path(__file__).resolve().parents[2]
    local = Path(sys.argv[1]).resolve()
    evidence = root / 'poc/groth16-comparison/evidence'
    read = lambda name: json.loads((local / name).read_text())
    setup = read('setup-01/setup.json')
    assert setup['constraints'] == 491548 and setup['publicFieldInputs'] == 4
    wallets = {k: read(f'wallet-01/wallet-{k}-report.json') for k in ['a', 'c']}
    assert all(w['sdkVerified'] and w['proofBytes'] == 128 and w['operationBytes'] == 702 for w in wallets.values())
    expected = read('fixtures-reviewed/expected.json')
    assert all(t['nativeEstimatedBytes'] == 967 and t['transientMass'] == 3868 for t in expected['operations'])
    profile = read('profile-reviewed-result/report.json')
    assert profile['cycleBudget'] == 32000000
    assert profile['unexpectedError'] == 'Session limit exceeded: 32000000 >= 32000000'
    controls = read('negative-execution-results.json')
    assert len(controls) == 13
    assert sum(v.get('expectedAuthenticationFailureConfirmed', False) for v in controls.values()) == 5
    assert all(v['outcomes'] == [2] and v['balances'] == [1_000_000_000]
               for k, v in controls.items() if k.startswith('malformed-only-'))
    reverified = read('wallet-reverification-final.json')
    assert reverified['changedIntentRejected'] and reverified['preparedParametersRecomputed']
    files = {}
    dirs = ['wallet-01', 'fixtures-reviewed', 'programs-final', 'programs-02', 'programs-03',
            'diagnostic-source', 'final-source', 'profile-reviewed-result']
    dirs += [p.name for p in local.glob('case-*') if p.is_dir()]
    for dirname in dirs:
        for p in sorted((local / dirname).rglob('*')):
            if p.is_file():
                files[str(p.relative_to(local))] = p.read_bytes()
    for name in ['vk.bin', 'pvk.bin', 'pvk-uncompressed.bin', 'setup.json']:
        files['setup-01/' + name] = (local / 'setup-01' / name).read_bytes()
    for pattern in ['*.resources.json', '*.stdout.log', '*.stderr.log', '*source.json',
                    '*final*.log', 'guest-rebuild.log', 'negative-execution-results.json',
                    'wallet-reverification-final.json']:
        for p in local.glob(pattern):
            files[p.name] = p.read_bytes()
    assert not any(Path(n).name == 'public-proving-parameters.bin' for n in files)
    assert not any(n.endswith(('.key', '.pem', '.env', 'classifier-receipt.bin')) for n in files)
    snapshots = {}
    for stem in ['diagnostic-source', 'final-source']:
        snapshots[stem] = read(stem + '.json')
        for name, expected_hash in snapshots[stem]['workingTreeSha256'].items():
            assert sha((local / stem / name).read_bytes()) == expected_hash
    manifest = {n: {'bytes': len(b), 'sha256': sha(b)} for n, b in sorted(files.items())}
    files['manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    archive = evidence / 'local-groth16-artifacts.tar.gz'
    with archive.open('wb') as f, gzip.GzipFile(fileobj=f, mode='wb', filename='', mtime=0) as z:
        with tarfile.open(fileobj=z, mode='w') as t:
            for name, raw in sorted(files.items()):
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(raw), 0o644
                t.addfile(info, io.BytesIO(raw))
    with tarfile.open(archive) as t:
        for name, entry in manifest.items():
            raw = t.extractfile(name).read()
            assert len(raw) == entry['bytes'] and sha(raw) == entry['sha256']
    proving = local / 'setup-01/public-proving-parameters.bin'
    with proving.open('rb') as f:
        proving_sha = hashlib.file_digest(f, 'sha256').hexdigest()
    baseline = json.loads((root / 'poc/proof-classification/evidence/classification.json').read_text())
    stage = lambda n: re.findall(r'PROFILE ([a-z_]+) (\d+)', (local / n).read_text())
    result = {
        'scope': 'REAL_SPECIALIZED_WALLET_PROOFS_AND_BOUNDED_GUEST_TESTS_NOT_COMPLETE_OUTER_CLASSIFICATION',
        'sourceCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'baseMain': 'eb9cdd99046faa53ae3c530e4cb064b050316459',
        'nativePin': '01b532e8b553523216471682649693af92f0fd16',
        'vprogsPin': 'f9b84a863a7c7c20586a9cf947550475e894f72e',
        'arkworks': '0.5', 'risc0Sdk': '3.0.3',
        'specializedCircuitNotReceiptWrapper': True, 'setup': setup,
        'publicProvingParameters': {'bytes': proving.stat().st_size, 'sha256': proving_sha,
                                   'archived': False, 'neededForVerification': False},
        'walletProofs': wallets, 'setupResources': read('setup-run.resources.json'),
        'twoWalletJobResources': read('wallet-run.resources.json'),
        'walletReverification': reverified, 'nativeFixture': expected,
        'outerExecutionBudgetCycles': 32000000, 'outerProofBudgetSeconds': 3600,
        'fullSequenceCompleted': False, 'outerProofAttempted': False, 'outerProofProduced': False,
        'outerProvingSeconds': None, 'outerProvingMemory': None,
        'completeClassifierCycles': None, 'classifierCycleLowerBound': 32000000,
        'completeClassifierSegments': None, 'budgetFailure': profile,
        'finalProfileResources': read('profile-reviewed.resources.json'),
        'initialKeyLoadDiagnosticStages': stage('profile-diagnostic.stdout.log'),
        'optimizedDiagnosticStages': stage('profile-reviewed.stdout.log'),
        'diagnosticCyclesAreNotCryptographicallyProven': True,
        'negativeGuestExecutions': controls,
        'validInvalidValidAndReplayGuestQualification': 'BLOCKED_BY_VALID_PROOF_EXECUTION_BUDGET',
        'watchdogTest': read('watchdog-test.resources.json'),
        'baseline': {'scope': baseline['scope'], 'walletArtifactBytes': 223418,
                     'operationBytes': 223992, 'nativeEstimatedBytes': 224257,
                     'transientMass': 897028, 'userCycles': 870829938, 'segments': 880,
                     'outerProofProduced': False},
        'newTN10Broadcasts': 0, 'fundedTrialReady': False, 'actualPrivacyPayment': False,
        'sourceSnapshots': snapshots,
        'programSha256': {p.name: sha(p.read_bytes()) for p in (local / 'programs-final').glob('*')},
        'parameterSha256': {p.name: sha(p.read_bytes()) for p in (local / 'setup-01').glob('*.bin') if p != proving},
        'hardware': {'cpuQuota': Path('/sys/fs/cgroup/cpu.max').read_text().strip(),
                     'memoryLimitBytes': int(Path('/sys/fs/cgroup/memory.max').read_text()),
                     'walletProvingThreads': 4, 'r0vmVersion': '3.0.3',
                     'r0vmSha256': sha(Path('/workspace/scratch/kpi-lane-tools/r0vm').read_bytes())},
        'artifactArchive': {'path': archive.name, 'bytes': archive.stat().st_size,
                            'sha256': sha(archive.read_bytes()), 'manifestEntries': len(manifest)},
    }
    (evidence / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['artifactArchive'], indent=2))


if __name__ == '__main__':
    main()
