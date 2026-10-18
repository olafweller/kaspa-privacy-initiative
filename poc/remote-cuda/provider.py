"""RunPod REST schema adapter used only on the independent guard host."""
import datetime
import json
import re
import urllib.request

from common import NoRedirect, json_request


def created_unix(value):
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        except ValueError:
            return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f %z UTC').timestamp()
    return float(value)


def provider_request(url, token, method='GET', value=None):
    if not url.startswith('https://rest.runpod.io/'):
        return json_request(url, token, method, value)
    if method != 'GET':
        assert re.fullmatch(r'https://rest\.runpod\.io/v1/pods/[A-Za-z0-9]{6,64}/stop', url)
        return json_request(url, token, method, value)
    assert re.fullmatch(r'https://rest\.runpod\.io/v1/pods/[A-Za-z0-9]{6,64}', url)
    # REST omits machine details unless explicitly requested. Never infer a GPU
    # type from the template name, image, or owner-supplied lease.
    req = urllib.request.Request(url+'?includeMachine=true', headers={
        'Authorization': 'Bearer '+token, 'User-Agent': 'kpi-remote-cuda/1.0',
        'Accept': 'application/json', 'Content-Type': 'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=10) as reply:
        raw = reply.read(64*1024**2+1)
        assert len(raw) <= 64*1024**2
    pod = json.loads(raw)
    machine_type = (pod.get('machine') or {}).get('gpuTypeId')
    if machine_type is not None:
        assert pod.get('gpuTypeId') in (None, machine_type), 'conflicting provider GPU types'
        pod['gpuTypeId'] = machine_type
    return pod
