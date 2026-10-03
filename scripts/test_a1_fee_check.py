import copy
from decimal import Decimal
from fractions import Fraction
import unittest

import a1_fee_check as f
import a1_check as c


class FeeRules(unittest.TestCase):
    def test_rational_ceiling_and_no_binary_float(self):
        self.assertEqual(f.ceiling(Fraction(5, 4) * Fraction(Decimal('100.01')) * 173073), 21636289)
        self.assertEqual((11 * max(30000000, 60000000) + 9) // 10, 66000000)

    def test_expired_quote_rejects_before_any_artifact_change(self):
        manifest = {'pins': {'rusty_kaspa_commit': 'pin'}}
        quote = {'network': 'testnet-10', 'pins': {'rusty_kaspa_commit': 'pin'},
                 'observations': [{'status': 'observed', 'dag': {'network': 'testnet-10'},
                  'info': {'isSynced': True, 'serverVersion': '2.1.0'},
                  'observed_at_utc': '2026-10-03T00:00:00Z'}]}
        original = copy.deepcopy(manifest)
        with self.assertRaises(c.Invalid): f.qualify(manifest, {}, {}, quote, 1791072000)
        self.assertEqual(manifest, original)


if __name__ == '__main__': unittest.main()
