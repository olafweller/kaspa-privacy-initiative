#!/usr/bin/env python3
"""G3 native-receipt/scanner coupling; imported S0 checkpoint, NOT G5 recovery.

Reads only receipts exported by actual TestConsensus storage/virtual processing.
The logical rollback-only accounting observation is NOT a native globally
unspent intermediate S0 observation: native reorg installs its alternative.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from a1_check import require, load_json
from a1_recovery import Scanner, native_callback, rpc_spk, rpc_uint


def groups(receipts, blocks):
    require([x['accepting_block'] for x in receipts] == blocks, 'native acceptance group/path mismatch')
    result = []
    for group in receipts:
        indexed = {(mb['block_hash'], tx['index_within_block']): tx['transaction_id']
                   for mb in group['acceptance_data'] for tx in mb['accepted_transactions']}
        bodies = []
        require(len(indexed) == len(group['accepted_bodies']), 'native accepted body completeness')
        seen = set()
        for receipt in group['accepted_bodies']:
            source = (receipt['source_block'], receipt['index_within_block'])
            require(source not in seen, 'duplicate native accepted source/index')
            seen.add(source)
            require(indexed.get(source) == receipt['txid'], 'body source/index not natively accepted')
            tx = copy.deepcopy(receipt['transaction'])
            require(tx['id'] == receipt['txid'], 'stored body/acceptance ID disagreement')
            tx['verboseData'] = {'transactionId': receipt['txid'], 'hash': receipt['full_hash']}
            bodies.append(tx)
        require(seen == set(indexed), 'missing native accepted source/index')
        result.append({'chainBlockHeader': {'hash': group['accepting_block']}, 'acceptedTransactions': bodies})
    return result


def page(start, added, removed, accepted):
    return {'startHash': start, 'response': {'removedChainBlockHashes': removed,
        'addedChainBlockHashes': added, 'chainBlockAcceptedTransactions': accepted}}


def inventory(native):
    return {(outpoint['transactionId'], outpoint['index']): entry for outpoint, entry in native}


def reconcile(scanner, native, horizon):
    utxos = [{'transaction_id': outpoint['transactionId'], 'index': str(outpoint['index']),
              'value': str(entry['amount']), 'spk_hex': rpc_spk(entry['scriptPublicKey']).hex(),
              'covenant': entry['covenantId']} for outpoint, entry in native]
    return scanner.reconcile_utxos(utxos, horizon)


def run(race, manifest, artifact_hash, callback):
    require(race['receipt_schema'] == 'kpi-a1-native-reorg/v1', 'missing real native receipts')
    point = race['original_outpoint']; s0 = manifest['states']['s0']
    require(rpc_uint(race['original_input_entry']['amount']) == int(s0['R']) and
            rpc_spk(race['original_input_entry']['scriptPublicKey']).hex() == s0['spk_hex'], 'native checkpoint terms mismatch')
    locator = {'network': manifest['network'], 'genesis_hex': manifest['genesis_hex'], 'instance_hex': manifest['instance_hex'],
        's0_txid_hex': point['transactionId'], 's0_index': str(point['index']), 's0_amount': s0['R'],
        's0_spk_hex': s0['spk_hex'], 's0_covenant': None, 'scan_start_hash': race['synthetic_genesis_hash'],
        'scan_start_blue_score': '0', 'scan_start_daa_score': '0', 'artifact_index_sha256': artifact_hash}
    initial = race['initial_chain_blocks']; added = race['added_chain_blocks']; removed = race['removed_chain_blocks']
    require(initial and added and removed, 'native real removal/reapplication required')
    first = page(locator['scan_start_hash'], initial, [], groups(race['initial_chain_acceptance_data'], initial))
    reorg = page(initial[-1], added, removed, groups(race['new_chain_acceptance_data'], added))
    scanner = Scanner(locator, manifest, callback, artifact_hash)
    before = scanner.page(first, initial[-1])
    reconcile(scanner, race['before_reorg_virtual_utxos'], initial[-1])
    require(len(before['transitions']) == 1 and before['transitions'][0]['txid'] == race['winner_txid'], 'scanner/native initial winner disagree')
    native_before = inventory(race['before_reorg_virtual_utxos']); native_after = inventory(race['after_reorg_virtual_utxos'])
    original = (point['transactionId'], point['index'])
    require(original not in native_before and original not in native_after, 'native original must remain spent across atomic alternative replacement')
    # Inspect logical rollback independently before replaying the replacement;
    # this is an accounting/pointer observation, not an intermediate UTXO claim.
    retained = [h for h in initial if h not in removed]
    rollback_horizon = retained[-1] if retained else locator['scan_start_hash']
    rollback = scanner.page(page(initial[-1], [], removed, []), rollback_horizon)
    require(rollback['state'] == 's0' and tuple(rollback['current_outpoint']) == original and rollback['paid'] == rollback['fees'] == '0', 'orphan paid/fees/pointer not rolled back')
    after = scanner.page(page(rollback_horizon, added, [], reorg['response']['chainBlockAcceptedTransactions']), added[-1])
    reconcile(scanner, race['after_reorg_virtual_utxos'], added[-1])
    require(len(after['transitions']) == 1 and after['transitions'][0]['txid'] == race['loser_txid'], 'alternate not replayed exactly once')
    require(not any(p[0] == race['winner_txid'] for p in native_after), 'orphan payout/reserve survived actual native UTXO rollback')
    atom = Scanner(locator, manifest, callback, artifact_hash)
    atom.page(first, initial[-1]); atomic_after = atom.page(reorg, added[-1])
    require(atomic_after == after, 'atomic native chain-path replay differs from rollback/reapply accounting')
    require(not after['lineage_history_complete'], 'imported checkpoint must not masquerade as G5 funding recovery')
    return {'winner_txid': race['winner_txid'], 'alternate_txid': race['loser_txid'],
        'initial': before, 'logical_rollback_before_alternate': rollback, 'after_atomic_native_reorg': after,
        'removed_count': len(removed), 'added_count': len(added), 'native_original_remains_spent': True,
        'native_old_winner_outputs_absent': True, 'native_final_utxos_reconciled': True,
        'rollback_and_atomic_replay_agree': True, 'funding_lineage_recovery_demonstrated': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--stateful', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--reference-binary', type=Path, required=True)
    args = parser.parse_args()
    manifest = load_json(args.bundle / 'manifest.json')
    approved = load_json(args.bundle / 'independent-checker-report.json')
    require(approved['parameter_consistency'] is True, 'independent parameter inspection required')
    races = load_json(args.stateful)
    artifact_hash = hashlib.sha256((args.bundle / 'manifest.json').read_bytes()).hexdigest()
    outcomes = {}
    for name in ('continue_vs_continue', 'continue_vs_terminal'):
        race = races[name]; point = race['original_outpoint']
        entries = {point['transactionId'] + ':' + str(point['index']): race['original_input_entry']}
        outcomes[name] = run(race, manifest, artifact_hash, native_callback(args.binary, args.reference_binary, entries))
    print(json.dumps({'schema': 'kpi-a1-native-reorg-scanner/v1',
        'scope': 'G3 offline real native DAG receipts coupled to recovery scanner from imported S0 checkpoint; no G5 funding recovery, public TN10 or machine loss.',
        'stateful_receipt_sha256': hashlib.sha256(args.stateful.read_bytes()).hexdigest(),
        'reorgs': outcomes}, indent=2))


if __name__ == '__main__':
    main()
