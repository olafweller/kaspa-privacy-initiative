#!/usr/bin/env python3
"""Read-only provider lookup on the independent guard host; never creates a Pod."""
import datetime
import json
import os
from pathlib import Path
import re
import sys
import time

from common import json_request, lease_check


def create(pod_id, storage_hourly, stopped_hourly, target):
    assert re.fullmatch(r'[A-Za-z0-9]{6,64}', pod_id)
    pod = json_request('https://rest.runpod.io/v1/pods/'+pod_id, os.environ['RUNPOD_API_KEY'])
    assert pod['id'] == pod_id and pod['gpuCount'] == 1 and pod['gpuTypeId'] == 'NVIDIA L40S'
    assert pod['volumeInGb'] >= 10 and pod['memoryInGb'] >= 32 and pod['vcpuCount'] >= 4
    assert pod.get('volumeMountPath') == '/workspace', 'persistent volume mount must match the worker output path'
    created = pod['createdAt']
    created = (datetime.datetime.fromisoformat(created.replace('Z', '+00:00')).timestamp()
               if isinstance(created, str) else float(created))
    lease = {'podId': pod_id, 'gpuCount': 1, 'gpuType': 'NVIDIA L40S',
             'createdUnix': created, 'stopUnix': created+7200,
             'serviceUrl': f'https://{pod_id}-8080.proxy.runpod.net',
             'actualGpuHourlyUsd': str(pod['costPerHr']),
             'actualStorageHourlyUsd': storage_hourly,
             'stoppedStorageHourlyUsd': stopped_hourly, 'retentionHours': 24}
    lease_check(lease)
    assert time.time() < created+7200, 'lease already expired'
    with target.open('x') as output:
        json.dump(lease, output, indent=2)
        output.write('\n')
    print('Lease saved from provider creation time; no resource was created or started.')


if __name__ == '__main__':
    create(sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]))
