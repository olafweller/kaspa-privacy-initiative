"""Offline tests; synthetic targets are explicitly not chain/proof evidence."""
import copy
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import bundle
import run_stage


def target(stage='deposit', root='11', tip='22', next_root='33', next_tip='44'):
    journal = bytes.fromhex(root*32+tip*32+next_root*32+next_tip*32+'55'*32+'66'*32+'77'*32+'88'*32+'99'*32+'aa'*32+'bb'*32)
    return {'schema': 'KPI_TN10_FROZEN_BATCH_V1', 'trial': 'synthetic-unfunded',
            'stage': stage, 'journalHex': journal.hex(), 'journalSha256': bundle.sha(journal)}


class Preparation(unittest.TestCase):
    def lease(self):
        return {'podId': 'SYNTHETIC-NOT-A-LEASE', 'createdUnix': 1000, 'stopUnix': 8200}

    def test_shared_deadline_is_not_reset_between_chain_waits(self):
        ledger = run_stage.reserve(None, target(), 'a'*64, self.lease(), 1100)
        self.assertEqual(ledger['deadlineUnix'], 4700)
        ledger['completed'] = ['deposit']
        ledger['lastJournalHex'] = ledger.pop('pendingJournalHex')
        next_target = target('credit-transfer', '33', '44', '12', '13')
        new = run_stage.reserve(ledger, next_target, 'b'*64, self.lease(), 2000)
        self.assertEqual(new['deadlineUnix'], 4700)

    def test_failed_or_interrupted_stage_cannot_retry(self):
        ledger = run_stage.reserve(None, target(), 'a'*64, self.lease(), 1100)
        with self.assertRaises(ValueError):
            run_stage.reserve(ledger, target(), 'a'*64, self.lease(), 1101)
        with self.assertRaises(ValueError):
            run_stage.reserve(ledger, target('credit-transfer'), 'b'*64, self.lease(), 1101)

    def test_deadline_lease_extension_and_insufficient_transfer_margin_rejected(self):
        lease = self.lease()
        ledger = run_stage.reserve(None, target(), 'a'*64, lease, 1100)
        with self.assertRaises(ValueError):
            run_stage.reserve(ledger, target(), 'a'*64, lease, 4700)
        with self.assertRaises(ValueError):
            run_stage.reserve(ledger, target(), 'a'*64, lease | {'stopUnix': 8300}, 1200)
        with self.assertRaises(ValueError):
            run_stage.reserve(None, target(), 'a'*64, lease, 5000)

    def test_reorg_root_lane_or_trial_change_cannot_advance(self):
        ledger = run_stage.reserve(None, target(), 'a'*64, self.lease(), 1100)
        ledger['completed'] = ['deposit']
        ledger['lastJournalHex'] = ledger.pop('pendingJournalHex')
        for changed in [target('credit-transfer'), target('credit-transfer', '33', '00'),
                        target('credit-transfer', '33', '44') | {'trial': 'other'}]:
            with self.assertRaises(ValueError):
                run_stage.reserve(copy.deepcopy(ledger), changed, 'b'*64, self.lease(), 1200)

    def test_public_bundle_excludes_keys_and_rejects_changed_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            t = target()
            for name, field in [('guest.program.bin', 'programSha256'), ('input.bin', 'inputSha256'), ('journal.bin', 'journalSha256')]:
                raw = bytes.fromhex(t['journalHex']) if name == 'journal.bin' else b'SYNTHETIC-public-only'
                (p/name).write_bytes(raw)
                t[field] = bundle.sha(raw)
            (p/'target.json').write_text(json.dumps(t))
            (p/'bob.key').write_bytes(b'synthetic-secret-never-archive')
            expected = bundle.sha((p/'target.json').read_bytes())
            result = bundle.bundle(p, expected, p/'public.tgz')
            with tarfile.open(p/'public.tgz') as tar:
                self.assertEqual(tar.getnames(), list(bundle.FILES))
            self.assertEqual(result['files'], list(bundle.FILES))
            (p/'input.bin').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                bundle.bundle(p, expected, p/'changed.tgz')


if __name__ == '__main__':
    unittest.main()
