#!/usr/bin/env python3
"""Prepare only public, hash-checked PR40 inputs and an independent CPU verifier."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_SHA = '01107d542cb0c333ec509362de59bbb6c402a4d243c13f13954f485e3c256cfc'
IMAGE = '397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716'
CLAIMS = {
    'segment-24': '328f16f86bb6835a1f322380b26557c3038fbba07ff93dbcbf55ccde81a720cc',
    'segment-25': 'b0af71e4c202f3775452bbf8ee1091feb62f4463a00515c7878fe3de199ca2c9',
    'lift-24': '328f16f86bb6835a1f322380b26557c3038fbba07ff93dbcbf55ccde81a720cc',
    'lift-25': 'b0af71e4c202f3775452bbf8ee1091feb62f4463a00515c7878fe3de199ca2c9',
    'join': '7917795912b2877505c126d8a996d19089603eb8044dee3cd76fff08caf4cc31',
}
INPUTS = ['program.bin', 'input.bin', 'expected-journal.bin', 'session.json',
          'session-claim.bin', 'segments/24.bincode', 'segments/25.bincode']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_archive(path, expected_sha=None):
    if expected_sha is not None:
        assert sha(path.read_bytes()) == expected_sha, 'archive hash mismatch'
    contents = {}
    with tarfile.open(path, 'r:gz') as archive:
        for item in archive:
            name = PurePosixPath(item.name)
            assert len(contents) < 512 and name.parts and len(item.name) <= 240
            assert item.isfile() and not name.is_absolute() and '..' not in name.parts
            assert str(name) == item.name and item.name not in contents
            assert item.size <= 32*1024**2
            contents[item.name] = archive.extractfile(item).read()
            assert sum(map(len, contents.values())) <= 128*1024**2
    return contents


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as target:
        target.write(data)


def build(host, out):
    source = ROOT / 'poc/proof-phase-diagnostics/evidence/local-phase-artifacts.tar.gz'
    contents = checked_archive(source, ARCHIVE_SHA)
    manifest = json.loads((source.parent / 'comparison.json').read_text())['archiveManifest']
    assert set(contents) == set(manifest)
    for name, data in contents.items():
        assert sha(data) == manifest[name]['sha256'] and len(data) == manifest[name]['bytes']
    out.mkdir(parents=True)
    inputs = {}
    for name in INPUTS:
        data = contents['assets/'+name]
        inputs[name] = {'sha256': sha(data), 'bytes': len(data)}
        write(out/'inputs'/name, data)
        write(out/'baseline'/name, data)
    for phase, claim in CLAIMS.items():
        assert json.loads(contents[f'assets/{phase}-verified.json'])['claimDigest'] == claim
        write(out/'baseline'/f'{phase}.bin', contents[f'assets/{phase}.bin'])
    write(out/'bin/kpi-takeover-host', host.read_bytes())
    (out/'bin/kpi-takeover-host').chmod(0o755)
    result = subprocess.run([str(host.resolve()), 'phase-diagnostics', 'compare',
                             str((out/'baseline').resolve())],
                            env=__import__('os').environ | {'RISC0_PROVER': 'ipc'},
                            capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode()
    policy = {'scope': 'FIXED_PR40_PARTIAL_CUDA_QUALIFICATION',
              'referenceArchiveSha256': ARCHIVE_SHA, 'expectedProgramImage': IMAGE,
              'inputs': inputs, 'cpuClaims': CLAIMS,
              'cpuVerifierSha256': sha(host.read_bytes()),
              'sourceRevision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
    write(out/'workload.json', (json.dumps(policy, indent=2, sort_keys=True)+'\n').encode())
    archive_path = out/'public-package.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as archive:
        for p in sorted(out.rglob('*')):
            if p.is_file() and p != archive_path:
                data = p.read_bytes()
                item = tarfile.TarInfo(p.relative_to(out).as_posix())
                item.size = len(data)
                item.mode = 0o755 if p.name == 'kpi-takeover-host' else 0o644
                archive.addfile(item, io.BytesIO(data))
    checked_archive(archive_path, sha(archive_path.read_bytes()))
    print(json.dumps({'archive': str(archive_path), 'bytes': archive_path.stat().st_size,
                      'sha256': sha(archive_path.read_bytes()), 'baselineCpuVerification': True}))


if __name__ == '__main__':
    build(Path(sys.argv[1]), Path(sys.argv[2]))
