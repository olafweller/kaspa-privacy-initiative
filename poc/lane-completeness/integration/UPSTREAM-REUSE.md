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
| vProgs settlement ABI and covenant | Reuse the existing adapted covenant and 352-byte journal. Real settlement binds the current covenant/state, guest identity, lane, claimed successor and selected-chain end anchor. Preserve both previously documented covenant adaptations. |
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
Bootstrap the covenant at the corresponding tip and the explicit initial KPI
state, then publish three operations. The preactivated checkpoint is intentional:
the old guest does not prove first-touch, expiry/reactivation or a general
bootstrap history. No mandatory count-to-three check is added to its relation.

This is integration research under open RFC-0001, not an architecture selection.
No private notes, nullifiers, shielded liabilities, bridge or exit subsystem is
introduced. Security invariants and the historical offline evidence remain in
force. The owner explicitly authorized this TN10 integration in the current
request, superseding the earlier handoff's publication-only scope.
