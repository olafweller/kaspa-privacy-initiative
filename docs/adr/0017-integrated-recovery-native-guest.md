# ADR-0017: integrate partial and exact-reserve exits in a new guest

Status: Owner-requested local integration and execution qualification, 2026-10-19.
Extends [ADR-0016](0016-user-held-recovery-and-terminal-exit.md). No outer proving,
GPU rental, funding or broadcasting is included.

## Decision

Preserve PR54's actual TN10 instance and all PR55 source/artifact bindings.
Introduce a separate relation/guest and state resource/hash/transaction/batch
domains. Reuse the wallet circuit, parameters, VK, economic nullifiers, checked
BN254 backend, accepted-lane fold and native settlement ABI. There is no migration,
admin key, operator callback, new cryptographic arithmetic or change to old funds.

Admit one pending authorized exit against one reserve >= its amount. Keep its
liability and pinned reserve until its actual permission/payout transactions are
encountered in authenticated lane data. Commit the permission hash in the exit
journal. Detect the issued permission by covenant binding, exact script/rent and
native outpoint. A positive-change payout has three outputs; an exact-reserve
payout has two. Both require the fixed lane, permission/reserve/sponsor inputs,
full permission consumption, recipient principal+rent lower bound and separate
sponsor output. Reconcile by actual tracked outpoints even without honest tags;
never book an unreconciled accepted spend as an economic no-op. Remove an exhausted
reserve rather than inserting a zero-valued entry. Other reserves stay unchanged.

The new full-drain prefix reproduces PR55's locally reviewed native restrictions;
the positive-change prefix retains PR49's policy. The established upstream
permission verifier is unchanged. Its zero expected-change branch already exists.
Merely relaxing accounting while retaining old scripts is insufficient. Replacing
native checks with builder conventions or a host success flag is rejected.

## Local chain and proof boundary

Prepare six linked batches: deposit, credit/payment, Bob exit, Bob permission/
payout reconciliation, Alice exit, Alice permission/payout reconciliation. Reuse
public real wallet-proof fixtures from PR55, never original wallet secrets. Their
native chain context remains synthetic. Record both permission transaction IDs
before the reconciliation input is frozen; later genuine receipt-bearing issuance
must have those same IDs. Transaction IDs omit signature witnesses, allowing this
preparation without a fabricated receipt. Native permission issuance acceptance
is NOT established by a synthetic covenant-bound UTXO or CPU execution alone.

The new program ID must be pinned before measurement. Compile full expected
journals into the independent receipt verifier; reject old receipts and dev mode.
A prepared genuine-receipt issuance check must verify the new receipt and actual
native state/permission scripts before claiming that milestone. No new outer
receipt is generated in this task.

## Finite measurement and remaining live work

The checked-in measurement plan precedes execution: 160M user cycles and 900
seconds per case, four CPU threads, 3,600 seconds across the entire campaign.
Explicit semantic errors alone count as rejection; resource failures do not.
No automatic retry or budget extension. Record the full journals, cycles,
segments, timings and resources. This does not revise prior comparison results.

A future funded trial needs a fresh native bootstrap/outpoint/covenant whose state
script pins this new program from inception. Its actual chain inputs need their
own proofs. The old PR54 reserve remains under the old guest, including its old
positive-change limitation. Independent user administration, replaceable public
data/proving services, current-chain/UTXO anchoring and the N-user shutdown gate
remain separate qualifications. A later bounded outer-proof proposal retains the
existing aggregate hour and two-hour lease, subject to separate release.
