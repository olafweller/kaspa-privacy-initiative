import sys
from pathlib import Path
sys.path.append(str(next((p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists()),Path('/opt/kpi'))/'poc/remote-cuda'))
"""One reviewed program/trial and four public arrivals; no executable uploads."""
import json
import os
from pathlib import Path
import re
import sys
from common import sha
from staged_archive import open_archive

ROOT = next((p for p in Path(__file__).resolve().parents if (p/'AGENTS.md').exists()),Path('/opt/kpi'))
sys.path.append(str(ROOT/'poc/remote-cuda'))
import run_stage as reviewed

SCOPE = 'STAGED_RECOVERY_TN10_SIX_V1'
IMAGE = '095a2fb2f58c350ccd2688ae7f72748c915bd973c60fd4abaa8d87b282ad68b5'
JOIN = '7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e'
PROGRAM = '6039c3ef645d620bdd7eef6384750e73f51bcc8f9182aae1b1ac3c963601e75b'
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
    assert p['hostBinarySha256'] == json.loads(Path(__file__).with_name('pins.json').read_text())['hostBinarySha256'] == sha((package/'bin/kpi-recovery-tn10').read_bytes())
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
    if (t['schema'] != 'KPI_RECOVERY_TN10_FROZEN_BATCH_V1' or t['trial'] != policy['trial'] or
            t['stage'] != stage or t['image'] != IMAGE or t['join'] != JOIN or
            t['programSha256'] != PROGRAM or t['cycleLimit'] != 160000000 or
            t['aggregateProofSeconds'] != 3600 or t['automaticRetry'] is not False or
            t['segmentPo2'] != (20 if stage in ('credit-transfer','bob-exit','alice-exit') else 16)):
        raise ValueError('wrong trial, stage, reviewed identities or limits')
    if len(files['input.bin']) > 1024**2 or len(files['journal.bin']) != 352:
        raise ValueError('frozen input/journal length')
    for name, field in [('guest.program.bin','programSha256'),('input.bin','inputSha256'),('journal.bin','journalSha256')]:
        if sha(files[name]) != t[field]: raise ValueError('asset hash mismatch')
    if files['journal.bin'].hex() != t['journalHex']:
        raise ValueError('complete expected journal mismatch')
    return files, t



def validate_trial(trial):
    assert trial['schema']=='KPI_RECOVERY_TN10_TRIAL_V1' and trial['guestImage']==IMAGE and trial['programSha256']==PROGRAM
    assert trial['network']=='testnet-10' and trial['domain']=='0a712763b53b5872e21f25ea109487aa8d7933932cc761c55583da41e9e0cf54'
    assert trial['batches']==list(CASES) and trial['sharedProofSeconds']==3600 and trial['maxRentalSeconds']==7200
    # Runtime receives only the public trial, never a wallet/sponsor secret.
    assert set(trial)=={'schema','trial','network','scope','lane','domain','guestImage','joinControl','programSha256','walletParametersSha256','alice','bob','sponsorNative','principalSompi','bobPrincipalSompi','aliceFinalPrincipalSompi','stateRentSompi','permissionRentSompi','fundingAuthorized','broadcastAuthorized','gpuAuthorized','roleCustody','batches','sharedProofSeconds','maxRentalSeconds','gpuAttempts','planningLimitUsd'}
    for role in ('alice','bob'):
        assert set(trial[role])=={'owner','incoming'}
        for name in ('owner','incoming'):digest(trial[role][name])
    digest(trial['trial'])
    assert trial['joinControl']==JOIN and trial['principalSompi']==1000000000 and trial['bobPrincipalSompi']==400000000 and trial['aliceFinalPrincipalSompi']==600000000
    assert trial['gpuAttempts']==1 and trial['planningLimitUsd']==5 and trial['stateRentSompi']==100000000 and trial['permissionRentSompi']==50000000
    return trial


def build(binary,out,trial_path,program=None):
    trial=validate_trial(json.loads(trial_path.read_text()))
    program=program or ROOT/'poc/recovery-native/evidence/fixtures/guest.program.bin'
    out.mkdir(parents=True)
    for dest,source in [('bin/kpi-recovery-tn10',binary),('guest.program.bin',program),('trial.json',trial_path)]:write(out/dest,source.read_bytes())
    (out/'bin/kpi-recovery-tn10').chmod(0o755)
    p={'scope':SCOPE,'trial':trial['trial'],'trialSha256':sha((out/'trial.json').read_bytes()),
       'guestImage':IMAGE,'joinControl':JOIN,'programSha256':PROGRAM,'hostBinarySha256':sha(binary.read_bytes()),
       'cudaProverSha256':CUDA,'cases':list(CASES),'aggregateSeconds':3600,'rentalSeconds':7200,
       'uploadFiles':list(PUBLIC),'walletSecretsIncluded':False,'proofAndRentalAuthorized':False,'nativeFundingAndBroadcastAuthorized':False}
    write(out/'staged-policy.json',(json.dumps(p,indent=2,sort_keys=True)+'\n').encode())
    return check(out)
