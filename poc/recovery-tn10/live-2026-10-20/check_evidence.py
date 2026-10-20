#!/usr/bin/env python3
"""Reverify retained actual-input receipts on CPU; no wallets, proving or RPC."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'poc/recovery-tn10/service'))
sys.path.append(str(ROOT / 'poc/remote-cuda'))
from staged_package import base

CASES = ('deposit', 'credit-transfer', 'bob-exit', 'bob-reconcile', 'alice-exit', 'alice-reconcile')


def main():
    evidence = HERE / 'evidence'
    read = lambda p: json.loads(p.read_text())
    manifest = read(evidence / 'manifest.json')['files']
    files = {p.relative_to(evidence).as_posix() for p in evidence.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    expected = {'result.json'} | {f'{directory}/{case}.{suffix}' for case in CASES for directory, suffix in (('targets', 'json'), ('receipts', 'bin'), ('cpu', 'json'))}
    assert files == set(manifest) == expected, 'exact allowlisted public evidence required'
    for name, record in manifest.items():
        raw = (evidence / name).read_bytes()
        assert len(raw) == record['bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256'], name
    result = read(evidence / 'result.json')
    assert tuple(result['stages']) == CASES and result['allSixFinalReceiptsVerified']
    assert result['totalDistinctCryptographicNegativeControls'] == 90
    assert result['independentBAndCloudCpuVerification']
    qualifications = result['signedNativeQualifications']
    assert set(qualifications) == set(result['nativeAcceptedTransactions']) - {'funding'}
    for label, record in qualifications.items():
        q = record['qualification']
        assert record['transactionId'] == result['nativeAcceptedTransactions'][label]['transactionId']
        assert q['allInputScriptsExecuted'] and q['feeSompi'] >= q['requiredFeeSompi']
    assert sum(v['qualification']['feeSompi'] for k, v in qualifications.items() if k.endswith('-settlement')) == 285_598_400
    assert result['allSixMatchingProcessCudaQualified']
    timing = result['timing']
    assert timing['originalSharedDeadlineUnix'] - timing['firstStageStartUnix'] == 3600
    assert timing['withinOriginal3600SecondLimit'] and not timing['deadlineExtended']
    assert timing['lastProofProcessEndUnixApprox'] <= timing['originalSharedDeadlineUnix']
    assert abs(timing['sharedProofAndWaitSecondsApprox'] - (timing['lastProofProcessEndUnixApprox'] - timing['firstStageStartUnix'])) < 1e-6
    lease = result['lease']
    assert lease['stopUnix'] - lease['createdUnix'] == 7200
    assert result['providerStop']['providerDesiredExitedConfirmed']
    assert result['providerStop']['provider']['desiredStatus'] == 'EXITED'
    assert result['providerStop']['guardStop']['providerDesiredExitedConfirmed']
    deleted = result['providerDeletion']
    assert deleted['providerGetStatus'] == 404 and deleted['podAbsentFromList']
    assert deleted['bArchiveRevalidatedBeforeDelete'] and deleted['deletedPodVolumeGb'] == 10
    assert deleted['deletedContainerDiskGb'] == 90 and not deleted['networkVolumeCreated']
    assert deleted['podId'] == lease['podId'] == result['providerStop']['provider']['id']
    assert 'ActiveState=inactive' in deleted['guardUnitState'] and 'UnitFileState=disabled' in deleted['guardUnitState']
    assert result['cost']['computeAndStorageEstimateUsd'] < 5 and not result['cost']['actualInvoiceAvailable']
    native = result['finalNativeReadback']
    assert native['bobPayoutSompi'] == 450_000_000 and native['alicePayoutSompi'] == 650_000_000
    assert all(native[k] for k in ('bothRecipientOutputsPresent', 'bothPermissionsSpent', 'initialAndRemainingReserveSpent', 'allPreviousStateOutputsSpent'))
    accounting = result['finalCheckpoint']['accounting']
    assert all(accounting[k] == 0 for k in ('reserve_principal', 'private_liability', 'pending_deposits', 'unpaid_exits', 'outstanding_permission_rent_excluded'))
    assert accounting['state_covenant_rent_excluded'] == 100_000_000
    assert result['coldBRecovery']['freshReplay'] and result['coldBRecovery']['networkUnavailable']
    assert result['coldBRecovery']['publicMaterializedCacheInaccessible'] and result['coldBRecovery']['originalCacheAbsentOnB']
    assert result['originalControllerInterruption']['executionDenied'] and not result['originalControllerInterruption']['activeOriginalJobsAtOutage']
    assert result['ownerReportedMintRecovery']['bob']['freshT7RestoreBothWallets']
    assert result['ownerReportedMintRecovery']['alice']['aliceRecoveredSompi'] == 600_000_000
    assert not result['retainedPrivateEvidence']['ownerReceiveFilesAndPublicInputBodiesPublished']
    assert not result['retainedPrivateEvidence']['userSecretsTransferred']
    journals = []
    with tempfile.TemporaryDirectory(prefix='kpi-live-receipts-') as directory:
        directory = Path(directory)
        trusted = base(directory / 'trusted')
        verifier = trusted / 'bin/kpi-recovery-tn10'
        env = {'PATH': os.defpath, 'LANG': 'C', 'RAYON_NUM_THREADS': '4'}
        for case in CASES:
            expected = result['stages'][case]
            target = evidence / 'targets' / (case + '.json')
            receipt = evidence / 'receipts' / (case + '.bin')
            target_value = read(target)
            assert target_value['stage'] == case and target_value['trial'] == result['trial']
            assert target_value['cycleLimit'] == 160_000_000 and target_value['aggregateProofSeconds'] == 3600
            assert expected['userCycles'] <= 160_000_000
            assert expected['segmentPo2'] == target_value['segmentPo2'] == (20 if case in ('credit-transfer', 'bob-exit', 'alice-exit') else 16)
            assert expected['matchingActiveGpuSamples'] > 0 and expected['matchingActiveGpuSamples'] <= expected['sampleCount']
            assert expected['cpuAffinity'] == [0, 1, 2, 3] and expected['computeThreads'] == 4
            journal = bytes.fromhex(target_value['journalHex'])
            assert len(journal) == 352 and hashlib.sha256(journal).hexdigest() == expected['journalSha256']
            journals.append(journal)
            assert hashlib.sha256(target.read_bytes()).hexdigest() == expected['targetSha256']
            assert hashlib.sha256(receipt.read_bytes()).hexdigest() == expected['receiptSha256']
            output = directory / case
            run = subprocess.run([str(verifier), 'verify', str(target), expected['targetSha256'], str(receipt), str(output)], env=env, capture_output=True, text=True, timeout=120)
            assert run.returncode == 0, (case, run.stderr)
            verified = read(output / 'verification.json')
            assert verified == read(evidence / 'cpu' / (case + '.json')), 'fresh verification must equal retained report'
            assert verified['image'] == result['guestImage'] and verified['join'] == result['joinControl']
            assert not verified['developmentMode'] and verified['noUnresolvedAssumptions']
            negatives = verified['negativeControls']
            assert negatives['tamperedJournalOffsetsRejected'] == list(range(0, 352, 32))
            assert all(negatives[k] for k in ('wrongImageRejected', 'corruptedSealRejected', 'malformedControlInclusionRejected', 'wrongExpectedControlRejectedBySealVerifier'))
    for previous, current in zip(journals, journals[1:]):
        assert previous[64:96] == current[:32] and previous[96:128] == current[32:64], 'state/lane-tip discontinuity'
        assert previous[160:256] == current[160:256] and previous[320:352] == current[320:352], 'protocol/covenant/lane substitution'
    assert journals[-1][64:96].hex() == result['finalCheckpoint']['stateRoot']
    assert abs(sum(v['producerProcessWallSeconds'] for v in result['stages'].values()) - result['sumProducerProcessWallSeconds']) < 1e-6
    print('OK: six actual-input receipt seals and exact journals freshly verified on CPU; 90 cryptographic mutations, journal continuity and retained closure records checked. No proving, wallet access, RPC, provider or broadcast.')


if __name__ == '__main__':
    main()
