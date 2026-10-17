#!/usr/bin/env python3
"""Offline cross-check of the retained live rehearsal; never signs or uses RPC.

Reuses the independent Python native-ID/lane and public-state codecs, not Rust
execution or proof reports. SDK cryptographic verification is a separate command.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'poc/lane-completeness/integration'))
from check_capture import reconstruct, transaction_id

spec = importlib.util.spec_from_file_location('native_audit', ROOT / 'poc/native-value/audit.py')
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unpack(raw):
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        members = archive.getmembers()
        assert all(m.isfile() and not Path(m.name).is_absolute()
                   and '..' not in Path(m.name).parts and Path(m.name).suffix not in {'.key', '.pem'}
                   for m in members)
        files = {m.name: archive.extractfile(m).read() for m in members}
        assert len(files) == len(members), 'duplicate archive member'
        return files


def verify(files, manifest):
    assert set(files) == set(manifest)
    for name, expected in manifest.items():
        assert len(files[name]) == expected['bytes'] and digest(files[name]) == expected['sha256'], name


def state_root(state):
    # Pinned core/smt/src/hashed_node.rs: leaf-domain byte || key || value_hash.
    return hashlib.sha256(b'\x01' + bytes([0x71]) * 32 + native.state_hash(state)).digest()


def expanded_header(header):
    # VirtualChainV2 uses run-length parent levels; getBlock expands each level.
    header = dict(header)
    parents = header['parentsByLevel']
    if parents and len(parents[0]) == 2 and type(parents[0][0]) is int:
        expanded = []
        for end_exclusive, hashes in parents:
            assert end_exclusive > len(expanded)
            expanded.extend([hashes] * (end_exclusive - len(expanded)))
        header['parentsByLevel'] = expanded
    return header


def audit(evidence):
    result = json.loads((evidence / 'tn10-rehearsal.json').read_text())
    raw = (evidence / result['artifactArchive']['path']).read_bytes()
    assert digest(raw) == result['artifactArchive']['sha256']
    assert len(raw) == result['artifactArchive']['bytes']
    outer = unpack(raw)
    manifest = json.loads(outer.pop('manifest.json'))
    verify(outer, manifest)
    public = unpack(outer['vps-public.tar.gz'])
    verify(public, json.loads(outer['vps-public.manifest.json']))
    read = lambda name: json.loads(public[name])
    identity = read('identity.json')
    lane, owner = bytes.fromhex(identity['lane']), identity['keys']['user']['owner']
    covenant = read('prepared.json')['covenantId']
    captures, bundles = {}, {}
    for label, capture_name, prepared in [
        ('prefix', 'prefix-capture.json', 'prefix-prepared'),
        ('final', 'catchup-capture.json', 'clean-executor/full-prepared'),
    ]:
        capture = read(capture_name)
        derived = reconstruct(capture, lane)
        bundle = json.loads(outer[prepared + '/bundle.json'])
        assert derived['ordered_transaction_ids'] == bundle['orderedIds']
        assert derived['seq_commit'] == bundle['anchorSeqCommit']
        assert derived['lane_tip'] == outer[label + '-proof/aggregate-journal.bin'][96:128].hex()
        try:
            reconstruct(capture, lane, omit=True)
        except ValueError as error:
            assert 'derived lane does not match fixed TN10 end anchor' in str(error), str(error)
        else:
            raise AssertionError('native omission accepted')
        state = json.loads(outer[prepared + '/state.json'])
        journal = outer[label + '-proof/aggregate-journal.bin']
        assert journal == outer[prepared + '/aggregate.journal.bin']
        assert state_root(state) == journal[64:96]
        balance = native.user_balance(state, owner)
        assert balance == bundle['spendableSompi'] == (1_000_000_000 if label == 'prefix' else 600_000_000)
        assert journal[160:192].hex() == covenant
        assert journal[320:352].hex() == capture['laneKey']
        # Inspect every prepared tx: its identity, global merge position and context
        # are independently derived from the complete raw accepted-chain response.
        records = {r['label']: json.loads(r['raw'])['params'] for r in capture['records']}
        parent_time = records['start-block']['block']['header']['timestamp']
        positions = {}
        for block in records['accepted']['chainBlockAcceptedTransactions'][:capture['intervalBlocks']]:
            header = block['chainBlockHeader']
            context = native.H('SeqCommitMergesetContext',
                               native.struct.pack('<QQQ', parent_time, header['daaScore'], header['blueScore']))
            for index, tx in enumerate(block['acceptedTransactions']):
                if tx['subnetworkId'] == lane.hex():
                    positions[transaction_id(tx).hex()] = (index, context)
            parent_time = header['timestamp']
        for batch in bundle['batches']:
            for stem in batch['transactions']:
                inp = json.loads(outer[prepared + '/' + stem + '.json'])
                tx_journal = outer[label + '-proof/' + stem + '-journal.bin']
                assert tx_journal == outer[prepared + '/' + stem + '.journal.bin']
                txid = tx_journal[2:34].hex()
                index, context = positions[txid]
                assert txid in derived['ordered_transaction_ids']
                assert inp['tx']['merge_idx'] == int.from_bytes(tx_journal[34:38], 'little') == index
                assert bytes(inp['context']) == tx_journal[38:70] == context
        captures[label] = derived
        bundles[label] = bundle
    prefix = outer['prefix-proof/aggregate-journal.bin']
    final = outer['final-proof/aggregate-journal.bin']
    omission = outer['omission-proof/aggregate-journal.bin']
    assert prefix[64:128] == final[:64] == omission[:64]
    assert final[128:160] != omission[128:160]
    assert omission[64:96] == prefix[64:96]
    om = json.loads(outer['clean-executor/omission-prepared/bundle.json'])
    assert om['anchorSeqCommit'] == bundles['final']['anchorSeqCommit'] and om['omittedTransactions'] == 1
    assert om['orderedIds'] == [] and len(bundles['final']['orderedIds']) == 1
    assert outer['clean-executor/reconstructed-prefix/state.json'] == outer['prefix-prepared/state.json']
    reconstruction = json.loads(outer['clean-executor/reconstruction.json'])
    assert reconstruction['originalAccountStateImported'] is False
    assert reconstruction['stateRoot'] == prefix[64:96].hex()
    fees = {}
    done, accounting = read('complete.json'), read('reconciliation.json')
    confirmations = {json.loads(r['raw'])['params']['block']['header']['hash']:
                     json.loads(r['raw'])['params']['block']
                     for r in read('reconciliation-rpc-v2.json') if r['method'] == 'getBlock'}
    for label in ['fund-fee', 'fund-user', 'seed', 'bootstrap', 'deposit',
                  'prefix-settlement', 'withdraw', 'final-settlement', 'payout']:
        built, request, accepted = (read(label + '-' + suffix + '.json')
                                    for suffix in ['transaction', 'request', 'accepted'])
        tx = built['transaction']
        assert transaction_id(tx).hex() == built['transactionId'] == transaction_id(accepted['transaction']).hex()
        block = confirmations[accepted['header']['hash']]
        assert block['verboseData']['isChainBlock']
        assert expanded_header(block['header']) == expanded_header(accepted['header'])
        inputs = {native.point(e['outpoint']): e['utxoEntry']['amount'] for e in request['utxos']['entries']}
        for name in ['covenantUtxo', 'permissionUtxo', 'delegateUtxo']:
            if name in request:
                e = request[name]; inputs[native.point(e['outpoint'])] = e['utxoEntry']['amount']
        fees[label] = sum(inputs[native.point(i['previousOutpoint'])] for i in tx['inputs']) - sum(o['value'] for o in tx['outputs'])
        assert fees[label] >= 0 and fees[label] == built['feeSompi'] == done['feesSompi'][label]
    for label, journal in [('prefix', prefix), ('final', final), ('omission', omission)]:
        assert outer[label + '-proof/aggregate-receipt.bin'] == public[label + '-receipt.bin']
        built = read(label + '-settlement-transaction.json')
        assert built['newState'] == journal[64:96].hex() and built['newTip'] == journal[96:128].hex()
    valid_req, omit_req = read('final-settlement-request.json'), read('omission-settlement-request.json')
    assert valid_req['end'] == omit_req['end'] and valid_req['covenantUtxo'] == omit_req['covenantUtxo']
    assert 'ZK Integrity: Verification failed' in read('omission-settlement-rejected.json')['reason']
    payout, request = read('payout-transaction.json'), read('payout-request.json')
    spent = {native.point(i['previousOutpoint']) for i in payout['transaction']['inputs']}
    assert native.point(request['permissionUtxo']['outpoint']) in spent
    assert (read('deposit-transaction.json')['transactionId'], 0) in spent
    outs = payout['transaction']['outputs']
    assert outs[0]['value'] == 450_000_000 and outs[0]['scriptPublicKey'] == '000020' + owner + 'ac'
    delegate = read('deposit-transaction.json')['transaction']['outputs'][0]
    assert delegate['value'] == 1_000_000_000 and outs[1]['value'] == 600_000_000
    assert outs[1]['scriptPublicKey'] == delegate['scriptPublicKey']
    assert done['paid']['utxoEntry']['amount'] == outs[0]['value'] and done['reserve']['utxoEntry']['amount'] == outs[1]['value']
    assert done['unpaidClaimsSompi'] == 0 and done['appSpendableSompi'] == done['reservedNativeSompi'] == 600_000_000
    assert read('payout-replay-rejected.json')['id'] != payout['transactionId']
    for attack in ['underpay', 'reserve', 'recipient']:
        assert 'script ran, but verification failed' in read('payout-' + attack + '-rejected.json')['reason']
    balances = {role: sum(e['utxoEntry']['amount'] for e in reply['entries'])
                for role, reply in accounting['balances'].items()}
    assert balances == accounting['balancesSompi']
    initial = sum(e['utxoEntry']['amount'] for e in read('fund-fee-request.json')['utxos']['entries'])
    assert initial == sum(balances.values()) + 100_000_000 + 600_000_000 + sum(fees.values())
    assert sum(fees.values()) == done['totalFeesSompi'] == 193_850_800
    stop_headers = [json.loads(r['raw'])['params']['block']['header'] for r in read('stop-job-rpc.json') if r['method'] == 'getBlock']
    gap = read('withdraw-accepted.json')['header']['blueScore'] - stop_headers[0]['blueScore']
    assert gap == 175 and gap > 100
    return {'scope': 'OFFLINE_RECORDED_L1_ORDER_STATE_AND_ACCOUNTING_AUDIT_NOT_NEW_CHAIN_OBSERVATION',
            'outerMembersVerified': len(manifest), 'publicVpsMembersVerified': len(public),
            'orderedInputsAndContexts': captures, 'confirmedTransactionCount': len(fees),
            'totalFeesSompi': sum(fees.values()), 'paidPrincipalSompi': 400_000_000,
            'refundedRentSompi': 50_000_000, 'remainingReserveSompi': 600_000_000,
            'remainingAccountBalanceSompi': 600_000_000, 'unpaidClaimsSompi': 0,
            'gapFromObservedStopTipBlueScores': gap, 'sameEndpointOmissionRejectedByNode': True,
            'cleanPublicReplayMatched': True, 'independentOperator': False, 'privacy': False,
            'zkVerification': 'Separate kpi-takeover-verify command; this Python audit is not a proof verifier.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.evidence), indent=2))
