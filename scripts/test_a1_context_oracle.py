import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location("oracle", Path(__file__).with_name("a1_context_oracle.py"))
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


class OracleTests(unittest.TestCase):
    def context(self, outputs):
        base = bytearray(b"KPI-A1/TN10/finite/v1\0" + bytes(154))
        self.assertEqual(len(base), 176)
        base.append(outputs)
        for i in range(outputs):
            spk = b"\0\0\x20" + bytes([0x40 + i]) * 32 + b"\xac"
            base.extend(struct.pack("<QI", 10 + i, len(spk)) + spk + b"\0")
        return bytes(base)

    def test_exact_field_coverage_and_output_order(self):
        for count, expected in [(1, 19), (2, 25)]:
            context = self.context(count)
            mutations = dict(oracle.mutations(context))
            self.assertEqual(len(mutations), expected)
            self.assertEqual(len(mutations), len(set(mutations)))
            for key in oracle.AMOUNTS:
                self.assertIn(key, mutations)
            for name, changed in mutations.items():
                self.assertNotEqual(changed, context)
                self.assertEqual(len(changed), len(context))
                if name != "output_order":
                    self.assertEqual(sum(a != b for a, b in zip(changed, context)), 1)
            self.assertEqual("output_order" in mutations, count == 2)

    def test_original_structure_rejects_truncation_and_bad_metadata(self):
        context = self.context(1)
        for bad in [context[:-1], context + b"\0", context[:-1] + b"\x01"]:
            with self.assertRaises(ValueError):
                oracle.records(bad)

    def test_tag_uses_raw_outpoint_and_little_endian_index(self):
        # Independent Node crypto SHA256 over manually concatenated literal hex.
        self.assertEqual(oracle.tag(b"abc", bytes(32), bytes(range(32)), 0x04030201),
                         "e1f7cd0734d51ac8c476c1325b8f9cc33b03a4079581c7bdb0504e6fe86a20c1")


if __name__ == "__main__":
    unittest.main()
