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

    def bound_fixture(self):
        evidence = Path(__file__).resolve().parents[1] / 'poc/a1/evidence'
        binding = f.load_binding(evidence / 'fixture-2026-10-03')
        manifest = copy.deepcopy(binding['manifest'])
        measurement = json.loads((evidence / 'fixture-2026-10-03/report.json').read_text())
        # Pure binding-unit fixture. This does not claim a new SDK/native run.
        sdk = json.loads((evidence / 'fixture-2026-10-03/sdk-roundtrip.json').read_text())
        sdk.update(schema='kpi-a1-sdk-roundtrip/v2', manifest_sha256=binding['manifest_sha256'])
        for receipt in sdk['branches']:
            bound = binding['branches'][receipt['branch']]
            receipt.update(decoded_transaction=copy.deepcopy(bound['request']['transaction']),
                           input_entry=copy.deepcopy(bound['request']['entry']),
                           measurement_sha256=bound['measurement_sha256'],
                           artifacts_sha256=copy.deepcopy(bound['artifacts_sha256']))
        quote = f.quote_json(evidence / 'fee-quote-g4.json')
        now = max(datetime.fromisoformat(x['observed_at_utc'].replace('Z', '+00:00')).timestamp()
                  for x in quote['observations']) + 1
        return manifest, measurement, sdk, quote, now, binding

    def test_exact_bound_fixture_qualifies(self):
        self.assertEqual(f.qualify(*self.bound_fixture())['branches']['s0_continue']['fixed_fee_sompi'], '30000000')

    def test_changed_fee_budget_txid_full_hash_reject(self):
        for field, value, error in [('fee_sompi','1','fee binding'), ('compute_budget',1,'budget binding'),
                                    ('txid','00'*32,'txid binding'), ('full_hash','00'*32,'full hash binding')]:
            args = self.bound_fixture(); args[2]['branches'][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(c.Invalid, error): f.qualify(*args)

    def test_branch_identity_duplicates_and_mixed_records_reject(self):
        for mode in ('duplicate','wrong-branch','mixed'):
            args = self.bound_fixture(); rows=args[2]['branches']
            if mode=='duplicate': rows.append(copy.deepcopy(rows[0]))
            elif mode=='wrong-branch': rows[0]['branch']='s2_terminal'
            else: rows[0]['decoded_transaction']=copy.deepcopy(rows[1]['decoded_transaction'])
            with self.subTest(mode=mode), self.assertRaises(c.Invalid): f.qualify(*args)

    def test_manifest_artifact_and_measurement_hashes_reject(self):
        for field in ('manifest','artifact','measurement','body','entry','storage'):
            args=self.bound_fixture(); receipt=args[2]['branches'][0]
            if field=='manifest':args[2]['manifest_sha256']='00'*32
            elif field=='artifact':receipt['artifacts_sha256']['s0.redeem']='00'*32
            elif field=='measurement':receipt['measurement_sha256']='00'*32
            elif field=='body':receipt['decoded_transaction']['outputs'][0]['value']='1'
            elif field=='entry':receipt['input_entry']['amount']=1
            else:receipt['committed_storage_mass']='1'
            with self.subTest(field=field), self.assertRaises(c.Invalid): f.qualify(*args)

    def test_stale_measurement_and_coordinated_mass_mutations_reject(self):
        for field in ('txid','fee_sompi','compute_budget','meter'):
            args=self.bound_fixture();measurement=args[1]['G4_decoded_measurements']['s0_continue']
            if field=='meter':
                measurement['meter']['storage_mass']=400000
                next(x for x in args[2]['branches'] if x['branch']=='s0_continue')['native_masses']['storage']=400000
            else:measurement[field]='00'*32 if field=='txid' else 1
            with self.subTest(field=field), self.assertRaisesRegex(c.Invalid,'different transaction measurement'):
                f.qualify(*args)

    def test_changed_manifest_terms_and_unbound_legacy_receipt_reject(self):
        args=self.bound_fixture();args[0]['branches']['s0_continue']['fee']='1'
        with self.assertRaisesRegex(c.Invalid,'manifest binding'):f.qualify(*args)
        args=self.bound_fixture();args[2]['schema']='kpi-a1-sdk-roundtrip/v1'
        with self.assertRaisesRegex(c.Invalid,'SDK manifest'):f.qualify(*args)


if __name__ == '__main__': unittest.main()
