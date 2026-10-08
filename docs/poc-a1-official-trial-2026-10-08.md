# A1 official trial 2026-10-08 — autonomous S1 recovery after physical loss of A

Live run: **2026-10-08**, testnet-10 (TN10), test KAS only.
[PR #22](https://github.com/olafweller/kaspa-privacy-initiative/pull/22) remains draft.

**Result: PASS for the scoped scenario.** After the original machine A was
physically switched off, recovery machine B detected the loss through
independent machine C, rediscovered the live S1 reserve, generated a fresh
Groth16 proof, and the resulting terminal transaction paid out on TN10. No
human or A action was involved between power-off and payout.

This closes the **S1 autonomous-recovery scenario**. It does **not** close the
full G5/G6 gate set (see [Scope](#scope-what-this-does-and-does-not-show)).
[Attempt 1](poc-a1-live-attempt-1.md) and [attempt 2](poc-a1-live-attempt-2.md)
remain unchanged historical failures.

Run ID: `finite-cold-65b7dee37b3c4308a9f60e4f2a037353`.

## What happened, in plain terms

1. A locked 32.1 test KAS in a covenant (S0). The covenant only releases funds
   when spent with a valid zero-knowledge proof for the frozen A1 circuit.
2. A made a proof-gated continuation (S0 → S1): 4 test KAS paid out, 18.1 test
   KAS stayed locked as the S1 reserve.
3. A was switched off. C, an independent node/archive machine, measured that
   every monitored route to A had disappeared.
4. Only after C's independent loss boundary did B start. B had a pre-positioned
   encrypted owner backup, the public artifacts and the old S0 locator, but
   **no** S1 pointer or body from A. B rediscovered S1 from chain history
   retained by C, produced a fresh proof, validated the full transaction
   natively, and handed it to C, which broadcast it once.
5. TN10 accepted the payout of 8.1 test KAS. C confirmed acceptance twice,
   120.56 seconds apart.

## Transactions

| Step | Txid | Amounts (sompi) |
| --- | --- | --- |
| Funding / S0 | [`158a06aa…6623f`](https://tn10.kaspa.stream/transactions/158a06aaa00c8d93371e472d8f2d3fc340f3517ff4a8d2df329d15e862c6623f) | S0 reserve `3,210,000,000`; fee `1,000,204,700` |
| S0 → S1 continuation | [`52073b12…d7186`](https://tn10.kaspa.stream/transactions/52073b123ebef0c6d1e3966668c3676da5d258775cd7a4901931be54e90d7186) | S1 `1,810,000,000` + payout `400,000,000` + fee `1,000,000,000` |
| **Autonomous S1 terminal** | [`085f8fa5…0ff83`](https://tn10.kaspa.stream/transactions/085f8fa5a0439dc7cc30c851805f6e44e637b8b2fe2cac0d930a7da250f0ff83) | payout `810,000,000` + fee `1,000,000,000` |

Full txids, full hashes, accepting blocks and receipt hashes are in the
[public record](../poc/a1/evidence/official-trial-2026-10-08/public-record.json).
Recipient of both payouts:
`kaspatest:qq9yj8pss8x9kcvc8l6tcq7gsuk3f8mhrzs74vq7juskj8d5lhwx6e0ummdw7`.

Accounting: `3,210,000,000 = 1,210,000,000 to recipient + 2,000,000,000 fees`.
The fees are fixed experimental values chosen for guaranteed admission, not a
cost estimate (see [issue #23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23)).

## Timeline (UTC)

| Event | Time |
| --- | --- |
| S0 accepted, C independent confirmation | 06:00:27 |
| S1 accepted (C durable event); C loss detection armed; B armed | 06:00:53–06:00:54 |
| Operator alarm, then physical power-off of A | 06:01:46 → 06:02:08 (last A boot ended) |
| First C probe with all A routes absent | 06:02:08.789 |
| C loss boundary (ten consecutive absent samples) | 06:02:32.978 |
| B released, bound to C's loss digest | 06:02:33.666 |
| B fresh proof + native Full validation ready | 06:05:51.633 |
| Terminal accepted (accepting-block timestamp) | 06:05:58.189 |
| C initial / later acceptance observation | 06:07:33.003 / 06:09:33.559 |
| A powered on again; C records A return | 06:50:21.713 |

C measured continuous A absence for 2,889.9 seconds (≈48 minutes). The A
return after payout produced C's existing fail-closed "A became reachable"
fault record; it occurred 41 minutes after the later observation and does not
affect the completed payout.

## Scope: what this does and does not show

Demonstrated in this run:

- physical loss of A after an accepted S0 → S1, with B starting only after C's
  independent loss boundary;
- B's independent S1 discovery from the old S0 locator and C-retained history,
  without an S1 pointer from A;
- a fresh terminal proof, native Full validation, one broadcast, and TN10
  acceptance with exact payout, recipient and S1 spentness;
- C's later-observation interval of at least 120 seconds.

Not demonstrated:

- the full G5/G6 matrix: recovery from S0 (direct S0 exit after A loss), the
  competing-spend result, and archive/artifact-loss and adversarial cases in
  live conditions remain open per the [implementation plan](poc-a1-implementation-plan.md);
- independence from C: C remained the chain/archive source and broadcaster;
- any privacy property. A1 is a finite same-owner covenant. Amounts and
  recipients are public on chain. There are no notes, nullifiers, private
  transfers or relays;
- security, audit, production readiness, permanent finality, post-quantum
  security, or trust-free setup (single-party Groth16 setup).

## Runtime provenance

The run used the A1 runtime from the A1 work tree at
`575d0e93afdb9d5f522d9fd5500026f3ca2ba018` **plus local operational repairs that
are not yet in this repository**. These repairs were made during rehearsals and
before funding:

- one canonical integer-sompi representation for amount comparisons across A,
  B and C (an `int`/`str` mismatch had blocked the previous funded run);
- C's terminal confirmation scan starts from its sealed pre-funding checkpoint
  instead of a moving chain tip, keeping reorg detection;
- tolerant comparison of equivalent block-parent encodings from two node APIs;
- a larger evidence-reader limit and a 30-second journal sampling bound;
- 2 seconds of cross-host clock-skew tolerance in 37 freshness comparisons
  (maximum ages unchanged);
- C's B-peer discovery restricted to B's dedicated probe port.

Bounds on amounts, recipients, fees, proofs, replay, one-attempt submission and
the ≥120-second observation interval were not relaxed. The executed sources are
bound by hashes in the public record (role-sources and submit-claim source
hashes, plus a local source-snapshot hash). Consolidating these repairs into
the repository, with tests, is follow-up work. Until then, checking out this
branch alone does not reproduce the run.

## Rehearsals and earlier funded runs

Three rehearsals preceded this run on the same day. A stayed powered on and
all A routes were closed. Each produced an autonomous TN10 payout:
[`bd2b02e7…4b410`](https://tn10.kaspa.stream/transactions/bd2b02e7ee884fdece224f90c2c994fc87de122be08144292a421b8ce1f4b410),
[`6e0b0af8…9d927`](https://tn10.kaspa.stream/transactions/6e0b0af8c83e3884a274faf9a02c12b7ef13cebbd76280453251dcdb8129d927),
[`490be608…78b50`](https://tn10.kaspa.stream/transactions/490be6088f8f95b4598653ab027948a1008c07e20dd147ed094b9d6a9b078b50).
Their post-payout confirmation step failed for the three causes repaired above.

Between attempt 2 and these rehearsals, eight further funded live runs (6–7
October) did **not** complete autonomous recovery. They failed in orchestration,
capture or startup glue, not in the covenant or proof system. Their reserves
remain locked in their covenants unless noted (on-chain state checked
2026-10-08):

| S0 funding txid | Furthest stage | Reported cause | Reserve now |
| --- | --- | --- | --- |
| `3dc28adf…12606` | S1 accepted | not reconstructed for this record | S1 6.4 locked |
| `12a938b2…0711d` | S1 accepted | not reconstructed for this record | S1 6.4 locked |
| `5f0fdc65…a8c8a` | S0 accepted | capture failed before continuation | S0 32.1 locked |
| `2c58c9d1…9fd8f` | S0 accepted | continuation step failed (resource/path limits) | S0 32.1 locked |
| `ed1e7177…53c1e` | S1 accepted | missing directory in the recovery path | S1 18.1 locked |
| `ea698fc3…10ac2` | S1 accepted | C observer sampling deadline exceeded before B armed | S1 18.1 locked |
| `3d5ff090…1598c` | B recovery completed | B sandbox blocked the SDK's local loopback check | S1 18.1 locked |
| `d5626ab5…97c5b` | B recovery completed | C rejected payout: `int` vs `str` amount compare | exited by separate owner action, [`592c62fd…dc9f0`](https://tn10.kaspa.stream/transactions/592c62fd447b7ee7adc8238df678acb7a269b036f4677f28373f2d1c0e6dc9f0) |

All of these reserves are test KAS (131.3 test KAS locked in total). None were
retried within their run identity. Detailed causes and receipts are retained
in local operator records.

## Public evidence and limits

The [public record](../poc/a1/evidence/official-trial-2026-10-08/public-record.json)
contains public identifiers, accounting, timeline, and SHA-256 references to
retained private receipts. Claim secrets, recipient keys, backup/unlock
material, SSH credentials, infrastructure configuration and logs are withheld.
Hashes bind retained records. They are not independent proof of acceptance;
anyone can check acceptance via the linked TN10 transactions.

Next steps: map existing evidence to every G5/G6 criterion, run the S0-direct
recovery and competing-spend cases, and consolidate the runtime repairs into
the repository. This publication changes no protocol, invariant, ADR or prior
evidence.
