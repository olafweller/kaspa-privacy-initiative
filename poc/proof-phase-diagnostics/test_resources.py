"""Check that timeouts kill descendants and failures stay failures, without proving."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

spec = importlib.util.spec_from_file_location('phase_runner', Path(__file__).with_name('run.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class Resources(unittest.TestCase):
    def setUp(self):
        self.previous_cpus = runner.CPUS
        runner.CPUS = set(sorted(os.sched_getaffinity(0))[:4])
        # GitHub hosts may expose a different cgroup hierarchy. Exercise the
        # real process groups, /proc sampling and hard limits while providing
        # deterministic auxiliary environment counters for these unit tests.
        self.previous_cgroup = runner.CGROUP
        self.cgroup_directory = tempfile.TemporaryDirectory()
        runner.CGROUP = Path(self.cgroup_directory.name)
        (runner.CGROUP / 'memory.events').write_text('max 0\noom 0\noom_kill 0\n')
        (runner.CGROUP / 'cpu.stat').write_text('usage_usec 0\nuser_usec 0\nsystem_usec 0\n')

    def tearDown(self):
        runner.CPUS = self.previous_cpus
        runner.CGROUP = self.previous_cgroup
        self.cgroup_directory.cleanup()

    def test_nonzero_exit_not_a_success(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / 'nonzero'
            result = runner.phase([sys.executable, '-c', 'raise SystemExit(17)'],
                                  10, prefix, time.monotonic()+10)
            self.assertEqual(result['exitCode'], 17)
            self.assertIsNone(result['limitExceeded'])
            self.assertEqual(set(result['cgroupDelta']), set(result['cgroupBefore']))
            self.assertTrue(prefix.with_suffix('.resources.json').is_file())

    def test_aggregate_timeout_kills_ipc_descendant(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / 'kill'
            pidfile = Path(directory) / 'grandchild.pid'
            code = ('import subprocess,time; from pathlib import Path; '
                    'child=subprocess.Popen(["sleep","60"]); '
                    f'Path({str(pidfile)!r}).write_text(str(child.pid)); time.sleep(60)')
            result = runner.phase([sys.executable, '-c', code],
                                  10, prefix, time.monotonic()+1)
            self.assertEqual(result['limitExceeded'], 'aggregate-wall-time')
            self.assertNotEqual(result['exitCode'], 0)
            self.assertLess(result['seconds'], 5)
            pid = int(pidfile.read_text())
            for _ in range(10):
                path = Path(f'/proc/{pid}/stat')
                if not path.exists() or path.read_text().rsplit(')', 1)[1].split()[0] == 'Z':
                    break
                time.sleep(0.1)
            else:
                self.fail('IPC descendant remains active after timeout')


if __name__ == '__main__':
    unittest.main()
