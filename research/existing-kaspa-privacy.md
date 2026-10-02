# Existing Kaspa Privacy Work

**Last reviewed:** 2026-10-02

**Scope:** prior forum discussion and selected official upstream source. This is not an exhaustive search of public Kaspa projects, and no privacy demo was reproduced.

## 1. Kaspa Research discussion: optional privacy layer

A [forum post dated September 8, 2026](https://research.kas.pa/t/optional-privacy-layer-for-kaspa-similar-to-litecoin-mweb/522) asks whether Toccata could support an optional privacy domain for native KAS, with transparent entry/exit and confidential internal activity. It mentions covenants, introspection, and proof verification.

This is prior public discussion of the same broad goal. It is a feasibility question, not a protocol specification, deployed implementation, or independent security result. Do not present the optional-native-KAS concept as novel to this repository.

## 2. Toccata primitives and full-vProgs research

The [pinned upstream map](kaspa-toccata-vprogs.md) records active specifications and exact node/docs/runtime/research revisions. The builder page's live-Toccata claim is supported by post-Toccata code/release evidence. It does not establish a complete shielded pool.

The inspected `kaspanet/research` source is the full-vProgs v0.0.1 draft. Its composition and dependency-metering design is research evidence, not a deployed privacy implementation or a mandatory dependency of a single based app.

## 3. Public runtime and exit components inspected

At vProgs commit `f9b84a863a7c7c20586a9cf947550475e894f72e`, the inspected files include:

- [Transaction processor](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/transaction-processor/src/main.rs): demonstration resource increments.
- [Processor with exits](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/transaction-processor-with-exits/src/main.rs): synthetic exit generation for covenant coverage.
- [Runtime withdrawal action](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/action/withdraw.rs): authorization, balance debit, and exit emission.
- [Permission script](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/api/src/permission_script.rs): withdrawal-output and reserve-continuation constraints.
- [TN10 flow runbook](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/examples/tn10-flow/scripts/README.md): settlement/catch-up demo, defaulting to development-mode proving.

These are candidate references for execution and settlement. The reviewed guests/actions do not implement KPI's shielded note/nullifier lifecycle. No independently verified complete shielded native-KAS pool was identified in this limited review; this does not establish that none exists elsewhere or on another branch.

Reuse posture: study proof encoding, settlement bindings, catch-up, and payout checks; adapt only after licensing, compatibility, and security review. Reject synthetic exits or development-mode proof acceptance as evidence of shielded authorization or proof soundness. No code has been imported.

## 4. Historical payout lesson and current status

[vProgs issue #77](https://github.com/kaspanet/vprogs/issues/77) concerned insufficient payout-amount constraints. GitHub reports it closed on July 9, 2026. The reviewed permission script checks destination, payout value, continuation value, and delegate change. Do not present the historical report as a verified current vulnerability.

The enduring lesson is that a correct destination and a valid proof do not by themselves guarantee the correct amount is paid. Inspect all outputs and intermediate exit liabilities. This review did not run the regression suite or audit the entire exit implementation.

## 5. Architecture hypotheses

Our interpretation of current upstream sources is that direct inline-ZK covenants merit investigation before requiring a shared runtime. Batching through a based app may later help throughput. Neither conclusion establishes privacy, safe exits, or recovery. See [ADR-0001](../docs/adr/0001-state-architecture.md).

## Open action items

- [ ] map additional public Kaspa privacy code to exact files, branches, commits, and reproduction steps;
- [ ] reproduce any relevant TN10 privacy demo with real proofs and test KAS only;
- [ ] define the exact opcodes, verifier parameters, and budgets for PoC A;
- [ ] identify which based-app components are necessary for this application and why;
- [ ] complete the mature-protocol reuse/adapt/reject comparison before implementing notes, nullifiers, proving, exits, or scanning;
- [ ] record reusable code licensing;
- [ ] seek builder feedback through the project's normal collaboration process.
