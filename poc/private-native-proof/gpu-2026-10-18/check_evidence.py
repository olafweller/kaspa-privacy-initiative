#!/usr/bin/env python3
"""Offline audit of the failed attempt; never contacts provider or starts proving."""
import hashlib
import json
from pathlib import Path
import sys

from reproduce_output_contract import reproduce

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'poc/remote-cuda'))
from package import checked_archive
from lifecycle_package import INPUTS, IMAGE, continuity


def main():
    evidence = HERE/'evidence'
    read = lambda name: json.loads((evidence/name).read_text())
    manifest = read('manifest.json')
    for name, record in manifest['files'].items():
        raw = (evidence/name).read_bytes()
        assert len(raw) == record['bytes']
        assert hashlib.sha256(raw).hexdigest() == record['sha256'], name
    lease = read('lease.json')
    result = read('result.json')
    assert result['attempts'] == 1 and result['proofsProduced'] == result['candidateReceipts'] == 0
    assert result['outcome'] == 'FAILED_BEFORE_FIRST_PROOF'
    assert result['cryptographicSuccess'] is False and result['CUDAQualification'].startswith('NOT_ESTABLISHED')
    assert result['nativeNewExitVerification'] == 'NOT_RUN_NO_EXIT_RECEIPT'
    assert result['aggregateProofSecondsLimit'] == 3600 and lease['stopUnix']-lease['createdUnix'] == 7200
    assert not result['automaticRetry'] and not result['runtimeOrGuestChangedDuringAttempt']
    assert not result['TN10Broadcast'] and not result['nativeFunding']
    terminal = read('artifacts/terminal-backup.json')
    archive = evidence/'terminal-artifacts.tar.gz'
    assert archive.stat().st_size == terminal['bytes']
    contents = checked_archive(archive, terminal['sha256'])
    for name, digest in INPUTS.items():
        assert hashlib.sha256(contents['assets/'+name]).hexdigest() == digest
    assert not any('/receipt.bin' in n or '/candidate-receipt.bin' in n for n in contents)
    assert b'No such file or directory' in contents['aggregate.stderr.log']
    assert b'deposit-prove' in contents['aggregate.stderr.log']
    stage = json.loads(contents['stages/00-deposit-prove.json'])
    assert stage['exitCode'] == 1 and stage['case'] == 'deposit'
    assert 'proofs/deposit/started.json' not in contents
    for path in ['results/b-verification.json', 'results/independent-verification/verification.json',
                 'cloud-zero-receipt-audit.json']:
        audit = read(path)
        if 'result' in audit:
            assert audit['archiveAndPublicInputsVerified']
            audit = audit['result']
        assert audit['verifiedCount'] == 0 and not audit['allFourCryptographicallyVerified']
    stop = read('results/provider-stop-observation.json')
    deleted = read('results/provider-deletion.json')
    assert stop['providerDesiredExitedConfirmed'] and stop['guardStop']['providerDesiredExitedConfirmed']
    assert deleted['providerGetStatus'] == 404 and deleted['providerListStatus'] == 200
    assert deleted['podAbsentFromList'] and deleted['remainingPodCount'] == 0
    assert deleted['bArchiveRevalidatedBeforeDelete'] and deleted['cloudRecoveryVerified']
    assert 'ActiveState=inactive' in deleted['guardUnitState'] and 'UnitFileState=disabled' in deleted['guardUnitState']
    assert lease['podId'] == stop['provider']['id'] == deleted['podId'] == result['podId']
    costs = read('cost-estimate.json')
    assert costs['actualInvoiceAvailable'] is False
    assert abs(costs['gpuCostFromProviderReportedExitApproxUsd'] -
               costs['providerReportedRunningSecondsApprox']/3600*float(lease['actualGpuHourlyUsd'])) < 1e-12
    assert costs['gpuPlusConservativeStorageToObservedExitEstimateUsd'] < result['planningUsd']
    assert reproduce() == read('output-contract-reproduction.json')
    print(f"OK: {len(manifest['files'])} evidence files; failed first stage/zero receipts; "
          "independent preservation, provider stop/deletion and directory-contract reproduction. "
          "No proof/provider action run.")


if __name__ == '__main__':
    main()
