#!/usr/bin/env python3
"""Offline retained execution/package checks; no proving, RPC or provider calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]

def main():
    evidence = ROOT / 'evidence'
    manifest = json.loads((evidence / 'manifest.json').read_text())
    for name, entry in manifest['files'].items():
        raw = (evidence / name).read_bytes()
        assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256'], name
    bindings = json.loads((ROOT / 'runmanifest.json').read_text())
    for name, expected in bindings['sourceSha256'].items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == expected, name
    plan = json.loads((ROOT / 'measurement-plan.json').read_text())
    campaign = json.loads((evidence / 'cpu/campaign.json').read_text())
    assert campaign['completed'] and campaign['wallSeconds'] <= plan['wallLimitCampaignSeconds']
    assert len(campaign['cases']) == 15
    assert all(row['exitCode'] == 0 and not row['timeout'] and row['wallSeconds'] <= plan['wallLimitPerCaseSeconds'] for row in campaign['cases'])
    image = (evidence / 'expected-image.txt').read_text().strip()
    targets = json.loads((evidence / 'targets.json').read_text())
    assert targets['expectedProgramImage'] == image == bindings['program']['image']
    for name in plan['positiveCases']:
        report = json.loads((evidence / 'cpu' / name / 'report.json').read_text())
        journal = (evidence / 'fixtures' / (name + '.journal.bin')).read_bytes()
        assert report['expectedImage'] == image and report['exactExpectedJournalMatched']
        assert report['userCycles'] <= plan['cycleLimitPerCase'] and report['segments'] > 1
        assert hashlib.sha256(journal).hexdigest() == report['journalSha256'] == targets['batches'][name]['expectedJournalSha256']
    for name in ['auth-root', 'auth-tip', 'auth-inclusion', 'auth-last-touch', 'auth-covenant', 'auth-lane', 'unreconciled-payout']:
        report = json.loads((evidence / 'cpu' / name / 'report.json').read_text())
        reason = (evidence / 'fixtures' / (name + '.abort.txt')).read_text().strip()
        assert report['expectedAbortConfirmed'] and report['expectedImage'] == image
        assert report['error'].startswith('Guest panicked:') and reason in report['error']
    host = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / '.local/ci-target/release/kpi-recovery-native-host'
    subprocess.run([str(host.resolve()), 'check-package', str(evidence / 'fixtures')], check=True)
    print('15 stored CPU cases and frozen six-batch package verified. No outer receipt or native issuance proof is claimed.')

if __name__ == '__main__':
    main()
