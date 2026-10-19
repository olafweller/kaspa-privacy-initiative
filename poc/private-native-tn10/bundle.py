"""Freeze one PUBLIC stage for a future prover; never archive the trial directory.

No network, provider, signing or proof invocation is present here. The expected
target hash must already be retained by the trusted controller/B.
"""
import hashlib
import io
import json
from pathlib import Path
import tarfile

FILES = ('guest.program.bin', 'input.bin', 'journal.bin', 'target.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bundle(stage, expected, output):
    stage, output = Path(stage), Path(output)
    target_bytes = (stage/'target.json').read_bytes()
    if sha(target_bytes) != expected:
        raise ValueError('independently expected target hash required')
    target = json.loads(target_bytes)
    if target['schema'] != 'KPI_TN10_FROZEN_BATCH_V1':
        raise ValueError('wrong target schema')
    data = {}
    for name, field in [('guest.program.bin', 'programSha256'),
                        ('input.bin', 'inputSha256'), ('journal.bin', 'journalSha256')]:
        path = stage/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('regular public files required')
        data[name] = path.read_bytes()
        if sha(data[name]) != target[field]:
            raise ValueError('frozen public asset mismatch: '+name)
    if data['journal.bin'].hex() != target['journalHex']:
        raise ValueError('exact journal mismatch')
    data['target.json'] = target_bytes
    # Exclusive creation; an interrupted archive is never a resumable result.
    with output.open('xb') as raw:
        with tarfile.open(fileobj=raw, mode='w:gz') as tar:
            for name in FILES:
                item = tarfile.TarInfo(name)
                item.size, item.mode, item.mtime = len(data[name]), 0o600, 0
                tar.addfile(item, io.BytesIO(data[name]))
        raw.flush()
        import os
        os.fsync(raw.fileno())
    return {'scope': 'ONE_FROZEN_PUBLIC_TN10_BATCH_NO_PROOF_STARTED',
            'targetSha256': expected, 'archiveSha256': sha(output.read_bytes()),
            'files': list(FILES), 'stage': target['stage']}


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 4:
        raise SystemExit('STAGE_DIR EXPECTED_TARGET_SHA NEW_ARCHIVE')
    print(json.dumps(bundle(*sys.argv[1:]), indent=2))
