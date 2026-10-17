# ADR 0009: bounded accelerated BN254 qualification

Date: 2026-10-17. Status: research decision; not production architecture adoption.

## Context

[ADR 0008](0008-specialized-groth16-comparison.md) established compact specialized
wallet proofs but the ordinary Arkworks guest verifier exceeded the original
32M-cycle limit before completing its first valid classification. Its complete
execution cost is unknown. The owner authorized one concrete backend experiment.

## Decision

Qualify the officially documented `substrate-bn` 0.6.0 RISC Zero patch,
`risc0/paritytech-bn` commit `22108fe8c6ea1ebc1358fc4fd6854a6bf46e3509`,
tag `v0.6.0-risczero.0`, with actual SDK 3.0.3 guest execution. Do not infer
compatibility from dependency ranges or documentation. Retain Arkworks as the
reference and as the canonical, curve/subgroup decoder of submitted proofs.
Use a thin adapter to existing scalar/group/pairing APIs, not new arithmetic.

Reuse the exact PR37 setup/VK, proof bytes, complete intents/operations and
native order fixtures. New classifier code has a new expected program identity,
recorded before execution/proving. Preserve all old measurements and evidence.

The [predeclared plan](../../poc/accelerated-bn254/PLAN.md) fixes build/smoke,
practical, execution-only calibration and outer-proving limits. A full 32M-cycle,
600-second profile is required before the one-hour real outer proof. The one
128M/900-second calibration is labelled separately and cannot qualify that proof.
An execution/resource failure is not a valid rejection. Do not upgrade the VM,
weaken decoding or expand into private notes/TN10 transactions to obtain success.

## Sources and consequences

- [Official RISC Zero 3.0 precompiles](https://dev.risczero.com/api/zkvm/precompiles):
  documents the exact patch candidate and profiling/precompile qualification.
- [Pinned patch manifest](https://github.com/risc0/paritytech-bn/blob/22108fe8c6ea1ebc1358fc4fd6854a6bf46e3509/Cargo.toml):
  bigint2 1.4 target dependency with `unstable`. Exact resolved dependencies are
  recorded in both guest lockfiles; they do not establish production stability.
- [Pinned patch arithmetic](https://github.com/risc0/paritytech-bn/blob/22108fe8c6ea1ebc1358fc4fd6854a6bf46e3509/src/arith.rs):
  target-specific field operations call bigint2 precompiles. Dynamic execution
  evidence must establish that path is actually exercised.

Single-party research setup assumptions persist unchanged. No additional secret
witness enters the classifier. Backend qualification is distinct from a complete
classification receipt and from real accepted-lane/native settlement integration.

## Outcome

The [completed measurement](../../poc/accelerated-bn254/RESULTS.md) qualifies the
candidate's build/runtime compatibility and observes its bigint2 path in a
dynamic smoke profile. The full original fixture completes in 117,473,222 cycles
under the separate calibration cap. Practical 32M execution still fails, so the
conditional outer proof is not attempted. No budget is redefined retrospectively.
A future 128M practical phase is a concrete proposed decision, not this result.
