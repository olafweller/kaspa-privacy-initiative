#!/usr/bin/env python3
"""Authenticated, single fixed workload behind RunPod's HTTPS proxy."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time

from common import atomic, lease_check
import worker


class Job:
    def __init__(self, package, volume, lease, token, execute=worker.execute,
                 scope="FIXED_FIVE_PARTIAL_PROOFS_ONLY"):
        assert len(token) >= 32
        self.package, self.volume, self.lease, self.token = package, volume, lease, token
        self.execute = execute
        self.digest = lease_check(lease)
        self.lock = threading.RLock()
        self.guard_seen = 0
        self.volume.mkdir(parents=True, exist_ok=True)
        self.output = volume/'gpu-attempt'
        state = volume/'state.json'
        if state.exists():
            self.state = json.loads(state.read_text())
            if self.state['state'] in ('starting', 'running'):
                self.state.update(state='interrupted', phase='service-restarted-no-retry')
                if self.output.exists():
                    self.state['artifact'] = worker.snapshot(self.output)
                atomic(state, self.state)
        else:
            self.state = {'state': 'idle', 'scope': scope}

    def update(self, value):
        with self.lock:
            self.state.update(value)
            atomic(self.volume/'state.json', self.state)

    def guard(self, value):
        assert value == {'leaseDigest': self.digest, 'podId': self.lease['podId'],
                         'stopUnix': self.lease['stopUnix']}
        assert time.time() < self.lease['stopUnix']
        with self.lock:
            self.guard_seen = time.monotonic()
        return {'armed': True, 'leaseDigest': self.digest, 'stopUnix': self.lease['stopUnix']}

    def status(self):
        with self.lock:
            return self.state | {'podId': self.lease['podId'], 'leaseDigest': self.digest,
                'stopUnix': self.lease['stopUnix'],
                'guardHeartbeatFresh': self.guard_seen > 0 and time.monotonic()-self.guard_seen < 90}

    def start(self):
        with self.lock:
            assert self.status()['guardHeartbeatFresh'], 'external watchdog must be armed'
            assert time.time()+3660 < self.lease['stopUnix'], 'reserve a full diagnostic hour plus retrieval time'
            marker = self.volume/'attempt-once.json'
            if marker.exists():
                return {'jobId': 'gpu-attempt', 'alreadyStarted': True}
            with marker.open('x') as output:
                json.dump({'unixSeconds': time.time(), 'leaseDigest': self.digest}, output)
            self.update({'state': 'starting', 'phase': 'hardware-preflight'})
            threading.Thread(target=self.run, daemon=True).start()
            return {'jobId': 'gpu-attempt', 'alreadyStarted': False}

    def run(self):
        try:
            self.execute(self.package, self.output, self.lease, self.update)
        except Exception as error:
            result = {'state': 'failed', 'failure': type(error).__name__,
                      'failureDetail': str(error)[:256]}
            if self.output.exists():
                try:
                    result['artifact'] = worker.snapshot(self.output)
                except Exception:
                    result['artifactPreservedOnVolumeOnly'] = True
            self.update(result)


class App:
    """Boot without a quote; accept exactly one authenticated, Pod-bound lease."""
    def __init__(self, package, volume, pod_id, token, execute=worker.execute,
                 scope="FIXED_FIVE_PARTIAL_PROOFS_ONLY"):
        assert token.isascii() and len(token) >= 32
        self.package, self.volume, self.pod_id, self.token = package, volume, pod_id, token
        self.output = volume/'gpu-attempt'
        self.lock = threading.RLock()
        self.job = None
        self.execute, self.scope = execute, scope
        volume.mkdir(parents=True, exist_ok=True)
        if (volume/'lease.json').exists():
            self.configure(json.loads((volume/'lease.json').read_text()))

    def configure(self, value):
        lease_check(value)
        assert value['podId'] == self.pod_id
        assert value['createdUnix'] <= time.time()+60, 'creation time is in the future'
        with self.lock:
            if self.job:
                assert self.job.lease == value
            else:
                file = self.volume/'lease.json'
                if file.exists():
                    assert json.loads(file.read_text()) == value
                else:
                    atomic(file, value)
                self.job = Job(self.package, self.volume, value, self.token, self.execute, self.scope)
        return {'configured': True, 'leaseDigest': self.job.digest}

    def status(self):
        return self.job.status() if self.job else {'state': 'unconfigured', 'podId': self.pod_id}

    def guard(self, value):
        assert self.job is not None
        return self.job.guard(value)

    def start(self):
        assert self.job is not None
        return self.job.start()


def handler(job):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            pass  # Never log credentials, bodies or arbitrary URL strings.

        def reply(self, code, value):
            data = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            value = self.headers.get('Authorization', '')
            return value.isascii() and hmac.compare_digest(value, 'Bearer '+job.token)

        def do_GET(self):
            self.close_connection = True
            if not self.authorized():
                return self.reply(401, {'error': 'unauthorized'})
            if self.path == '/v1/status':
                return self.reply(200, job.status())
            if self.path == '/v1/artifacts':
                archive = job.output/'artifacts.tar.gz'
                if not archive.exists():
                    return self.reply(409, {'error': 'no completed checkpoint archive'})
                data = archive.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'application/gzip')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                return self.wfile.write(data)
            self.reply(404, {'error': 'unknown fixed route'})

        def do_POST(self):
            self.close_connection = True
            if not self.authorized():
                return self.reply(401, {'error': 'unauthorized'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                assert 0 <= length <= 4096
                assert self.headers.get('Transfer-Encoding') is None
                value = json.loads(self.rfile.read(length) or b'{}')
                if self.path == '/v1/configure':
                    assert isinstance(job, App)
                    return self.reply(200, job.configure(value))
                if self.path == '/v1/guard':
                    return self.reply(200, job.guard(value))
                if self.path == '/v1/start':
                    assert value == {}, 'workload cannot be selected by client'
                    return self.reply(202, job.start())
                self.reply(404, {'error': 'unknown fixed route'})
            except (AssertionError, ValueError, KeyError, TypeError):
                self.reply(409, {'error': 'invalid request, lease or guard state'})
    return Handler


if __name__ == '__main__':
    assert 'RISC0_DEV_MODE' not in os.environ
    volume = Path('/workspace/kpi')
    job = App(Path('/opt/kpi/package'), volume, os.environ['RUNPOD_POD_ID'], os.environ['KPI_GPU_TOKEN'])
    ThreadingHTTPServer(('0.0.0.0', 8080), handler(job)).serve_forever()
