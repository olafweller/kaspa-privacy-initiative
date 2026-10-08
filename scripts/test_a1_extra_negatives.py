import json
import unittest
import a1_check as c
from a1_extra_negatives import assert_result


class RejectionLayers(unittest.TestCase):
    def test_stale_id_mass_and_process_errors_cannot_count_as_script_rejection(self):
        for error in ('Error: "decoded transaction ID mismatch"',
                      'Error: "utxo: WrongMass(0, 27)"', 'process crashed',
                      'Error: "isolation: NoTxInputs"'):
            with self.subTest(error=error), self.assertRaisesRegex(c.Invalid, 'wrong rejection layer'):
                assert_result(1, '', error, False, 'redeem-full-SPK')

    def test_acceptance_and_wrong_verifier_failure_are_not_negative_success(self):
        with self.assertRaisesRegex(c.Invalid, 'unexpectedly accepted'):
            assert_result(0, '{}', '', False, 'redeem-full-SPK')
        with self.assertRaisesRegex(c.Invalid, 'wrong rejection layer'):
            assert_result(1, '', 'Error: "utxo: SignatureInvalid(VerifyError)"',
                          False, 'native-verifier-canonical-scalar')

    def test_expected_script_and_positive_layers(self):
        self.assertEqual(assert_result(1, '', 'Error: "utxo: SignatureInvalid(VerifyError)"',
                                       False, 'redeem-full-SPK'), 'native-script-verify')
        self.assertEqual(assert_result(0, json.dumps({'full_valid': True}), '', True, ''),
                         'native-Full-success')
        with self.assertRaises(c.Invalid):
            assert_result(0, '{}', '', True, '')
