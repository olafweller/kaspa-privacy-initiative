# Kaspa Toccata and vProgs Research Notes

**Last reviewed:** 2026-10-02

**Original source-review scope:** specifications, repository trees, and selected source files. No node, prover, or TN10 transaction was run during that October 2 review. Source inspection establishes implemented interfaces, not end-to-end shielded-pool feasibility or security.

**Later experimental evidence:** the October 3 [A0 report](../docs/poc-a0.md)
records real local proof/consensus-code execution and a live A0.5 terminal reserve
release, accepted-body/payout observation and missing-input replay rejection.
The source-review snapshot below remains dated October 2. Live observations use
two synchronized native RPC endpoints, with own-node genesis/header validation
and explicit remote-observation trust. Full private-state/recovery gates remain
unvalidated.

The October 3 local continuation rechecked Rusty Kaspa/vProgs/research heads;
they still match the pins below. A [read-only TN10 transport preflight](../docs/poc-a0.md#a05-local-continuation-transport-preflight)
reached a synchronized node reporting 2.1.0 through a REST v2.3.0 interface,
but required A0 transaction fields are absent from that schema and genesis
retrieval failed with HTTP 403. The continuation therefore uses the pinned native SDK and an own TN10 node,
with retained-key and full-validator gates before funding. See the linked report
for the current execution status. REST compatibility is not evidence about the
availability of the L1 verifier.

## Source snapshots

Default-branch heads resolved through the GitHub API on the review date:

| Repository | Branch | Commit | Commit date (UTC) |
| --- | --- | --- | --- |
| [kaspanet/kips](https://github.com/kaspanet/kips/tree/e4ae2332117b5cb68bd6188e065ef885b6d17939) | master | `e4ae2332117b5cb68bd6188e065ef885b6d17939` | 2026-07-15 |
| [kaspanet/rusty-kaspa](https://github.com/kaspanet/rusty-kaspa/tree/01b532e8b553523216471682649693af92f0fd16) | master | `01b532e8b553523216471682649693af92f0fd16` | 2026-09-22 |
| [kaspanet/docs](https://github.com/kaspanet/docs/tree/0ac77d043a802fc8196abfd5812ac2afbd97a2b9) | main | `0ac77d043a802fc8196abfd5812ac2afbd97a2b9` | 2026-07-02 |
| [kaspanet/vprogs](https://github.com/kaspanet/vprogs/tree/f9b84a863a7c7c20586a9cf947550475e894f72e) | master | `f9b84a863a7c7c20586a9cf947550475e894f72e` | 2026-07-28 |
| [kaspanet/research](https://github.com/kaspanet/research/tree/c923faca11a49148fa7d912d27ce00197a5c5a4a) | main | `c923faca11a49148fa7d912d27ce00197a5c5a4a` | 2025-09-14 |

These are review snapshots, not a tested compatible dependency set. The latest Rusty Kaspa release resolves to [v2.1.0](https://github.com/kaspanet/rusty-kaspa/releases/tag/v2.1.0), published September 22, 2026; the builder page still displays v2.0.1. Use release metadata and exact source when version details differ.

## Verified capability and its limits

The [Kaspa builder overview](https://kaspa.org/build) reports mainnet Toccata activation on June 30, 2026. Its live feature summary matches these active specifications:

- [KIP-16](https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0016.md): `OpZkPrecompile` (`0xa6`).
- [KIP-17](https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0017.md): covenant opcode extensions and introspection.
- [KIP-20](https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0020.md): covenant IDs, output bindings, and covenant contexts.
- [KIP-21](https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0021.md): lane sequencing commitments.

The [opcode implementation](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/opcodes/mod.rs) contains the verifier and input/output/covenant introspection operations. Current [network parameters](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/params.rs) and v2.1.0 release notes reflect post-Toccata consensus. This supports researching a current-primitives PoC. It does not prove that a particular TN10 endpoint accepts its transaction layout or budgets.

### Exact verifier surface

The [precompile tags and pricing](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/tags.rs) select:

| Tag | Implemented verifier | Constraints observed in source |
| --- | --- | --- |
| `0x20` | [Groth16 over BN254](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/groth16/mod.rs) | Compressed key/proof; scalar-field public inputs; key/input arity checks; reject trailing key/proof bytes; metered key processing. |
| `0x21` | [RISC Zero Succinct receipt](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/risc0/mod.rs) | Claim, seal, journal digest, image ID, control ID/inclusion proof, hash-function ID; currently Poseidon2 only; control proof depth bounded to 8. |

A valid proof must still be constrained by the covenant to the intended key/program, prior state, successor script/root, reserve amounts, and withdrawal outputs. Caller-supplied verification parameters must not let an attacker choose an easier statement.

The source prices base verification at `Gram(140000)` for Groth16 and `Gram(250000)` for RISC Zero Succinct, converted to script units. Groth16 additionally charges `250000` script units per `gamma_abc_g1` key element. These are compute accounting figures, not KAS fees or measured KPI throughput; include transaction/storage mass and surrounding script work in a benchmark.

Rusty Kaspa v2.1.0 includes [the standalone ZK SDK](https://github.com/kaspanet/rusty-kaspa/tree/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/zk-sdk) for proof-to-script tooling. Study its serializers/builders before writing custom encodings. No Halo 2 verifier tag is present in this snapshot; a different proof system needs a supported reduction or consensus support. Setup and confidentiality assumptions belong to the selected construction, not to the generic availability of a ZK opcode.

## Based apps and the current runtime

The [based-app guide](https://github.com/kaspanet/docs/blob/0ac77d043a802fc8196abfd5812ac2afbd97a2b9/content/docs/toccata/based-apps.mdx) separates L1 lane ordering from off-chain execution/proving and covenant settlement. Asynchronous execution does not make an unproven transition settled or an exit withdrawable.

The pinned [vProgs README](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/README.md) explicitly warns of prototype APIs and architecture changes. Inspected surfaces include:

- [L1 bridge](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/l1/bridge/src/bridge.rs): chain-following worker and event interface.
- [Transaction guest](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/transaction-processor/src/main.rs): demonstration resource increments, not a shielded-note protocol. Its callback has a deposit parameter absent from the guide's older sketch.
- [Settlement builder](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/covenant/src/settlement.rs): distinct real-proof and development paths; sequencing/output bindings need review in the path actually used.
- [Runtime withdrawal action](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/action/withdraw.rs): authorization, checked balance debit, and exit emission. This is not evidence of shielded authorization or unlinkability.
- [Permission script](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/api/src/permission_script.rs): destination, payout-amount, continuation, and delegate-change checks.

The [TN10 runbook](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/examples/tn10-flow/scripts/README.md) supplies bootstrap/resume/catch-up procedures and requires replay from the deployment block for fresh catch-up. It defaults to `RISC0_DEV_MODE=1` and a dev redeem. That is useful for plumbing, but cannot establish I-5 proof soundness. Its real-proof instructions use a CUDA build without development mode; that path has not been reproduced here.

The [workspace manifest](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/Cargo.toml) tracks Rusty Kaspa `master`. Pin resolved dependency revisions, lockfiles, guest images, and toolchains for reproducible experiments; do not infer current build compatibility from this review.

## Full vProgs research is a separate evidence layer

The [v0.0.1 draft specification source](https://github.com/kaspanet/research/blob/c923faca11a49148fa7d912d27ce00197a5c5a4a/vProgs/main.tex) discusses cross-program composition, computational dependencies, scope gas, and proposed L1 responsibilities. It is a research design, not a declaration that every described feature is deployed. Candidate C can be evaluated as a single based app without assuming full cross-app vProgs composition is necessary.

## Guide drift and security history

The [references guide](https://github.com/kaspanet/docs/blob/0ac77d043a802fc8196abfd5812ac2afbd97a2b9/content/docs/toccata/references.mdx) is a useful map, but `vprogs/docs/proving-pipeline.md` is absent at the reviewed runtime head. The older `rusty-kaspa/examples/zk-covenant-rollup` path used in guide/history material is also absent at the reviewed node head. Resolve actual tree paths rather than copy obsolete examples.

[vProgs issue #77](https://github.com/kaspanet/vprogs/issues/77) is closed (July 9, 2026). The inspected permission script now checks payout amounts as well as destinations. This is evidence of a changed implementation, not an independent audit or proof that all exit risks are resolved.

## Hypothesis and next validation gates

Candidate A is a plausible smallest experiment because [inline ZK](https://github.com/kaspanet/docs/blob/0ac77d043a802fc8196abfd5812ac2afbd97a2b9/content/docs/toccata/inline-zk.mdx) directly binds a proven transition to a covenant successor. This is our inference; no architecture is accepted.

- [ ] Specify authenticated commitment/nullifier state and atomic deposit/exit accounting.
- [ ] Pin and build a compatible node, SDK, prover, and verifier configuration.
- [ ] Demonstrate a real proof accepted on TN10 with malformed/wrong-program proofs rejected.
- [ ] Measure proof size, proving time/memory, verification budgets, and contention.
- [ ] Test replay, stale settlement state, wrong roots, and cross-pool/lane binding.
- [ ] Specify encrypted note delivery and recovery data; test a clean independent rebuild.
- [ ] Establish permissionless exit after loss of the default prover/state service.

See [RFC-0001](../docs/rfc/0001-state-architecture.md). None of these gates is satisfied merely by a mock/development-mode settlement.
