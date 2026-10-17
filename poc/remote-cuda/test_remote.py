"""CPU-only control tests. Simulated jobs are never CUDA/proving evidence."""
from http.client import HTTPConnection
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from common import lease_check
from package import checked_archive
from service import App, Job, handler, ThreadingHTTPServer
from watchdog import Guard
import worker

TOKEN = 'unit-test-token-not-a-credential-000000000'


def lease():
    now = time.time()
    return {'podId': 'unittest123', 'createdUnix': now, 'stopUnix': now+7200,
            'gpuCount': 1, 'gpuType': 'NVIDIA L40S', 'actualGpuHourlyUsd': '1.09',
            'actualStorageHourlyUsd': '0.014',
            'stoppedStorageHourlyUsd': '0.0028', 'retentionHours': 24,
            'serviceUrl': 'https://unittest123-8080.proxy.runpod.net'}


class Remote(unittest.TestCase):
    def test_bootstrap_binds_one_lease_to_the_actual_pod(self):
        with tempfile.TemporaryDirectory() as directory:
            rental = lease()
            root = Path(directory)
            app = App(root, root/'volume', rental['podId'], TOKEN)
            self.assertEqual(app.status()['state'], 'unconfigured')
            with self.assertRaises(AssertionError):
                app.start()
            wrong = rental | {'podId': 'different123',
                'serviceUrl': 'https://different123-8080.proxy.runpod.net'}
            with self.assertRaises(AssertionError):
                app.configure(wrong)
            self.assertTrue(app.configure(rental)['configured'])
            self.assertTrue(app.configure(rental)['configured'])
            with self.assertRaises(AssertionError):
                app.configure(rental | {'stopUnix': rental['stopUnix']-1})
            restarted = App(root, app.volume, rental['podId'], TOKEN)
            self.assertEqual(restarted.status()['leaseDigest'], lease_check(rental))

    def test_cost_duration_and_host_are_checked(self):
        base = lease()
        lease_check(base)
        for key, value in [('actualGpuHourlyUsd', '10'), ('actualGpuHourlyUsd', 'nan'),
                           ('stopUnix', base['createdUnix']+7201),
                           ('serviceUrl', 'https://elsewhere.example'), ('gpuCount', 2)]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                lease_check(base | {key: value})

    def test_archive_traversal_and_duplicate_names_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'unsafe.tar.gz'
            for names in [['../escape'], ['same', 'same']]:
                with tarfile.open(path, 'w:gz') as archive:
                    for name in names:
                        info = tarfile.TarInfo(name)
                        info.size = 1
                        archive.addfile(info, io.BytesIO(b'x'))
                with self.assertRaises(AssertionError):
                    checked_archive(path)

    def test_http_auth_guard_single_start_and_disconnection(self):
        with tempfile.TemporaryDirectory() as directory:
            started, finish = threading.Event(), threading.Event()
            calls = []
            def simulated(package, out, rental, update):
                calls.append(1)
                started.set()
                finish.wait(5)
                update({'state': 'completed', 'simulationOnly': True})
            job = Job(Path(directory), Path(directory)/'volume', lease(), TOKEN, simulated)
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler(job))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def http(method, path, body=None, auth=TOKEN):
                conn = HTTPConnection(*server.server_address, timeout=2)
                conn.request(method, path, json.dumps(body) if body is not None else None,
                             {'Authorization': 'Bearer '+auth, 'Content-Type': 'application/json'})
                reply = conn.getresponse()
                status, data = reply.status, json.loads(reply.read())
                conn.close()  # Disappearing control client does not stop the job.
                return status, data
            try:
                self.assertEqual(http('GET', '/v1/status', auth='wrong')[0], 401)
                self.assertEqual(http('POST', '/v1/start', {})[0], 409)
                guard = {'leaseDigest': job.digest, 'podId': job.lease['podId'],
                         'stopUnix': job.lease['stopUnix']}
                self.assertEqual(http('POST', '/v1/guard', guard)[0], 200)
                self.assertEqual(http('POST', '/v1/start', {'command': 'anything'})[0], 409)
                self.assertEqual(http('POST', '/v1/start', {})[0], 202)
                self.assertTrue(started.wait(2))
                self.assertTrue(http('POST', '/v1/start', {})[1]['alreadyStarted'])
                self.assertEqual(len(calls), 1)
                finish.set()
                for _ in range(50):
                    if job.status()['state'] == 'completed': break
                    time.sleep(0.02)
                restarted = Job(Path(directory), job.volume, job.lease, TOKEN, simulated)
                restarted.guard(guard)
                self.assertTrue(restarted.start()['alreadyStarted'])
                self.assertEqual(len(calls), 1)
            finally:
                finish.set()
                server.shutdown()
                server.server_close()

    def test_restart_marks_interrupted_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            volume = Path(directory)
            (volume/'state.json').write_text(json.dumps({'state': 'running'}))
            (volume/'attempt-once.json').write_text('{}')
            job = Job(volume, volume, lease(), TOKEN)
            self.assertEqual(job.status()['state'], 'interrupted')

    def test_external_watchdog_stops_after_controller_is_gone(self):
        with tempfile.TemporaryDirectory() as directory:
            rental = lease()
            now = [rental['createdUnix']]
            calls = []
            stopped = [False]
            def provider(url, token, method='GET', value=None):
                calls.append((url, method))
                if url.endswith('/stop'):
                    stopped[0] = True
                    return {}
                if url.endswith('/v1/guard'):
                    return {'armed': True, 'leaseDigest': lease_check(rental), 'stopUnix': rental['stopUnix']}
                if url.endswith('/v1/configure'):
                    return {'configured': True, 'leaseDigest': lease_check(rental)}
                if url.endswith('/v1/status'):
                    return {'state': 'running', 'leaseDigest': lease_check(rental)}
                return {'id': rental['podId'], 'createdAt': rental['createdUnix'],
                    'gpuCount': 1, 'gpuTypeId': 'NVIDIA L40S', 'costPerHr': 1.09,
                    'volumeInGb': 10, 'memoryInGb': 32, 'vcpuCount': 4,
                    'desiredStatus': 'EXITED' if stopped[0] else 'RUNNING'}
            guard = Guard(rental, Path(directory), 'provider-test-only', TOKEN,
                          json_call=provider, now=lambda: now[0])
            self.assertFalse(guard.step())
            now[0] = rental['stopUnix']-60
            self.assertTrue(guard.step())
            self.assertTrue(any(url.endswith('/stop') and method == 'POST' for url, method in calls))
            self.assertTrue(json.loads((Path(directory)/'stop.json').read_text())['providerDesiredExitedConfirmed'])

    def test_stop_ack_without_exited_readback_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            rental = lease()
            def provider(url, token, method='GET', value=None):
                return {'id': rental['podId'], 'createdAt': rental['createdUnix'], 'desiredStatus': 'RUNNING'}
            guard = Guard(rental, Path(directory), 'test-only', TOKEN,
                          json_call=provider, now=lambda: rental['stopUnix'])
            self.assertFalse(guard.step())

    def test_timeout_kills_real_descendant_and_strips_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pidfile = root/'pid'
            code = ('import os,subprocess,time; from pathlib import Path; '
                    'assert "KPI_GPU_TOKEN" not in os.environ and "RUNPOD_API_KEY" not in os.environ; '
                    'p=subprocess.Popen(["sleep","60"]); '
                    f'Path({str(pidfile)!r}).write_text(str(p.pid)); time.sleep(60)')
            with patch.dict(os.environ, {'RISC0_SERVER_PATH': sys.executable,
                                         'KPI_GPU_TOKEN': TOKEN, 'RUNPOD_API_KEY': 'test-only'}), \
                    patch.object(worker, 'CPU_COUNT', min(4, len(os.sched_getaffinity(0)))):
                report = worker.run_phase([sys.executable, '-c', code], 1,
                            root/'timeout', time.monotonic()+10, False, '')
            self.assertEqual(report['failure'], 'phase-wall-time')
            self.assertNotEqual(report['exitCode'], 0)
            pid = int(pidfile.read_text())
            for _ in range(10):
                path = Path(f'/proc/{pid}/stat')
                if not path.exists() or path.read_text().rsplit(')', 1)[1].split()[0] == 'Z': break
                time.sleep(0.1)
            else: self.fail('Descendant remains running')


if __name__ == '__main__':
    unittest.main()
