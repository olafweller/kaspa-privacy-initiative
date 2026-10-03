#!/usr/bin/env python3
"""Isolated PK-load/fresh-proof/Full CLI resource samples, not discovery evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

import a1_check as c


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path); p.add_argument('binary', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args(); samples = []
    with tempfile.TemporaryDirectory(prefix='kpi-a1-isolated-proof-') as temporary:
        root = Path(temporary)
        for branch in c.BRANCHES:
            original = c.load_json(a.bundle / (branch + '.validate.json'))
            op = original['transaction']['inputs'][0]['previousOutpoint']
            request = root / (branch + '.request.json')
            request.write_bytes(c.canonical_json({'txid': op['transactionId'], 'index': str(op['index']), 'entry': original['entry']}))
            proof_output = root / (branch + '.transaction.json'); time_output = root / (branch + '.time.txt')
            command = [str(a.binary), 'fresh-continue' if branch == 's0_continue' else 'fresh-terminal', str(a.bundle)]
            if branch != 's0_continue': command.append(branch)
            command += [str(a.bundle / 'claim-secret.bin'), str(request), str(proof_output)]
            env = dict(os.environ); env['RAYON_NUM_THREADS'] = '4'
            result = subprocess.run(['/usr/bin/time', '-f', '%e %U %S %M', '-o', str(time_output)] + command,
                                    check=True, capture_output=True, text=True, env=env)
            fresh = json.loads(result.stdout); c.require(fresh['fresh_proof'] and fresh['native_full'], 'fresh sample invalid')
            elapsed, user, system, rss = time_output.read_text().strip().split()
            transaction = c.load_json(proof_output)
            new_signature = bytes.fromhex(transaction['inputs'][0]['signatureScript'])
            old_signature = bytes.fromhex(original['transaction']['inputs'][0]['signatureScript'])
            c.require(new_signature[68:196] != old_signature[68:196], 'pre-generated proof reused')
            samples.append({'branch': branch, 'wall_seconds_including_PK_load': elapsed,
                            'user_cpu_seconds': user, 'system_cpu_seconds': system,
                            'maximum_RSS_KiB': rss, 'fresh_proof_and_native_Full': True,
                            'proof_bytes_differ_from_golden': True, 'same_transaction_id_expected': transaction['id'] == original['transaction']['id']})
    report = {'schema': 'kpi-a1-isolated-prover-samples/v1', 'samples': samples,
              'binary_sha256': c.sha(a.binary.read_bytes()),
              'scope': 'isolated file-only CLI process; includes validated PK parse, proof and Full; supplied known UTXO, not current-chain discovery',
              'single_local_sample_not_performance_guarantee': True, 'funding_authorized': False}
    with a.output.open('xb') as stream: stream.write(c.canonical_json(report))
    print(json.dumps({'samples': len(samples), 'fresh_proofs_valid': True}))


if __name__ == '__main__': main()
