"""Focused CPU-only checks for the separate full-classifier package/job."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import full_package
import full_worker
from service import App
from test_remote import lease, TOKEN


class Full(unittest.TestCase):
    def test_archived_qualification_and_fixtures_are_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'package'
            full_package.build(out)
            p = json.loads((out/'full-workload.json').read_text())
            self.assertEqual(p['expectedProgramImage'], full_package.IMAGE)
            self.assertEqual(len(p['inputs']), 116)
            self.assertEqual(p['executionCycleLimit'], 128000000)
            self.assertEqual(p['wholeProofJobSecondsLimit'], 3600)
            # An otherwise complete package with a changed fixture fails before
            # any proof process, GPU call or provider action is reached.
            fixture = out/'inputs/fixtures/valid-invalid-valid.bin'
            fixture.write_bytes(fixture.read_bytes()+b'changed')
            with self.assertRaises(AssertionError):
                full_worker.check_inputs(out, p)

    def test_separate_fixed_job_uses_injected_executor_and_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invoked = []
            def execute(package, output, rental, update):
                invoked.append((package, output, rental))
                update({'state': 'completed'})
            app = App(root/'full-package', root/'full-volume', 'unittest123', TOKEN,
                      execute=execute, scope='FIXED_FULL_CLASSIFIER_ONE_SUCCINCT_RECEIPT')
            rental = lease()
            app.configure(rental)
            self.assertEqual(app.status()['scope'], 'FIXED_FULL_CLASSIFIER_ONE_SUCCINCT_RECEIPT')
            with self.assertRaises(AssertionError):
                app.start()
            app.guard({'leaseDigest': app.job.digest, 'podId': rental['podId'], 'stopUnix': rental['stopUnix']})
            # Run the service thread inline to check durable single-attempt
            # semantics deterministically, without a real GPU/proof.
            with patch('service.threading.Thread') as thread:
                thread.return_value.start.side_effect = app.job.run
                self.assertFalse(app.start()['alreadyStarted'])
                self.assertTrue(app.start()['alreadyStarted'])
            self.assertEqual(len(invoked), 1)
            self.assertEqual(invoked[0][1], root/'full-volume/gpu-attempt')
            self.assertTrue((root/'full-volume/attempt-once.json').is_file())
            self.assertFalse((root/'state.json').exists())


if __name__ == '__main__':
    unittest.main()
