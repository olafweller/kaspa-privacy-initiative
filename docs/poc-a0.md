# PoC A0 — native-KAS reserve release feasibility

**Date:** 2026-10-03. **Scope:** experimental local and live TN10 evidence; no production protocol.

**Result: the narrow A0.5 terminal reserve-release experiment succeeded.** A real
Groth16 proof authorized the funded TN10 reserve release; the exact 10 test-KAS
payout and consumed reserve were observed through two native RPC endpoints.
A distinct-ID replay was rejected for a missing input. The circuit, covenant,
10.2 / 10 / 0.2 accounting and full-validator flags were preserved. See the
[live result](#a05-live-tn10-result) and [machine-readable evidence](../poc/a0/evidence/a05-live-tn10.json).

## Question and evidence boundary

Can a native-KAS reserve be spent only after a real cryptographic proof verifies
and the transaction meets the covenant's state/output conditions?

The original cloud baseline exercised a terminal withdrawal against pinned
Rusty Kaspa consensus code with a supplied UTXO. One valid fixture and stateless
replay passed; 28 invalid variants failed and four circuit tests passed. That
cloud run had no permitted TN10 endpoint or funded reserve and established only
local execution. Its original measurements and source-review records remain below.

The local continuation reproduced that baseline first, retained fresh KPI claim
and wallet material, and executed A0.5 on TN10. The own pinned node independently
validated genesis and headers, but its large UTXO import remained incomplete.
Live UTXO/acceptance observations therefore come from two synchronized native
RPC endpoints matching the locally validated headers. Their honesty is an explicit
trust assumption; two URLs do not establish independent operators. This is not
local validation of the full live UTXO set, a finality proof or an audit.

The [experiment decision](adr/0002-a0-reserve-release-experiment.md) records scope
and documentation reconciliation. RFC-0001 remains Open. Neither the broader
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
| Exact replay with the same supplied UTXO | **Accepted**, intentionally demonstrating the stateless boundary; no live double-spend rejection was tested in this original baseline |

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

## Original cloud review findings and deliverables

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
  architecture/PoC references are updated without accepting RFC-0001.

The source, lockfile, runner, documentation, and sanitized evidence are prepared
for the user-authorized feature branch and draft PR. Build caches and transient logs remain
ignored. No witness, wallet private key, setup secret, API token, or funding
material from a generated experiment is part of the deliverable. Circuit unit
tests contain explicitly synthetic, public, non-funding witness bytes. That original publication established local evidence only. The A0.5 continuation
and its separate live evidence are recorded below.

### Original cloud publication review of the actual diff

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

The original fixture hazards are explicit in the handoff: its recipient key is
discarded inside `policy()`, the outpoint and DAA context are synthetic, and the
fixed fee cannot be increased by adding a sponsor input or reducing payout.
None of these is a live deployment facility. Do not fund before the adapter
retains the original proving material, controls the recipient, verifies TN10,
and checks current fee/policy requirements. The A0.5 adapter addresses these
requirements separately from the original ephemeral fixture.

## A0.5 local continuation: transport preflight

On October 3, the existing `poc-a0-reserve-release` branch for draft PR #20 was
fetched and continued without changing the circuit, covenant, amounts, budget,
validator flags or upstream/toolchain pins. The lockfile adds two direct names
already present in the graph (`kaspa-addresses`, `borsh`); dependency versions
are unchanged. The original baseline passed before adapter implementation.

The reproducible, read-only [preflight](../scripts/a0_tn10_preflight.mjs) uses
only `https://api-tn10.kaspa.org`; it does not read environment files, generate
keys, construct transactions or submit anything. Run:

```bash
node --test scripts/a0_tn10_preflight.test.mjs
node scripts/a0_tn10_preflight.mjs
```

Exit status 2 means blocked before wallet/funding. Even a complete advertised
schema does not authorize funding: wire preservation, genesis verification,
persistent proving material and exact local spend validation remain required.
The [timestamped public evidence](../poc/a0/evidence/tn10-rest-preflight.json)
records:

- Network endpoint: `kaspa-testnet-10`; virtual DAA score `587081669`.
- Node endpoint: version `2.1.0`, synchronized, UTXO-indexed. The endpoint does
  not report a source revision, so this is not verified node-commit provenance.
- Fee estimate: `100` sompi/gram. At the fixture's 171,335 compute grams, the
  calculated floor is 17,133,500 sompi; the unchanged 20,000,000 sompi fee buffer
  exceeds it. No actual transaction fee or relay acceptance was measured.
- Genesis block query: HTTP `403`, Cloudflare HTML response. Its contents were
  discarded to avoid retaining client/network identifiers. Actual genesis
  verification remains incomplete; the domain constant alone is insufficient.
- Advertised REST version `v2.3.0`: `SubmitTxInput` lacks `computeBudget`,
  `SubmitTxOutput` lacks `covenant`, `SubmitTxModel` lacks `mass`, `gas`, and
  `payload`, and the UTXO response model lacks `covenantId`.

This is supported by the [version-matched REST-server source](https://github.com/kaspa-ng/kaspa-rest-server/blob/e479a5da8dfdb1e3a96105a5460c773dacca4a60/endpoints/kaspad_requests/submit_transaction_request.py):
its model cannot carry the missing fields; its Python-SDK conversion forwards
only `sigOpCount` and supplies mass zero. Its [gRPC input/output definitions](https://github.com/kaspa-ng/kaspa-rest-server/blob/e479a5da8dfdb1e3a96105a5460c773dacca4a60/kaspad/protos/rpc.proto)
also lack compute-budget/covenant fields. Source matching the advertised release
is evidence of a transport limitation, not an independently verified binary
revision or a measured live rejection. No transaction POST was attempted.

REST-server [v2.4.1 source](https://github.com/kaspa-ng/kaspa-rest-server/blob/c638eb5cceff30591cd9b35b241752878a2cfad0/endpoints/kaspad_requests/submit_transaction_request.py)
adds compute-budget/covenant fields but still initializes mass to zero in this
conversion. An API version upgrade alone is not evidence of exact A0 support.
Prefer a current TN10 node's native wRPC/gRPC interface with exact transaction
and UTXO round trips; then verify genesis, validation context and acceptance.

The KasPact generic environment, wallet, balance and transfer scripts were
inspected. Its transfer serializer carries `sigOpCount`, omits A0's budget/mass/
covenant fields, and converts u64 sequences to JavaScript `Number`. Reusing it
unchanged could lose A0's `u64::MAX` sequence precision as well. No KasPact code,
configuration, secrets, database or historical artifacts were copied. The new
preflight/benchmark tooling is original KPI code and requires no KasPact checkout.
Existing `.env.*` ignore protection was checked before any wallet work.

### Native adapter and pre-funding checks

The supplied REST route is not used for transaction submission. The new
[orchestrator](../scripts/a0_tn10.mjs) uses the official v2.1.0 Node SDK and a
loopback-only v2.1.0 TN10 node for independent genesis/header validation.
Two explicit synchronized public native-RPC endpoints supply and corroborate
live UTXO/acceptance observations while the own node imports its large UTXO set.
This remote observation trust is explicit in ADR-0002; it is not local full-UTXO
validation or proof that the two services have independent operators. [Setup](../scripts/setup_a0_tn10.sh) verifies the
release archive SHA-256 values. The [runbook](poc-a0-tn10-runbook.md) records
reproduction and stop/resume boundaries.

The file-only Rust adapter calls the original circuit, redeem script and full
validator. It retains a fresh claim, proving key, matching VK and public terms
outside Git with restricted permissions and a reload-verified local backup.
Separate KPI funding and recipient keys remain in ignored `.env.tn10.local`.
No KasPact secret is copied. A future contributor can use any authorized TN10
funding source with the documented environment fields.

The live P2SH address is derived from the original redeem bytes using upstream
`pay_to_script_hash_script` and `extract_script_pub_key_address`. SDK field
roundtrips preserve u64 values as BigInt/decimal strings, the v1 compute budget,
full output scripts, explicit absent covenant metadata and storage mass. The
SDK transaction ID is recomputed rather than trusting an optional cached ID.
Missing metadata, malformed widths and altered IDs fail closed.

Before any reserve funding, the signed funding transaction determines the exact
future reserve outpoint. A fresh proof under the retained original key spends
that exact output; the SDK reconstruction is then passed through the same full
validator. After funding acceptance, the actual unspent output, DAA score and
median time are read again before generating the release. One input, one payout
and the original 10.2 / 10 / 0.2 test-KAS accounting remain mandatory.

Submission alone is insufficient. The observer requires accepted transaction
IDs with accepting-block blue-score distance from the sink greater than 20 and the exact payout UTXO, then checks
that the reserve disappeared and compares the accepted block transaction body
field by field. A later recheck is required. This observation policy is not a
finality proof. Exact and distinct-ID replay attempts separate cached/already-known
responses from spent-input rejection; the latter replay first passes full local
validation against the original supplied UTXO.

At this checkpoint the local signed funding fixture and retained-key reserve
proof roundtrip pass. The own node has validated headers and is importing its UTXO set. Both public
RPC endpoints report synchronized TN10/2.1.0 and match three locally validated
headers. All broadcast paths require those identity checks and a review tied to
the current source/binary hashes.
The subsequent live result and exact identifiers follow.

### Repeated local measurements

[Five baseline samples](../poc/a0/evidence/local-host-benchmark.json) were collected
on an Intel i7-1165G7 (8 logical CPUs), Linux Mint 22.3, kernel 6.8.0-142, Rust
1.91.0 release build. Each sample reran fresh setup/proving and all 30 expected
outcomes. The host was shared with other work; these are latency samples, not
throughput measurements.

| Measurement | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: |
| Setup (ms) | 2859.887 | 2873.487 | 4417.833 |
| Proving (ms) | 990.104 | 1034.974 | 1840.455 |
| Full valid-transaction validation (ms) | 7.262 | 8.223 | 12.779 |
| Whole-harness maximum RSS (KiB) | 265572 | 271008 | 284020 |

The proof is 128 bytes, VK 424 bytes, redeem script 576 bytes and signature
script 775 bytes. The 975-byte upstream transaction estimate is not an actual
RPC capture. Compute mass is 171335 grams, transient mass 3900 and storage mass
20; the fixed budget is 1700. Actual live RPC frame size and fee remain separate
measurements. Whole-harness RSS is not isolated prover memory. These results do
not establish cryptographic correctness or compare equivalent work with RISC Zero.

## A0.5 live TN10 result

The [sanitized live artifact](../poc/a0/evidence/a05-live-tn10.json) includes the
public manifest/VK/redeem, actual funding and release transactions, proof/public
inputs, observed UTXOs, native submission receipts and frame sizes, accepted-body
readback, exact replay errors, later observations and the adversarial review.
Private wallet/claim/proving material is excluded. The local cold bootstrap did
not finish its UTXO import; it later restarted that phase when the pruning point
advanced. The experiment node was stopped after the RPC observations, retaining
its ignored data and the separate wallet/proving backup. No local full-UTXO
validation is claimed.

| Event | Identifier / result |
| --- | --- |
| Fresh KPI wallet bootstrap, 12 test KAS | `27a70f75bd135a1e899160c43af5f00be44db87c1954148dd36bb71864c06c9a` |
| Reserve funding | `67aab5bfb85e9fb1fb6eaa08c6216ca44ed98c823d4d1141361ac75be0db004f` |
| Actual reserve outpoint | `67aab5bfb85e9fb1fb6eaa08c6216ca44ed98c823d4d1141361ac75be0db004f:0` |
| Reserve release / payout output 0 | `29d875bbdf31cb14205b6f429d63c475b9ad85e558e932b1c70ff1dbc0e2b554` |
| Release-containing block | `c38a5439db59c5768e62a37d162f19cd04c4802a8a2e33a35a80050fa3c76210` |
| Accepting block | `c8dc02dd15e6451ff328eb3708d00a1b638bd004e5ad98a2405a76a2de431a6f` |
| Acceptance/UTXO observed | 2026-10-03 17:56:52.669 UTC; DAA 587174865 |
| Later recheck | 17:59:21.269 UTC; 153.474 s since submission; DAA 587175971 |
| Distinct-ID replay | `a50d798017854a931ab7a9d570ace689796b70815ea2860ed6c86a36bd1dfade` |

The fixed reserve address was
`kaspatest:pqc9cdt4u94f4yf4lxxawr9mz6ypc53rypc72mm2phtulartxmvhw2lxjzegy`.
The controlled recipient was
`kaspatest:qr33u5pnjefh90vcgfc8dexl8re3kuv2ulys0skqhqxup2erjvly2s38lsrz4`.
The accepted body exactly matches the locally validated SDK transaction: one
10.2 test-KAS reserve input, one 10 test-KAS output to that fixed full script,
`covenant=None`, 0.2 test-KAS fee, no successor or extra output. Both endpoints
reported the same accepting block and exact body/payout; the reserve was absent
and no distinct-replay payout existed. A later read-only
[public REST-index response](https://api-tn10.kaspa.org/transactions/29d875bbdf31cb14205b6f429d63c475b9ad85e558e932b1c70ff1dbc0e2b554)
also reports the same accepted block, outpoint, proof bytes, v1 budget and payout.
Its previous-input amount is absent; native funding/UTXO records supply that value.
This does not establish REST write compatibility or provider independence.
The later native check adds 1106 virtual DAA
score over the first acceptance observation, not a permanent-finality claim.

Exact replay returned `was already accepted by the consensus`. The distinct-ID
variant changed sequence from u64::MAX to u64::MAX-1 and first passed full local
validation against the original supplied UTXO. Its node error was
`is an orphan where orphan is disallowed`. The [pinned mempool path](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/validate_and_insert_transaction.rs)
maps `RejectMissingOutpoint` to that error when orphans are forbidden. Combined
with the known funded output, accepted consuming transaction and absent reserve,
this is evidence of spent-input rejection. The error does not itself say
“double spend”, and proof invalidity is not the rejection cause. This resolves
the precise spentness boundary that the stateless local fixture could not test.

| Live measurement | Result / scope |
| --- | --- |
| Proof generation | 889.026 ms, one retained-key live sample |
| Full local release validation | 10.380 ms |
| Proof / VK / redeem / signature | 128 / 424 / 576 / 775 bytes |
| Consensus Borsh transaction encoding | 965 bytes; not the RPC wire encoding |
| Captured native-wRPC submission message | 998 bytes including RPC envelope; excluding WebSocket/TCP/TLS framing |
| Upstream estimated transaction size | 975 bytes; an estimate, not the captured message |
| Compute / storage / transient mass | 171335 / 20 / 3900 grams |
| Actual reserve-release fee | 20000000 sompi = 0.2 test KAS |
| Ordinary bootstrap / reserve-funding fees | 815400 / 704700 sompi |
| Broadcast to accepted-ID and exact-UTXO observation | 4851 ms, with blue-score-distance >20 policy |

Node/SDK release: 2.1.0; source revision:
`01b532e8b553523216471682649693af92f0fd16`; Rust 1.91.0;
arkworks BN254/Groth16 0.6.0; Node 22.22.3. The source/binary pins apply to the
local validator, SDK and own node; remote endpoints report 2.1.0, but their
executable hashes were not measured. Archive/binary hashes, local environment
and five independent baseline samples are in the linked artifacts. Whole-harness
RAM measurements are not isolated prover RAM or local-node memory.

### Adapter changes and post-live review

No circuit, covenant, amount, budget or full-validation rule changed. The live
adapter adds retained key/claim material, controlled recipient ownership, P2SH
address derivation, actual outpoint/UTXO context, exact SDK serialization and
accepted-body checks. The public-RPC observation trust is documented separately.

Two transport hazards were caught before reserve funding: the SDK may retain a
supplied cached transaction ID, and its ordinary v0 generator commits overall
mass where TN10 requires the storage component. IDs are explicitly recomputed;
the v0 mass component is corrected using upstream code with exact integer-range
checks, then signatures/accounting/full validation are checked unchanged. Saved
genesis u64 fields also require explicit bounded BigInt restoration after pruning.

The initial highest-priority fee estimate exceeded the fixed release fee, but a
lower bucket fitted it with a subsecond estimate. The reviewed policy accepts a
bucket fitting the unchanged fee with at most 30 seconds estimated inclusion,
above the pinned relay floor. Actual inclusion was then observed; the estimate
was not treated as a guarantee. No accounting or proof change was needed.

The post-live adversarial review found no added inflation, payout-redirection,
extra-output, key-substitution or privileged-withdrawal path. Sequence can vary
without changing the authorization terms, intentionally used for the distinct-ID
replay; copying a proof cannot redirect the fixed payout. Dependency failure can
halt operation. Persistent local backup does not establish independent recovery.
All value/timing links are public; Groth16 trusted setup, unaudited code, non-PQ
security, local-host integrity and remote observation honesty remain assumptions.
Seven Rust tests (four circuit, three adapter) and thirteen Node tests (nine SDK/
policy, four preflight) pass alongside the preserved 28-invalid-variant baseline.

### Recommendation for A1, not implementation

Review this A0.5 evidence first. Then define an A1 ADR/test matrix for **one
authenticated successor reserve/state with explicit liability conservation and
an independently executable terminal exit**. Test competing transitions, stale/
wrong-state and cross-instance proofs, fee accounting and recovery without the
original operator. Revisit the existing mature-protocol/Kaspa work before choosing
state/note/nullifier machinery. Do not infer a private multi-user pool, select
Candidate A, or begin A1 from this terminal success alone.

## Security and architectural interpretation

- Groth16 setup is performed locally for the experiment. Its toxic-waste handling
  is not a reviewed ceremony; a malicious setup party could forge proofs.
- The proof depends on BN254/Groth16, SHA-256, arkworks, and pinned Kaspa consensus
  code. BN254/Groth16 is not post-quantum secure. Passing tests is not an audit.
- Witnesses are not transmitted to RPC services or published. The live adapter
  deliberately persists restricted local claim/proving material and a backup.
  Memory is not hardened/zeroized; a hosted prover would learn the witness.
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
Live A0.5 improves the credibility of the direct L1 authorization path specifically.
Further work still requires robust circuit/setup review, general claim issuance/
conservation, and reconstructable independent exits. No A1 implementation began.

PQ requirements and migration research are tracked separately in [issue #19](https://github.com/olafweller/kaspa-privacy-initiative/issues/19). This tracking item does not redesign A0.
