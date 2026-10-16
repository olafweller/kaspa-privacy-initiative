# KPI integration scope after the Sutton feedback

Reviewed again on 2026-10-17 (Europe/Amsterdam). Michael Sutton's advice remains
the owner's reported feedback, not an approved transcript or endorsement. The
[feedback note](../../../research/technical-discussion-michael-sutton-based-apps-2026-10.md)
already identifies lane sequencing and settlement machinery. The offline PoC
tested a conditional gate; it did not establish that KPI must implement a new
general lane service.

## Current upstream and deployed compatibility

| Repository | Default-branch HEAD fetched for this integration |
| --- | --- |
| kaspanet/kips | `e4ae2332117b5cb68bd6188e065ef885b6d17939` |
| kaspanet/docs | `0ac77d043a802fc8196abfd5812ac2afbd97a2b9` |
| kaspanet/vprogs | `f9b84a863a7c7c20586a9cf947550475e894f72e` |
| kaspanet/rusty-kaspa | `f7d7877363fb97c2ec6871be0e8cbc351d44df10` |

Rusty Kaspa advanced six commits beyond `01b532e8...`. The inspected differences
include consensus-core `no_std`/Rust 1.95 requirements, paginated UTXO RPC,
mass/generator fixes, RocksDB settings and internal virtual seqcommit storage.
The lane hashing/SMT algorithms and `getSeqCommitLaneProof` response used here
have not changed in that range; transaction-ID hashing changes are imports for
`no_std`. This is a source comparison, not testing every newer code path.

The VPS reports node version 2.1.0. The adapter deliberately pins the earlier
2.1.0 source `01b532e8b553523216471682649693af92f0fd16`, compatible with retained
proof inputs and Rust 1.91. All git dependencies are checked in the lockfile;
build with `--locked`. Node version plus the retained binary SHA-256 identifies
the deployed artifact; a source-to-binary reproducible build is not claimed.

## Reuse versus KPI work

| Existing mechanism | Reuse / remaining KPI responsibility |
| --- | --- |
| KIP-21 ordinary v1 user-lane transactions | Reuse normal fee-funded publication. A lane namespace is not reserved. The KPI payload's semantics and invalid-operation/no-op rules belong to KPI. |
| `getVirtualChainFromBlockV2(Full)` and the vProgs L1 bridge pattern | Reuse accepted selected-chain order; enumerate the entire stream before filtering. The small capture adapter records native RPC responses and maps them into the retained guest input; it is not a replacement bridge, scheduler or archive service. |
| `getSeqCommitLaneProof` and Kaspa SMT/hash helpers | Use the actual local-node start/end witnesses and header anchors. Reuse `OwnedSmtProof`, `ActivityDigestBuilder`, `activity_leaf`, `mergeset_context_hash`, `lane_tip_next` and seqcommit composition. A second Python implementation cross-checks the same capture. |
| Native transaction decoding/hashing | Reuse `RpcOptionalTransaction -> Transaction`, native transaction IDs and `transaction_v1_rest_preimage`. Never trust a separately supplied payload/ID pair. Raw RPC strings retain u64 values exactly. |
| vProgs wallet construction | Reuse activity, fee-input/change, storage-mass, signing and settlement construction, with the documented mass-limit API patch. Add change to the upstream one-output bootstrap template. |
| vProgs settlement ABI and covenant | Reuse the existing adapted covenant and 352-byte journal. Real settlement binds the current covenant/state, guest identity, lane, claimed successor and selected-chain end anchor. The live build additionally selects the official lift-19 control identity via an explicit feature; the offline default remains lift-20. Both remain fixed-circuit covenants, with the same image/root/journal checks. |
| vProgs recursive proving/runtime | Available reference architecture, not required to reimplement for this narrow monolithic app. The retained real RISC Zero guest proves the KPI fold directly. This trial does not validate the full recursive runner or cross-app composition. |
| Canonical bridge deposits/exits | Existing reuse candidates, outside this trial. Publishing a public operation and advancing a covenant is not a shielded deposit, transfer or withdrawal. |

Primary source paths at the exact commits above: `kip-0021.md` and
`kip-0021/seqcommit-accessor.md`; docs `content/docs/toccata/based-apps.mdx`;
vProgs `l1/bridge/src/worker.rs`, `l1/wallet/src/build/`,
`zk/abi/src/batch_processor/verifier.rs`, `zk/abi/src/batch_aggregator/verifier.rs`,
`zk/abi/src/batch_aggregator/journal/state_transition.rs`, and
`zk/backend/risc0/covenant/src/script.rs`; Kaspa
`consensus/seq-commit/tests/prove_lane_activity.rs`,
`rpc/service/src/service.rs`, `rpc/core/src/model/message.rs`,
`consensus/core/src/hashing/tx.rs`, and `crypto/smt/src/proof.rs`.
The overview's 320-byte ABI description remains behind the 352-byte code ABI.
The upstream `examples/tn10-flow/scripts/README.md` defaults to development
settlement and is not evidence of real proof verification.

## Smallest missing KPI property

For one real, already-active user lane, prove that the deterministic public KPI
fold of **all accepted operations in one fixed interval** can advance its actual
TN10 covenant, while a signed settlement claiming a different new state with
the same real receipt is rejected. Independently omit one accepted operation
from the captured interval and require a mismatch against the unchanged node
end anchor. This connects the retained offline relation to actual input,
funding, UTXO state, proof verification and confirmation.

Use a seed transaction outside the measured interval to activate the lane.
Publish three operations, capture the interval and profile the actual guest
execution before choosing its fixed circuit. Bootstrap a catch-up covenant at
the known seed tip and explicit initial state, then prove against the actual
covenant identity. The preactivated checkpoint is intentional:
the old guest does not prove first-touch, expiry/reactivation or a general
bootstrap history. No mandatory count-to-three check is added to its relation.

This is integration research under open RFC-0001, not an architecture selection.
No private notes, nullifiers, shielded liabilities, bridge or exit subsystem is
introduced. Security invariants and the historical offline evidence remain in
force. The owner explicitly authorized this TN10 integration in the current
request, superseding the earlier handoff's publication-only scope.


## Observed monolithic proof-shape boundary

The first real live receipt used 524,288 padded cycles (one segment) and the
SDK verified it. Its official control ID was
`8c2fdd36ede09a4b9d316a43c51f1160cbd8876659c5f35810c3a119c60d3843`
(`lift_rv32im_v2_19.zkr`). The existing offline covenant fixed
`lift_rv32im_v2_20.zkr` and correctly rejected it in local script evaluation
before any settlement broadcast. This is a retained compatibility failure, not
an invalid computation or a TN10 rejection.

The new `monolithic-lift19` feature fixes the shorter circuit into a **fresh**
covenant identity; default/offline behavior remains lift-20. No existing UTXO is
upgraded, no verifier assertion is removed and no executor-selected control ID
is trusted. Program-image, allowed-control-root, empty-assumptions and exact
journal checks remain. See [live pin patch](../vendor/covenant/live19.patch).
This illustrates why the general solution should use a compatible established
recursive proving trajectory with its resolve pin, rather than advertise this
fixed-shape monolithic experiment as a general vProgs runtime.


The later capture also demonstrated that SMT witness depth changes execution
size even with three operations. The reproducible path therefore profiles the
actual captured workload **before** bootstrap, selects the explicit official
lift-19 or lift-20 builder, and rechecks the real-input profile after inserting
the actual covenant ID. This execution-only measurement creates no receipt and
is never represented as proof verification. The real proof and node validation
remain mandatory. The added stage avoids guessing verifier identity from an
operation count; it does not widen any deployed covenant's accepted circuits.
