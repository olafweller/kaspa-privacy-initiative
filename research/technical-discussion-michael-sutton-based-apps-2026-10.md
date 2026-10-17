# Technical discussion: Michael Sutton on Based Apps and KPI

**Discussion:** October 2026, between KPI initiator Olaf Weller and Kaspa core developer Michael Sutton; exact day not recorded here.

**Recorded:** 2026-10-13. **Status:** external technical feedback and research input.

These notes paraphrase Michael's advice **as reported by Olaf** in the brief supplied for this note. They are not an approved transcript, contain no direct quotations, and have not been represented as reviewed by Michael. The conversation is not an architecture decision, formal endorsement of KPI, or evidence that a KPI implementation works. [RFC-0001](../docs/rfc/0001-state-architecture.md) remains Open.

## Subsequent experiment outcome, 2026-10-17

The [scoped feasibility conclusion](../docs/based-app-feasibility-2026-10-17.md)
now records the real TN10 results from PRs #31–#33 against five acceptance
criteria, including valid settlement and same-endpoint omission rejection.
The planning note below remains historical; the final report states the actual
workloads and boundaries. No endorsement or independent review is attributed to
Michael by these subsequent results. Development focus moves to
[shielded native KAS and financial privacy](../docs/shielded-kas-next.md).

## Michael's advice as reported by Olaf

Michael suggested investigating the existing **Based App architecture as the primary candidate for KPI's execution and settlement model**, particularly for a shared shielded state. Olaf reported the following architectural guidance:

1. KIP-21 supplies application-specific L1 sequencing commitments through lanes.
2. Users or relayers can submit app operations as ordinary L1 transactions carrying application payloads.
3. Kaspa supplies an independently verifiable ordering of accepted operations.
4. A properly designed execution proof can bind the old state, the exact lane interval processed and the resulting new state.
5. The settlement covenant can reject a proof that does not correctly account for that claimed interval.
6. This potentially addresses a major gap in the earlier A + batching concept: independently authenticating the input set so a batcher cannot falsely claim to have processed every operation in an interval.
7. A single Based App can use important L1 primitives without waiting for full cross-application vProgs composability.
8. Canonical bridge designs offer potentially reusable native-KAS deposit, settlement and L2-to-L1 exit patterns.
9. Existing vProgs code may supply reusable execution, proving, state-management and settlement infrastructure.
10. Sharding appears unnecessarily complex for the initial investigation unless measurements demonstrate a scaling requirement.

Michael also raised feasibility questions about individual proof costs, recursive proving, shared commitment trees, nullifiers and the scaling challenges of private payment history. No quantitative conclusions or working shielded construction are attributed to him here.

## Independently checked primary sources

The following is **source verification**, separate from the conversation report. On 2026-10-13, default-branch heads were fetched and the linked specifications, documentation and selected code read. These four heads match the [2026-10-08 source map](kaspa-toccata-vprogs.md). No build, proof generation, node query or live network activation check was performed for this note.

| Repository | Reviewed commit |
| --- | --- |
| `kaspanet/kips` (`master`) | `e4ae2332117b5cb68bd6188e065ef885b6d17939` |
| `kaspanet/docs` (`main`) | `0ac77d043a802fc8196abfd5812ac2afbd97a2b9` |
| `kaspanet/rusty-kaspa` (`master`) | `01b532e8b553523216471682649693af92f0fd16` |
| `kaspanet/vprogs` (`master`) | `f9b84a863a7c7c20586a9cf947550475e894f72e` |

| Supported claim | Primary evidence and precise boundary |
| --- | --- |
| App-local accepted ordering is committed through lanes. | [KIP-21][K21], sections 1–2, 4.2 and 5–6, defines lanes by transaction `subnetwork_id`, ordered activity leaves binding transaction ID, version and `merge_idx`, recursive lane tips and global anchoring. A lane is a sequencing namespace, not a shielded-state shard. |
| App operations can travel in ordinary L1 transactions. | [Toccata Based Apps][Based] describes v1 transactions with lane, gas, payload and normal inputs/outputs. L1 carries and orders bytes; the app defines their meaning. [Transaction hashing][TxHash] supplies the payload-to-transaction-ID binding needed to authenticate those bytes. Relayers still need an app-defined authorization and fee model. |
| A lane interval can be independently authenticated. | [KIP-21][K21], sections 10.1–10.3, describes two-anchor lane proofs and reactivation handling; [lane-activity test source][LaneTest] illustrates reconstructing a tip and checking it against a header commitment. This supports a mechanism to investigate, not a reproduced KPI completeness proof. |
| Settlement can bind execution to L1 activity and state. | [vProgs batch verifier][Batch] derives activity from verified transaction journals; [aggregator][Aggregate] chains state/lane transitions and derives a sequencing commitment; [journal][Journal] carries state, lane and program identities; [covenant script][Script] binds that journal to the proof, current state and continuation, using `OpChainblockSeqCommit`. The [opcode implementation][Opcode] and [accessor specification][Accessor] impose selected-parent and depth conditions. Correct program constraints and pinned identities remain essential. |
| A single Based App is a present research surface distinct from full composability. | [Toccata Based Apps][Based] documents lane submission, off-chain execution and covenant settlement. KIP-21's future-vProgs section is explicitly informative. Using this surface does not establish confidential execution or require adopting the entire future composition model. |
| Native-KAS bridge patterns and runtime components exist to study. | Michael's public [canonical bridge design][Bridge] discusses native backing, entry delegation, state-chain authenticity and exit delivery. [Settlement construction][Settlement], [withdrawal action][Withdraw] and [permission script][Permission] supply code references. The [vProgs README][VReadme] describes scheduling, execution and storage, explicitly as early/prototype infrastructure. These are reuse candidates, not a complete KPI bridge or security result. |

Source limitations matter. The [KIP-21 proving companion][Proving] is a reserved scope document, not a complete proving/witness specification. The [programmability overview][Overview] cautions against assuming the current Based Apps option fits a custom account or privacy-first execution model; that makes adaptation a question to test. Also, the Toccata guide describes a 320-byte journal, while the pinned [ABI code][Journal] encodes 352 bytes including `deposit_spk_hash`. An experiment must follow compatible pinned code and encodings rather than copy the overview's ABI size. The [TN10 example guide][Dev] defaults to development-mode settlement; that path is insufficient evidence of proof-enforced completeness.

## KPI interpretation: authenticate the batch input set

**Interpretation:** A + batching needs more than a proof that seven supplied operations executed correctly. It needs an independently authenticated definition of which operations the batch was obligated to consider. A batcher's manifest or operation count alone does not supply that definition.

For a fixed KPI lane and accepting-chain-block interval `(B_start, B_end]`, the intended statement is:

```text
new_state = deterministic_execute(
    old_state,
    all accepted KPI-lane operations after B_start through B_end, in canonical order
)
```

**Hypothesis requiring testing:** bind the old state and processed lane tip to the live settlement input; bind the complete ordered transaction/payload sequence to lane witnesses and authenticated anchors; pin lane, covenant/genesis and guest/verifier identities; and bind the new state, processed tip and any required outputs to the successor. With sound proofs, correct constraints and hash bindings, omitting included operations while retaining the same complete-interval claim should fail proof/anchor verification.

Every accepted lane transaction must be accounted for, including deterministic rejection or no-op outcomes under specified app rules. Completeness does not mean an invalid app operation must successfully change state. Reordering, duplicate execution and payload substitution must also be rejected. A valid shorter interval can leave later operations pending; it does not establish that the whole target interval was processed. Lane inactivity, purge/reactivation, reorgs and interval boundaries need explicit handling before generalizing the result.

This changes the input-authentication question from an operator assertion into a proposed proof obligation. It does not by itself establish permissionless settlement progress or a private payment system.

## Four distinct failure cases

| Failure case | What sequencing/completeness can establish | What remains unresolved |
| --- | --- | --- |
| Censorship before L1 inclusion/acceptance | Nothing in an interval proof obliges a miner or relay to include a transaction that never entered the accepted lane sequence. | Submission access, miner/relay filtering, fees and inclusion delays. KIP-21 does not automatically prevent all censorship. |
| Incorrect omission of included operations from a claimed interval | A correctly constrained proof and covenant should reject a complete-interval claim with missing operations or wrong order. | Reproduce that rejection with real proofs and the actual settlement verifier; specify invalid-operation semantics. |
| Executor refusal, delay or failure | Invalid state advancement can be prevented even when progress stops. | Independent execution/proving, fee funding, backlog catch-up and exit liveness. Safety alone cannot force an executor to work or advance the endpoint. |
| Incomplete data availability after pruning | Commitments can authenticate available data. | They cannot recover missing payloads, ciphertexts or witnesses. Define independently retained history/snapshots and discovery data; no indispensable archive operator. |

Based Apps do not automatically solve privacy, trustless exits, note discovery, fee privacy or long-term recovery. Public lane payloads must not contain private spend witnesses. A shared commitment root does not itself establish an effective anonymity set or remove nullifier/settlement contention.

## Research priority and relationship to existing KPI work

**Proposed investigation order, not a decision:** prioritize an early single-Based-App/KIP-21 interval-completeness experiment for C. Retain A, including optional batching, as the comparison baseline for native output binding, cost and contention. Keep the same conservation, privacy, recovery and permissionless-exit requirements across candidates.

Keep B/sharding open but defer initial implementation until a common-workload measurement shows a bottleneck that batching, independent proving or a single shared state cannot adequately address. Evidence should identify throughput/latency, shared-tree/nullifier contention, proving resources and witness-refresh costs, and show that partitioning helps while preserving anonymity and coherent backing. Adding cross-shard nullification, reserve allocation and migration machinery before such evidence would broaden the research problem without a demonstrated benefit.

This revises RFC-0001's earlier emphasis on A as the smallest control with an early C comparison; it does not contradict its open A/B/C status. [ARCHITECTURE.md](../docs/ARCHITECTURE.md) still presents candidates without selecting one. [A0](../docs/poc-a0.md) and [A1](../docs/poc-a1-official-trial-2026-10-08.md) answer scoped reserve questions; their historical decision to defer lanes/runtime from those experiments remains valid. The [Phase 1 review](phase1-source-review-2026-10-08.md) remains dated source evidence. No historical evidence, accepted ADR, security invariant or protocol behavior changes here.

## Proposed small feasibility PoC

**Plan only; no experiment was run by this documentation change.** Start offline and unfunded. Publish the ten test operations into a local KPI-lane fixture using pinned upstream consensus ordering/commitment machinery or independently verifiable captured data. This is simulated publication, not L1 broadcast or observed inclusion. Preserve transaction bytes, accepted ordering, block context, lane witnesses and anchors independently of the executor's manifest.

1. Specify a deterministic, order-sensitive toy Based App, one valid lane ID, initial state and the exact `(B_start, B_end]` interval. Use ten valid operations with distinct effects; include unrelated lane activity and an empty block to exercise filtering and continuity. Pin program IDs, ABI, consensus dependencies and fixture provenance.
2. Reconstruct canonical accepted ordering from the fixture and verify the payload/transaction identities, lane-tip evolution and anchors. Do not substitute mempool arrival or broadcast order for acceptance order.
3. Execute all ten operations and generate a real execution/aggregate proof for the complete interval. Validate a synthetic settlement transaction offline with the pinned covenant/proof verifier and authenticated fixture seqcommit context. Record acceptance of the correct state and interval, with no network funding or broadcast.
4. Deliberately omit three operations, for example positions 3, 6 and 9, while claiming **the same start/end anchors and full interval**. Reuse the canonical endpoint evidence. Demonstrate that a seven-operation transition cannot satisfy the complete claim: record proving/anchor failures and rejection of a settlement submission with a proof/journal mismatch. Never fabricate a valid proof of a false statement. A host-only list/count check is insufficient; distinguish guest/proving failure from covenant rejection. Do not count an honestly shortened interval as an invalid claim.
5. Reconstruct using a second executor from only the independently retained raw fixture, identities and witnesses. Compare ordered IDs, lane tips, rejection outcomes and state roots without importing the first executor's derived state or filtered list. Proof bytes need not be identical. Add focused wrong-lane, reordered-input, stale-state and changed-endpoint controls; report initial activation assumptions and any untested purge/reactivation or reorg cases.
6. Report proof time/memory/size, aggregation costs, synthetic L1 verification/resource costs and required retained data. If compatible real proving or covenant verification is unavailable, report a blocker or partial result rather than claiming completeness was demonstrated.

Only after separate authorization should a TN10 version publish ten actual lane transactions, verify network/genesis/activation and acceptance ordering, and repeat the omission and independent-executor checks using test KAS only. Native-KAS deposit/exit integration is a later, separately scoped investigation: authenticate deposits, constrain integer-sompi conservation, nullify claims, bind reserve debits and exact payouts, and retain backing for unpaid exits. The public bridge design's `BKAS` terminology does not introduce a separate KPI privacy token; KPI's asset remains claims on native KAS.

## Unresolved feasibility questions

- **Individual and recursive proof cost:** can users prove privately on practical hardware; can the runtime verify those proofs inside execution and aggregate them with compatible L1 verification? Measure both stages, setup assumptions, memory, latency, proof/data size and fees. Recursion is not an assumed cost-free solution.
- **Shared commitment trees and nullifiers:** what membership anchors, current spentness proofs, duplicate rules and root updates allow concurrent private submissions? Can executors verify public proofs without other users' secrets? Measure witness churn and serialized dependencies before adding shards.
- **Private payment history and pruning:** distinguish restoring spendable notes from recovering complete history. Which ciphertexts, commitments, nullifiers, accepted/rejected outcomes, snapshots, keys and delivery metadata must survive? How do storage and scan costs grow, and can independent users authenticate and discover everything needed after operators disappear?
- **Native settlement and exits:** which canonical bridge components can be reused safely for shielded claims, pending liabilities and permissionless payout? An emitted permission or debit is not evidence of a completed native withdrawal.
- **Privacy and liveness:** how much do lane payload shape, resource access, batching, fees, timing and note retrieval reveal? Can independent provers/executors progress and users exit after prolonged downtime, pruning or fee changes without an admin path or a linked public fee wallet?

These questions retain the [RFC's common N-user recovery gate](../docs/rfc/0001-state-architecture.md#n-user-shutdown-gate-comparable-acceptance-evidence) and [security invariants](../SECURITY-INVARIANTS.md). A successful ten-operation PoC would address a narrow sequencing/settlement claim, not accept an architecture or establish production security.

[K21]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0021.md
[Accessor]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0021/seqcommit-accessor.md
[Proving]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0021/proving-spec.md
[Based]: https://github.com/kaspanet/docs/blob/0ac77d043a802fc8196abfd5812ac2afbd97a2b9/content/docs/toccata/based-apps.mdx
[Overview]: https://github.com/kaspanet/docs/blob/0ac77d043a802fc8196abfd5812ac2afbd97a2b9/content/docs/programmability/based-apps.mdx
[TxHash]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/hashing/tx.rs
[LaneTest]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/seq-commit/tests/prove_lane_activity.rs
[Opcode]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/opcodes/mod.rs
[Batch]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/abi/src/batch_processor/verifier.rs
[Aggregate]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/abi/src/batch_aggregator/verifier.rs
[Journal]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/abi/src/batch_aggregator/journal/state_transition.rs
[Script]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/covenant/src/script.rs
[Settlement]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/covenant/src/settlement.rs
[Withdraw]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/action/withdraw.rs
[Permission]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/api/src/permission_script.rs
[VReadme]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/README.md
[Dev]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/examples/tn10-flow/scripts/README.md
[Bridge]: https://research.kas.pa/t/l1-l2-canonical-bridge-entry-exit-mechanism/258
