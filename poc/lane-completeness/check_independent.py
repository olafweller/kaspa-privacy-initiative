#!/usr/bin/env python3
"""Reproduce adversarial checks of the separate public-data executor."""
import copy
import json
import pathlib
import sys
from independent_executor import OP, reconstruct

p = pathlib.Path(sys.argv[1])
fixture = json.loads(p.read_text())
reconstruct(fixture)
results = {}

def reject(name, mutate):
    bad = copy.deepcopy(fixture)
    mutate(bad)
    try:
        reconstruct(bad)
    except (AssertionError, KeyError, IndexError) as e:
        results[name] = {"rejected": True, "error": str(e)}
    else:
        raise AssertionError(name + " unexpectedly accepted")

def omit(bad):
    for block in bad["blocks"]:
        bodies = {b["id"]: b for b in block["bodies_in_arrival_order"]}
        block["accepted_ids"] = [txid for txid in block["accepted_ids"]
            if bytes.fromhex(bodies[txid]["payload"]) not in [OP+n.to_bytes(4, "little") for n in (3,6,9)]]

reject("omit_3_6_9_same_anchor", omit)
reject("reorder_accepted_ids", lambda b: b["blocks"][0]["accepted_ids"].reverse())
reject("missing_body", lambda b: b["blocks"][0]["bodies_in_arrival_order"].pop())
reject("corrupted_payload", lambda b: b["blocks"][0]["bodies_in_arrival_order"][0].update(payload="ff"))
reject("wrong_start_tip", lambda b: b.update(old_tip="00"*32))
reject("wrong_smt_sibling", lambda b: b["end_witness"]["siblings"][0].__setitem__(0, b["end_witness"]["siblings"][0][0] ^ 1))
print(json.dumps(results, indent=2))
