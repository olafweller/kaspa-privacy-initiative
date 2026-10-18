"""Small public configuration/transport helpers; credentials are never serialized."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.request
import urllib.parse


def sha(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as temp:
        json.dump(value, temp, indent=2)
        temp.write('\n')
        temp.flush()
        os.fsync(temp.fileno())
    os.replace(temp.name, path)


def lease_check(lease):
    assert lease['gpuCount'] == 1 and lease['gpuType'] == 'NVIDIA L40S'
    assert re.fullmatch(r'[A-Za-z0-9]{6,64}', lease['podId'])
    created, deadline = lease['createdUnix'], lease['stopUnix']
    assert all(isinstance(v, (int, float)) and math.isfinite(v) for v in (created, deadline))
    assert 0 < deadline-created <= 7200
    hourly, disk_hourly = float(lease['actualGpuHourlyUsd']), float(lease['actualStorageHourlyUsd'])
    assert math.isfinite(hourly) and math.isfinite(disk_hourly) and hourly > 0 and disk_hourly >= 0
    stopped = float(lease['stoppedStorageHourlyUsd'])
    retention = float(lease['retentionHours'])
    assert math.isfinite(stopped) and stopped >= 0 and 0 <= retention <= 24
    assert (hourly+disk_hourly)*(deadline-created)/3600 + stopped*retention <= 5
    expected = f'https://{lease["podId"]}-8080.proxy.runpod.net'
    assert lease['serviceUrl'] == expected
    return sha(json.dumps(lease, sort_keys=True, separators=(',', ':')).encode())


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, token, method='GET', value=None, timeout=10):
    parsed = urllib.parse.urlsplit(url)
    assert parsed.scheme == 'https' and not parsed.username and not parsed.password
    assert not parsed.query and not parsed.fragment
    data = None if value is None else json.dumps(value).encode()
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={'Authorization': 'Bearer '+token,
                                          'User-Agent': 'kpi-remote-cuda/1.0',
                                          'Accept': 'application/json',
                                          'Content-Type': 'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as reply:
        data = reply.read(64*1024**2+1)
        assert len(data) <= 64*1024**2
        return data


def json_request(url, token, method='GET', value=None):
    data = request(url, token, method, value)
    return json.loads(data) if data.strip() else {}  # Provider stop may return 204.
