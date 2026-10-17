#!/usr/bin/env python3
"""Package one completed public rehearsal directory; never read wallet keys."""
from pathlib import Path
import argparse
import hashlib
import json
import tarfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('trial')
p.add_argument('output')
a = p.parse_args()
root = Path('/opt/kpi-pr31-cloud-20261017/takeover')
trial = Path(a.trial).resolve()
output = Path(a.output).resolve()
assert trial.parent == root and trial.name.startswith('trial-')
assert output.parent == root and not output.exists()
assert (trial / 'complete.json').is_file() and (trial / 'reconciliation.json').is_file()
files = sorted(f for f in trial.rglob('*') if f.is_file())
assert not any(f.is_symlink() or f.suffix in {'.key', '.pem'} for f in files)
manifest = {}
with tarfile.open(output, 'w:gz') as archive:
    for file in files:
        name = str(file.relative_to(trial))
        raw = file.read_bytes()
        manifest[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        archive.add(file, arcname=name, recursive=False)
Path(str(output) + '.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'archive': str(output), 'publicFiles': len(files),
                  'bytes': output.stat().st_size,
                  'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))
