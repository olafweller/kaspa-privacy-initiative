"""One reviewed program/trial and four public arrivals; no executable uploads."""
import json
import os
from pathlib import Path
import re
import sys
from common import sha
from staged_archive import open_archive

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'private-native-tn10'))
import run_stage as reviewed

SCOPE = 'STAGED_TN10_PRIVATE_LIFECYCLE_V1'
IMAGE = '794cfff4cfa509799ec1f6750678d3fe4bc8623522aa647cc65e6b53955c4bc9'
JOIN = '7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e'
PROGRAM = '213ed12a0f0b514443fcab9608de5d42e0961fc6704fd51d49326106ead1e375'
CUDA = '4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb'
CASES = reviewed.CASES
PUBLIC = ('guest.program.bin', 'input.bin', 'journal.bin', 'target.json')
MAX_UPLOAD = 8*1024**2
MAX_UPLOAD_TAR = 16*1024**2  # Includes headers, PAX/GNU metadata and padding.


def digest(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('canonical SHA256 required')
    return value


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def check(package, cuda=False):
    p = json.loads((package/'staged-policy.json').read_text())
    assert p['scope'] == SCOPE and p['cases'] == list(CASES)
    assert p['guestImage'] == IMAGE and p['joinControl'] == JOIN
    assert p['cudaProverSha256'] == CUDA and p['programSha256'] == PROGRAM
    assert p['aggregateSeconds'] == 3600 and p['rentalSeconds'] == 7200
    assert p['hostBinarySha256'] == sha((package/'bin/kpi-private-native-tn10').read_bytes())
    assert sha((package/'guest.program.bin').read_bytes()) == PROGRAM
    trial = json.loads((package/'trial.json').read_text())
    assert p['trial'] == trial['trial'] and p['trialSha256'] == sha((package/'trial.json').read_bytes())
    if cuda: assert sha(Path(os.environ['RISC0_SERVER_PATH']).read_bytes()) == CUDA
    return p


def unpack(data, expected, policy, stage):
    """Check all members before writing anything; never tar.extract()."""
    digest(expected)
    if stage not in CASES or not 0 < len(data) <= MAX_UPLOAD:
        raise ValueError('fixed stage / bounded public upload required')
    files = {}
    with open_archive(data, MAX_UPLOAD, MAX_UPLOAD_TAR, len(PUBLIC)) as (tar, members):
        for item in members:
            if item.name not in PUBLIC or item.name in files or not item.isfile():
                raise ValueError('unknown, duplicate, linked or non-regular public asset')
            if item.size < 0 or item.size > 2*1024**2:
                raise ValueError('public asset size exceeds frozen guest/package bounds')
            files[item.name] = tar.extractfile(item).read(item.size+1)
            if len(files[item.name]) != item.size: raise ValueError('truncated asset')
    if set(files) != set(PUBLIC) or sha(files['target.json']) != expected:
        raise ValueError('missing public asset / independently approved target mismatch')
    t = json.loads(files['target.json'])
    if (t['schema'] != 'KPI_TN10_FROZEN_BATCH_V1' or t['trial'] != policy['trial'] or
            t['stage'] != stage or t['image'] != IMAGE or t['join'] != JOIN or
            t['programSha256'] != PROGRAM or t['cycleLimit'] != 160000000 or
            t['aggregateProofSeconds'] != 3600 or t['automaticRetry'] is not False or
            t['segmentPo2'] != (20 if stage in ('credit-transfer', 'exit') else 16)):
        raise ValueError('wrong trial, stage, reviewed identities or limits')
    if len(files['input.bin']) > 1024**2 or len(files['journal.bin']) != 352:
        raise ValueError('frozen input/journal length')
    for name, field in [('guest.program.bin','programSha256'),('input.bin','inputSha256'),('journal.bin','journalSha256')]:
        if sha(files[name]) != t[field]: raise ValueError('asset hash mismatch')
    if files['journal.bin'].hex() != t['journalHex']:
        raise ValueError('complete expected journal mismatch')
    return files, t


def build(binary, out):
    base = ROOT/'poc/private-native-tn10'
    # Preserve the reviewed source/artifact bindings; do not rebuild the guest.
    for name, expected in json.loads((base/'evidence/source-sha256.json').read_text()).items():
        assert sha((ROOT/name).read_bytes()) == expected, name
    m = json.loads((base/'runmanifest.json').read_text())
    assert sha(binary.read_bytes()) == m['pins']['hostBinarySha256']
    out.mkdir(parents=True)
    for dest, source in [('bin/kpi-private-native-tn10',binary),('guest.program.bin',ROOT/'poc/private-native/evidence/guest.program.bin'),('trial.json',base/'evidence/unfunded-trial.json')]:
        write(out/dest, source.read_bytes())
    (out/'bin/kpi-private-native-tn10').chmod(0o755)
    p = {'scope':SCOPE,'trial':m['trial'],'trialSha256':sha((out/'trial.json').read_bytes()),
         'guestImage':IMAGE,'joinControl':JOIN,'programSha256':PROGRAM,
         'hostBinarySha256':sha(binary.read_bytes()),'cudaProverSha256':CUDA,
         'cases':list(CASES),'aggregateSeconds':3600,'rentalSeconds':7200,
         'uploadFiles':list(PUBLIC),'walletSecretsIncluded':False,
         'proofAndRentalAuthorized':False,'nativeFundingAndBroadcastAuthorized':False}
    write(out/'staged-policy.json',(json.dumps(p,indent=2,sort_keys=True)+'\n').encode())
    return check(out)
