#!/usr/bin/env python3
"""Recheck real stored receipts on trusted CPU; no proving or provider access."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'poc/remote-cuda'))
from package import checked_archive, write
from lifecycle_package import restore, CASES, IMAGE
from lifecycle_control import verify


def main():
    evidence = HERE/'evidence'
    read = lambda name: json.loads((evidence/name).read_text())
    manifest = read('manifest.json')
    for name, record in manifest['files'].items():
        data = (evidence/name).read_bytes()
        assert len(data) == record['bytes']
        assert hashlib.sha256(data).hexdigest() == record['sha256'], name
    result = read('result.json')
    assert result['receiptCount'] == 4 and result['programImage'] == IMAGE
    assert result['cryptographicSuccess'] and result['independentBAndCloudVerification']
    assert result['allFourMatchingProcessCUDAQualified']
    assert result['aggregateWholeJobSeconds'] <= result['aggregateProofLimitSeconds'] == 3600
    assert not result['TN10Broadcast'] and not result['nativeFunding'] and not result['automaticRetry']
    lease = read('lease.json')
    assert lease['stopUnix']-lease['createdUnix'] == 7200
    backup = read('artifacts/terminal-backup.json')
    data = checked_archive(evidence/'terminal-artifacts.tar.gz', backup['sha256'])
    assert (evidence/'terminal-artifacts.tar.gz').stat().st_size == backup['bytes']
    observed = read('results/b-verification.json')
    assert observed['fullLocalExperimentCompleted'] and observed['cryptographicSuccess'] and observed['CUDAQualification']
    stop = read('results/provider-stop-observation.json')
    deleted = read('results/provider-deletion.json')
    assert lease['podId'] == result['podId'] == stop['provider']['id'] == deleted['podId']
    assert stop['providerDesiredExitedConfirmed'] and stop['guardStop']['providerDesiredExitedConfirmed']
    assert deleted['providerGetStatus'] == 404 and deleted['podAbsentFromList']
    assert deleted['remainingPodCount'] == 0 and deleted['bArchiveRevalidatedBeforeDelete'] and deleted['cloudRecoveryVerified']
    assert deleted['receiptCount'] == 4 and deleted['deletedPodVolumeGb'] == 10
    assert deleted['deletedContainerDiskGb'] == 90 and not deleted['networkVolumeCreated']
    assert 'ActiveState=inactive' in deleted['guardUnitState'] and 'UnitFileState=disabled' in deleted['guardUnitState']
    stages = result['stages']
    assert len(stages) == 9 and all(s['finished'] and s['exitCode'] == 0 for s in stages)
    cuda = observed['cudaByBatch']
    assert set(cuda) == set(CASES) and all(v['matchingProcessCudaActivityObserved'] for v in cuda.values())
    assert result['sampledPeakMatchingGpuVramMiB'] == observed['aggregateResources']['peakMatchingGpuProcessVramMiB']
    costs = read('cost-estimate.json')
    assert costs['actualInvoiceAvailable'] is False and costs['conservativeComputeAndStorageEstimateUsd'] < 5
    assert abs(costs['computeEstimateUsd'] - costs['providerReportedComputeSecondsApprox']/3600*float(lease['actualGpuHourlyUsd'])) < 1e-12
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        trusted = root/'trusted'
        restore(trusted)
        returned = root/'returned'
        returned.mkdir()
        for name, raw in data.items():
            write(returned/name, raw)
        audit = verify(trusted, returned, root/'cpu')
        assert audit['verifiedCount'] == 4 and audit['allFourCryptographicallyVerified']
        assert audit['nativePermissionAndRestrictedPayoutVerified'] and not audit['failures']
        assert {case:row['sha256'] for case,row in audit['verifiedReceipts'].items()} == result['receiptHashes']
        for case in CASES:
            report = json.loads((root/'cpu'/case/'verification.json').read_text())
            assert report['programImage'] == IMAGE and report['exactJournalVerified']
            assert report['developmentMode'] is False and report['noUnresolvedAssumptions']
            controls = report['negativeControls']
            assert controls['tamperedJournalOffsetsRejected'] == list(range(0,352,32))
            assert all(controls[k] for k in ('wrongImageRejected','corruptedSealRejected',
                       'malformedControlInclusionRejected','wrongExpectedControlRejectedBySealVerifier'))
        native = json.loads((root/'cpu/native-exit/native-verification.json').read_text())
        assert native['permissionIssuanceReceiptVerified'] and native['matchesFrozenReconciliationInput']
        payout = native['payout']
        assert payout['positiveNativeScriptsAccepted'] and all(x['rejected'] for x in payout['negativeControls'])
        assert payout['principalPaidSompi'] == 400_000_000 and payout['permissionRentRefundSompi'] == 50_000_000
        assert payout['delegateChangeSompi'] == 600_000_000 and payout['stateRentExcludedSompi'] == 100_000_000
    print(f"OK: {len(manifest['files'])} evidence files; four genuine receipts, exact journals, "
          "cryptographic negatives and native exit reverified on CPU; CUDA/stop/deletion records checked. "
          "No proof generation or network/provider action.")


if __name__ == '__main__':
    main()
