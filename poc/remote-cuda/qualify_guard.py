#!/usr/bin/env python3
"""CPU-only guard recovery across real process restarts; provider is simulated."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from common import atomic, lease_check, sha
from watchdog import Guard

DATA = b"public simulated backup; no proof or credential!!!!"
TOKEN = "simulation-only-not-a-credential-000000000"


def stage(root, name):
    lease = json.loads((root/"lease.json").read_text())
    digest = lease_check(lease)
    archive = root/(sha(DATA)+".tar.gz")
    if name == "partial":
        archive.write_bytes(b"cut")
        atomic(root/"terminal-backup.json", {"sha256": sha(DATA), "savedUnix": lease["createdUnix"]-61})
        return
    def provider(url, token, method="GET", value=None):
        if url.endswith("/stop"):
            atomic(root/"simulated-provider-stop.json", {"stopped": True})
            return {}
        if url.endswith("/v1/configure"):
            return {"configured": True, "leaseDigest": digest}
        if url.endswith("/v1/guard"):
            return {"armed": True, "leaseDigest": digest, "stopUnix": lease["stopUnix"]}
        if url.endswith("/v1/status"):
            return {"state": "completed", "leaseDigest": digest,
                    "artifact": {"sha256": sha(DATA), "bytes": len(DATA)}}
        assert url == "https://rest.runpod.io/v1/pods/"+lease["podId"]
        return {"id": lease["podId"], "createdAt": lease["createdUnix"],
                "gpuCount": 1, "gpuTypeId": "NVIDIA L40S", "costPerHr": 1.09,
                "volumeInGb": 10, "volumeMountPath": "/workspace", "memoryInGb": 32, "vcpuCount": 4,
                "desiredStatus": "EXITED" if (root/"simulated-provider-stop.json").exists() else "RUNNING"}
    now = lease["createdUnix"]+(61 if name == "restart" else 0)
    guard = Guard(lease, root, TOKEN, TOKEN, json_call=provider,
                  bytes_call=lambda *args: DATA, now=lambda: now)
    assert guard.step() == (name == "restart")
    assert archive.stat().st_size == len(DATA) and sha(archive.read_bytes()) == sha(DATA)
    assert json.loads((root/"terminal-backup.json").read_text())["savedUnix"] == lease["createdUnix"]
    assert not json.loads((root/"latest-artifact.json").read_text())["cpuVerified"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--stage", choices=("partial", "recover", "restart"))
    args = parser.parse_args()
    if args.stage:
        stage(args.directory, args.stage)
        return
    args.directory.mkdir(parents=True, exist_ok=False)
    now = time.time()
    lease = {"podId": "simulation123", "createdUnix": now, "stopUnix": now+7200,
             "gpuCount": 1, "gpuType": "NVIDIA L40S", "actualGpuHourlyUsd": "1.09",
             "actualStorageHourlyUsd": "0.014", "stoppedStorageHourlyUsd": "0.0028", "retentionHours": 24,
             "serviceUrl": "https://simulation123-8080.proxy.runpod.net"}
    atomic(args.directory/"lease.json", lease)
    for name in ("partial", "recover", "restart"):
        subprocess.run([sys.executable, str(Path(__file__).resolve()), str(args.directory.resolve()),
                        "--stage", name], check=True, timeout=15)
    report = {"scope": "SIMULATED_PROVIDER_REAL_FILESYSTEM_AND_SEPARATE_PROCESS_RESTARTS",
              "host": platform.node(), "python": platform.python_version(),
              "archiveBytes": len(DATA), "archiveSha256": sha(DATA),
              "truncatedCopyRepaired": True, "restartRecheckedCopyAndRetainedGrace": True,
              "simulatedProviderStopConfirmed": True, "liveProviderCalled": False,
              "hostRebooted": False, "gpuUsed": False,
              "sourceSha256": {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                               for name in ("common.py", "watchdog.py", "qualify_guard.py")}}
    atomic(args.directory/"qualification.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
