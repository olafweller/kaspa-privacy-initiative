#!/usr/bin/env python3
"""Offline package/evidence binding; no VM execution, proving, rental or RPC."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'poc/remote-cuda'))
from lifecycle_package import restore, check, CASES, IMAGE, CONTROL


def main():
    e=Path(__file__).resolve().parent/'evidence'
    identity=json.loads((e/'package-identity.json').read_text())
    with tempfile.TemporaryDirectory() as d:
        policy=restore(Path(d)/'package');check(Path(d)/'package')
    assert policy['cases']==list(CASES) and policy['expectedProgramImage']==IMAGE and policy['expectedJoinControl']==CONTROL
    m=e/'qualification-manifest.json'
    for name,h in json.loads(m.read_text())['files'].items():
        raw=(e/name).read_bytes();assert len(raw)==h['bytes'] and hashlib.sha256(raw).hexdigest()==h['sha256'],name
    print('Fixed public package, four-batch continuity, reviewed binaries and source bindings: OK; no proving.')


if __name__=='__main__':main()
