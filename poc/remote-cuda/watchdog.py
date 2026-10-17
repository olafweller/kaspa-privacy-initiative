#!/usr/bin/env python3
"""Run on an independent durable CPU host, never in the controlling Codex task."""
import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

from common import atomic, json_request, lease_check, request, sha


def archive_matches(path, digest, size):
    try:
        with path.open('rb') as source:
            return os.fstat(source.fileno()).st_size == size and sha(source.read()) == digest
    except FileNotFoundError:
        return False


def save_archive(directory, data):
    """Publish a checked durable copy; a hash-shaped filename is not evidence."""
    digest, size = sha(data), len(data)
    path = directory/(digest+'.tar.gz')
    repaired = not archive_matches(path, digest, size)
    if repaired:
        # Discard completion records left by an interrupted older guard before
        # attempting repair. A failed repair must not leave a false completion.
        for name in ('latest-artifact.json', 'terminal-backup.json'):
            record = directory/name
            try:
                previous = json.loads(record.read_text())
            except FileNotFoundError:
                continue
            except (ValueError, TypeError):
                previous = {'sha256': digest}
            if not isinstance(previous, dict) or previous.get('sha256') == digest:
                record.unlink()
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, prefix='.archive-', delete=False) as target:
                temporary = Path(target.name)
                target.write(data)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    # Also sync a reused copy: a previous process may have died after rename
    # but before syncing the directory. Confirm the actual saved bytes first.
    with path.open('rb') as source:
        assert os.fstat(source.fileno()).st_size == size and sha(source.read()) == digest, 'saved archive mismatch'
        os.fsync(source.fileno())
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return repaired


class Guard:
    def __init__(self, lease, directory, provider_key, service_key,
                 json_call=json_request, bytes_call=request, now=time.time):
        self.lease, self.directory = lease, directory
        self.digest = lease_check(lease)
        self.provider_key, self.service_key = provider_key, service_key
        self.json_call, self.bytes_call, self.now = json_call, bytes_call, now
        assert provider_key and len(service_key) >= 32
        directory.mkdir(parents=True, exist_ok=True)
        self.base = 'https://rest.runpod.io/v1/pods/'+lease['podId']

    def stop(self):
        before = self.json_call(self.base, self.provider_key)
        assert before['id'] == self.lease['podId']
        raw = before['createdAt']
        created = (datetime.datetime.fromisoformat(raw.replace('Z', '+00:00')).timestamp()
                   if isinstance(raw, str) else float(raw))
        assert abs(created-self.lease['createdUnix']) <= 1, 'refuse to stop a different lease'
        if before.get('desiredStatus') == 'EXITED':
            pod = before  # A previous request/operator may already have stopped it.
        else:
            self.json_call(self.base+'/stop', self.provider_key, 'POST')
            pod = self.json_call(self.base, self.provider_key)
        confirmed = pod.get('id') == self.lease['podId'] and pod.get('desiredStatus') == 'EXITED'
        atomic(self.directory/'stop.json', {'requestedUnix': self.now(),
            'providerDesiredExitedConfirmed': confirmed, 'podId': self.lease['podId'],
            'note': 'Compute stop is separate from volume cleanup and actual billing reconciliation.'})
        return confirmed

    def step(self):
        # Stop proactively one minute before the absolute rental deadline.
        if self.now() >= self.lease['stopUnix']-60:
            return self.stop()
        pod = self.json_call(self.base, self.provider_key)
        assert pod['id'] == self.lease['podId']
        if pod.get('desiredStatus') == 'EXITED':
            atomic(self.directory/'stop.json', {'observedUnix': self.now(),
                'providerDesiredExitedConfirmed': True, 'podId': self.lease['podId'],
                'note': 'Already stopped; volume cleanup and billing remain separate.'})
            return True
        raw_created = pod['createdAt']
        created = (datetime.datetime.fromisoformat(raw_created.replace('Z', '+00:00')).timestamp()
                   if isinstance(raw_created, str) else float(raw_created))
        if (abs(created-self.lease['createdUnix']) > 1 or pod['gpuCount'] != 1 or
                float(pod['costPerHr']) > float(self.lease['actualGpuHourlyUsd']) or
                pod.get('gpuTypeId') != 'NVIDIA L40S' or pod.get('volumeInGb', 0) < 10 or
                pod.get('volumeMountPath') != '/workspace' or
                pod.get('memoryInGb', 0) < 32 or pod.get('vcpuCount', 0) < 4):
            return self.stop()  # Declared quote/resources no longer fit; do not arm work.
        url = self.lease['serviceUrl']
        configured = self.json_call(url+'/v1/configure', self.service_key, 'POST', self.lease)
        assert configured['configured'] and configured['leaseDigest'] == self.digest
        ack = self.json_call(url+'/v1/guard', self.service_key, 'POST',
            {'leaseDigest': self.digest, 'podId': self.lease['podId'], 'stopUnix': self.lease['stopUnix']})
        assert ack['armed'] and ack['leaseDigest'] == self.digest and ack['stopUnix'] == self.lease['stopUnix']
        status = self.json_call(url+'/v1/status', self.service_key)
        assert status['leaseDigest'] == self.digest
        atomic(self.directory/'guard.json', {'heartbeatUnix': self.now(), 'leaseDigest': self.digest,
                                             'stopUnix': self.lease['stopUnix'], 'workerState': status['state']})
        if status['state'] in ('failed', 'interrupted') and not status.get('artifact'):
            atomic(self.directory/'terminal-without-download.json', status)
            return self.stop()  # Preserve volume; do not burn GPU time on retrieval failure.
        if status.get('artifact'):
            data = self.bytes_call(url+'/v1/artifacts', self.service_key)
            if sha(data) == status['artifact']['sha256'] and len(data) == status['artifact']['bytes']:
                repaired = save_archive(self.directory, data)
                atomic(self.directory/'latest-artifact.json', {'sha256': sha(data), 'bytes': len(data),
                       'cpuVerified': False, 'note': 'Transport hash checked; independent CPU comparison still required.'})
                if status['state'] in ('completed', 'failed', 'interrupted'):
                    terminal = self.directory/'terminal-backup.json'
                    try:
                        previous = json.loads(terminal.read_text())
                    except (FileNotFoundError, ValueError):
                        previous = {}
                    if (repaired or not isinstance(previous, dict) or previous.get('sha256') != sha(data) or
                            previous.get('bytes') != len(data) or previous.get('leaseDigest') != self.digest):
                        atomic(terminal, {'sha256': sha(data), 'bytes': len(data),
                            'leaseDigest': self.digest, 'savedUnix': self.now()})
                    # A short bounded grace lets Codex fetch through the Pod
                    # proxy; the external copy also survives a lost controller.
                    if self.now()-json.loads(terminal.read_text())['savedUnix'] >= 60:
                        return self.stop()
        return False


def serve(guard, poll_seconds=10):
    stopped = threading.Event()
    def remember(error):
        try:
            atomic(guard.directory/'last-error.json', {'unixSeconds': time.time(),
                'errorType': type(error).__name__, 'stopUnix': guard.lease['stopUnix']})
        except OSError:
            pass  # A full backup disk must not disable provider-stop retries.
    def deadline_stop():
        # Independent of an in-flight GPU status request or artifact download.
        while not stopped.is_set():
            try:
                if guard.stop():
                    stopped.set()
                    return
            except Exception as error:
                remember(error)
            stopped.wait(poll_seconds)
    timer = threading.Timer(max(0, guard.lease['stopUnix']-60-time.time()), deadline_stop)
    timer.daemon = True
    timer.start()
    try:
        while not stopped.is_set():
            try:
                if guard.step():
                    stopped.set()
                    break
            except Exception as error:
                remember(error)
            stopped.wait(poll_seconds)
    finally:
        stopped.set()
        timer.cancel()


if __name__ == '__main__':
    lease = json.loads(Path(sys.argv[1]).read_text())
    guard = Guard(lease, Path(sys.argv[2]), os.environ['RUNPOD_API_KEY'], os.environ['KPI_GPU_TOKEN'])
    serve(guard)
