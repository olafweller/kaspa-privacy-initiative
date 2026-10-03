"""Receipt-boundary unit negatives, not native/A1 proof-positive evidence."""
import copy
import unittest
from a1_check import Invalid
from a1_reorg_check import groups


class NativeReceiptTests(unittest.TestCase):
    def setUp(self):
        self.block = 'ab' * 32
        self.data = [{'accepting_block': self.block,
                     'acceptance_data': [{'block_hash': 'cd' * 32,
                        'accepted_transactions': [{'index_within_block': 1, 'transaction_id': 'ef' * 32}]}],
                     'accepted_bodies': [{'source_block': 'cd' * 32, 'index_within_block': 1,
                        'txid': 'ef' * 32, 'full_hash': '01' * 32, 'transaction': {'id': 'ef' * 32}}]}]

    def test_exact_native_source_index(self):
        result = groups(self.data, [self.block])
        self.assertEqual(result[0]['acceptedTransactions'][0]['verboseData']['transactionId'], 'ef' * 32)

    def test_missing_body_rejected(self):
        data = copy.deepcopy(self.data); data[0]['accepted_bodies'] = []
        with self.assertRaises(Invalid): groups(data, [self.block])

    def test_unaccepted_body_index_rejected(self):
        data = copy.deepcopy(self.data); data[0]['accepted_bodies'][0]['index_within_block'] = 2
        with self.assertRaises(Invalid): groups(data, [self.block])

    def test_wrong_chain_order_rejected(self):
        with self.assertRaises(Invalid): groups(self.data, ['00' * 32])

    def test_duplicate_cannot_replace_missing_body(self):
        data = copy.deepcopy(self.data)
        data[0]['acceptance_data'][0]['accepted_transactions'].append({'index_within_block': 2, 'transaction_id': '12' * 32})
        data[0]['accepted_bodies'].append(copy.deepcopy(data[0]['accepted_bodies'][0]))
        with self.assertRaises(Invalid): groups(data, [self.block])


if __name__ == '__main__': unittest.main()
