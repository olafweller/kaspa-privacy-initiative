#!/usr/bin/env python3
"""Independent hashlib tag oracles over actual generated A1 context bytes.

No production encoder/compiler imports. Private secret bytes are read locally
and are never included in output. Output tags and contexts are public test data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct

BRANCHES = ("s0_continue", "s0_terminal", "s1_terminal")
AMOUNTS = ("R", "L", "B", "fee", "next_R", "next_L", "next_B")


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs)


def hex_bytes(value):
    if not isinstance(value, str) or len(value) % 2 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("canonical lowercase hex required")
    return bytes.fromhex(value)


def records(context):
    if len(context) < 177 or context[:22] != b"KPI-A1/TN10/finite/v1\0":
        raise ValueError("context prefix/length")
    offset = 177
    result = []
    for _ in range(context[176]):
        if offset + 12 > len(context):
            raise ValueError("truncated output record")
        size = struct.unpack_from("<I", context, offset + 8)[0]
        end = offset + 12 + size + 1
        if size < 3 or end > len(context) or context[end - 1] != 0:
            raise ValueError("SPK/metadata shape")
        result.append((offset, offset + 8, offset + 12, end - 1, end))
        offset = end
    if offset != len(context) or len(result) not in (1, 2):
        raise ValueError("record count/trailing context")
    return result


def mutations(context):
    # Exact offsets are frozen in ADR-0003, not imported from a KPI encoder.
    changes = [("domain", 0), ("genesis", 22), ("instance", 54),
               ("stage", 86), ("mode", 87), ("claim_commitment", 88)]
    changes += [(name, 120 + 8 * index) for index, name in enumerate(AMOUNTS)]
    changes.append(("output_count", 176))
    rows = records(context)
    for index, (start, size, spk, metadata, _) in enumerate(rows):
        changes += [(f"output_{index}_value", start), (f"output_{index}_spk_length", size),
                    (f"output_{index}_spk_version", spk + 1),
                    (f"output_{index}_script", spk + 2),
                    (f"output_{index}_metadata", metadata)]
    result = []
    for name, offset in changes:
        changed = bytearray(context)
        changed[offset] ^= 1
        result.append((name, bytes(changed)))
    if len(rows) == 2:
        first, second = rows
        result.append(("output_order", context[:177] + context[second[0]:second[4]] + context[first[0]:first[4]]))
    return result


def tag(context, secret, txid, index):
    return hashlib.sha256(context + secret + txid + struct.pack("<I", index)).hexdigest()


def build(bundle, secret_path):
    manifest = load(bundle / "manifest.json")
    secret = Path(secret_path).read_bytes()
    if len(secret) != 32 or hashlib.sha256(secret).hexdigest() != manifest["claim_commitment_hex"]:
        raise ValueError("private claim backup mismatch")
    report = {"schema": "kpi-a1-context-oracle/v1", "source": "independent-python-hashlib-no-production-imports", "branches": {}}
    for branch in BRANCHES:
        context = hex_bytes(manifest["branches"][branch]["context_hex"])
        if context[88:120].hex() != manifest["claim_commitment_hex"]:
            raise ValueError("context claim commitment differs")
        transaction = load(bundle / (branch + ".transaction.json"))
        previous = transaction["inputs"][0]["previousOutpoint"]
        txid = hex_bytes(previous["transactionId"])
        index = int(previous["index"])
        if len(txid) != 32 or not 0 <= index <= 0xffffffff:
            raise ValueError("outpoint width")
        values = [{"name": name, "context_hex": changed.hex(), "tag_hex": tag(changed, secret, txid, index), "wrong_secret": False}
                  for name, changed in mutations(context)]
        wrong_secret = bytes([secret[0] ^ 1]) + secret[1:]
        values.append({"name": "wrong_secret_original_C", "context_hex": context.hex(),
                       "tag_hex": tag(context, wrong_secret, txid, index), "wrong_secret": True})
        report["branches"][branch] = {"context_hex": context.hex(), "context_sha256": hashlib.sha256(context).hexdigest(),
            "txid_hex": txid.hex(), "index": str(index), "original_tag_hex": tag(context, secret, txid, index), "mutations": values}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("secret", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = (json.dumps(build(args.bundle, args.secret), indent=2, sort_keys=True) + "\n").encode()
    # Exclusive creation: never overwrite a retained reviewer oracle.
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
    print(json.dumps({"oracle_written": True, "branches": 3, "private_material_in_output": False}))


if __name__ == "__main__":
    main()
