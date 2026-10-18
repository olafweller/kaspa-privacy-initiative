#!/usr/bin/env python3
"""Offline integrity/accounting check; retained execution is not rerun here."""
import ast
import hashlib
import json
from pathlib import Path


def check():
    root = Path(__file__).resolve().parent
    evidence = root / 'evidence'
    manifest = json.loads((evidence / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        data = (evidence / name).read_bytes()
        assert len(data) == expected['bytes'], name
        assert hashlib.sha256(data).hexdigest() == expected['sha256'], name
    for file in root.glob('*.py'):
        ast.parse(file.read_text(), filename=str(file))
    bindings = json.loads((evidence / 'source-bindings.json').read_text())
    for name, expected in bindings['sourceFiles'].items():
        assert hashlib.sha256((root.parents[1] / name).read_bytes()).hexdigest() == expected, name
    rows = json.loads((evidence / 'lifecycle.json').read_text())['rows']
    assert len(rows) == 7
    for row in rows:
        a = row['accounting']
        assert all(type(v) is int and 0 <= v <= 2**64 - 1 for v in a.values())
        assert a['reserve_principal'] == a['private_liability'] + a['pending_deposits'] + a['unpaid_exits']
        assert a['state_covenant_rent_excluded'] == 100000000
    assert rows[0]['accounting']['reserve_principal'] == 0
    assert rows[-1]['accounting']['reserve_principal'] == 600000000
    assert rows[-1]['accounting']['unpaid_exits'] == 0
    native = json.loads((evidence / 'native-payout.json').read_text())
    assert native['positiveNativeScriptsAccepted']
    assert not native['permissionIssuanceReceiptVerified']
    assert not native['actualTN10Broadcast']
    assert native['recipientNativeOutputSompi'] == native['principalPaidSompi'] + native['permissionRentRefundSompi'] == 450000000
    assert native['sponsorInputSompi'] - native['sponsorChangeSompi'] == native['nativeFeeSompi']
    campaign = json.loads((evidence / 'execution/campaign.json').read_text())
    assert campaign['completed'] and len(campaign['cases']) == 17
    assert all(c['exitCode'] == 0 and not c['timeout'] for c in campaign['cases'])
    target = json.loads((evidence / 'targets.json').read_text())
    assert not target['gpuRentalAuthorized'] and not target['TN10BroadcastAuthorized']
    for case, batch in target['batches'].items():
        report = json.loads((evidence / 'execution' / case / 'report.json').read_text())
        assert report['exactExpectedJournalMatched']
        assert report['expectedImage'] == target['expectedProgramImage']
        assert report['userCycles'] == batch['measuredUserCycles'] <= 160000000
        assert report['segments'] == batch['measuredSegments'] > 1
        journal = bytes.fromhex(batch['expectedJournalHex'])
        assert len(journal) == 352
        assert hashlib.sha256(journal).hexdigest() == batch['expectedJournalSha256']
        assert journal == (evidence / (case + '.journal.bin')).read_bytes()
    print(f'OK: {len(manifest["files"])} evidence files; exact sompi accounting; 17 retained executions. No live proof or chain test run.')


if __name__ == '__main__':
    check()
