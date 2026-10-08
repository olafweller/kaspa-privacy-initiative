#!/usr/bin/env python3
"""Published 2026-10-08 trial templates: complete, placeholder-only, reproducible."""
import contextlib
import hashlib
import io
import json
import pathlib
import re
import tempfile
import unittest

import a1_trial_source as t

SOURCE = t.DEFAULT_SOURCE


class TrialSourceTemplates(unittest.TestCase):
    def setUp(self):
        self.manifest = t.load(SOURCE)

    def test_manifest_lists_every_template(self):
        self.assertEqual(len(self.manifest['files']), 113)
        for role in ('A/', 'B/', 'C/', 'witness/'):
            self.assertTrue(any(k.startswith(role) for k in self.manifest['files']), role)

    def test_templates_contain_no_machine_local_values(self):
        local = re.compile(r'/home/|\b(?!127\.0\.0\.1\b|0\.0\.0\.0\b)\d{1,3}(\.\d{1,3}){3}\b')
        for rel, entry in self.manifest['files'].items():
            text = (SOURCE / rel).read_text('utf-8')
            self.assertIsNone(local.search(text), rel)
            used = sorted(p for p in self.manifest['placeholders'] if p in text)
            self.assertEqual(used, entry['placeholders'], rel)

    def test_unchanged_templates_hash_to_deployed_bytes(self):
        for rel, entry in self.manifest['files'].items():
            if not entry['placeholders']:
                raw = (SOURCE / rel).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['deployed_sha256'], rel)

    def test_C_sources_match_the_submit_claim_in_the_public_record(self):
        record = json.loads((SOURCE.parent / 'public-record.json').read_bytes())
        pins = {rel.rsplit('/', 1)[1]: entry['deployed_sha256']
                for rel, entry in self.manifest['files'].items()
                if rel.startswith('C/software/')}
        encoded = json.dumps(pins, sort_keys=True, separators=(',', ':')).encode()
        self.assertEqual(hashlib.sha256(encoded).hexdigest(),
                         record['one_submit_claim']['sources_sha256'])

    def test_wrong_values_are_reported_and_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            values = pathlib.Path(d) / 'values.json'
            values.write_text(json.dumps({p: 'x' for p in self.manifest['placeholders']}))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(t.main(['verify', '--values', str(values)]), 1)
            values.write_text(json.dumps({'@KPI_REPO@': 'x'}))
            with self.assertRaises(SystemExit):
                t.main(['verify', '--values', str(values)])


if __name__ == '__main__':
    unittest.main()
