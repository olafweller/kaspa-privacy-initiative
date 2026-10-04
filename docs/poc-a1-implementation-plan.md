# A1 implementation plan

**Status:** this page preserves the G0 specification merged at
`0193d1847aa53468d6056a925ffb60f2d69e5b23` and its implementation handoff.
Separately authorized unfunded implementation is on `poc-a1-successor-state`
in [draft PR #22](https://github.com/olafweller/kaspa-privacy-initiative/pull/22).
Local/native-synthetic G1–G4 evidence and the supplemental-negative/fee-receipt
qualification repairs are recorded in the [A1 report](poc-a1-proof-report.md).
G5 tooling and isolated-container rehearsals do not close independent
machine-loss/live-archive recovery. Full independent G5 remains open; G6 is
unauthorized and unexecuted. The requirements below are the specification,
not a claim that A1 is merged or every gate has passed. No A1 funding,
broadcast, node reconfiguration or invariant change occurred.
The [ADR](adr/0003-a1-successor-reserve.md) and
[threat/test matrix](poc-a1-threat-test-matrix.md) define the target and oracles.

## Prerequisite review

[PR #20](https://github.com/olafweller/kaspa-privacy-initiative/pull/20) merged
A0/A0.5 as experimental research evidence at
`3a1efa8db9672025f5282970703cb7256428c1be`. That is the A1 baseline;
re-review intervening A0 changes before depending on them. Merging the experiment
does not establish production readiness or accept RFC-0001.

The ADR now freezes the finite graph, same-owner policy, ordered output layouts,
canonical context, raw selector dispatch, five-push witness ABI, owner fee-credit
accounting, artifact inspection and recovery discovery/topology. Upstream heads
and native limits were rechecked at G0. Recheck compatibility before execution;
changes to frozen rules require documented review, not silent adaptation. Do
not promote the finite experiment into a note system or accept RFC-0001.

## Ordered work packages and gates

| Gate | Deliverable / frozen requirement | Required evidence / dependency |
| --- | --- | --- |
| G0 — specification closure | Closed specification in ADR, matrix and this plan | Raw selectors and opcode framing, exact witness ABI, context bytes/hashes independently calculated, SPK/verifier pins, acyclic graph, artifact/checker/setup-receipt contract, discovery/topology, fee formulas and source-estimated resources are frozen. Closed as specification only; ADR acceptance remains project review. Implementation separately authorized. |
| G1 — integer model and codec | Isolated A1 manifest/state model; byte-format vectors | Independently calculated golden examples, checked sums/ranges, forbidden states/modes, partial payout and rebate. Matrix 01–03, 09. No setup or funding until inconsistent manifests deterministically reject. |
| G2 — finite scripts and real proof | S1-terminal first; S0 continuation and terminal; three fixed setups, independent checker | First falsifier: actual two-VK S0 and one-VK S1 fit the pinned VM, every successful trace executes matching output checks/key/tag20/verifier. Freeze three fully literal real-proof golden transactions and public UTXO contexts. Independent context/R1CS/script inspection plus witnessed final setup receipts required. Original-key one-field mutated context/range negatives must reject; foreign-key rejection separately labeled. Matrix 04–07, 09, 14–15, 18–21, 25. |
| G3 — stateful safety | Native consensus test harness for competing spends and controlled reorgs | Both S0 alternatives first valid independently; at most one accepts; loser has no payout/successor. Distinct-ID locally valid replay rejected for spent input. Rollback restores state and payout accounting together. Matrix 08–10; model and stateless validator alone are insufficient. |
| G4 — adapter and resource qualification | File-only preparation; pinned SDK roundtrip; measurement report | Full validation of final decoded transactions, script-enforced version1/native/gas0/payload0/lock0, adapter sequence/budget policy and ID/full-hash/mass. Measure every branch, actual relay configuration and rational fee/headroom policy. Qualify full accepted-body RPC retrieval/pagination separately from observation trust. Matrix 05–07, 13, 16–17, 20, 22–25. No live submission path needed yet. |
| G5 — independent recovery and adversarial review | Clean-machine terminal proofs from both states; abrupt-loss, archive/page/reorg and artifact-loss tests | Separate original/recovery/chain-archive failure domains; independently retain public artifacts and old S0 locator/checkpoint before continuation. Both terminal spendability A and accepted lineage/accounting B must pass. Disable original services/storage; discover accepted S1, freshly prove and validate. Abrupt loss precedes original S1 pointer/body save. Review invariant rows and setup/observation assumptions. Matrix 10–15, 21–24. |
| G6 — separately authorized TN10 execution | Bounded test-fund runbook and public evidence | Only after G0–G5 pass and live execution is instructed: pre-funding proof, accepted continuation, competing-spend result, clean-machine S1 exit and separate S0 direct exit. Observe actual spentness/payout, exact body, later recheck; do not infer permanent finality. |

Implementation should live in separate `poc/a1/` and A1-specific runner/test
files. Preserve A0 source, its historical evidence and its 30-outcome baseline;
any shared-helper refactor needs independent justification and regression checks.
Suggested A1 boundaries are manifest/accounting, canonical encoding, branch
circuit, script construction, local validator harness, recovery bundle and
optional later native transport. These were proposed responsibilities at G0;
the separate implementation now uses these boundaries without changing the
frozen graph or invariant scope.

G1 implements the frozen schema and compares against the G0 independently
calculated vectors. G2–G5 must reconcile on identical manifest/output bytes.
The independent checker must not import the production serializer/compiler,
and an adversarial reviewer should not author the safety assertion being
evaluated. G0 design closure alone authorized no implementation. The subsequent
explicit G1–G5 instruction authorizes unfunded local falsification, not G6.

## Frozen G0 handoff checklist

| Item | Specification location / implementation obligation |
| --- | --- |
| Selector | ADR: exact raw `00` S0 continue; raw `01` S0/S1 terminal; OP_EQUAL dispatch only. Equivalent pushes permitted. Matrix 18 exhausts bypasses. |
| Witness | Five pushes: tag-high32, tag-low32, proof128, selector1, exact redeem. Depth4 at redeem entry; alternate empty; five verifier inputs derived/ordered as specified. Matrix 19 adds malformed/order vectors. |
| SPK/verifier | Full version-0 standard P2SH reserves and fixed version-0 P2PK recipient. Two S0 keys, one S1 key, Groth16 tag20, five canonical Fr32 inputs. Matrix 20. |
| Context | ADR complete hex vectors: continue 276 bytes, each terminal 226; Python packing/independent literal Node calculation agree on hashes/tags. Codec fixtures are unfunded; G1 compares implementation, G2 compares original constraints. |
| Construction | Fixed S1 -> VK_1t -> D1/SPK1 -> S0 continuation constants/VK_0c; separate S0-terminal VK_0t; D0/SPK0 -> funding -> dynamic inputs. No own-artifact/future-txid/whole-manifest cycle. |
| Inspection | Human manifest and strict `kpi-a1-artifacts/v1`; independent context/compiler/R1CS evaluator/script checker; owner-intent comparison; supervised exact final setup and PK/VK/hash receipt. Proof success alone cannot qualify. Matrix 21. |
| Discovery | Retained `kpi-a1-locator/v1` S0 locator + pre-funding checkpoint. Independent indexed node/archive scans accepted bodies with native v2 Full, or v1 accepted-ID/body join; cursor pagination, pruning and removal/reorg rules. Matrix 22/23. |
| Topology | A original, B clean recovery, C independent chain/archive accessible after A loss. Prefer fully synced local pinned node once independently available; do not await or disturb current sync. G5 records concrete machines/source capabilities. |
| Fees | f0/fc/f1 frozen before funding using actual relay plus 25% quote-rate headroom; B0 >= max(f0,fc+f1) plus 10% refundable credit headroom. No post-funding fee modification/rescue. Matrix 24. |
| Resources/layers | Source limits verified; G0 estimated S0 at 1.2–1.6 KiB, conservative 2-KiB qualification ceiling, one verifier 155000 grams plus surrounding work. G2/G4 measurements were pending at handoff; current measurements are in the report. ADR enforcement map prevents adapter/consensus conflation. Matrix 25. |

G0 closes what must be built and falsified, not circuit/setup correctness or
artifact availability. Concrete A1 artifact bytes, source/checker commits, lock
hashes, budgets/fees and machines are generated/recorded in G1–G5 under this
contract; they cannot be supplied as fictitious G0 measurements. A schema/checker
contract is frozen here; checker code belongs to the separate implementation.

## Measurement and pre-funding checklist

Measure all three branches separately: setup/proving/standalone and Full
verification latency, circuit constraints, isolated prover memory if available,
proof/VK/redeem/signature bytes, actual transaction serialization, compute,
storage and transient mass, executed script units, finite committed budget,
relay floor and fixed-fee headroom. Label estimates versus actual encodings.
S0 stores two VKs but executes one branch; continuation adds an output. A0's
sizes, budget 1700 and 0.2-test-KAS fee are not A1 measurements.

Before funding, prove both S0 branches against the exact planned signed funding
outpoint, roundtrip the transactions through the pinned SDK, and run the actual
Full validator. Generate and validate an S1 terminal proof against the exact
planned continuation output; changing any planned transaction field requires
recomputing its ID and dependent proofs. Also exercise fresh proof generation
after the actual accepted S1 outpoint is independently observed. Pre-generated
fixtures cannot substitute for the fresh recovery proof.

All three branch fees must satisfy the ADR's checked rational relay/fee headroom
rules and <=5-minute quote policy; B0 must cover max(f0,fc+f1) plus 10% refundable
credit headroom. Apply the 10% execution headroom budget formula to measured
script units, then repeat Full validation with final serialization. Rebuild and
reinspect an unfunded instance when changed fees require new constants. Any
failed branch prevents funding.
Fee insufficiency after funding is a documented liveness limit; no principal
haircut, sponsor input or administrator rescue is introduced.

Implement redeem checks for native subnetwork/version, gas/payload/lock time;
validate final decoded fields, full input UTXO context, absent covenant metadata,
exact transaction IDs/full hashes, integer widths and recipient-key control.
Use the ADR's field-by-field enforcement map. Do not claim adapter restrictions are
covenant-enforced. Sequence variants used for competing/replay tests must first
pass full local validation; disabled relative-lock semantics must remain valid.

## Recovery and observation procedure

Use separate instances for the direct-S0 and continued-S1 runs. Recovery uses
the matrix's declared inventory and time limits, on a clean machine without
access to the original filesystem/services and without precomputed exit proofs.
The owner brings the private claim/recipient backup; independently retained
public parameters and C's accepted-history archive authenticate current state.
PK_1t cannot be reconstructed from a hash or regenerated by a fresh setup.
Use ADR discovery exactly: pre-funding checkpoint/S0 locator, fixed scan horizon,
complete cursor pages of accepted DAG-mergeset bodies, strict output/metadata/
proof checks, derived S1 index0 and current UTXO check. Matching S1 address is
insufficient. A gap/pruning failure without an independent archive fails lineage
B; distinguish whether terminal spendability A can still succeed.

Before the later experiment, declare original A, recovery B and chain/archive C,
concrete independently accessible machines, binary/source pins, data-source
capabilities and retention start/horizon. C archives acceptance bodies/pages
before funding, independently of A. Test >one page and no-progress/gap/removal
cases, shutdown immediately after independent S1 acceptance before original
pointer/body save, and reorg rollback of payouts/state together. A separate
directory on A or original-host RPC is not the clean recovery topology.

Prefer a fully synchronized independently operated TN10 node. If only remote
UTXO/acceptance observations are available, document and review that trust route
before execution; matching headers and two URLs are not full local UTXO
validation or proof of operator independence. Uncertain submission saves the
intended ID and halts for reconciliation; it does not automatically retry,
refund, treat pending value as paid, or switch reserve state.

Record acceptance, exact transaction body, current reserve/payout UTXOs,
confirmation policy and later observation. For races and replay distinguish
already-known responses, proof rejection, missing-input rejection and actual
accepted conflicting state. A successful one-user recovery remains narrower
than the roadmap's N-user private-transfer/shutdown gate.

## Evidence and completion criteria

Public evidence should include source/toolchain/upstream pins, artifact hashes,
public manifest/keys/scripts, expected and actual test outcomes by matrix ID,
rejecting layer/errors, resource measurements, accepted bodies/outpoints,
observation trust, recovery inventory/time results and adversarial findings.
Exclude claim secrets, recipient/funding private keys, backup unlock material
and setup randomness. Inspect actual secret values before publication; a keyword
scan alone does not prove absence. Historical A0 evidence remains immutable.

A later local A1 result passes only if G1–G5 succeed for every branch and the
report plainly labels missing live evidence. A live A1 result additionally needs
G6 and every required payout/recovery result. Any bypass, unrecoverable state,
insufficient fee or ambiguous state blocks a success claim. Passing never implies
cryptographic correctness, production safety, anonymity, PQ security or a chosen
production state architecture.

## Original G0 handoff boundary and current execution boundary

G0 was closed as a source-grounded specification with independent codec
calculations and subsequently merged through PR #21 by the project. This does
not accept Candidate A/RFC-0001. The separately instructed implementation has
executed the first two-VK native falsifier successfully and measures S0 at 1289
bytes, one matching verifier and nine combined stack elements. No hard protocol
blocker has been found. The implementation PR remains draft/unmerged.

The report distinguishes model, actual native Full, native stateful consensus,
SDK qualification, same-host namespace recovery and pending independent
machine/archive evidence. Passing local checks or a namespace rehearsal does
not close full G5. Until all G1–G5 pass and a separate G6 instruction is given,
no reserve may be funded. Quotes/configuration must also be refreshed before
future funding; the publicly known recipient fixture key must never be used.

Actual hard protocol incompatibility stops work; failures must not be patched
by weaker output/VK/accounting constraints. All security invariants and trusted
single-party setup/chain-observation limits remain explicit and unchanged.
