# A1 implementation plan

**Status:** Proposed; design deliverable only. No A1 code, setup, tests, funding
or broadcast has begun. Future execution needs a separate user instruction.
The [ADR](adr/0003-a1-successor-reserve.md) and
[threat/test matrix](poc-a1-threat-test-matrix.md) define the target and oracles.

## Prerequisite review

[PR #20](https://github.com/olafweller/kaspa-privacy-initiative/pull/20) merged
A0/A0.5 as experimental research evidence at
`3a1efa8db9672025f5282970703cb7256428c1be`. That is the A1 baseline;
re-review intervening A0 changes before depending on them. Merging the experiment
does not establish production readiness or accept ADR-0001.

Freeze the finite graph, same-owner policy, ordered output layouts, canonical
context, branch selectors, owner fee-credit accounting and recovery inventory.
Refresh the ADR's pinned upstream/source comparisons before implementation and
record any changed compatibility assumptions. Do not silently promote the
finite experiment into a note system or accept ADR-0001.

## Ordered work packages and gates

| Gate | Future deliverable | Required evidence / dependency |
| --- | --- | --- |
| G0 — design review | Reviewed ADR, matrix and artifact schema | Resolve canonical selector/witness bytes, parameter inspection method, fee policy and independent recovery environment. User authorizes implementation separately. |
| G1 — integer model and codec | Isolated A1 manifest/state model; byte-format vectors | Independently calculated golden examples, checked sums/ranges, forbidden states/modes, partial payout and rebate. Matrix 01–03, 09. No setup or funding until inconsistent manifests deterministically reject. |
| G2 — finite scripts and real proof | S1-terminal first; S0 continuation and terminal; three fixed setups | Verify exact successor bytes, immutable VKs, canonical selectors and all five public-input widths. All three branches pass pinned Full validation. Independent original-context golden tags must satisfy original constraints; one-field-mutated reference tags must not. Separately test foreign-setup/cross-branch proofs against the unchanged funded script. Matrix 04–07, 09, 14–15. |
| G3 — stateful safety | Native consensus test harness for competing spends and controlled reorgs | Both S0 alternatives first valid independently; at most one accepts; loser has no payout/successor. Distinct-ID locally valid replay rejected for spent input. Rollback restores state and payout accounting together. Matrix 08–10; model and stateless validator alone are insufficient. |
| G4 — adapter and resource qualification | File-only preparation; pinned SDK roundtrip; measurement report | Full validation of final decoded transactions, immutable envelope fields and exact ID/mass. Measure every branch and enforce funding gates below. Matrix 05–07, 13, 16–17. No live submission path needed yet. |
| G5 — independent recovery and adversarial review | Clean-machine terminal proofs from both states; abrupt-loss and artifact-loss tests | Disable original services/access; recover all required material, generate fresh proofs, independently validate exact payouts within declared limits. Include loss immediately after continuation acceptance before original-host archival/pointer update; discover S1 independently from the old S0 locator. Review all invariant rows and setup/observation assumptions. Matrix 11–15. |
| G6 — separately authorized TN10 execution | Bounded test-fund runbook and public evidence | Only after G0–G5 pass and live execution is instructed: pre-funding proof, accepted continuation, competing-spend result, clean-machine S1 exit and separate S0 direct exit. Observe actual spentness/payout, exact body, later recheck; do not infer permanent finality. |

Implementation should live in separate `poc/a1/` and A1-specific runner/test
files. Preserve A0 source, its historical evidence and its 30-outcome baseline;
any shared-helper refactor needs independent justification and regression checks.
Suggested A1 boundaries are manifest/accounting, canonical encoding, branch
circuit, script construction, local validator harness, recovery bundle and
optional later native transport. These are proposed responsibilities, not files
created in this design task.

After G1 freezes shared schemas, circuit/script work and reference-vector/recovery
tooling may proceed in parallel with clear file ownership. G2–G5 must reconcile
on identical manifest/output bytes. An adversarial reviewer should not author
the safety assertion they are evaluating. Parallel work never bypasses a gate.

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

All three branch fees must fit measured current policy, and `B0` must cover
both direct exit and continue-plus-exit. Any failed branch prevents funding.
Fee insufficiency after funding is a documented liveness limit; no principal
haircut, sponsor input or administrator rescue is introduced.

Explicitly validate native subnetwork/version, gas/payload/lock-time policy,
full input UTXO context, absent covenant metadata, exact transaction IDs,
integer widths and recipient-key control. Document which checks are consensus,
script, circuit, or adapter policy. Do not claim adapter restrictions are
covenant-enforced. Sequence variants used for competing/replay tests must first
pass full local validation; disabled relative-lock semantics must remain valid.

## Recovery and observation procedure

Use separate instances for the direct-S0 and continued-S1 runs. Recovery uses
the matrix's declared inventory and time limits, on a clean machine without
access to the original filesystem/services and without precomputed exit proofs.
The owner brings private backup material; public parameters/history come from
independent retained copies or authenticated chain data. Public proving keys
cannot be reconstructed from a hash or regenerated by a fresh setup.

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

## Implementation handoff boundary

This proposal is ready for a local implementation agent to assess and complete
G0. It is not an executable script specification with G0 already satisfied.
Before G2, freeze the exact selector opcodes, witness stack order and rejection
vectors. G0 must also specify how a separate reviewer reconstructs branch
constants and inspects their circuit/script use: artifact hashes and successful
proofs alone do not establish that setup encoded the intended relation. Preserve
the stated setup trust assumption. Record the immutable artifact schema, chosen
recovery machine/data source and provisional fee policy before implementation;
actual budgets and fee affordability remain measured G4 gates. A separate user
instruction is required to begin code; this draft does not provide it.
