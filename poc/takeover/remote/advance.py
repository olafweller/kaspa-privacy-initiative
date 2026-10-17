#!/usr/bin/env python3
"""Advance one explicitly selected fresh rehearsal, with no mutation retries.

Run from repository root after the prefix proof job has started. Keys remain on
VPS. Reconstruct from public captures in a new directory before publishing the
post-stop withdrawal. Every remote failure stops this driver for inspection.
"""
from pathlib import Path
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import time

BASE = Path('.local/takeover/live')
NAME = (BASE / 'trial-name.txt').read_text().strip()
assert NAME.startswith('trial-') and '/' not in NAME
TRIAL = '/opt/kpi-pr31-cloud-20261017/takeover/' + NAME
WORK = BASE / NAME
PROGRAMS = '.local/takeover/rebuilt-programs-01'
REMOTE = 'poc/lane-completeness/integration/remote.py'
HOST = '.local/ci-target/release/kpi-takeover-host'
PREPARE = '.local/ci-target/release/kpi-takeover-prepare'
VALIDATOR = '.local/ci-target/release/kpi-tn10-integration'
IDENTITY = json.loads((BASE / 'identity.json').read_text())
META = json.loads((WORK / 'prepared.json').read_text())
LANE, COV = IDENTITY['lane'], META['covenantId']

def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)

def get(name, destination):
    run(['python3', REMOTE, 'get', 'takeover/' + NAME + '/' + name, destination])

def stage(name, label=None):
    args = ['/opt/kpi-cloud-https/bin/node', '/opt/kpi-pr31-cloud-20261017/takeover/run-v1.mjs', name, TRIAL]
    if label is not None:
        args.append(label)
    with (WORK / f'{name}-{label or "job"}-terminal.log').open('xb') as log:
        run(['python3', REMOTE, 'exec', shlex.join(args)], stdout=log, stderr=subprocess.STDOUT)
    print('REMOTE_COMPLETE', name, label or '', flush=True)

def upload(source, label):
    run(['node', 'poc/lane-completeness/integration/upload.mjs', source, 'takeover/' + NAME + '/' + label + '-receipt.bin'])

def prepare(capture, state, output, omit=None):
    args = [PREPARE, capture, LANE, COV, state, PROGRAMS, output, VALIDATOR]
    if omit:
        args.append(omit)
    run(args)

def prove(label, prepared):
    run(['python3', 'poc/takeover/measure.py', WORK / (label + '-proof-run'), HOST,
         'bundle', prepared, PROGRAMS, WORK / (label + '-proof')],
        env={**os.environ, 'RISC0_PROVER': 'ipc',
             'RISC0_SERVER_PATH': '/workspace/scratch/kpi-lane-tools/r0vm', 'RAYON_NUM_THREADS': '4'})
    print('PROOF_COMPLETE', label, flush=True)

def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')

# Read-only wait for the separately measured prefix proof; never restart it.
resource = WORK / 'prefix-proof-run.resources.json'
while not resource.exists():
    time.sleep(1)
assert json.loads(resource.read_text())['exitCode'] == 0
assert json.loads((WORK / 'prefix-proof/complete.json').read_text())['fixedCapturedAnchorAccepted']
upload(WORK / 'prefix-proof/aggregate-receipt.bin', 'prefix')
stage('settle', 'prefix')
stage('stop')

# Clean replay contains only public captures and derived state. Never import the
# original prefix state or private wallet files into this new execution directory.
clean = WORK / 'clean-executor'
clean.mkdir(mode=0o700)
shutil.copy2(WORK / 'prefix-capture.json', clean / 'prefix-capture.json')
for name in ['prefix-settlement-transaction.json', 'prefix-settlement-accepted.json',
             'executor-stop.json', 'stop-job-rpc.json']:
    get(name, clean / name)
prepare(clean / 'prefix-capture.json', 'empty', clean / 'reconstructed-prefix')
checkpoint = json.loads((clean / 'prefix-settlement-transaction.json').read_text())
stop = json.loads((clean / 'executor-stop.json').read_text())
journal = (clean / 'reconstructed-prefix/aggregate.journal.bin').read_bytes()
assert journal[64:96].hex() == checkpoint['newState'] == stop['state']
assert journal[96:128].hex() == checkpoint['newTip'] == stop['laneProof']['lane']['tip']
records = json.loads((clean / 'stop-job-rpc.json').read_text())
utxos = [json.loads(x['raw'])['params'] for x in records if x['method'] == 'getUtxosByAddresses']
entry = next(e for reply in utxos for e in reply['entries']
             if e['outpoint']['transactionId'] == checkpoint['transactionId'] and e['outpoint']['index'] == 0)
assert entry['utxoEntry']['covenantId'] == COV and entry['utxoEntry']['amount'] == 100_000_000
assert entry['utxoEntry']['scriptPublicKey'] == checkpoint['transaction']['outputs'][0]['scriptPublicKey']
save(clean / 'reconstruction.json', {'scope': 'CLEAN_PUBLIC_REPLAY_SAME_OWNER_NODE',
    'stateRoot': checkpoint['newState'], 'tip': checkpoint['newTip'], 'currentUtxo': entry,
    'originalAccountStateImported': False, 'sourceCaptureSha256': hashlib.sha256((clean / 'prefix-capture.json').read_bytes()).hexdigest()})
print('CLEAN_RECONSTRUCTION_CONFIRMED', flush=True)

stage('withdraw')
for name in ['catchup-capture.json', 'withdraw-transaction.json', 'withdraw-accepted.json', 'gap.json']:
    get(name, clean / name)
state = clean / 'reconstructed-prefix/state.json'
prepare(clean / 'catchup-capture.json', state, clean / 'full-prepared')
assert json.loads((clean / 'full-prepared/bundle.json').read_text())['spendableSompi'] == 600_000_000
withdrawal = json.loads((clean / 'withdraw-transaction.json').read_text())
prepare(clean / 'catchup-capture.json', state, clean / 'omission-prepared', withdrawal['transactionId'])
assert json.loads((clean / 'omission-prepared/bundle.json').read_text())['spendableSompi'] == 1_000_000_000
prove('omission', clean / 'omission-prepared')
assert not json.loads((WORK / 'omission-proof/complete.json').read_text())['fixedCapturedAnchorAccepted']
prove('final', clean / 'full-prepared')
assert json.loads((WORK / 'final-proof/complete.json').read_text())['fixedCapturedAnchorAccepted']
upload(WORK / 'omission-proof/aggregate-receipt.bin', 'omission')
upload(WORK / 'final-proof/aggregate-receipt.bin', 'final')
stage('settle', 'omission')
stage('settle', 'final')
stage('payout')
get('complete.json', WORK / 'complete.json')
result = json.loads((WORK / 'complete.json').read_text())
assert result['reservedNativeSompi'] == result['appSpendableSompi'] == 600_000_000
assert result['unpaidClaimsSompi'] == 0 and result['gap']['stoppedGapBlueScores'] > 100
print('REHEARSAL_CONFIRMED_COMPLETE', NAME, flush=True)
