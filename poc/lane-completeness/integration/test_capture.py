#!/usr/bin/env python3
"""Adversarial mutations of retained live RPC evidence, with its end anchor fixed."""
import copy
import gzip
import json
from pathlib import Path
import sys
import unittest
from check_capture import reconstruct

SOURCE = Path(sys.argv.pop(1))
LANE = bytes.fromhex(sys.argv.pop(1))


def change_record(capture, label, mutate):
    record = next(r for r in capture['records'] if r['label'] == label)
    wire = json.loads(record['raw'])
    mutate(wire['params'])
    record['raw'] = json.dumps(wire)


class LiveCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = SOURCE.read_bytes()
        cls.source = json.loads(gzip.decompress(data) if SOURCE.suffix == '.gz' else data)

    def test_valid_live_interval(self):
        self.assertTrue(reconstruct(self.source, LANE)['ordered_transaction_ids'])

    def test_omission_against_same_anchor(self):
        with self.assertRaisesRegex(ValueError, 'fixed TN10 end anchor'):
            reconstruct(self.source, LANE, omit=True)

    def mutate_stream(self, mutate):
        capture = copy.deepcopy(self.source)
        for label in ['accepted', 'accepted-recheck']:
            change_record(capture, label, lambda r: mutate(r['chainBlockAcceptedTransactions']))
        return capture

    def test_payload_substitution(self):
        def mutate(blocks):
            tx = next(t for b in blocks for t in b['acceptedTransactions'] if t['subnetworkId'] == LANE.hex())
            tx['payload'] += '00'
        with self.assertRaisesRegex(ValueError, 'ID mismatch'):
            reconstruct(self.mutate_stream(mutate), LANE)

    def test_accepted_duplicate(self):
        def mutate(blocks):
            b = next(b for b in blocks if any(t['subnetworkId'] == LANE.hex() for t in b['acceptedTransactions']))
            tx = next(t for t in b['acceptedTransactions'] if t['subnetworkId'] == LANE.hex())
            b['acceptedTransactions'].append(copy.deepcopy(tx))
        with self.assertRaisesRegex(ValueError, 'duplicate accepted'):
            reconstruct(self.mutate_stream(mutate), LANE)

    def test_wrong_lane(self):
        lane = bytearray(LANE); lane[1] ^= 1
        with self.assertRaisesRegex(ValueError, 'wrong lane key'):
            reconstruct(self.source, bytes(lane))

    def test_changed_endpoint(self):
        capture = copy.deepcopy(self.source)
        change_record(capture, 'end-block', lambda r: r['block']['header'].update(acceptedIdMerkleRoot='99' * 32))
        with self.assertRaisesRegex(ValueError, 'end witness mismatch'):
            reconstruct(capture, LANE)

    def test_corrupt_witness(self):
        capture = copy.deepcopy(self.source)
        change_record(capture, 'end-proof', lambda r: r.update(smtProof=r['smtProof'][:-1]))
        with self.assertRaisesRegex(ValueError, 'SMT'):
            reconstruct(capture, LANE)

    def test_reorg(self):
        capture = copy.deepcopy(self.source)
        change_record(capture, 'accepted-recheck', lambda r: r.update(removedChainBlockHashes=['99' * 32]))
        with self.assertRaisesRegex(ValueError, 'reorg'):
            reconstruct(capture, LANE)


if __name__ == '__main__':
    unittest.main()
