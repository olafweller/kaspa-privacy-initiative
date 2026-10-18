"""Fixed public private-note package. No directory traversal of wallet state."""
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile

from package import ROOT, checked_archive, sha, write

SCOPE = 'FIXED_PRIVATE_NOTE_ONE_SUCCINCT_RECEIPT'
IMAGE = '20d8431e18f42c6e337ab726f166914516e3ebcd70577e67d49e687737901f8b'
CONTROL = '7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e'
PROGRAM_SHA = '531e2c5415844446af254634c43e02bd64644cd669625b3edefb554f1e7ab191'
INPUT_SHA = 'd43a228f371f30f7bcd80eb7d035f79a9d128245a6d88135b39de2b4c57cfa2f'
JOURNAL_SHA = '88ba872f3aca413a41b83e91ba40c4eb0b27eb9db31150b7af3d133bb6ccf22e'
CUDA_SHA = '4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb'
BINS = ('kpi-private-note-producer', 'kpi-private-note-verifier', 'kpi-private-note-native')
INPUTS = {
    'guest.program.bin': ('poc/private-note-chain/evidence/guest.program.bin', PROGRAM_SHA),
    'input.bin': ('poc/private-note-chain/evidence/public/valid-invalid-valid.input.bin', INPUT_SHA),
    'expected-journal.bin': ('poc/private-note-chain/calibration-160m/evidence/expected-journal.bin', JOURNAL_SHA),
}


def build(binaries, out):
    out.mkdir(parents=True)
    inputs = {}
    for name, (source, digest) in INPUTS.items():
        data = (ROOT/source).read_bytes()
        assert sha(data) == digest, 'frozen public target changed'
        write(out/'inputs'/name, data)
        inputs[name] = {'sha256': digest, 'bytes': len(data)}
    specs = {}
    for name in BINS:
        data = (binaries/name).read_bytes()
        write(out/'bin'/name, data)
        (out/'bin'/name).chmod(0o755)
        specs[name] = {'sha256': sha(data), 'bytes': len(data)}
    policy = {'scope': SCOPE, 'expectedProgramImage': IMAGE, 'expectedControlId': CONTROL,
              'expectedHashfn': 'poseidon2', 'expectedJournalBytes': 352,
              'expectedJournalSha256': JOURNAL_SHA, 'cudaProverSha256': CUDA_SHA,
              'executionCycleLimit': 160000000, 'wholeProofJobSecondsLimit': 3600,
              'inputs': inputs, 'binaries': specs, 'walletSecretsIncluded': False,
              'walletSetupParametersIncluded': False}
    write(out/'private-workload.json', (json.dumps(policy, indent=2, sort_keys=True)+'\n').encode())
    return policy


def archive(package, destination):
    expected = {'private-workload.json'} | {'inputs/'+n for n in INPUTS} | {'bin/'+n for n in BINS}
    files = {p.relative_to(package).as_posix(): p for p in package.rglob('*') if p.is_file()}
    assert set(files) == expected and not any(p.is_symlink() for p in files.values())
    with destination.open('xb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as compressed, tarfile.open(fileobj=compressed, mode='w') as tar:
        for name, path in sorted(files.items()):
            data = path.read_bytes()
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o755 if name.startswith('bin/') else 0o644
            tar.addfile(item, io.BytesIO(data))
    return {'bytes': destination.stat().st_size, 'sha256': sha(destination.read_bytes())}


def restore(out):
    evidence = ROOT/'poc/private-note-proof/evidence'
    identity = json.loads((evidence/'package-identity.json').read_text())
    for name, digest in identity['sourceFiles'].items():
        assert sha((ROOT/name).read_bytes()) == digest, 'source/binary manifest drift: '+name
    contents = checked_archive(evidence/'public-package.tar.gz', identity['archive']['sha256'])
    allowed = {'private-workload.json'} | {'inputs/'+n for n in INPUTS} | {'bin/'+n for n in BINS}
    assert set(contents) == allowed
    out.mkdir(parents=True)
    for name, data in contents.items():
        write(out/name, data)
        if name.startswith('bin/'):
            (out/name).chmod(0o755)
    policy = json.loads(contents['private-workload.json'])
    assert sha(contents['private-workload.json']) == identity['policySha256']
    return policy


if __name__ == '__main__':
    if sys.argv[1] == 'restore':
        policy = restore(Path(sys.argv[2]))
    elif sys.argv[1] == 'build':
        policy = build(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit('build BIN_DIRECTORY NEW_PACKAGE | restore NEW_PACKAGE')
    print(json.dumps({'scope': policy['scope'], 'expectedProgramImage': IMAGE, 'expectedControlId': CONTROL}))
