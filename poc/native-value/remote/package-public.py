#!/usr/bin/env python3
"""Package public trial files only, preserving raw JSON bytes under gzip.

Wallet keys live outside the trial. No general /opt archive or secret reads.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path('/opt/kpi-pr31-cloud-20261017/native-value')
p = argparse.ArgumentParser()
p.add_argument('trial')
p.add_argument('output')
a = p.parse_args()
trial = Path(a.trial).resolve()
output = Path(a.output).resolve()
assert trial.parent == ROOT and trial.name.startswith('trial-')
assert output.parent == ROOT and not output.exists()
output.mkdir(mode=0o700)
manifest = {}
public_files = sorted(f for f in trial.rglob('*') if f.is_file())
assert not any(f.is_symlink() or f.suffix == '.key' for f in public_files)
with tarfile.open(output / 'public-trial.tar.gz', 'w:gz') as archive:
    for file in public_files:
        name = str(file.relative_to(trial))
        raw = file.read_bytes()
        manifest[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        if (name.endswith('-capture.json') or name.endswith('-rpc.json')):
            packed = output / (name.replace('/', '__') + '.gz')
            packed.write_bytes(gzip.compress(raw, mtime=0))
        else:
            archive.add(file, arcname=name, recursive=False)
(output / 'original-member-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'output': str(output), 'publicFiles': len(manifest),
                  'files': {f.name: f.stat().st_size for f in output.iterdir()}}))
