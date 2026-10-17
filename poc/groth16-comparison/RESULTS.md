# Specialized Groth16 comparison — 2026-10-17

**Outcome: much smaller wallet proofs, but the selected ordinary verifier does
not fit the agreed 32-million-cycle outer execution budget.** Two real
specialized proofs were generated and reverified. The full three-operation guest
run reaches its limit before a first completed classification is observed.
No outer proof was attempted or produced. This is a bounded research result,
not a demonstrated shielded payment or a rejection of Groth16 in general.

## Measured comparison

Same SHA-256 preimage/value/full-intent predicate, same 96-byte public journal,
u64 semantics, 570-byte intent and native shell as [PR36](../proof-classification/RESULTS.md).
The specialized circuit has **491,548 R1CS constraints**, with four packed scalar
public inputs. R1CS constraint counts and zkVM cycle counts are different units.

| Measurement | PR36 RISC Zero wallet receipt | Specialized BN254/Groth16 |
| --- | ---: | ---: |
| Wallet artifact bytes | 223,418 | **128** |
| Complete proxy operation bytes | 223,992 | **702** |
| Native estimated bytes | 224,257 | **967** |
| Native compute mass | 234,617 | **11,327** |
| Native transient mass | 897,028 | **3,868** |
| Fraction of pinned block transient limit | 89.7028% | **0.3868%** |
| Wallet A proving seconds | 87.06 | **4.30** |
| Wallet C proving seconds | 88.88 | **4.10** |
| Full outer classifier execution | 870,829,938 cycles; 880 segments | **Incomplete at 32,000,000-cycle limit** |
| Outer classification receipt produced | No | **No** |

The complete specialized operation is about **319 times smaller**. This is an
actual encoding/dimension comparison, not admission, transaction fees, monetary
cost, production throughput or a whole privacy protocol measurement. The native
parameters remain compatible pin `01b532e`, with block limits 500,000 compute and
1,000,000 transient. Storage mass, actual signatures/UTXO amounts, real vProgs
metadata and final encrypted notes are not qualified by dummy native shells.

Setup itself took **8.00 seconds**, 9.51 seconds for the measured job, with
maximum individual-process RSS **1,081,952 KiB (1.03 GiB)**. The two-wallet job
took **39.54 seconds**, including checked loading of public proving parameters,
circuit synthesis, proving and verification; maximum individual-process RSS was
**1,559,556 KiB (1.49 GiB)**. The 4.30/4.10 figures isolate proof generation and
must not be presented as complete cold-start wallet latency. The measured setup
uses **94,702,320 bytes (90.3 MiB)** of public proving parameters. No browser,
phone, GPU or independently operated wallet benchmark was run.

## What hit the budget

The first implementation revalidated immutable prepared-key points in every
execution. Debug profiling showed about **30.4 million cycles** at key load.
Exporting verified prepared parameters as immutable uncompressed constants
reduced that point to about **1.93 million cycles**. The host independently
recomputes both compressed and static prepared bytes from the checked VK; the
program image pins them. This does not skip validation of submitted proofs.

The optimized run reaches about **11.48 million cycles** after checked decoding
of the first actual proof, then hits 32 million without a completed
classification log. Ordinary input preparation/pairing work remains beyond the
remaining budget. Stage counts come from the executor's diagnostic cycle API;
they are not cryptographically proven gas accounting. The actual session-limit
error and all stdout/stderr are retained.

The complete specialized classifier cycle count and segment count are unknown;
there is a lower bound, not a valid full-run estimate. We do not claim a cycle
speedup relative to PR36. The one-hour proof budget was never entered because
profiling did not qualify. This pre-agreed research limit is not a theorem that
the route cannot produce an outer proof with another implementation or budget.

## Verification and negative controls

The wallet proofs use the specialized circuit directly, not a RISC Zero receipt
wrapper. Their preimage, checked integer equation, exact public amount/fee,
SHA-256 commitments and complete intent digest are constrained in R1CS. Boundary
tests cover zero input, inflation, `u64::MAX`, overflow, wrong secret and an altered
delivery/intent byte. No cheaper hash or weaker statement was substituted.

The intended main fixture is valid A, a corrupted proof for **unconsumed C**, then
genuine C. Negating its C point preserves canonical on-curve subgroup encoding
but fails actual pairing verification. Host verification confirms both genuine
proofs and rejects the corruption and fourteen public-input mutations. A separate
process reverified the retained proofs and recomputed parameter equality using
only public verification data, without opening proving parameters.

Five guest authentication controls (withholding, substitution, omission,
reordering, trailing host verdict) produce the **specific expected** assertion.
Eight standalone malformed-operation guest executions reject empty/truncated/
oversized encodings, unreduced fields, zero encoding, a deliberately on-curve
wrong-subgroup G2 point, trailing bytes and an oversized declared length, without
changing the proxy balance. These are **single-invalid-operation execution
controls**, not completed valid-invalid-valid or outer-proof tests. Each
submitted proof retains checked canonical/curve/subgroup decoding.

Full guest valid-invalid-valid, replay-after-valid and invalid-then-valid
continuation are **not qualified**: the valid verification budget blocks them.
A resource/IPC failure cannot count as an authentication success. The process-group
wall-time watchdog was also exercised; expiry returns a budget failure.

## Setup and scope

The one-party circuit-specific research setup uses fresh OS entropy. It is not
a public ceremony or production soundness claim; compromised setup randomness
would undermine Groth16 soundness. No predictable seed or trapdoor scalars were
serialized. Public proving parameters remain locally retained and hashed. VK,
prepared/static key data, actual proofs, program and exact source/evidence are
published; verification does not require the large proving parameter file.

The endpoint is still a fixed local ordered native-ID fixture. No new accepted
TN10 lane, settlement, note membership/ownership/nullifier, actual reserve or
private payout is demonstrated. Opaque delivery records are not note encryption.
No testnet broadcast, real fund, signing key, funded output or node service was
touched. Security invariants and legacy/migration/recovery requirements remain.

## Recommendation

Keep specialized Groth16 as the more compact wallet/publication candidate for
further study, **without selecting it as the completed KPI architecture**. The
next bounded decision should examine an existing maintained accelerated BN254
verification backend for the same outer VM, or explicitly reconsider the research
budget using measured evidence. Do not implement custom curve arithmetic or
weaken subgroup, public-input or ordering checks to fit the current cap.

Before connecting the full private note circuit, produce and separately verify
one complete outer classification receipt under declared practical limits. A
proof for an easier malformed-only case would not close this target. Real
accepted-lane/native settlement integration and the conditional TN10 trial stay
gated. Smaller wallet proofs alone do not establish financial privacy.
