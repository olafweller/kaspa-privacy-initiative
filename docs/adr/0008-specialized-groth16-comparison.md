# ADR-0008: specialized BN254/Groth16 comparison

Status: Accepted for one local unfunded comparison, 2026-10-17.

## Decision and unchanged statement

Implement the already identified specialized wallet circuit with Arkworks 0.5,
not a Groth16 compression of a RISC Zero receipt. Reuse the PR35 mature-protocol
review and PR36 canonical 570-byte intent, SHA-256 hashes, exact u64 sum/preimage
relation and 96-byte public journal. Pack that identical journal into four BN254
scalar public inputs. Hash the entire intent in the circuit; do not leave unused
intent fields unbound or replace SHA-256 with a cheaper different relation.

Wallet witnesses are the secret, four u64 values and intent bytes. Constrain
each amount to 64 bits and require input > 0 and input = pay + change + fee over
the scalar field, where three u64 terms cannot wrap that field. Match pay/fee
to intent fields and secret/value hashes to intent commitments. Bind the
resulting 96-byte journal, including the entire intent digest, to public inputs.

Use unchanged Arkworks BN254 subgroup/encoding checks and Groth16 verification
as ordinary computation in the outer RISC Zero guest. Pin the exact VK and
prepared VK bytes in that program. The circuit identity is a domain-separated
hash of the VK; preparing a key is a deterministic public optimization. Recompute
and compare prepared parameters from VK in the host/reviewer path. No optional
assumption or host verdict decides acceptance.

Measured optimization: the initial guest spent about 30.4 million cycles loading
and revalidating immutable prepared key data. Export the publicly recomputed,
checked prepared VK in uncompressed form and compile those bytes into the guest;
load those fixed trusted constants without repeating subgroup validation.
The program image binds them. The separate host/reviewer recomputes equality
from the checked VK. This optimization never applies to submitted proofs:
their canonical decoding, curve and subgroup validation remain enabled.

## Setup and scope

Use fresh OS entropy for this one-party, circuit-specific research setup and
wallet proof blinding. Do not publish a predictable seed or serialize trapdoor
scalars. This is not a ceremony, independently audited setup or production
soundness claim. Retain public proving parameters locally with hashes; publish
the VK/prepared VK, proofs and exact source/artifacts needed for verification.
A fresh reproduction creates a new setup/pin, not an upgrade to any funded pool.

The endpoint remains a fixed independently expected local native-ID fixture,
not actual TN10 accepted-lane authentication. The proxy counter, opaque delivery
records and within-batch replay set are not shielded notes, private economics,
cross-batch nullifiers, a native payout or recovery. No funds or broadcasts.

## Budget and completion

Before the expensive run: at most 32,000,000 classifier cycles for the three
operations and at most 3,600 seconds for outer proof production on this Cloud
CPU environment. A budget failure is a measured blocker, not invalidity.
First profile; only if it fits produce one real resolved outer receipt, with
development mode disabled. Verify it in a separate verifier invocation against
the expected root, all three IDs/outcomes and final proxy state.

Repeat actual corrupted-proof and invalid-before-unspent-valid cases, malformed
points/encodings, altered public fields, replay, withheld/substituted/reordered
input and host-verdict controls. The harness must recognize the specific expected
guest assertions; resource/IPC/other runtime failures cannot pass those tests.
Measure setup/wallet/outer time and memory separately, wire size and native masses.
Compare with PR36 without extrapolating unmeasured proving time or monetary fees.
If the budget is exceeded retain the concrete result and recommend the next
design decision without weakening the predicate or inventing a third candidate.

## Observed outcome

The [comparison](../../poc/groth16-comparison/RESULTS.md) produces genuine 128-byte
wallet proofs and 702-byte operations, but the ordinary verifier still hits the
32-million-cycle budget after optimizing immutable key loading. No outer proof
is generated. Compact publication alone does not qualify the full private
protocol or authorize a funded TN10 trial.
