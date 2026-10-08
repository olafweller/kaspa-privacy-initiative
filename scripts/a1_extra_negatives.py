#!/usr/bin/env python3
"""Supplemental real native-VM negatives over observed A1 golden requests.

The native validator receives decoded final transactions and recomputes their
ID. No network, proving, new setup or private backup is used. Failures retain
their actual error; an isolation failure is not credited to a circuit check.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import time

import a1_check as c


def push(data):
    if len(data) == 0: return b'\x00'
    if len(data) <= 75: return bytes([len(data)]) + data
    if len(data) <= 255: return b'\x4c' + bytes([len(data)]) + data
    return b'\x4d' + len(data).to_bytes(2, 'little') + data


def assert_result(returncode, stdout, stderr, expected, reason):
    """Any decoder, preparation, mass or unrelated failure invalidates coverage."""
    if expected:
        c.require(returncode == 0 and json.loads(stdout).get('full_valid') is True,
                  'native Full positive control failed')
        return 'native-Full-success'
    c.require(returncode != 0, 'fund-safety negative unexpectedly accepted')
    error = stderr.strip()
    if reason == 'native-verifier-canonical-scalar':
        c.require(error.startswith('Error: "utxo: SignatureInvalid(ZkIntegrity(') and
                  'ARK serialization error' in error, 'wrong rejection layer: ' + error)
        return 'native-verifier-canonical-scalar'
    c.require(error == 'Error: "utxo: SignatureInvalid(VerifyError)"',
              'wrong rejection layer: ' + error)
    return 'native-script-verify'


def run(bundle, binary):
    cases = []
    with tempfile.TemporaryDirectory(prefix='kpi-a1-extra-negative-') as temporary:
        path = Path(temporary) / 'request.json'
        def check(name, request, expected=False, reason='redeem-script'):
            start = time.monotonic()
            path.write_bytes(c.canonical_json(request))
            prepared = subprocess.run([str(binary), 'prepare-body', str(path)],
                                      capture_output=True, text=True, check=True)
            final = json.loads(prepared.stdout)
            path.write_bytes(c.canonical_json(final))
            p = subprocess.run([str(binary), 'validate-body', str(path)], capture_output=True, text=True)
            layer = assert_result(p.returncode, p.stdout, p.stderr, expected, reason)
            cases.append({'case': name, 'accepted': p.returncode == 0, 'expected': expected,
                          'expected_check': reason, 'actual_layer': layer,
                          'final_request_sha256': c.sha(c.canonical_json(final)),
                          'final_txid': final['transaction']['id'],
                          'final_storage_mass': final['transaction']['storageMass'],
                          'id_recomputed': True, 'storage_mass_recomputed': True,
                          'actual_result': p.stdout.strip() if expected else p.stderr.strip(),
                          'milliseconds': (time.monotonic() - start) * 1000})
        for branch in c.BRANCHES:
            base = c.load_json(bundle / (branch + '.validate.json'))
            sig = bytes.fromhex(base['transaction']['inputs'][0]['signatureScript'])
            items = [sig[1:33], sig[34:66], sig[68:196],
                     bytes([0 if branch == 's0_continue' else 1]),
                     (bundle / ('s1.redeem' if branch == 's1_terminal' else 's0.redeem')).read_bytes()]
            check(branch + '/positive', base, True, 'native-Full-positive-control')
            for position in (0, 1):
                for size in (0, 16, 64):
                    changed = copy.deepcopy(base); values = list(items); values[position] = bytes(size)
                    changed['transaction']['inputs'][0]['signatureScript'] = b''.join(map(push, values)).hex()
                    check(f'{branch}/scalar_{position}_size_{size}', changed, reason='redeem-size')
                changed = copy.deepcopy(base); values = list(items)
                values[position] = c.FR.to_bytes(32, 'little')
                changed['transaction']['inputs'][0]['signatureScript'] = b''.join(map(push, values)).hex()
                check(f'{branch}/scalar_{position}_equals_Fr', changed, reason='native-verifier-canonical-scalar')
            for index in range(len(base['transaction']['outputs'])):
                changed = copy.deepcopy(base); changed['transaction']['outputs'].pop(index)
                check(f'{branch}/missing_output_{index}', changed, reason='redeem-output-count')
                full_spk = bytes.fromhex(base['transaction']['outputs'][index]['scriptPublicKey'])
                script = full_spk[2:]
                for offset in range(len(script)):
                    changed = copy.deepcopy(base); mutated = bytearray(script); mutated[offset] ^= 1
                    changed['transaction']['outputs'][index]['scriptPublicKey'] = (full_spk[:2] + mutated).hex()
                    check(f'{branch}/output_{index}_script_byte_{offset}', changed, reason='redeem-full-SPK')
            changed = copy.deepcopy(base)
            changed['transaction']['inputs'][0]['computeBudget'] += 1
            check(branch + '/different_sufficient_budget', changed, True, 'consensus-valid-adapter-exact-budget-refuses')
        changed = c.load_json(bundle / 's1_terminal.validate.json')
        manifest = c.load_json(bundle / 'manifest.json')
        spk = bytes.fromhex(manifest['states']['s1']['spk_hex'])
        changed['transaction']['outputs'][0]['scriptPublicKey'] = spk.hex()
        check('s1_terminal/attempt_S2_same_S1_script', changed, reason='redeem-fixed-terminal-recipient')
    return {'schema': 'kpi-a1-native-supplement/v2', 'validator_binary_sha256': c.sha(binary.read_bytes()), 'scope': 'real-golden-unfunded-native-Full-supplement-finalized-ID-and-mass', 'cases': cases,
            'case_count': len(cases), 'funding_authorized': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path); p.add_argument('binary', type=Path); p.add_argument('output', type=Path)
    a = p.parse_args()
    data = run(a.bundle, a.binary)
    with a.output.open('xb') as stream: stream.write(c.canonical_json(data))
    print(json.dumps({'case_count': data['case_count'], 'all_expected_outcomes': True}))


if __name__ == '__main__': main()
