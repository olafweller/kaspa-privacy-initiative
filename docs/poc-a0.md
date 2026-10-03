# PoC A0 — native-KAS reserve release feasibility

**Date:** 2026-10-03. **Scope:** experimental, local evidence; no production protocol.

**Result: partial success, with live TN10 execution blocked.** A freshly generated
Groth16 proof passed the unmodified upstream transaction validator with full
script/mass validation and TN10 parameters. All 28 invalid transaction variants
were rejected. Four circuit tests passed. No funded or observed TN10 spend exists.

## Question and evidence boundary

Can a native-KAS reserve be spent only after a real cryptographic proof verifies
and the transaction meets the covenant's state/output conditions?

A0 exercises a terminal withdrawal against pinned Rusty Kaspa consensus code.
The reserve UTXO supplied locally is a fixture. It has not been funded on TN10.
No transaction was submitted, mined, or observed on TN10, and there are no TN10
transaction IDs. Local validator acceptance must not be described as an on-chain
reserve release. The live-network feasibility question remains open.

The current environment permits upstream/package downloads but has no configured
TN10 RPC endpoint, test funding, or outbound TCP destination grants. Its allowed
HTTP destinations do not include the TN10 seeders in the inspected node config.
No credentials or wallet keys were requested or used. This is an environment
blocker, not evidence that Kaspa lacks the required consensus primitives.

The [experiment decision](adr/0002-a0-reserve-release-experiment.md) records scope
and documentation reconciliation. ADR-0001 remains Proposed. Neither the broader
PoC A nor the repository's permissionless recovery gate is satisfied by A0.

## Exact authorization path

1. The spending input references a native reserve UTXO whose script is P2SH.
2. Kaspa validates the redeem-script hash against that UTXO's locking script.
3. The redeem script fixes the Groth16 BN254 verification key and verifier tag
   `0x20`; the spender cannot substitute an easier proof statement.
4. Transaction introspection enforces one input, one output, the exact reserve
   amount, payout amount, and complete recipient script including its version.
5. The actual input outpoint is bound to the proof's public inputs. The circuit's
   fixed context commits to the domain and claim terms.
6. `OpZkPrecompile` runs the real Groth16 verifier. A malformed or invalid proof
   returns an execution error; successful verification pushes true. Script
   execution must finish successfully under its resource budget.
7. The upstream transaction validator also checks native input/output accounting,
   script execution, mass commitments, and other transaction rules. A live node
   must additionally resolve the actual unspent input, enforce its chain/mempool
   context, and accept the transaction into the canonical ledger.

There is no off-chain approval bit, oracle, operator signature, or receipt server
between proof verification and script authorization. The verification result is
consensus-visible because it is executed inside the spending transaction's
script validation. KIP-20 covenant IDs are not needed for this terminal P2SH
covenant; they do not supply payout/accounting checks automatically.

See [pinned upstream analysis](poc-a0-upstream.md) for exact implementation links
and the checks that local populated-transaction validation does not perform.

## Statement, state, and accounting

The private witness is a fresh 32-byte secret. The circuit proves knowledge of a
preimage of a fixed SHA-256 claim commitment and computes a second SHA-256
authorization tag over fixed context, that secret, and the actual outpoint.
The five public field elements encode the transaction ID in two 128-bit limbs,
the 32-bit output index, and the tag in two 128-bit limbs. All integer widths are
constrained; no 256-bit digest is silently reduced into a scalar field.

The immutable context includes the TN10 domain/genesis, claim state, full payout
script, reserve value, payout value, fee, and terminal-transition marker. These
are circuit constants bound by the circuit-specific verification key; the
covenant checks the matching transaction terms. A different claim requires a
different setup/key in this deliberately inefficient experiment.

The current unspent outpoint represents the live claim state. A valid withdrawal
terminates it. There is no successor, Merkle tree, nullifier, private transfer,
pending exit, or hidden liability ledger. The [proof appendix](poc-a0-proof.md)
specifies encoding, established components reviewed, and limitations.

The invariant remains:

```text
outstanding user liabilities <= native KAS reserved for users
before: liability A; native reserve R = A + F
after valid terminal payout: liability 0; reserve 0; recipient paid A
```

F is a separately funded, explicit experimental miner-fee buffer, not additional
user liability. Exact input and output values fix the fee. No maintainer payment
or alternate withdrawal path exists. A0 assumes the initial claim was correctly
funded; it does not prove a general deposit/claim-issuance mechanism.

## Reproduction

Prerequisites: Linux, Git, Rust/rustup, a C/C++ compiler, libclang, OpenSSL headers,
pkg-config, network access to GitHub and Rust/package registries, and sufficient
memory/disk to build the upstream consensus crate including RocksDB. A typical
Debian/Ubuntu setup uses `build-essential libclang-dev libssl-dev pkg-config`.
Install Rust `1.91.0` with the minimal profile.

From the repository root:

```bash
rustup toolchain install 1.91.0 --profile minimal
./scripts/run_poc_a0.sh
./scripts/run_poc_a0.sh test
python3 scripts/check_docs.py
git diff --check
```

The runner checks out upstream v2.1.0 into the repository parent's
`upstream/rusty-kaspa` directory if absent, then requires exact revision
`01b532e8b553523216471682649693af92f0fd16` and a clean source tree. Existing
checkouts are never reset. Relative path dependencies deliberately use that
layout; `Cargo.lock` pins registry dependencies. Do not run the Cargo command
against an unverified or modified upstream tree.

`CARGO_BUILD_JOBS` defaults to 4. `BINDGEN_EXTRA_CLANG_ARGS` is respected if supplied;
otherwise the runner locates GCC's builtin headers for minimal cloud images.
`LIBCLANG_PATH` is respected or selected from installed LLVM library directories.
Use the runner for both execution and tests to keep native build settings stable.
`CARGO_TARGET_DIR` may select a disposable build-cache location. No secret,
RPC, funding, or wallet environment variable is required by the local harness.
The runner performs no network transaction or GitHub write.

For actual TN10 continuation, first provide a reachable node running the pinned
rules and independently verify its network is `testnet-10` and its genesis.
Build a test-only funding transaction for the generated reserve conditions,
retain the experiment's private witness/proving key locally, obtain the real
funding outpoint, and regenerate the authorization proof for that outpoint.
Then construct and submit the spend, observe its acceptance and confirmations,
and repeat the applicable negative variants against the node. That wallet/RPC
adapter and persistence lifecycle are not implemented here; there is no honest
one-command TN10 reproduction or transaction ID to provide yet. Never fund the
ephemeral local fixture script: the harness discards its secret/setup material.

The [A0.5 live-TN10 handoff](poc-a0-live-tn10-handoff.md) specifies the next local
session's adapter, persistence, pre-funding checks and evidence requirements.

## Executed tests and benchmarks

The [machine-readable run](../poc/a0/evidence/local-run.json) records every case,
actual error, and timing. The [environment record](../poc/a0/evidence/environment.json)
records hardware/toolchain context. The harness calls isolation validation and
`TransactionValidator::validate_populated_transaction_and_get_fee` with
`TxValidationFlags::Full`, production mass parameters, and no verification bypass.
It additionally measures the real metered `TxScriptEngine`. There is no mocked
proof or simulated script interpreter.

The [verification record](../poc/a0/evidence/verification.json) records executed
commands, test counts, and SHA-256 hashes of the tested source/build inputs.

| Case group | Measured result and enforcement layer |
| --- | --- |
| Correct terminal release | Accepted; returned fee 20,000,000 sompi |
| Malformed/trailing proof | Rejected by real Groth16 decoding/integrity checks |
| Wrong state or domain | Independently valid proofs under different setup keys rejected by pinned verifier |
| Replacement verifier/redeem script | Rejected by P2SH identity check (`EvalFalse`) |
| Replay on another txid/index, including index `u32::MAX` | Rejected by Groth16 verification against actual introspected outpoint |
| Wrong recipient or recipient script version | Rejected by covenant (`VerifyError`) |
| Underpayment/overpayment; changed reserve value | Rejected by covenant (`VerifyError`) |
| Extra/missing outputs; valid extra covenant metadata | Rejected by covenant (`VerifyError`), with mass recomputed |
| Extra distinct reserve input | Rejected by covenant input-count condition |
| Duplicate reserve input | Rejected by upstream isolation validation |
| Empty authorization / identity proof | Rejected by stack validation / real Groth16 verification |
| Modified public tag; noncanonical scalar; 31/33-byte scalar | Rejected by verifier/field decoding |
| Zero / `u64::MAX` amount | Rejected by upstream monetary range checks |
| Insufficient compute budget | Rejected by actual script resource meter |
| Exact replay with the same supplied UTXO | **Accepted**, intentionally demonstrating the stateless boundary; no live double-spend rejection was tested |

There are 30 harness cases: one authorized transaction, 28 rejected variants,
and one accepted replay-boundary diagnostic. The four circuit tests separately
check native/gadget SHA-256 agreement at integer boundaries, a wrong secret even
with its recomputed tag, a 128-bit limb overflow, and wrong/overflowing outpoint
indices. These constraints tests are supplementary; the successful path uses a
fresh real proof inside the actual consensus verifier.

| Measurement | Reference run (`local-run.json`) |
| --- | --- |
| Compressed proof / verifying key | 128 / 424 bytes |
| Redeem script / signature script | 576 / 775 bytes |
| Transaction size | 975 bytes, upstream serialized-size **estimate**, not RPC wire capture |
| Fresh setup | 2.285 seconds |
| Main proof generation | 1.089 seconds |
| Standalone Groth16 verification | 2.878 ms |
| Full valid transaction validation | 3.928 ms |
| Executed script units | 15,501,434 |
| Committed input budget | 1,700 units = 170,000 compute grams, plus ordinary transaction costs |
| Transaction compute / storage / transient mass | 171,335 / 20 / 3,900 |
| Default relay-fee floor estimate | 17,133,500 sompi = 0.171335 test KAS |
| Configured reserve / payout / fee | 10.2 / 10 / 0.2 test KAS (local fixture values) |
| Complete harness runtime | 9.122 seconds, including additional wrong-domain/state setups and proofs |

The fee floor is a calculation using the pinned default policy and normalized
non-contextual mass. It is not a mempool admission test. Mass dimensions fit the
pinned TN10 block limits; no actual block was built. Measurements are single
samples on a shared Xeon Platinum 8573C VM with 5 visible CPUs, a 4-core cgroup
quota, and a 16 GiB memory limit, compiled with Rust 1.91.0 release optimization.
Do not infer throughput, mobile feasibility, confirmation latency, or production
fees. Fresh randomness means proof bytes and timings vary between reproductions.

## Review findings and deliverables

The parallel integration, proof, implementation, and adversarial tracks were
reconciled before implementation. Review caught an omitted payout covenant-
metadata restriction and a wrong-state test that mutated the terminal marker
instead of the state ID. Both were corrected and exercised in the final run.
A missing-output fixture initially failed on stale mass; recomputing mass made
it reach the intended covenant rejection. No release bypass was found in the
limited second-pass review; that is not an independent security audit.

- `poc/a0/src/circuit.rs`: actual SHA-256/Groth16 statement and constraint tests.
- `poc/a0/src/main.rs`: fresh setup/proof, P2SH covenant, full upstream validator,
  rejection matrix, and measurements. It has no funding/submission interface.
- `poc/a0/Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`: pinned build inputs;
  package publishing disabled.
- `scripts/run_poc_a0.sh`: verifies the upstream commit and clean tree, then runs
  either the experiment or circuit tests with consistent native build settings.
- `poc/a0/evidence/`: sanitized measurements and environment/source provenance.
- This report, proof/upstream appendices, and ADR-0002: evidence and boundaries;
  architecture/PoC references are updated without accepting ADR-0001.

The source, lockfile, runner, documentation, and sanitized evidence are prepared
for the user-authorized feature branch and draft PR. Build caches and transient logs remain
ignored. No witness, wallet private key, setup secret, API token, or funding
material from a generated experiment is part of the deliverable. Circuit unit
tests contain explicitly synthetic, public, non-funding witness bytes. Publication
does not change the local-only experimental evidence or complete A0.

### Publication review of the actual diff

The final publication review re-read AGENTS.md, the invariants, threat model,
architecture, both ADRs and this report, then inspected both Rust sources,
the runner, manifests/lockfile and evidence. No additional release bypass was
identified and no security-critical code was changed. The earlier fixes remain
in place. This is a limited implementation review, not an independent audit.

The [fresh publication recheck](../poc/a0/evidence/publication-verification.json)
records a second successful 30-case run and four passing circuit tests against
the unchanged source hashes. The benchmark table preserves the original
single-run reference measurement; the recheck is a separate sample.

| Binding | Actual enforcement / limitation |
| --- | --- |
| Reserve outpoint | Script derives txid/index; both enter the SHA-256 circuit relation |
| Protocol, deployment/pool context, prior state | Fixed label and fresh single-claim state ID are circuit constants bound through the pinned VK; no general pool namespace/tree exists |
| Network/domain | Fixed TN10 genesis constant; client must independently verify the connected chain before funding; no genesis-introspection opcode |
| Verifier/program | Compressed VK and tag `0x20` fixed inside P2SH redeem script |
| Recipient/amount | Exact full script/version and payout value checked by introspection; same terms in fixed circuit context |
| Output layout/continuation | Exactly one output; terminal full payment, zero successor reserve and no unpaid claim; partial/continuing exits unsupported |
| Covenant metadata | Payout authorizing-input marker must be `-1` (`covenant=None`) |
| Accounting/fees | Exact one input R and one payout A imply F = R - A; F is separate experimental funding |
| Replay/stale/cross-instance use | Different outpoint/context/key rejected; exact spentness belongs to live UTXO lookup; copied identical chain state remains outside the claim |
| Malformed/range semantics | Canonical 32-byte Fr decoding; 128/32-bit circuit bounds; exact positive amount constants and upstream monetary checks |
| Admin/operator paths | No alternate branch, owner override, key replacement or operator-signature release path; trusted setup remains an assumption |

The live-use hazards are explicit in the handoff: the current recipient key is
discarded inside `policy()`, the outpoint and DAA context are synthetic, and the
fixed fee cannot be increased by adding a sponsor input or reducing payout.
None of these is a live deployment facility. Do not fund before the adapter
retains the original proving material, controls the recipient, verifies TN10,
and checks current fee/policy requirements.

## Security and architectural interpretation

- Groth16 setup is performed locally for the experiment. Its toxic-waste handling
  is not a reviewed ceremony; a malicious setup party could forge proofs.
- The proof depends on BN254/Groth16, SHA-256, arkworks, and pinned Kaspa consensus
  code. BN254/Groth16 is not post-quantum secure. Passing tests is not an audit.
- Witnesses remain in the local process and are not printed or persisted. Memory
  is not hardened/zeroized. A hosted prover receiving the witness would learn it.
- Amounts, recipient, outpoint, claim linkage, fees, and operation timing are
  public. No anonymity, unlinkability, or multi-user privacy is established.
- Exact output checks prevent a proof-valid withdrawal from redirecting or
  underpaying this one claim. They do not establish private supply conservation.
- A TN10 domain literal is not a chain-identity oracle: copied identical state
  on another chain is outside the demonstrated replay boundary.
- A valid proof is reusable against the same supplied local UTXO. Actual replay
  rejection requires live UTXO consumption. Different-outpoint proof rejection
  is a distinct cryptographic condition.
- No independent recovery, pruning, reorg, persistent-state, concurrent-spend,
  mainnet, or continuing-pool claim follows from the terminal experiment.

Candidate A has a concrete direct-verifier path worth testing further. Its
production architecture, proof system, and recovery model remain unaccepted.
Further work must establish live TN10 acceptance, robust circuit/setup review,
general claim issuance/conservation, and reconstructable independent exits.

PQ requirements and migration research are tracked separately in [issue #19](https://github.com/olafweller/kaspa-privacy-initiative/issues/19). This tracking item does not redesign A0.
