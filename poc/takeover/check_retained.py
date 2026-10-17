#!/usr/bin/env python3
"""Exercise prepare on retained public captures. No RPC, keys, signing or proving.

Build the host and retained validator first; pass an empty, new output directory.
The program bytes used here are the imported artifacts, not a guest rebuild.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', type=Path)
p.add_argument('--bin-dir', type=Path, default=ROOT / '.local/ci-target/release')
p.add_argument('--program-dir', type=Path, default=ROOT / '.local/takeover')
a = p.parse_args()
out = a.output.resolve()
out.mkdir()  # Preserve prior runs; never overwrite them.
public = out / 'public'
public.mkdir()
evidence = ROOT / 'poc/native-value/evidence'
with tarfile.open(evidence / 'public-trial.tar.gz') as t:
    # Only the named public application states are needed, never wallet files.
    for name in ['prefix-input.json', 'prefix-state.json', 'final-output.json']:
        member = t.getmember(name)
        assert member.isfile()
        (public / name).write_bytes(t.extractfile(member).read())
reference = json.loads((public / 'prefix-input.json').read_text())
lane = bytes(reference['lane']['lane']).hex()
cov = bytes(reference['lane']['covenant']).hex()
report = {'scope': 'RETAINED_PUBLIC_CAPTURE_PREPARATION_NO_NEW_PROOFS',
          'actualTN10Settlement': False, 'cases': {}, 'programSha256': {}}
for name in ['transaction', 'batch', 'aggregate']:
    report['programSha256'][name] = hashlib.sha256(
        (a.program_dir / f'{name}.program.bin').read_bytes()).hexdigest()

def prepare(name, capture, state, omitted=None, succeeds=True):
    target = out / name
    cmd = [str(a.bin_dir / 'kpi-takeover-prepare'), str(capture), lane, cov,
           str(state), str(a.program_dir), str(target),
           str(a.bin_dir / 'kpi-tn10-integration')]
    if omitted is not None:
        cmd.append(omitted)
    result = subprocess.run(cmd, capture_output=True)
    (out / f'{name}.stdout.log').write_bytes(result.stdout)
    (out / f'{name}.stderr.log').write_bytes(result.stderr)
    assert (result.returncode == 0) == succeeds, (name, result.stderr.decode())
    return target

for name, state in [('prefix2', 'empty'), ('final2', public / 'prefix-state.json')]:
    capture = public / f'{name}-capture.json'
    capture.write_bytes(gzip.decompress((evidence / f'{name}-capture.json.gz').read_bytes()))
    target = prepare(name, capture, state)
    expected = (json.loads((public / 'prefix-state.json').read_text()) if name == 'prefix2'
                else json.loads((public / 'final-output.json').read_text())['state'])
    assert json.loads((target / 'state.json').read_text()) == expected, name
    manifest = json.loads((target / 'bundle.json').read_text())
    report['cases'][name] = {'matchesRetainedState': True, 'batches': len(manifest['batches']),
                             'spendableSompi': manifest['spendableSompi']}
    original_journal = (target / 'aggregate.journal.bin').read_bytes()
    if name == 'final2':
        assert original_journal[:32] == (out / 'prefix2/aggregate.journal.bin').read_bytes()[64:96]
        assert original_journal[32:64] == (out / 'prefix2/aggregate.journal.bin').read_bytes()[96:128]
        report['cases'][name]['stateAndTipContinuePrefix'] = True
    omitted = manifest['orderedIds'][0]
    negative = prepare(f'{name}-omitted', capture, state, omitted)
    bad_journal = (negative / 'aggregate.journal.bin').read_bytes()
    assert bad_journal[128:160] != original_journal[128:160]
    report['cases'][name]['omissionChangesFixedEndpointCommitment'] = True

# Compose contiguous retained intervals so a single local proof bundle can cover
# both credit and withdrawal, starting at the original zero-balance checkpoint.
# This is a derivative of two captures; both original compressed files stay intact.
prefix = json.loads((public / 'prefix2-capture.json').read_text())
final = json.loads((public / 'final2-capture.json').read_text())
def block_hash(capture, label):
    record = next(r for r in capture['records'] if r['label'] == label)
    return json.loads(record['raw'])['params']['block']['header']['hash']
assert block_hash(prefix, 'end-block') == block_hash(final, 'start-block'), 'noncontiguous captures'
combined = json.loads(json.dumps(prefix))
combined['intervalBlocks'] += final['intervalBlocks']
for record in combined['records']:
    label = record['label']
    other = next(r for r in final['records'] if r['label'] == label)
    if label in ['end-block', 'end-proof', 'server-after']:
        record.update(other)
    elif label in ['accepted', 'accepted-recheck']:
        first_raw, second_raw = json.loads(record['raw']), json.loads(other['raw'])
        for field in ['addedChainBlockHashes', 'chainBlockAcceptedTransactions']:
            first_raw['params'][field] = (first_raw['params'][field][:prefix['intervalBlocks']]
                                          + second_raw['params'][field][:final['intervalBlocks']])
        record['raw'] = json.dumps(first_raw)
combined_path = public / 'combined-capture.json'
combined_path.write_text(json.dumps(combined))
target = prepare('combined', combined_path, 'empty')
assert json.loads((target / 'state.json').read_text()) == json.loads((public / 'final-output.json').read_text())['state']
manifest = json.loads((target / 'bundle.json').read_text())
report['cases']['combined'] = {'matchesRetainedState': True, 'blocks': combined['intervalBlocks'],
                               'batches': len(manifest['batches']), 'transactions': len(manifest['orderedIds']),
                               'spendableSompi': manifest['spendableSompi'], 'contiguousCaptureEndpoints': True}

# Change a lane payload while retaining its original claimed native ID, in both
# reads, so the rejection is caused by native ID validation rather than recheck.
capture = json.loads((public / 'prefix2-capture.json').read_text())
for record in capture['records']:
    if record['label'] not in ['accepted', 'accepted-recheck']:
        continue
    raw = json.loads(record['raw'])
    for block in raw['params']['chainBlockAcceptedTransactions']:
        tx = next((t for t in block['acceptedTransactions'] if t['subnetworkId'] == lane), None)
        if tx is not None:
            tx['payload'] += '00'
            break
    record['raw'] = json.dumps(raw)
bad = public / 'tampered-capture.json'
bad.write_text(json.dumps(capture))
prepare('tampered', bad, 'empty', succeeds=False)
assert 'retained native capture validation failed' in (out / 'tampered.stderr.log').read_text()
report['tamperedNativeBodyRejected'] = True
(out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
