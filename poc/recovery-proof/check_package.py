#!/usr/bin/env python3
"""Offline fixed public package and preparation evidence. Never prove or rent."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'poc/remote-cuda'))
from recovery_package import restore, check, BINS, CASES, IMAGE, CONTROL

def main():
    e = Path(__file__).resolve().parent/'evidence'
    bindings = json.loads((e.parent/'runmanifest.json').read_text())['trustedBClientFiles']
    for name, digest in bindings.items():
        assert hashlib.sha256((ROOT/'poc/remote-cuda'/name).read_bytes()).hexdigest() == digest, name
    with tempfile.TemporaryDirectory(prefix='kpi-recovery-package-') as d:
        package = Path(d)/'package'
        policy = restore(package)
        assert policy['cases'] == list(CASES)
        assert policy['expectedProgramImage'] == IMAGE and policy['expectedJoinControl'] == CONTROL
        for case in CASES:
            subprocess.run([str(package/'bin'/BINS[0]),'check-target',case,str(package/'inputs')],check=True,timeout=30)
        result = subprocess.run([str(package/'bin'/BINS[1]),'check-native-context'],check=True,capture_output=True,text=True,timeout=30)
        native = json.loads(result.stdout)
        assert not native['runtimeCorpusFilesNeeded'] and len(native['rows']) == 2
        check(package)
    manifest = e/'qualification-manifest.json'
    for name, h in json.loads(manifest.read_text())['files'].items():
        raw = (e/name).read_bytes()
        assert len(raw) == h['bytes'] and hashlib.sha256(raw).hexdigest() == h['sha256'], name
    print('Six frozen targets, 16/20 segment profiles, exact journal continuity and embedded public native contexts verified. No outer proof or permission issuance proof was produced.')

if __name__ == '__main__': main()
