"""Offline manifest/source evidence checks, no network or proving."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    manifest = json.loads((ROOT/'runmanifest.json').read_text())
    trial = json.loads((ROOT/manifest['publicTrial']).read_text())
    assert manifest['status'] == 'OFFLINE_PREPARATION_FOR_REVIEW_NOT_LIVE_READY'
    assert not any(manifest['authorizations'].values())
    assert manifest['trial'] == trial['trial']
    assert sha(ROOT/manifest['publicTrial']) == manifest['publicTrialSha256']
    assert manifest['pins']['guestImage'] == trial['guestImage']
    assert manifest['pins']['guestProgramSha256'] == sha(REPO/'poc/private-native/evidence/guest.program.bin')
    policy = manifest['futureProofPolicy']
    assert (policy['aggregateSeconds'], policy['rentalSecondsFromActualCreation'], policy['attempts']) == (3600, 7200, 1)
    assert policy['stagedImageDigest'] is None and policy['existingFixedImageIsNotStagedService']
    assert [s['name'] for s in manifest['stages']] == ['deposit', 'credit-transfer', 'exit', 'reconcile']
    for stage in manifest['stages']:
        assert stage['targetSha256'] is None and stage['receiptSha256'] is None
    for file, expected in json.loads((ROOT/'evidence/source-sha256.json').read_text()).items():
        assert sha(REPO/file) == expected, file
    print('TN10 preparation manifest/source bindings valid; actual-chain inputs, staged image and live release remain unset.')


if __name__ == '__main__':
    check()
