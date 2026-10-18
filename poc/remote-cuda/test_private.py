"""Fixed-input/tamper/start-boundary checks; no proving or provider calls."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from common import sha
from private_package import restore, INPUTS, SCOPE, IMAGE, CONTROL, BINS
from private_worker import check_inputs, execute
from service import App
from test_remote import lease, TOKEN


class Private(unittest.TestCase):
    def test_restored_package_fixed_bytes_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'package'
            policy = restore(p)
            # check_inputs reads the existing CUDA binary as well. Substitute
            # only the filesystem read in this CPU-only unit, not real proving.
            class Cuda:
                def read_bytes(self):
                    return b'unit-cuda'
            real_path = Path
            with patch.dict(os.environ, {'RISC0_SERVER_PATH': '/unit/cuda'}), \
                 patch('private_worker.Path', side_effect=lambda s: Cuda() if s == '/unit/cuda' else real_path(s)), \
                 patch('private_worker.sha', side_effect=lambda b: policy['cudaProverSha256'] if b == b'unit-cuda' else sha(b)):
                check_inputs(p, policy)
                for key, value in [('expectedProgramImage', '00'*32), ('expectedControlId', '00'*32),
                                   ('executionCycleLimit', 128000000), ('wholeProofJobSecondsLimit', 7200)]:
                    changed = copy.deepcopy(policy)
                    changed[key] = value
                    with self.assertRaises(AssertionError):
                        check_inputs(p, changed)
                changed = copy.deepcopy(policy)
                changed['inputs']['../other'] = changed['inputs']['input.bin']
                with self.assertRaises(AssertionError):
                    check_inputs(p, changed)
                for name in INPUTS:
                    file = p/'inputs'/name
                    old = file.read_bytes()
                    file.write_bytes(old+b'changed')
                    with self.assertRaises(AssertionError):
                        check_inputs(p, policy)
                    file.write_bytes(old)

    def test_compiled_producer_checks_target_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'package'
            restore(p)
            producer = str(p/'bin'/BINS[0])
            result = subprocess.run([producer, 'check-target', str(p/'inputs')], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['image'], IMAGE)
            self.assertEqual(report['control'], CONTROL)
            self.assertFalse(report['proofStarted'])
            file = p/'inputs/input.bin'
            file.write_bytes(file.read_bytes()+b'changed')
            result = subprocess.run([producer, 'check-target', str(p/'inputs')], capture_output=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)

    def test_insufficient_time_stops_before_hardware_or_process(self):
        with patch('private_worker.hardware') as gpu, patch('private_worker.run_phase') as process:
            rental = lease()
            rental['stopUnix'] = 0
            with self.assertRaises(AssertionError):
                execute(Path('/unused'), Path('/unused'), rental, lambda v: None)
            gpu.assert_not_called()
            process.assert_not_called()

    def test_unconfigured_and_unguarded_job_cannot_start(self):
        with tempfile.TemporaryDirectory() as directory:
            app = App(Path('/unused'), Path(directory)/'private', 'unittest123', TOKEN,
                      execute=execute, scope=SCOPE)
            with self.assertRaises(AssertionError):
                app.start()
            app.configure(lease())
            self.assertEqual(app.status()['scope'], SCOPE)
            with self.assertRaises(AssertionError):
                app.start()


if __name__ == '__main__':
    unittest.main()
