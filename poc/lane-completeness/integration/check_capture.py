#!/usr/bin/env python3
"""Independent Python reconstruction of a native TN10 RPC capture, without Rust.

Uses the retained Python hash/merkle implementation, not its synthetic-only entry
point. No network, signing, development receipts or zk proof verification.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from independent_executor import H, merkle, ZERO


def require(condition, message):
    if not condition:
        raise ValueError(message)


def u64(n):
    return struct.pack('<Q', n)


def blob(data):
    return u64(len(data)) + data


def transaction_id(t):
    version = t['version']
    require(version in (0, 1), 'unsupported transaction version')
    pre = struct.pack('<H', version) + u64(len(t['inputs']))
    for i in t['inputs']:
        pre += bytes.fromhex(i['previousOutpoint']['transactionId'])
        pre += struct.pack('<I', i['previousOutpoint']['index']) + blob(b'') + u64(i['sequence'])
    pre += u64(len(t['outputs']))
    for o in t['outputs']:
        spk = bytes.fromhex(o['scriptPublicKey'])
        require(len(spk) >= 2, 'truncated script public key')
        pre += u64(o['value']) + spk[:2] + blob(spk[2:])
        if version == 1:
            covenant = o['covenant']
            pre += bytes([covenant is not None])
            if covenant is not None:
                pre += struct.pack('<H', covenant['authorizingInput']) + bytes.fromhex(covenant['covenantId'])
    pre += u64(t['lockTime']) + bytes.fromhex(t['subnetworkId']) + u64(t['gas'])
    payload = bytes.fromhex(t['payload'])
    if version == 0:
        return hashlib.blake2b(pre + blob(payload), key=b'TransactionID', digest_size=32).digest()
    return H('TransactionV1Id', H('PayloadDigest', payload), H('TransactionRest', pre + blob(b'')))


def anchor(proof, key, lane):
    data = bytes(proof['smtProof'])
    require(len(data) >= 33, 'truncated SMT proof')
    bitmap, tag = data[:32], data[32]
    position = 33
    foreign = None
    if tag == 0:
        depth = 256
    else:
        require(tag in (1, 2) and len(data) >= 34, 'invalid SMT terminal')
        depth = data[33]; position = 34
        if tag == 2:
            require(len(data) >= 98, 'truncated conflicting leaf')
            foreign = data[34:66], data[66:98]; position = 98
    require((len(data) - position) % 32 == 0, 'SMT trailing bytes')
    siblings = [data[p:p+32] for p in range(position, len(data), 32)]
    require(len(siblings) == sum(not (bitmap[d//8] & (1 << (d%8))) for d in range(depth)), 'SMT sibling count')
    current = ZERO
    if lane is not None:
        tip, score = lane
        current = H('SeqCommitActiveCollapsedNode', key, H('SeqCommitActiveLeaf', tip, u64(score)))
    elif foreign is not None and foreign[0] != key:
        current = H('SeqCommitActiveCollapsedNode', *foreign)
    empties = [ZERO]
    for _ in range(256):
        empties.append(H('SeqCommitActiveNode', empties[-1], empties[-1]))
    for d in reversed(range(depth)):
        sibling = empties[255-d] if bitmap[d//8] & (1 << (d%8)) else siblings.pop()
        pair = (sibling, current) if key[d//8] & (0x80 >> (d%8)) else (current, sibling)
        current = H('SeqCommitActiveNode', *pair)
    activity = H('SeqCommitActivityRoot', bytes.fromhex(proof['inactivityShortcut']), current)
    state_root = H('SeqCommitmentMerkleBranchHash', activity, bytes.fromhex(proof['payloadAndCtxDigest']))
    return H('SeqCommitmentMerkleBranchHash', bytes.fromhex(proof['parentSeqCommit']), state_root)


def reconstruct(capture, subnet, omit=False):
    require(capture['kind'] == 'TN10_NATIVE_JSON_RPC_CAPTURE_V1' and capture['failure'] is None, 'incomplete capture')
    records = {r['label']: json.loads(r['raw'])['params'] for r in capture['records']}
    require(len(records) == len(capture['records']), 'duplicate record')
    for name in ['server-before', 'server-after']:
        require(records[name]['networkId'] == 'testnet-10' and records[name]['isSynced'], 'wrong network or unsynchronized node')
    key = H('SeqCommitLaneKey', subnet)
    require(key.hex() == capture['laneKey'], 'wrong lane key')
    start = records['start-block']['block']; end = records['end-block']['block']
    require(start['verboseData']['isChainBlock'] and end['verboseData']['isChainBlock'], 'orphan endpoint')
    def lane(p):
        return None if p['lane'] is None else (bytes.fromhex(p['lane']['tip']), p['lane']['blueScore'])
    sp, ep = records['start-proof'], records['end-proof']
    start_seq = bytes.fromhex(start['header']['acceptedIdMerkleRoot'])
    end_seq = bytes.fromhex(end['header']['acceptedIdMerkleRoot'])
    require(anchor(sp, key, lane(sp)) == start_seq, 'start witness mismatch')
    require(anchor(ep, key, lane(ep)) == end_seq, 'end witness mismatch')
    for name, block in [('start-proof', start), ('end-proof', end)]:
        request = next(r['request'] for r in capture['records'] if r['label'] == name)
        require(request == {'blockHash': block['header']['hash'], 'laneKey': key.hex()}, 'proof request binding')
    response = records['accepted']; recheck = records['accepted-recheck']
    require(not response['removedChainBlockHashes'] and not recheck['removedChainBlockHashes'], 'reorg capture')
    count = capture['intervalBlocks']
    blocks = response['chainBlockAcceptedTransactions'][:count]
    require(len(blocks) == count and blocks == recheck['chainBlockAcceptedTransactions'][:count], 'unstable/truncated interval')
    current = lane(sp); prev_seq = start_seq; prev_time = start['header']['timestamp']
    prev_score = start['header']['blueScore']
    state = hashlib.sha256(b'KPI-LANE-STATE-v1').digest()
    ids = []; operations = []; seen = set(); omitted = False
    for n, b in enumerate(blocks):
        header = b['chainBlockHeader']
        require(header['hash'] == response['addedChainBlockHashes'][n] and header['blueScore'] > prev_score, 'chain order')
        leaves = []
        for idx, tx in enumerate(b['acceptedTransactions']):
            txid = transaction_id(tx)
            require(txid.hex() == tx['verboseData']['transactionId'], 'transaction/payload ID mismatch')
            require(txid not in seen, 'duplicate accepted transaction'); seen.add(txid)
            if tx['subnetworkId'] != subnet.hex():
                continue
            if omit and not omitted:
                omitted = True; continue
            leaves.append(H('SeqCommitActivityLeaf', txid, struct.pack('<HI', tx['version'], idx)))
            ids.append(txid.hex())
            payload = bytes.fromhex(tx['payload'])
            if len(payload) == 15 and payload.startswith(b'KPI-LANE-v1'):
                operations.append(int.from_bytes(payload[11:], 'little'))
                state = hashlib.sha256(b'KPI-LANE-STATE-v1' + state + payload).digest()
        if leaves:
            require(current is None or header['blueScore'] - current[1] <= 432000, 'unsupported reactivation')
            parent = prev_seq if current is None else current[0]
            context = H('SeqCommitMergesetContext', struct.pack('<QQQ', prev_time, header['daaScore'], header['blueScore']))
            current = H('SeqCommitLaneTip', parent, key, merkle(leaves), context), header['blueScore']
        prev_time = header['timestamp']; prev_seq = bytes.fromhex(header['acceptedIdMerkleRoot']); prev_score = header['blueScore']
    require(blocks[-1]['chainBlockHeader']['hash'] == end['header']['hash'] and prev_seq == end_seq, 'end block mismatch')
    require(not omit or omitted, 'no applicable omission')
    require(anchor(ep, key, current) == end_seq, 'derived lane does not match fixed TN10 end anchor')
    require(current == lane(ep), 'derived lane entry mismatch')
    return {'lane_tip': None if current is None else current[0].hex(), 'seq_commit': end_seq.hex(),
            'ordered_transaction_ids': ids, 'recognized_kpi_operations': operations, 'state_from_initial_domain': state.hex()}


if __name__ == '__main__':
    source = json.loads(Path(sys.argv[1]).read_text())
    subnet = bytes.fromhex(sys.argv[2])
    result = reconstruct(source, subnet)
    try:
        reconstruct(source, subnet, omit=True)
    except ValueError as error:
        negative = {'rejected': True, 'reason': str(error)}
    else:
        raise ValueError('omission accepted')
    print(json.dumps({'scope': 'INDEPENDENT_PYTHON_LIVE_CAPTURE_NOT_ZK', 'valid': result, 'omission': negative}, indent=2))
