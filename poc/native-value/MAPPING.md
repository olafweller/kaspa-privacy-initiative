# Native-value based-app integration map

Reviewed 2026-10-17 UTC. PR31 baseline: `68100588133175442dab2b0a56ed6d784dc015ea`.
The full reference runtime is not assumed necessary or unnecessary for production.
This experiment tests a narrow compatible combination, not architecture acceptance.

## Exact source revisions

- vProgs [f9b84a863a7c7c20586a9cf947550475e894f72e](https://github.com/kaspanet/vprogs/tree/f9b84a863a7c7c20586a9cf947550475e894f72e): current default branch checked again.
- KIPs [e4ae2332117b5cb68bd6188e065ef885b6d17939](https://github.com/kaspanet/kips/tree/e4ae2332117b5cb68bd6188e065ef885b6d17939): current default branch.
- Kaspa docs [0ac77d043a802fc8196abfd5812ac2afbd97a2b9](https://github.com/kaspanet/docs/tree/0ac77d043a802fc8196abfd5812ac2afbd97a2b9): current default branch.
- Rusty Kaspa current master explicitly checked with `git ls-remote origin HEAD refs/heads/master`:
  [f7d7877363fb97c2ec6871be0e8cbc351d44df10](https://github.com/kaspanet/rusty-kaspa/tree/f7d7877363fb97c2ec6871be0e8cbc351d44df10).
  All experiment dependencies remain locked to the compatible 2.1.0 source
  [01b532e8b553523216471682649693af92f0fd16](https://github.com/kaspanet/rusty-kaspa/tree/01b532e8b553523216471682649693af92f0fd16).
  The local clone's plain `git fetch origin` follows its tag refspec and sets FETCH_HEAD
  to v2.1.0; FETCH_HEAD alone is **not** the current-master check.
- Real proving: RISC Zero 3.0.3, official local r0vm, v1compat kernel 2.2.2;
  exact transitive versions are in the separate host and guest lockfiles. SDK
  verification and native precompile verification are both required.

Source links below are at the vProgs commit above unless otherwise indicated.
"Tests exist" means inspected source tests, not a claim that upstream ran them
or that its development-mode demo performed real proof verification.

## Mechanisms and enforcement

| Mechanism / exact source | Implemented upstream and source tests | Small KPI adapter / enforcement location | TN10 obligation |
| --- | --- | --- | --- |
| Native deposit [action/deposit.rs][D], [deposit_policy.rs][DP], [tx_inputs.rs][TI] | Reads current transaction output amount/SPK through its ID-bound v1 preimage; derives delegate P2SH from config covenant; binds user identity to initial lock; checked-add and same-output dedup. Runtime e2e and `tn10-runtime/tests/runtime_actions.rs` exercise deposit. | **Guest:** reuse runtime executor and policy unchanged. Derive immutable config from actual covenant; disable config/admin actions. Extra wrapper rejects foreign covenant-bound funding outputs, records credited `(txid,index)`, authenticates complete prior public state. **L1:** actual acceptance establishes funding existence/value; the guest does not validate PoW itself. | Confirm actual 10-test-KAS delegate output, zero initial app balance, one credit; reject fake/double credits. |
| Ordered data [l1/bridge/src/worker.rs][B], [KIP-21][K], [batch verifier][BV] | Bridge retrieves ordered accepted activity; verifier rebuilds activity and lane tips, including failed app operations. General verifier supports lane expiry. | **Guest:** retained PR31 lane relation rebuilds IDs, accepted `merge_idx`, contexts, lane tip and SMT-derived seqcommit. **Host only:** raw capture, stable selected-chain recheck and reorg observation. Reuse actual L1 ordering; no new sequencer/relayer prerequisite. The bridge feeding data is not the native-value bridge. | All four commands remain committed, including unauthorized/replayed no-ops. Short continuously active intervals only. |
| Batch chaining [aggregate verifier][AV] | Checks previous/new state, tips, lane, images, covenant and blue-score carry; derives final seqcommit from lane proof. | **Guest:** canonical full public resource map hash equals old state; journal binds new map/tip and actual covenant. **Covenant:** consumes current state UTXO and reconstructs exact successor SPK; **L1:** prohibits reuse of spent state inputs. This monolithic route proves actions directly, rather than claiming recursive guest execution. | Settle a correct prefix then the rest, preserving state/tip continuity; same-anchor omission must fail native verification. |
| Proof/journal [state transition ABI][ABI], [covenant script][C] | 352-byte journal binds old/new state/tips, final seqcommit, covenant, image identities, permission hash, deposit hash and lane key. Production RISC0 verifier checks image, claim and assumptions. | Reuse adapted PR31 **covenant**, default fixed official lift-20 control pin and allowed-control root. New guest image, new domain pins, sponsored permission rent. Operational guest padding helps short batches use lift-20; its host-supplied cycle counter is **never** a validity condition. Actual profiles and real receipt identity remain mandatory. | Real receipts only; exact journal reconstruction; current TN10 precompile accepts valid state and rejects omitted-input receipt at the authentic end anchor. |
| Withdrawal [action/withdraw.rs][W], [auth.rs][AUTH], [signer_variants.rs][SIGN] | Runtime authorizes user's lock, minimum amount, checked-sub, emits recipient/amount exit. Supports signatures and spent-P2PK prev-tx witnesses. | **Guest:** reuse Withdraw and prev-tx witness authentication unchanged; binds exact user and recipient, records request ID; failed commands atomically discard effects. **L1:** validates the owner signature over the carrying transaction, including its payload. A copied witness with another funding input cannot authorize the user. | Real 4-test-KAS request, overdraw/unauthorized/replay tests; receiver alteration must fail an authentic check. |
| Exit permission [permission_tree.rs][PT], [permission_script.rs][PS], [delegate_script.rs][DS] | Guest commits exit Merkle root as permission-script hash. Settlement pins permission output/rent. Permission checks leaf, destination, deduct, updated root/count, delegate sum/change and final rent refund. Delegate script requires matching covenant-authorized permission input/suffix. Source `permission_spend.rs` tests script acceptance and payout/reserve mutations with the native engine. | Reuse exact **upstream** permission/delegate code via pinned dependencies. Small **host builder** constructs single-leaf claim spend, sponsors fee, measures native input budgets and signs only sponsor input. **L1 scripts and UTXO consensus**, not an operator key, authorize actual reserve release and claim consumption. | Confirm payout from the deposit's own delegate output, 6 test-KAS delegate change, spent permission, balanced underpayment/recipient/reserve negatives and distinct claim replay. |
| Backing and fees [deposit][D], [withdraw][W], [permission][PS] | Deposit credits authentic value, withdrawal moves balance into permission liability; permission consumes delegate value with exact change. State-covenant principal is carried forward; permission rent is settler-funded. | **Guest/action:** explicit u64 checked arithmetic. **Covenant/L1:** actual output and spentness rules. **Independent evidence audit:** sum spendable balances + unspent claims versus delegate reserve, using exact integer sompi. Fee quotes may be floating point upstream; principal and final fees are checked integer values, never rounded. | Show 0+0<=0; 10+0<=10; 6+4<=10 until payout; 6+0<=6 afterward. Keep 1-test-KAS state rent, 0.5 permission rent and transaction fees separate. |

## Checkpoints and progress

The operator chooses the seeded start and captured end blocks. After the first
settlement, the current covenant fixes the next old state and lane tip. The proof
must extend that tip with the claimed ordered input; it cannot silently replace
an old state or filter invalid app commands out of the lane commitment.

An end block must satisfy [the KIP-21 accessor conditions][KA]: known,
selected-parent-chain visible from validation, post-activation semantics and
inside the finality-based access window. This is **not** a requirement to use the
latest available block, a minimum batch count, an elapsed-time deadline or a
promise of continuous processing. No mandatory latest-endpoint rule was found
in the inspected guest, settlement covenant or L1 opcode. The runtime scheduler
choosing ready work does not turn its choice into such an L1 rule.

A correct prefix is therefore permitted while later accepted commands wait. The
experiment deliberately uses that permission. Its original three-command final
batch profiled as `[20,17]` segments and was resegmented **before any proof or
settlement**, retaining the same endpoints over the combined interval and every
command. No guest/verifier check or funded identity changed. This is an operator
batch-size choice, not censorship resistance or mandatory progress.

Another executor needs the current covenant UTXO and exact guest/program/domain
pins, authenticated public resource state matching its hash, ordered input bodies
and witnesses from its settled tip to a usable recent checkpoint, proving tools,
claim witnesses and independent fee/submission access. A state root alone does
not reconstruct those bytes. No original operator signature is needed by the
settlement or payout scripts, but takeover after data loss/pruning, automatic
rollback, arbitrary lane expiry and independent recovery are **not demonstrated**.

## Why this runtime subset

The retained fold alone cannot authenticate user balances or native exits. The
upstream account-action executor, deposit policy, transaction ABI, permission
accumulator and scripts provide that missing bridge logic. They run inside one
new monolithic guest with PR31's existing lane authentication. The full resource
SMT/scheduler/recursive proof hierarchy is unnecessary for this complete small
public state map; replacing it is not a claim that it is unnecessary at scale.
No cryptographic primitive, general lane service, privileged reserve key or
private-state design is added. See [ADR-0004](../../docs/adr/0004-public-based-app-native-value.md).

[D]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/action/deposit.rs
[DP]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/deposit_policy.rs
[TI]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/tx_inputs.rs
[B]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/l1/bridge/src/worker.rs
[K]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0021.md
[KA]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0021/seqcommit-accessor.md
[BV]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/abi/src/batch_processor/verifier.rs
[AV]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/abi/src/batch_aggregator/verifier.rs
[ABI]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/abi/src/batch_aggregator/journal/state_transition.rs
[C]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/covenant/src/script.rs
[W]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/action/withdraw.rs
[AUTH]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/auth.rs
[SIGN]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/signer_variants.rs
[PT]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/api/src/permission_tree.rs
[PS]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/api/src/permission_script.rs
[DS]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/abi/src/delegate_script.rs

**Additional bounded-guest limit:** the retained relation's `MAX_SPAN=100` is
relative to old lane last touch, not a general upstream limit. This cycle
captures both intervals before proving. Processing new commands after a long
idle gap, or independently withdrawing the remaining balance then, is not
established with this fixed guest. See the [adversarial review](ADVERSARIAL-REVIEW.md)
for the exact start-anchor and recovery boundary. Generalization needs the
upstream long-span/expiry proof trajectory, not a scheduler promise or admin key.
