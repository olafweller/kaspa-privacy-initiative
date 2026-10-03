import copy
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
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

    def test_storage_dominant_overall_mass_not_relay_mass_sets_headroom(self):
        overall, relay_mass, relay_floor, required = f.fee_requirements(
            {'compute': 100, 'storage': 400000, 'transient': 201}, Fraction(100))
        self.assertEqual((overall, relay_mass, relay_floor, required), (400000, 101, 10100, 50000000))
        self.assertGreater(required, 30000000)
        for invalid in ({'compute': True, 'storage': 0, 'transient': 0},
                        {'compute': -1, 'storage': 0, 'transient': 0}):
            with self.assertRaises(c.Invalid): f.fee_requirements(invalid, Fraction(100))

    def test_native_relay_zero_fallback_and_max_sompi_cap_are_separate(self):
        self.assertEqual(f.fee_requirements({'compute': 0, 'storage': 0, 'transient': 0}, Fraction(100)),
                         (0, 0, 100000, 100000))
        self.assertEqual(f.fee_requirements({'compute': c.MAX_SOMPI, 'storage': 0, 'transient': 0}, Fraction(100))[2],
                         c.MAX_SOMPI)

    def test_complete_qualifier_rejects_storage_dominant_policy_fixture(self):
        evidence = Path(__file__).resolve().parents[1] / 'poc/a1/evidence'
        manifest = c.load_json(evidence / 'fixture-2026-10-03/manifest.json')
        measurement = json.loads((evidence / 'fixture-2026-10-03/report.json').read_text())
        sdk = json.loads((evidence / 'fixture-2026-10-03/sdk-roundtrip.json').read_text())
        quote = f.quote_json(evidence / 'fee-quote-g4.json')
        now = max(datetime.fromisoformat(x['observed_at_utc'].replace('Z', '+00:00')).timestamp()
                  for x in quote['observations']) + 1
        f.qualify(manifest, measurement, sdk, quote, now)  # actual fixture positive control
        original = copy.deepcopy(manifest)
        # Synthetic policy mutation, not claimed as a native-decoded transaction:
        # both mass records agree and fit hard limits, but 30m cannot cover 50m.
        measurement['G4_decoded_measurements']['s0_continue']['meter']['storage_mass'] = 400000
        next(x for x in sdk['branches'] if x['branch'] == 's0_continue')['native_masses']['storage'] = 400000
        with self.assertRaisesRegex(c.Invalid, 'fee headroom fails'):
            f.qualify(manifest, measurement, sdk, quote, now)
        self.assertEqual(manifest, original)


if __name__ == '__main__': unittest.main()
