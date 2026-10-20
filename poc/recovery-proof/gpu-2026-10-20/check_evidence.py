#!/usr/bin/env python3
"""Reverify retained real receipts/native effects on CPU; never prove or rent."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'poc/remote-cuda'))
from recovery_control import extract, verify
from recovery_package import restore, CASES, IMAGE, CONTROL
from recovery_worker import cuda_by_batch


def main():
    evidence = HERE/'evidence'
    read = lambda n: json.loads((evidence/n).read_text())
    manifest = read('manifest.json')
    actual = {p.relative_to(evidence).as_posix() for p in evidence.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    assert actual == set(manifest['files']), 'unlisted or missing retained evidence'
    for name, record in manifest['files'].items():
        raw = (evidence/name).read_bytes()
        assert len(raw) == record['bytes'] and hashlib.sha256(raw).hexdigest() == record['sha256'], name
    result = read('result.json')
    assert result['programImage'] == IMAGE and result['joinControl'] == CONTROL
    assert result['receiptCount'] == 6 and result['cryptographicSuccess'] and result['CUDAQualification']
    assert result['independentBAndCloudVerification'] and not result['TN10Broadcast']
    assert not result['nativeFunding'] and not result['automaticRetry']
    assert result['aggregateWholeJobSeconds'] <= result['aggregateProofLimitSeconds'] == 3600
    lease = read('lease.json')
    assert lease['stopUnix'] - lease['createdUnix'] == 7200
    backup = read('artifacts/terminal-backup.json')
    assert (evidence/'terminal-artifacts.tar.gz').stat().st_size == backup['bytes']
    b = read('results/b-verification.json')
    cloud = read('results/cloud-recovery-verification.json')
    assert b['cryptographicSuccess'] and b['result']['allSixFinalReceiptsVerified']
    assert cloud['allSixFinalReceiptsVerified'] and cloud['verifiedCount'] == 6
    assert b['archiveSha256'] == cloud['archiveSha256'] == backup['sha256']
    assert len(b['stages']) == 14 and all(s['finished'] and s['exitCode'] == 0 for s in b['stages'])
    stop = read('results/provider-stop-observation.json')
    deleted = read('results/provider-deletion.json')
    assert lease['podId'] == result['podId'] == stop['provider']['id'] == deleted['podId']
    assert stop['providerDesiredExitedConfirmed'] and stop['guardStop']['providerDesiredExitedConfirmed']
    assert deleted['providerGetStatus'] == 404 and deleted['podAbsentFromList']
    assert deleted['bArchiveRevalidatedBeforeDelete'] and deleted['cloudRecoveryVerified']
    assert deleted['receiptCount'] == 6 and deleted['deletedPodVolumeGb'] == 10
    assert deleted['deletedContainerDiskGb'] == 90 and not deleted['networkVolumeCreated']
    assert 'ActiveState=inactive' in deleted['guardUnitState'] and 'UnitFileState=disabled' in deleted['guardUnitState']
    costs = read('cost-estimate.json')
    assert not costs['actualInvoiceAvailable'] and costs['conservativeComputeAndStorageEstimateUsd'] < 5
    assert abs(costs['computeEstimateUsd'] - costs['providerReportedComputeSecondsApprox']/3600*float(lease['actualGpuHourlyUsd'])) < 1e-12
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        trusted = root/'trusted'
        restore(trusted)
        returned = root/'returned'
        extract(evidence/'terminal-artifacts.tar.gz', returned, backup['sha256'])
        audit = verify(trusted, returned, root/'cpu')
        assert audit['allSixFinalReceiptsVerified'] and not audit['failures']
        assert {case:r['sha256'] for case,r in audit['verifiedReceipts'].items()} == result['receiptHashes']
        assert audit['verifiedReceipts'] == b['result']['verifiedReceipts'] == cloud['verifiedReceipts']
        assert cuda_by_batch(returned) == b['cuda-by-batch']
        assert all(row['matchingProcessCudaActivityObserved'] for row in cuda_by_batch(returned).values())
        gpu = json.loads((returned/'hardware.json').read_text())
        for line in (returned/'aggregate.samples.jsonl').read_text().splitlines():
            sample = json.loads(line)
            assert all(p['gpuUuid'] == gpu['uuid'] and p['pid'] in sample['groupPids'] for p in sample['matchingGpuProcesses'])
        for case in CASES:
            r = json.loads((root/'cpu'/case/'verification.json').read_text())
            assert r['programImage'] == IMAGE and r['controlId'] == CONTROL and r['exactJournalVerified']
            assert not r['developmentMode'] and r['noUnresolvedAssumptions']
            n = r['negativeControls']
            assert n['tamperedJournalOffsetsRejected'] == list(range(0,352,32))
            assert all(n[k] for k in ('wrongImageRejected','corruptedSealRejected','malformedControlInclusionRejected','wrongExpectedControlRejectedBySealVerifier'))
        for case, count, reserve in (('bob-exit',8,600_000_000),('alice-exit',9,0)):
            r = json.loads((root/'cpu/native'/case/'native-issuance.json').read_text())
            identities = json.loads((root/'cpu/native'/case/'native-identities-and-negatives.json').read_text())
            assert r['newReceiptVerified'] and r['frozenPermissionIdMatched'] and not r['nativeBroadcast']
            assert r['accounting']['reserve_principal'] == reserve
            assert r['accounting']['unpaid_exits'] == r['accounting']['outstanding_permission_rent_excluded'] == 0
            assert r['accounting']['state_covenant_rent_excluded'] == 100_000_000
            assert len(identities['negativeVariants']) == count and identities['newReceiptRequired']
    print('OK: six real receipts and exact journals reverified; 90 cryptographic mutations and both native exits/17 semantic negatives; CUDA telemetry and preservation/stop/deletion evidence checked. No proving, funding or network/provider action.')


if __name__ == '__main__':
    main()
