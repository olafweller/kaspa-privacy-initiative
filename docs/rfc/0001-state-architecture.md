# RFC-0001: State architecture for the first native-KAS privacy PoC

**Status:** Open

**Date:** 2026-10-02; comparison updated 2026-10-08.

**Review owner:** project review; no architecture accepted by this draft.

## Context

We need to determine the smallest architecture that can demonstrate:

```text
test KAS deposit -> private claim -> private value-conserving transfer
-> double-spend prevention -> authorized exit -> native test KAS withdrawal
```

The three candidates in [ARCHITECTURE.md](../ARCHITECTURE.md) share native-KAS backing but place state updates and ordering differently. The [2026-10-08 source review](../../research/phase1-source-review-2026-10-08.md) supplies the comparison below. Source facts are cited; candidate mechanisms, recovery scenarios and expected tradeoffs are **design hypotheses**, not demonstrated capabilities.

Fund safety, independent recovery, sender/receiver unlinkability, hidden internal amounts and useful scale are simultaneous requirements. A recoverable system with inadequate privacy or scale fails the goal. Native deposit/withdrawal amounts and destinations at public boundaries remain visible; no stronger claim is made.

This RFC proposes an investigation order, not an architecture decision, cryptographic selection or authorization to implement/run Phase 2. A, B and C remain open; batching is an option within the comparison.

## Constraints

- Preserve all [I-1 through I-16](../../SECURITY-INVARIANTS.md). No invariant change is proposed.
- Native KAS is the backing asset; no separate privacy token, real funds, mainnet experiment or privileged reserve withdrawal.
- Proofs must constrain integer ranges, authorization, authenticated state, conservation and actual settlement outputs. Membership or proof validity alone is insufficient.
- Use established constructions after source, licensing and specialist review. Conceptual reuse does not grant implementation rights or transfer a protocol's security result.
- Users must have independently executable discovery, proving and recovery/exit paths. A safe halt must not become permanent dependence on a departed operator.
- Later real-proof validation needs compatible pinned network/genesis, pool/program/key identity, encodings, dependencies and resource limits; source pins alone are not a validated toolchain.
- Separate confidentiality from timing, network, fee and wallet metadata. A hosted prover must not silently receive note/spend secrets.

## Source-grounded comparison inputs

| Reviewed fact / component | Implication for A/B/C | Source boundary |
| --- | --- | --- |
| KIP-10/17 introspection and KIP-20 covenant/output bindings | Direct reserve settlement is available to investigate in all three; economics must be constrained explicitly. | [Pinned primitive map][K]; [KIP-20][K20] is a specification, not a complete pool. |
| Groth16 `0x20` and RISC0 `0x21`; compute, storage and transient limits | A/B per-update verification has material L1 cost; A/C batching might amortize it. Ciphertext/data cost remains. | [Verifier dispatch][Tags] and [budget/relay table][Budgets]; no pool TPS derived from base verifier cost. |
| Pruning removes old bodies/acceptance/state-diff data | Every candidate needs authenticated retained recovery data beyond a current root or address UTXO query. | [Pruning implementation][Prune], [RPC/recovery analysis][Retention]; archival availability is an assumption to resolve. |
| Orchard note/key/nullifier relations and compact scanning | Candidate reference for a common anonymous membership domain and local discovery. | [Orchard assessment][O]; Halo2 is not directly accepted by current Kaspa tags; adaptation creates new review obligations. |
| Aztec indexed nullifier trees, tags and independent PXE | Candidate techniques for spent-state efficiency and discovery, applicable beyond C. | [Aztec v5.2.0 assessment][Z]; predecessor constraints, metadata, query leakage and archive loss remain material. |
| RAILGUN join-splits, encrypted events and shielded broadcaster fees | Candidate patterns for bounded conservation, scanning and avoiding a user's public fee input. | [RAILGUN V2 assessment][R]; relay policy, upgrades and circuit rights cannot be silently inherited. |
| Monero view/spend separation and MWEB compact recovery | Recovery must distinguish unspent value from complete history; configured anonymity is not effective anonymity. | [Monero][M] / [MWEB][W]; rings/visible output spends differ from private note membership, and their retention rules are not Kaspa's. |
| vProgs scheduler, state, settlement and withdrawal components | C may reuse integration concepts; A/B may study output bindings without adopting a runtime. | [Component table][V], [prototype README][VReadme]; private execution, real-proof compatibility and recoverability remain unvalidated. |

## Common recovery inventory

The [ROADMAP N-user shutdown gate][Gate] applies to all candidates. These are **required categories to specify**, not an already sufficient backup format.

| Data class | Public or independently retained data | User-held material / remaining requirement |
| --- | --- | --- |
| Identity and verification | Genesis/pool/version identities, verifier keys or guest images, canonical encodings and reproducible proving/validation software/artifacts | Spend/view secrets and derivation/restore metadata. A vanished artifact host must not prevent proving. |
| Accepted state and spentness | Authenticated ordered transitions, or complete state snapshots bound to accepted roots plus necessary updates; commitments, nullifiers, reserve outputs and unpaid-exit liabilities | Note preimages/randomness and any independently retained witnesses; verify against current accepted state, not a server's assertion. |
| Discovery | Encrypted notes and required tag/handshake/delivery metadata, authenticated to protocol activity; enough history for the chosen scan method | Discovery secrets, sender relationships/counters where needed, or documented recipient-held note backups. A seed alone is not assumed sufficient. |
| Exit and fee access | Independently usable submission/settlement paths and all public data needed to establish entitlement and actual payouts | The user's authorized fee entitlement or contribution method. No original operator, private database or privileged rescue key. |

A root authenticates data but cannot reconstruct it. Ciphertexts omitted from a state snapshot still need retention or documented user backups. A state snapshot also does not automatically prove complete discovery or historical acceptance: those bindings must be specified. No individual archive or default provider may be indispensable. An own validating L1 node can replace an RPC provider, but cannot recreate data already pruned everywhere.

## Options considered

### A. Minimal L1 covenant + ZK pool

**Mechanism (hypothesis).** A covenant reserve/state UTXO commits to note and spentness state. A transition consumes it and installs a successor; proofs establish hidden authorization/conservation, while covenant checks bind actual reserve, fee and payout outputs. The [native primitive map][K] supports investigating this surface. [Orchard][O] and [RAILGUN][R] provide note/conservation patterns, not ready-made Kaspa circuits.

**Privacy and scale.** One logical membership domain can keep candidates together; public updates, fees, entry/exit values and timing still correlate activity, especially with few users. Parallel proving does not remove competition for the latest state UTXO. Historical membership anchors might reduce witness churn, but current spentness/settlement must remain authenticated. Optional batches could amortize verification and updates; admission, ordering, rebasing, delay and fee behavior are unresolved.

**N-user recovery scenario (unproven).** Each user locates the canonical live reserve/state through independent validation, reconstructs the common inventory, locally discovers owned notes and checks spentness. The user generates a proof against an allowed membership anchor and the current spending state, builds the covenant-bound native withdrawal, pays an authorized fee and submits independently. Conflicting users must refresh/reprove as required until all valid claims exit; no operator may decide whose exit is permitted. A batch-only fallback would still need independently constructible batches.

**Additional data / failure point.** Retain the state-successor/acceptance chain or authenticated equivalent and all discovery/witness data. A current UTXO/root alone is insufficient. This candidate fails if independent recovery lacks data, repeated contention prevents usable exits, fees require a linked user wallet, or anonymity/throughput targets are not met. A1's finite same-owner recovery does not prove this scenario.

### B. Sharded/native covenant UTXO state

**Mechanism (hypothesis).** Partition reserve/state across covenant resources. Independent shards can progress concurrently; cross-shard transfers, nullification and reserve movement require reviewed atomic accounting or another fully proved coordination rule. The same [native bindings][K20] are relevant, but they supply no automatic cross-shard private protocol. [RAILGUN's per-tree nullifier context][R] is a warning to specify complete replay domains, not evidence for this scheme.

**Privacy and scale.** Physical state partitioning need not logically partition the commitment universe. Nevertheless, visible shard choice, migration and rebalance can identify a smaller candidate set even with a shared tree. A globally serialized spentness root could erase concurrency gains. Cross-shard proofs and witness updates add cost; per-shard reserves and aggregate backing need separately specified relations. Performance benefit and preserved unlinkability are both open.

**N-user recovery scenario (unproven).** Users reconstruct relevant shard roots, note-assignment/spentness domains and all in-flight migration/exit liabilities from accepted public data. They discover notes locally and determine a unique authorized spend domain. Each proves a withdrawal from the backing reserve; if funds moved, the protocol must let them complete or resolve the corresponding transfer/exit using independently available proofs and data. Replays cannot redeem the same note in both shards, and one failed shard/operator cannot require its private cooperation.

**Additional data / failure point.** Retain shard identities/version maps, migration dependencies, all relevant spentness state, reserve allocation and authenticated cross-shard updates. A hidden commitment plus a shard hint is not solvency or uniqueness evidence. This candidate fails if reserve fragmentation strands a valid user despite aggregate backing, global coordination cancels its scale benefit, or routing reveals unacceptable ownership links.

### C. Based app / vProgs shared state

**Mechanism (hypothesis).** L1 sequencing commitments order activity; a based app validates private operations, batches/proves transitions and settles state/exits through covenants. Compare one based app first; full cross-app vProgs composition is neither assumed required nor dismissed. [vProgs components][V] and [Aztec][Z] inform scheduling, private-client execution and data recovery, not implementation readiness.

**Privacy and scale.** A common membership/nullifier domain and batched settlement could preserve candidates and amortize L1 verification. Public payload/resource patterns, batch boundaries, queues and prover contacts can leak relationships. User-local proofs or another reviewed confidential-execution scheme must keep witnesses out of untrusted executors. Parallel execution/proving still needs coherent roots, duplicate rejection and serialized covenant settlement. No scaling claim follows from a prototype scheduler.

**N-user recovery scenario (unproven).** Users obtain authenticated sequencing intervals/payloads, accepted settlement roots and the common inventory. Independent software replays publicly verifiable transitions, distinguishes pending from settled claims and recovers each user's notes using only their own secrets. Independent provers must be able to advance valid settlement and redeem exit permissions, or execute a separately specified exit from settled state. No such fallback is established here. If replay/proving needs other users' private witnesses or the departed executor's database, this scenario fails.

**Additional data / failure point.** Retain lane/sequence proofs and payload history, guest/ABI versions, batch boundaries, settled roots and outstanding exit permissions. An emitted exit or accepted lane transaction is not a native payout. All created-but-unpaid liabilities remain backed. This candidate fails if publishing data leaks notes, withheld payloads block reconstruction, queues cannot be independently progressed, or settlement fees become an operator veto.

### Comparative assessment

These are source-grounded expectations, not measured results. A larger implementation can be useful only if it improves the full goal.

| Criterion | A: one state UTXO | B: sharded covenant state | C: based app/shared state |
| --- | --- | --- | --- |
| Scope / dependencies | Smallest settlement control; custom private rules/DA remain | Coordination, reserve allocation and wallet routing | Runtime, ordered replay, proofs, DA and settlement integration |
| Anonymous membership | Common domain possible; timing/fee links remain | Shared domain possible, but routing/partition leakage must be measured | Common domain possible; payload/executor metadata can narrow it |
| Low activity | Individual updates and distinctive exits expose timing | Small shard populations can worsen it | Sparse batches still correlate; waiting/padding costs matter |
| Contention | Current reserve/state input; stale proof/retry pressure | Local parallelism only if global dependencies allow it | Execution/proving may parallelize; shared roots and settlement remain |
| Batching | Optional direct batched transition | Optional per-/cross-shard batches; dependency cost | Core comparison opportunity; censorship/queue cost unresolved |
| Native exit | Proved note consumption plus bound reserve debit/payout | Unique claim and available backing in its spending domain | Settled entitlement plus exact permission/payout and unpaid liabilities |
| Pruning recovery | Common inventory plus accepted successor evidence | Same plus shard/assignment/migration state | Same plus authenticated sequencing/payload/batch/exit replay data |
| Fee privacy / liveness | Private-value fee or another reviewed method; volatility open | Same plus multi-shard coordination cost | Batch/relay compensation and settlement/payout fees; service filtering open |
| Proof / data cost | Per update or batch; actual backend adaptation unknown | Multiple roots/coordination; no demonstrated gain | Aggregation could amortize; public DA cost persists |
| Migration | Preserve liabilities and pool/verifier domains | Coordinated versions and cross-shard uniqueness | Guest/runtime/ABI/settlement versions and pending liabilities |

## N-user shutdown gate: comparable acceptance evidence

For a later **separately authorized** experiment, apply [the same gate][Gate] to each candidate:

1. Predeclare N greater than one, representative deposits/transfers, spent notes and any pending exits/migrations. Inventory exactly which data/software is public or independently retained and which secrets/backups each user needs.
2. Shut down every normal operator, prover, executor, indexer and hosted state service. After the declared pruning/history conditions, start independent software from the declared inputs; prohibit undeclared operator caches/cooperation.
3. Each user authenticates state, discovers all valid holdings, detects consumed notes and creates an authorized exit. For A record root conflicts/reproofs; B record migration/reserve dependencies; C record pending/proved/settled state and autonomous queue/permission completion.
4. Verify each native payout's recipient and integer-sompi amount, explicit fees/refunds, reserve debit and finality/reorg conditions. Every created unpaid claim remains a liability; balances shown by a wallet or emitted exits are not payout evidence.
5. Report every user's result, data gaps, elapsed time and infrastructure/fee dependencies. Missing required data or one failed exit blocks the gate; aggregate reconstruction percentages cannot excuse it. Separately evaluate privacy and scale against predeclared targets, including low activity and publicly linkable fee payments.

No candidate has passed this multi-user gate. Completing it would still not prove cryptographic correctness or production security.

## Security analysis

All candidates must satisfy the same obligations. None receives a waiver for being a testnet experiment.

| Invariants | Required check | Candidate-specific concern |
| --- | --- | --- |
| I-1, I-2, I-12 | Range-constrained claims and explicit deposits, exits, fees, and isolated reserves | A: all outputs; B: migration/solvency; C: pending exits and settlement accounting |
| I-3, I-14 | Spend authorization and recipient-verifiable spendability | A/B/C: reuse a reviewed note/key model; do not mistake inclusion for ownership |
| I-4, I-15 | Authenticated spent-state update and deterministic rejection | A: current nullifier root; B: cross-shard duplicates; C: batch duplicates and replay |
| I-5, I-6 | Pin verifier/program and bind current settlement state and domain | A: state UTXO/pool; B: complete shard input set; C: lane, sequence interval, and guest images |
| I-7, I-8, I-13 | Bind payout destination/value, reserve continuation, and explicit upgrade authority | No operator signature or upgrade mechanism may bypass withdrawal rules |
| I-9, I-10, I-11 | Reject unverifiable updates; independently reconstruct state and generate exits | State roots alone do not provide witnesses; C also needs deterministic lane replay |
| I-16 | State privacy limits and measured leakage | A: event timing; B: shard metadata; C: public payloads and outsourced witnesses |

For every deposit, claim creation must bind to new native backing and must not replay a deposit. For every withdrawal, claim consumption, any pending-exit entitlement, reserve debit, payout, change, and explicit fees must account for the same value atomically or through a proven intermediate state. Burning a private claim into an unpaid public exit does not eliminate the liability.

L1 input/output conservation alone does not prove private supply conservation or correct payout: an attacker can redirect value into another transaction output. A covenant must enforce the complete intended output layout.

A note inclusion anchor may be historical if the protocol explicitly permits it; that must not permit stale settlement-state or spent-state replay. Define this distinction before choosing root policies.

## Privacy analysis

The [protocol assessments][O] distinguish confidential notes from effective anonymity. Nullifiers must reject double spends without revealing which commitment was used. Entry/exit amounts, distinctive fees, timing, RPC interest, ciphertext/tag formats and wallet behavior remain potential links. A shared root is not a measured anonymity set; shard routing or batch partitions can shrink candidates.

P12 must cover incoming discovery, authenticated note reconstruction and recipient spendability, not only sender-created notes. [Aztec discovery][Z] may require sender/handshake metadata; [Orchard][O] and [RAILGUN][R] illustrate local decryption and accepted-commitment checks. Seed-only recovery and private server queries are not assumed solved.

[Shielded relay fees][R] illustrate avoiding a user's public gas input, but relay policy and public self-broadcast fallbacks have distinct privacy/liveness properties. A fee sponsor's existence does not establish permissionless exits. Fee authority must conserve principal, refundable entitlements and reserve isolation under changing relay/inclusion demand ([#23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23)).

For C, define how executors verify confidential operations from public proofs without receiving spend witnesses. For all candidates, hosted proving changes the confidentiality assumption. Low-activity timing and recorded encrypted-note exposure must be studied even when current circuits hide amounts.

## Phase 2 decision questions

These questions are inputs to a later review/decision; no construction below is selected.

| Decision topic | Specification/evidence required before accepting a candidate |
| --- | --- |
| Note, keys and commitments (P04/P12) | Which established construction fits the supported verifier and usable license? Canonical sompi/ranges, owner/view roles, randomness, recipient checks, encryption and pool/version binding; no automatic Orchard or RAILGUN circuit import. |
| Nullifiers and roots (P05) | What derives one marker per authorized note? Current spentness vs permitted historical inclusion anchors; indexed/sparse/other authenticated storage, batch duplicates, reorgs and cross-shard/lane/version replay. |
| Conservation and backing (P06/P07) | Equations for deposits, private transfers, fees, unpaid exits, migrations and completed payouts; bind all actual reserve/successor/payout/change outputs and reject unauthorized release. |
| Recovery/DA/discovery (P10/P12) | Minimal complete retained format, snapshot/history authentication, ciphertext retention and backup requirements; independent providers and proving artifacts; a per-candidate N-user shutdown plan with explicit pruning conditions. |
| Fee privacy and exits (P08/#23) | Fee-demand assumptions, safe contributions/substitution and refunds; preserve principal and exact payouts without an admin path. Can independent users prove/relay/settle and pay fees without linking their public wallets? |
| Anonymity and low activity (P09) | Chain/network/service adversaries; common candidate set vs observable partitions; timing/amount/query/fee fingerprints; acceptable delay/padding costs and falsifiable leakage targets. |
| Scale and batching (P03/P11) | Compare individual A updates, optional A batches, B dependencies and C batches with the same workload/privacy targets; proving resources, L1 compute/storage/transient mass, latency, contention, reproofs and witness-refresh cost. |
| Cryptography and migration (#19) | Assess proof soundness, signatures, commitments/nullifiers, encryption and retained-ciphertext threat horizons separately. State setup assumptions, verifier/program domains, downgrade prevention and liability-preserving migration with independent recovery and no privileged withdrawal key. |

[Orchard's circuit failure/migration lesson][O] makes clear that aggregate backing cannot substitute for authorized individual claims. [PQ signature experiments](../../research/kaspa-post-quantum-experiments.md) do not establish PQ note confidentiality. Code availability, implementation rights and specialist security review are separate prerequisites from choosing state architecture.

## Proposed direction / outcome

**Not decided. Provisional recommendation for review:** investigate a common logical anonymity domain, using A as the smallest settlement control and comparing optional batching on A with C early. Keep B as an explicit alternative, requiring coherent cross-shard nullification/backing and measured privacy as well as concurrency. A common logical domain need not mean one physical state object; none of these hypotheses is accepted.

The rationale is the combination of mature [Orchard][O] and [RAILGUN][R] note/membership patterns, material native [verification charges][Tags] and [resource limits][Budgets], and explicit [pruning/recovery gaps][Retention]. A is a useful control for exposing conservation and native output bindings with few execution components. Its single-state contention prevents treating that simplicity as a scaling argument. C's batching/integration may help but adds ordered-replay, confidential-execution and prototype-runtime obligations. B may parallelize work, but global spentness and observable routing can cancel its scale/privacy advantage.

If Phase 2 is later authorized, specify the shared economic, recovery and privacy requirements first, then compare candidate models against the same targets. Investigate batching as an option, not an assumption that all users must depend on a batch operator. Reject or redesign any candidate that cannot satisfy independent exits **and** the privacy/scale targets; do not rescue it with weaker invariants, trusted private state or an administrator withdrawal.

A0/A1 answer their scoped reserve questions, not the multi-user note, DA, fee-privacy or scale questions. There is no preferred production architecture, selected proof backend or implementation authorization. Human Kaspa/ZK review and community objections should precede a later decision/ADR. This update leaves ARCHITECTURE.md, invariants and the threat model unchanged.

## Objections / unresolved questions

- Can any adapted private lifecycle and retained data fit actual verifier, transaction and relay budgets with useful fees/latency?
- Can historical inclusion anchors, current spentness and optional batches reduce A's retry pressure safely?
- Can B preserve a common effective anonymity set and independently redeem every claim when reserves/migrations are distributed?
- Can C be recovered and reproved from authenticated public activity plus each user's own secrets, with no privileged executor witness or unavailable queue data?
- Can all candidates survive fee volatility and operator censorship without linking the user's public wallet or trapping principal?
- What privacy/scale thresholds and cryptographic migration assumptions would falsify the provisional investigation order?

## Evidence

- [Pinned upstream map](../../research/kaspa-toccata-vprogs.md): active KIPs, verifier source, prototype runtime, draft full-vProgs specification, and inspected exits.
- [Existing Kaspa work](../../research/existing-kaspa-privacy.md): public pool-code inspection, bounded searches and explicitly unverified author claims; no third-party demo reproduced.
- Dated mature-protocol component assessments: [Orchard](../../research/zcash-orchard.md), [Aztec](../../research/aztec.md), [RAILGUN](../../research/railgun.md), [Monero](../../research/monero.md), [MWEB](../../research/litecoin-mweb.md). These are provisional reuse/adaptation tables, not audits, implementation rights or accepted security results.
- [A0/A0.5](../poc-a0.md) demonstrated local real-proof validation plus a funded TN10 reserve release and observed native test-KAS payout on 2026-10-03. The own node lacked complete UTXO sync; live UTXO/acceptance observations used public native RPC endpoints. This earlier experiment did not demonstrate independent recovery, a privacy pool, an audit or production safety.
- A1's [S1 recovery](../poc-a1-official-trial-2026-10-08.md) and [S0 trials](../poc-a1-s0-trials-2026-10-08.md), included in merged [PR #22](https://github.com/olafweller/kaspa-privacy-initiative/pull/22), answer its core question for a finite same-owner covenant: independent recovery and native exit from S0 and S1 with the original machine physically off. S0 direct exit and competing terminal spends also succeeded; one candidate was accepted and the later candidate rejected, with submission intents about 1.4 seconds apart. The full G5/G6 matrix remains open; C/history availability, setup trust and fee liveness remain assumptions or unresolved limits. These results do not demonstrate multi-user privacy, pass the N-user recovery gate or accept this RFC.
- Fixed-fee exit liveness remains an [open production blocker (#23)](https://github.com/olafweller/kaspa-privacy-initiative/issues/23); per-instance Groth16 setups do not establish a scalable pool design.

## Revisit if

- Any candidate fails the recovery, privacy, fee-liveness or scale targets; A's simplicity alone is insufficient.
- B demonstrates coherent safe nullification/reserve movement with actual concurrency and preserved anonymity.
- C supplies reproducible confidential replay/proving/settlement and independent exits with meaningful batching gains.
- Upstream verifier, lane, runtime or upgrade semantics change relative to the dated source pins.
- Independent review identifies underconstraints, unavailable recovery data or hidden trust/rights assumptions.

[K]: ../../research/kaspa-toccata-vprogs.md#implemented-primitive-map
[K20]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0020.md
[Tags]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/tags.rs
[Budgets]: ../../research/kaspa-toccata-vprogs.md#consensus-limits-relay-policy-and-fee-cost
[Prune]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/src/pipeline/pruning_processor/processor.rs
[Retention]: ../../research/kaspa-toccata-vprogs.md#pruning-and-node-recovery-surface-p10--p12
[O]: ../../research/zcash-orchard.md
[Z]: ../../research/aztec.md
[R]: ../../research/railgun.md
[M]: ../../research/monero.md
[W]: ../../research/litecoin-mweb.md
[V]: ../../research/kaspa-toccata-vprogs.md#vprogs-components--provisional-assessment
[VReadme]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/README.md
[Gate]: ../ROADMAP.md#early-exit-and-recovery-gate
