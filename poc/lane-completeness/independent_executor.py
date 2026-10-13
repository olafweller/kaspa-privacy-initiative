#!/usr/bin/env python3
"""Independent public-data executor. No Rust/guest code imported; no network writes.

Reconstructs accepted order, checks v1 IDs and lane endpoints. Its fixture anchor
is synthetic; a live run requires independently verified canonical node anchors.
"""
import hashlib
import json
import struct
import sys
from blake3 import blake3

ZERO = bytes(32)
OP = b"KPI-LANE-v1"
STATE = b"KPI-LANE-STATE-v1"

def H(domain, *parts):
    return blake3(b"".join(parts), key=domain.encode().ljust(32, b"\0")).digest()

def merkle(leaves):
    # Kaspa pads a missing right subtree with ZERO, rather than duplicating it.
    if not leaves:
        return ZERO
    while len(leaves) > 1:
        leaves = [H("SeqCommitmentMerkleBranchHash", leaves[i], leaves[i+1] if i+1 < len(leaves) else ZERO)
                  for i in range(0, len(leaves), 2)]
    return leaves[0]

def anchor(w, key, tip):
    leaf = H("SeqCommitActiveLeaf", tip, struct.pack("<Q", w["blue_score"]))
    current = H("SeqCommitActiveCollapsedNode", key, leaf)
    siblings = [bytes(s) for s in w["siblings"]]
    bitmap = bytes(w["bitmap"])
    # Kaspa uses ZERO as the empty leaf, then recursively hashes empty branches.
    empties = [ZERO]
    for _ in range(256):
        empties.append(H("SeqCommitActiveNode", empties[-1], empties[-1]))
    for d in reversed(range(w["depth"])):
        sibling = empties[255-d] if bitmap[d//8] & (1 << (d%8)) else siblings.pop()
        pair = (sibling, current) if key[d//8] & (0x80 >> (d%8)) else (current, sibling)
        current = H("SeqCommitActiveNode", *pair)
    assert not siblings, "unused SMT siblings"
    activity = H("SeqCommitActivityRoot", bytes(w["shortcut"]), current)
    sr = H("SeqCommitmentMerkleBranchHash", activity, bytes(w["payload_ctx"]))
    return H("SeqCommitmentMerkleBranchHash", bytes(w["parent_seq"]), sr)

def parse_rest(rest):
    pos = 0
    def take(n):
        nonlocal pos
        assert n >= 0 and pos+n <= len(rest), "truncated transaction"
        out = rest[pos:pos+n]; pos += n; return out
    def length():
        return int.from_bytes(take(8), "little")
    assert take(2) == b"\x01\x00", "not v1"
    count = length(); assert 0 < count <= len(rest)//52
    for _ in range(count):
        take(36); assert length() == 0; take(8)
    count = length(); assert 0 < count <= len(rest)//19
    for _ in range(count):
        take(10); take(length()); flag = take(1)
        assert flag in (b"\0", b"\1")
        if flag == b"\1": take(34)
    take(8); lane = take(20); take(8); assert length() == 0
    assert pos == len(rest), "trailing bytes"
    return lane

def lanes_root(entries, depth=0):
    if not entries:
        return ZERO
    if len(entries) == 1:
        return H("SeqCommitActiveCollapsedNode", *entries[0])
    assert depth < 256
    left = [e for e in entries if not e[0][depth//8] & (0x80 >> (depth%8))]
    right = [e for e in entries if e[0][depth//8] & (0x80 >> (depth%8))]
    # Empty subtrees use canonical depth-specific hashes when a branch exists.
    def subtree(group):
        if group: return lanes_root(group, depth+1)
        empty = ZERO
        for _ in range(255-depth): empty = H("SeqCommitActiveNode", empty, empty)
        return empty
    return H("SeqCommitActiveNode", subtree(left), subtree(right))

def reconstruct(fixture):
    assert fixture["kind"] == "SYNTHETIC_OFFLINE_NOT_TN10"
    lane = bytes.fromhex(fixture["lane"]); key = H("SeqCommitLaneKey", lane)
    tip = bytes.fromhex(fixture["old_tip"]); state = bytes.fromhex(fixture["old_state"])
    assert anchor(fixture["start_witness"], key, tip).hex() == fixture["start_seq"]
    numbers = []; last_score = fixture["start_witness"]["blue_score"]
    active = {bytes.fromhex(e["lane"]): (bytes.fromhex(e["tip"]), e["blue_score"]) for e in fixture["initial_active_lanes"]}
    parent_seq = bytes.fromhex(fixture["start_seq"])
    for b in fixture["blocks"]:
        assert b["blue_score"] > last_score; last_score = b["blue_score"]
        bodies = {t["id"]: t for t in b["bodies_in_arrival_order"]}
        assert len(bodies) == len(b["bodies_in_arrival_order"]), "duplicate body"
        assert len(set(b["accepted_ids"])) == len(b["accepted_ids"]), "duplicate accepted id"
        leaves = []; all_lanes = {}
        for idx, txid in enumerate(b["accepted_ids"]):
            t = bodies[txid]; payload = bytes.fromhex(t["payload"]); rest = bytes.fromhex(t["rest"])
            actual_lane = parse_rest(rest)
            assert actual_lane.hex() == t["lane"] and t["version"] == 1
            computed = H("TransactionV1Id", H("PayloadDigest", payload), H("TransactionRest", rest))
            assert computed.hex() == txid, "transaction/payload ID mismatch"
            leaf = H("SeqCommitActivityLeaf", computed, struct.pack("<HI", 1, idx))
            all_lanes.setdefault(actual_lane, []).append(leaf)
            if actual_lane != lane: continue
            leaves.append(leaf)
            if len(payload) == len(OP)+4 and payload.startswith(OP):
                numbers.append(int.from_bytes(payload[-4:], "little"))
                state = hashlib.sha256(STATE + state + payload).digest()
        context = H("SeqCommitMergesetContext", struct.pack("<QQQ", b["prev_timestamp"], b["daa_score"], b["blue_score"]))
        if leaves:
            tip = H("SeqCommitLaneTip", tip, key, merkle(leaves), context)
        for lid, activity in all_lanes.items():
            lk = H("SeqCommitLaneKey", lid)
            previous = active[lid][0] if lid in active else parent_seq
            active[lid] = (H("SeqCommitLaneTip", previous, lk, merkle(activity), context), b["blue_score"])
        root = lanes_root([(H("SeqCommitLaneKey", lid), H("SeqCommitActiveLeaf", t, struct.pack("<Q", bs))) for lid, (t, bs) in active.items()])
        miners = []
        for m in b["miners"]:
            work = bytes.fromhex(m["blue_work_be"]).lstrip(b"\0")
            miners.append(H("SeqCommitMinerPayloadLeaf", bytes.fromhex(m["hash"]), struct.pack("<Q", len(work)), work,
                            H("PayloadDigest", bytes.fromhex(m["payload"]))))
        pd = H("SeqCommitmentMerkleBranchHash", context, merkle(miners))
        ar = H("SeqCommitActivityRoot", ZERO, root)
        parent_seq = H("SeqCommitmentMerkleBranchHash", parent_seq, H("SeqCommitmentMerkleBranchHash", ar, pd))
        assert parent_seq.hex() == b["seq_commit"], "complete per-block reconstruction mismatch"
    seq = anchor(fixture["end_witness"], key, tip)
    assert seq.hex() == fixture["blocks"][-1]["seq_commit"], "canonical endpoint mismatch"
    expected = fixture["expected"]
    assert list(state) == expected["state"] and list(tip) == expected["tip"] and list(seq) == expected["seq"]
    return {"scope": "independent Python synthetic fixture reconstruction", "operations": numbers,
            "state": state.hex(), "lane_tip": tip.hex(), "seq_commit": seq.hex(), "endpoint_verified": True}

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        fixture = json.load(f)
    result = reconstruct(fixture)
    print(json.dumps(result, indent=2))
