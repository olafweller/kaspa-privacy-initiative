#!/usr/bin/env python3
"""Public evidence audit: exact native fees, state/journal binding and backing.

No wallet, RPC, Rust imports or proof generation. SDK/native proof verification is
separate. Monetary state hash is independently reimplemented from its encoding.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys
import tarfile

INTEGRATION = Path(__file__).resolve().parents[1] / 'lane-completeness/integration'
sys.path.insert(0, str(INTEGRATION))
from check_capture import transaction_id, H


def u32(value):
    return struct.pack('<I', value)


def u64(value):
    assert type(value) is int and 0 <= value <= 0xffffffffffffffff
    return struct.pack('<Q', value)


def state_hash(state):
    blob = b'KPI-PUBLIC-NATIVE-STATE-v1' + u32(len(state['users']))
    previous = None
    for identity, data in state['users']:
        identity, data = bytes(identity), bytes(data)
        assert previous is None or previous < identity
        previous = identity
        blob += identity + u32(len(data)) + data
    blob += u32(len(state['credited']))
    for identity, index in state['credited']:
        blob += bytes(identity) + u32(index)
    blob += u32(len(state['requests']))
    for identity in state['requests']:
        blob += bytes(identity)
    return hashlib.sha256(blob).digest()


def user_balance(state, owner):
    pubkey = bytes.fromhex(owner)
    lock = hashlib.sha256(b'\x03\x01' + pubkey).digest()
    identity = hashlib.sha256(b'\x01' + lock).digest()
    assert len(state['users']) == 1
    key, value = state['users'][0]
    data = bytes(value)
    assert bytes(key) == identity and len(data) == 74 and data[0] == 1
    assert data[9:41] == lock and data[41] == 1 and data[42:] == pubkey
    return int.from_bytes(data[1:9], 'little')


def point(outpoint):
    return outpoint['transactionId'], outpoint['index']


class Evidence:
    def __init__(self, root):
        self.root = root
        with tarfile.open(root / 'public-trial.tar.gz') as archive:
            self.files = {m.name: archive.extractfile(m).read() for m in archive if m.isfile()}

    def raw(self, name):
        if name in self.files:
            return self.files[name]
        compressed = self.root / (name.replace('/', '__') + '.gz')
        if compressed.is_file():
            return gzip.decompress(compressed.read_bytes())
        return (self.root / name).read_bytes()

    def json(self, name):
        return json.loads(self.raw(name))


def audit(root):
    e = Evidence(root)
    manifest = e.json('original-member-sha256.json')
    for name, item in manifest.items():
        raw = e.raw(name)
        assert len(raw) == item['bytes']
        assert hashlib.sha256(raw).hexdigest() == item['sha256'], name
    confirmed = ['fund-user', 'seed', 'bootstrap', 'deposit', 'unauthorized', 'withdraw',
                 'replay', 'prefix-settlement', 'final-settlement', 'payout']
    fees = {}
    for label in confirmed:
        built, request = e.json(label + '-transaction.json'), e.json(label + '-request.json')
        accepted = e.json(label + '-accepted.json')
        tx = built['transaction']
        assert transaction_id(tx).hex() == built['transactionId']
        assert accepted['transaction']['verboseData']['transactionId'] == built['transactionId']
        assert transaction_id(accepted['transaction']).hex() == built['transactionId']
        inputs = {point(item['outpoint']): item['utxoEntry']['amount']
                  for item in request['utxos']['entries']}
        for name in ['covenantUtxo', 'permissionUtxo', 'delegateUtxo']:
            if name in request:
                item = request[name]
                inputs[point(item['outpoint'])] = item['utxoEntry']['amount']
        amount_in = sum(inputs[point(i['previousOutpoint'])] for i in tx['inputs'])
        amount_out = sum(o['value'] for o in tx['outputs'])
        fee = amount_in - amount_out
        assert type(fee) is int and fee >= 0 and fee == built['feeSompi'], label
        fees[label] = fee
    identity = e.json('identity.json')
    bootstrap = e.json('bootstrap-transaction.json')
    deposit = e.json('deposit-transaction.json')
    payout = e.json('payout-transaction.json')
    result = e.json('payout-result.json')
    assert point(payout['transaction']['inputs'][1]['previousOutpoint']) == (deposit['transactionId'], 0)
    deposit_output = deposit['transaction']['outputs'][0]
    covenant = bytes.fromhex(bootstrap['covenantId'])
    delegate_script = bytes.fromhex('b900a06900cf20') + covenant + bytes.fromhex('880000c97652947cbc0251758851')
    delegate_spk = '0000aa20' + hashlib.blake2b(delegate_script, digest_size=32).hexdigest() + '87'
    assert deposit_output['value'] == 1_000_000_000 and deposit_output['covenant'] is None
    assert deposit_output['scriptPublicKey'] == delegate_spk
    assert payout['transaction']['outputs'][1]['scriptPublicKey'] == delegate_spk
    assert payout['transaction']['outputs'][0]['scriptPublicKey'] == '000020' + identity['owner'] + 'ac'
    assert payout['transaction']['outputs'][0]['value'] == 450_000_000
    assert payout['transaction']['outputs'][1]['value'] == 600_000_000
    assert result['permissionConsumed'] and result['unpaidClaimsSompi'] == 0
    assert result['payout']['utxoEntry']['amount'] == 450_000_000
    assert result['reserve']['utxoEntry']['amount'] == 600_000_000
    assert e.json('payout-replay-rejected.json')['id'] != payout['transactionId']
    # Independently hash each complete public state and all fixed journal fields.
    journals = {}
    for label in ['prefix', 'final', 'omission']:
        input_data = e.json(label + '-input.json')
        report = json.loads((root / 'proofs' / label / 'report.json').read_text())
        output = report['output']
        lane = input_data['lane']
        assert state_hash(input_data['state']) == bytes(lane['old_state'])
        expected = (bytes(lane['old_state']) + bytes(lane['old_tip']) + state_hash(output['state'])
                    + bytes(output['lane']['tip']) + bytes(output['lane']['seq'])
                    + bytes(lane['covenant']) + bytes([0x61] * 32) + bytes([0x62] * 32)
                    + bytes(output['permission_hash']) + bytes(output['deposit_hash'])
                    + H('SeqCommitLaneKey', bytes(lane['lane'])))
        journal = (root / 'proofs' / label / 'journal.bin').read_bytes()
        assert expected == journal and len(journal) == 352
        if label == 'final':
            final_tx = e.json('final-settlement-transaction.json')['transaction']
            assert final_tx['outputs'][1]['scriptPublicKey'] == '0000aa20' + bytes(output['permission_hash']).hex() + '87'
            assert final_tx['outputs'][1]['covenant']['covenantId'] == bootstrap['covenantId']
        journals[label] = {'state': state_hash(output['state']).hex(),
                           'seq': bytes(output['lane']['seq']).hex()}
    assert journals['final']['seq'] != journals['omission']['seq']
    assert e.json('prefix-input.json')['lane']['old_state'] == list(state_hash({'users': [], 'credited': [], 'requests': []}))
    assert e.json('final-input.json')['lane']['old_state'] == list(bytes.fromhex(journals['prefix']['state']))
    prefix = e.json('prefix-output.json')
    final = e.json('final-output.json')
    assert [v['accepted'] for v in prefix['events']] == [True, False]
    assert [v['accepted'] for v in final['events']] == [True, False]
    assert user_balance(prefix['state'], identity['owner']) == 1_000_000_000
    assert user_balance(final['state'], identity['owner']) == 600_000_000
    assert prefix['events'][-1]['spendable'] == 1_000_000_000
    assert final['events'][-1]['spendable'] == 600_000_000
    assert final['exits'][0]['amount'] == 400_000_000
    # Four stages: pending claims remain liabilities until real native payment.
    stages = [dict(stage='initial', spendable=0, unpaidClaims=0, reserved=0),
              dict(stage='deposit_on_L1_uncredited', spendable=0, unpaidClaims=0, reserved=1_000_000_000),
              dict(stage='deposit_settled', spendable=1_000_000_000, unpaidClaims=0, reserved=1_000_000_000),
              dict(stage='withdrawal_settled_unpaid', spendable=600_000_000, unpaidClaims=400_000_000, reserved=1_000_000_000),
              dict(stage='payout_confirmed', spendable=600_000_000, unpaidClaims=0, reserved=600_000_000)]
    assert all(s['spendable'] + s['unpaidClaims'] <= s['reserved'] for s in stages)
    # The final-claim script also owes the recipient the sponsored permission rent.
    # Include that entitlement AND its already-locked native permission output;
    # never count uncommitted sponsor/treasury funds as backing.
    all_entitlements = []
    for stage in stages:
        rent = 50_000_000 if stage['stage'] == 'withdrawal_settled_unpaid' else 0
        liability = stage['spendable'] + stage['unpaidClaims'] + rent
        reserved = stage['reserved'] + rent
        assert liability <= reserved
        all_entitlements.append({'stage': stage['stage'], 'principalLiability': liability-rent,
                                 'rentClaim': rent, 'totalLiability': liability,
                                 'reservedPrincipal': stage['reserved'],
                                 'reservedPermissionRent': rent, 'totalReserved': reserved})

    post = e.json('postcheck.json')
    initial_sponsor = sum(v['utxoEntry']['amount'] for v in e.json('fund-user-request.json')['utxos']['entries'])
    ending_domains = {'sponsor': post['balancesSompi']['sponsor'],
                      'userNative': post['balancesSompi']['user'],
                      'stateRent': post['continuation']['utxoEntry']['amount'],
                      'userReserve': sum(v['utxoEntry']['amount'] for v in post['reserve']['entries'])}
    assert initial_sponsor == sum(ending_domains.values()) + sum(fees.values())
    assert ending_domains['stateRent'] == 100_000_000 and not post['claims']['entries']
    return {'scope': 'INDEPENDENT_PUBLIC_ACCOUNTING_AND_JOURNAL_AUDIT_NOT_ZK_VERIFIER',
            'initialSponsorSompi': initial_sponsor, 'endingDomainsSompi': ending_domains,
            'originalMembersVerified': len(manifest), 'confirmedTransactions': len(confirmed),
            'feesSompi': fees, 'totalFeesSompi': sum(fees.values()),
            'backingStagesSompi': stages, 'allEntitlementsIncludingRentSompi': all_entitlements,
            'stateRentSompi': 100_000_000,
            'permissionRentRefundSompi': 50_000_000, 'nativePrincipalPaidSompi': 400_000_000,
            'journals': journals, 'remainingIndependentRecoveryProven': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.evidence), indent=2))
