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
    assert campaign['completed'] and len(campaign['cases']) == 21
    assert all(c['exitCode'] == 0 and not c['timeout'] for c in campaign['cases'])
    declared = json.loads((evidence / 'execution-declaration.json').read_text())
    assert declared['cycleLimitPerCase'] == campaign['cycleLimitPerCase'] == 160000000
    assert declared['wallLimitPerCaseSeconds'] == campaign['wallLimitPerCaseSeconds'] == 900
    assert declared['wallLimitCampaignSeconds'] == campaign['wallLimitCampaignSeconds'] == 3600
    assert declared['cases'] == [c['case'] for c in campaign['cases']]
    for case in campaign['cases']:
        name = case['case']
        report = json.loads((evidence / 'execution' / name / 'report.json').read_text())
        assert report['expectedImage'] == declared['expectedProgramImage']
        if name.startswith('auth-') or name in ['reject-underpay', 'reject-reserve-diversion', 'reject-wrong-recipient']:
            assert report['expectedAbortConfirmed']
            assert report['error'].startswith('Guest panicked: ')
            if not name.startswith('auth-'):
                assert report['expectedAbortReason'] == 'unreconciled accepted native consumption'
        else:
            assert report['exactExpectedJournalMatched']
    regressions = json.loads((evidence / 'review-regressions.json').read_text())
    cases = {c['case']: c for c in regressions['cases']}
    assert cases['top-up']['restrictedNativeAccepted'] and cases['top-up']['outpointAdvanced']
    assert cases['top-up']['recipientSompi'] == 450000001
    assert cases['top-up']['accounting']['unpaid_exits'] == 0
    assert cases['versioned-sponsor-output']['restrictedNativeAccepted']
    assert cases['versioned-sponsor-output']['outpointAdvanced']
    assert cases['versioned-sponsor-output']['accounting']['unpaid_exits'] == 0
    for name in ['default-lane', 'partial', 'partial-three-outputs', 'extra-sponsor-input', 'extra-sponsor-output', 'foreign-reserve']:
        assert cases[name]['upstreamAccepted'] and not cases[name]['restrictedNativeAccepted']
        assert cases[name]['rejectedBeforeFundsMove']
    second = cases['second-deposit']
    assert second['nativeDepositAccepted'] and second['nativePayoutAccepted'] and second['otherDepositPreserved']
    assert second['reserves'] == 2
    assert second['accounting']['reserve_principal'] == 1600000000
    assert second['accounting']['pending_deposits'] == 1000000000
    assert second['accounting']['unpaid_exits'] == 0
    guard = json.loads((evidence / 'state-guard.json').read_text())
    assert guard['guardCopiedInContinuation'] and not guard['newLifecycleReceiptProduced']
    assert [c['accepted'] for c in guard['nativeEngineCases']] == [True, False, False]
    assert guard['archivedReceiptSha256'] == 'da7c485545c9bbdf08862e987cd5418aaf4eb7e64a833325951d19909150ce46'
    target = json.loads((evidence / 'targets.json').read_text())
    assert declared['expectedProgramImage'] == bindings['guestImage'] == target['expectedProgramImage']
    assert declared['programSha256'] == target['programSha256'] == campaign['programSha256']
    assert campaign['hostSha256'] == bindings['binaries']['kpi-private-native-host']['sha256']
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
    policy = json.loads((evidence / 'native-policy.json').read_text())
    redeem = bytes.fromhex(policy['permissionRedeem'])
    assert hashlib.blake2b(redeem, digest_size=32).digest() == bytes.fromhex(target['batches']['exit']['expectedJournalHex'])[256:288]
    print(f'OK: {len(manifest["files"])} evidence files; exact sompi accounting; 21 retained executions; native/accounting regressions. No live proof or chain test run.')


if __name__ == '__main__':
    check()
