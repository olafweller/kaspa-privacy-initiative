# ADR-0003: A1 finite successor reserve and independent terminal exit

**Status:** Proposed — design only; no A1 implementation or execution.

**Date:** 2026-10-03. **Decision owner:** project review.

## Problem and evidence boundary

[A0/A0.5](../poc-a0.md) demonstrated one proof-authorized terminal payout.
[PR #20](https://github.com/olafweller/kaspa-privacy-initiative/pull/20) was
squash-merged into main as experimental evidence at
`3a1efa8db9672025f5282970703cb7256428c1be`. It did not demonstrate that a
surviving liability remains backed and independently spendable after a transition.

A1 asks: can one real-proof partial payout install exactly one authenticated
successor reserve, preserve all remaining owner entitlement, and leave the owner
able to exit from either funded state after the original services disappear?

Propose a finite, same-owner experiment: **S0 → S1 → terminal**, with a direct
**S0 → terminal** alternative. S1 cannot continue. This is an intermediate
fund-safety experiment, not the repository's complete private-value lifecycle or
N-user recovery gate. No notes, nullifiers, ownership transfer, private balances,
new deposits into an existing instance, sponsorship, pool, shards or lanes are
introduced. Candidate A remains experimental; ADR-0001 remains Proposed.

All [I-1–I-16](../../SECURITY-INVARIANTS.md) remain unchanged. The
[matrix](../poc-a1-threat-test-matrix.md) distinguishes tested obligations from
properties this public single-claim fixture cannot demonstrate.

## Alternatives and proposed decision

| Option | Benefit | Cost / decision |
| --- | --- | --- |
| Finite scripts built successor first | Exact successor bytes known before S0 setup; small, reviewable graph | Three branch-specific setups; fixed amounts and recipient. **Proposed A1 baseline.** |
| Reusable state prefix and invariant script template | Could support repeated transitions under a stable verifier | Requires authenticated current-template reconstruction, canonical state encoding and additional script/resource validation. Defer; one successor does not require it. |
| Sharded state or based-app/vProgs settlement | Potential concurrency or batching | Adds ordering, state availability and cross-resource obligations unrelated to this falsifier. Retain under ADR-0001; defer from A1. |
| Terminal-only A0 repetition | Lowest additional complexity | Cannot test surviving liability or successor recovery. Insufficient for A1. |

The finite baseline is not evidence that arbitrary recurring covenants work.
Changing fixed terms requires a new setup and a new unfunded instance. There is
no upgrade, maintainer key, recovery bypass or post-funding key replacement.

## State and exact accounting

All amounts are integer sompi. `L_i` is remaining principal; `B_i` is the same
owner's refundable fee credit. **Total outstanding owner entitlement is
`E_i = L_i + B_i`, and native reserve `R_i = E_i`.** Fee credit is not treasury,
unowned surplus or another user's backing. This explicitly differs from A0's
separate, fully consumed fee-buffer fixture. Only a fixed authorized miner fee
may consume `B`; terminal exit refunds its unused portion to the owner.

| Branch | Exact accepted outputs, in order | Equations |
| --- | --- | --- |
| Continue S0 → S1 | 0: `R1` to exact S1 SPK; 1: `W` to fixed recipient | `0<W<L0`; `L1=L0-W`; `B1=B0-fc`; `R1=L1+B1`; `R0=W+R1+fc` |
| Exit S0 | 0: `P0` to fixed recipient | `P0=L0+B0-f0`; `R0=P0+f0`; remaining entitlement/reserve zero |
| Exit S1 | 0: `P1` to fixed recipient | `P1=L1+B1-f1`; `R1=P1+f1`; remaining entitlement/reserve zero |

Each branch consumes exactly one current reserve input. Every output has
`covenant=None`; there are no extra outputs, change, donations or sponsor inputs.
Require `L0,L1>0`, `0<fc<=B0`, `0<f0<=B0`, `0<f1<=B1`, hence `fc+f1<=B0`.
All amounts and sums must be within pinned native `MAX_SOMPI`
(`2,900,000,000,000,000,000`). Use checked integer arithmetic and sufficiently
wide intermediate sums, never floating point, truncation or equality modulo Fr.

There is no unpaid exit state. A liability reduction occurs only alongside the
actual payout and authorized fee in the same accepted transaction. Proof
creation, submission and RPC acknowledgement do not change settled entitlement.

An illustrative fixture, **not a validated fee quote**, is:

| Quantity | Sompi |
| --- | ---: |
| `L0`, `B0`, `R0` | 1,000,000,000; 60,000,000; 1,060,000,000 |
| `W`; each of `fc`, `f0`, `f1` | 400,000,000; 20,000,000 |
| `L1`, `B1`, `R1` | 600,000,000; 40,000,000; 640,000,000 |
| Direct `P0`; successor `P1` | 1,040,000,000; 620,000,000 |

Continue then exit pays 1,020,000,000 total and spends 40,000,000 in fees;
direct exit pays 1,040,000,000 and spends 20,000,000. Both exhaust exactly R0.
Actual fee constants and finite compute budgets must be selected from measured
branch costs before setup/funding. Fixed fees can later become inadequate:
A1 does not guarantee liveness under arbitrary future fees, and has no fee-bump
or operator override. An unfunded instance must be rebuilt if terms change.

## Acyclic construction and authentication

1. Generate one random 32-byte claim secret `s`, commitment `C=SHA256(s)`, and
   random 32-byte instance identifier. Verify control/recoverability of the one
   fixed native recipient key. The owner and recipient do not change at S1.
2. Check the complete integer manifest. Build S1's terminal circuit/setup,
   pinned verification key, redeem script and full ScriptPublicKey first.
3. Build S0's continuation circuit/setup with the **exact S1 SPK and amount**
   fixed in its context, and S0's direct-terminal circuit/setup. Construct S0
   with two strictly selected branches, each pinning its own verification key.
4. Independently inspect all generated constants, scripts and keys against the
   readable manifest; export and rehearse recovery before funding.

Kaspa P2SH commits the exact redeem bytes using its upstream Blake2b-256
construction; it is not SHA256 over a manifest. S0 pins S1's complete SPK,
including version. Each branch enforces actual transaction input amount,
output count/order, amounts, complete scripts and absent covenant metadata.
KIP-20 lineage is not used as a substitute for those checks.

Neither circuit context contains its own resulting VK or script hash. S1 does
not commit to S0's hash or a future funding outpoint. S0 commits only to the
already built S1 SPK. Outpoints remain dynamic proof inputs; this avoids a
setup/script/funding-ID cycle. A manifest hash authenticates no spend by itself.

## Proposed proof statement and canonical encoding

Retain A0's established Groth16 BN254 / SHA256 preimage relation, with three
distinct branch-specific setups. These remain single-party experimental setups,
not audited ceremonies or production key management. Each branch proves:

```text
SHA256(s) = C
SHA256(branch_context || s || actual_txid32 || actual_index_LE32) = T
```

`branch_context` is fixed at setup and encoded, without optional JSON fields:

```text
ASCII "KPI-A1/TN10/finite/v1" || 0x00
|| TN10_genesis32 || instance32 || stage_u8 || mode_u8 || C32
|| R_LE64 || L_LE64 || B_LE64 || fee_LE64
|| next_R_LE64 || next_L_LE64 || next_B_LE64
|| output_count_u8
|| ordered_output_records
```

Stage is 0 or 1. Mode 0 is continue (allowed only at stage 0); mode 1 is
terminal. Terminal `next_R,next_L,next_B` are zero. Each ordered output record
is `value_LE64 || SPK_length_LE32 || SPK_bytes || 0x00`; the last byte means
absent covenant metadata. `SPK_bytes` is big-endian u16 version followed by raw
script, matching A0/upstream introspection. Continue has exactly two records
(successor, recipient); terminal exactly one (recipient). No trailing bytes,
alternate encodings, unknown stages/modes or nonzero metadata flags are valid.
The manifest additionally supplies the full state graph and all three keys.

Public inputs, in order, remain five canonical 32-byte Fr scalars: txid low
128-bit limb, txid high 128-bit limb, u32 output index, tag low 128-bit limb,
tag high 128-bit limb. Limb integers are little endian; the circuit constrains
all higher bits to zero. No 256-bit digest is reduced modulo Fr. The script
derives the current outpoint inputs from introspection, not caller assertions.

The relation authenticates **fixed public terms**, not arbitrary hidden
accounting. Integer identities must be independently checked before setup; the
script then enforces the exact corresponding actual outputs. A circuit proving
knowledge of `s` cannot rescue inconsistent constants or an unconstrained output.
Passing the circuit alone is not sufficient validation.

Strict branch selector encoding and stack layout must be frozen as golden byte
vectors during the first future script feasibility gate. Require only canonical
selectors 0/1, exact witness shape and no alternative truthy encodings. Failure
to enforce these proposed bytes or resource limits blocks funding and requires
design review; no implementation behavior is claimed here.

## Single spend, state and recovery

The authenticated state is the current accepted reserve outpoint plus its exact
script/amount/branch constants. It is not a Merkle root or a hidden claim set.
Native UTXO consumption orders competing S0 branches. A proof against an old
supplied UTXO may pass stateless validation; current UTXO lookup must prevent a
second accepted transition. Different outpoints, stage, branch, instance or
fixed terms must reject reused proofs. Genesis labeling does not distinguish
identical state copied onto another chain.

On reorg, roll back payout observations and the current-state pointer together,
reconcile the accepted UTXO, and reprove against that outpoint. Never count S0
and S1 as concurrent backing or treat pending payout as settled.

Before funding, independently replicate public proving keys, VKs, exact scripts,
contexts, manifest, source/toolchain/SDK pins and the planned signed funding
locator. After each acceptance, independently archive the authenticated
transaction body/history and current outpoint before removing access to original
services for the orderly recovery test. Also test abrupt original-service loss
immediately after continuation acceptance, before its local archive/pointer
update: the independent recovery environment must discover S1 from the retained
S0 locator and independently available accepted-chain history. This requires
an independent node/archive retaining the accepted transaction body; an orderly
last-minute export is not sufficient evidence. Missing pruned history without
an independent replica is a failed recovery gate, not successful safe recovery.
A hash or pruned UTXO cannot recreate these bytes. Keep
claim secret and recipient recovery keys private and independently backed up;
setup toxic waste is not recovery material. Authenticate public artifacts
against the actual funded script and accepted transaction body, not just their
own checksums. Wrong or missing material must fail closed, never run a new setup.

Demonstrate a fresh terminal proof on a clean machine from **both S0 and S1 in
separate instances**, with the original host/services/storage inaccessible.
No pre-generated proof or original operator assistance is allowed. Record data
inventory, independent infrastructure, time limit, elapsed time and exact payout.
Prefer a synchronized independently operated node for chain observations;
using remote observations must carry explicit A0.5-style trust limits.

## Existing-work review and reuse

The [pinned A0 source comparison](../poc-a0-proof.md#existing-work-comparison-before-implementation)
is the starting evidence, not a claim of new audits. A1 source inspection covered
Rusty Kaspa `01b532e8b553523216471682649693af92f0fd16`, Aztec
`551aa413aec7c497886b567d83674f6e7edfae2f` and RAILGUN
`0aa2d13763a9fcfbb7b7ea9c02e004e71f1394bb`. Other pinned observations below
are inherited targeted A0 reviews; upstream currency must be refreshed before
future implementation. No mature-protocol code is imported by this design.

| Source | Reuse / adaptation / deferral |
| --- | --- |
| [Kaspa P2SH](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/standard.rs), [Groth16](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/groth16/mod.rs), [native limits](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/constants.rs) | Reuse real verifier/Full validation and exact output binding. New branch sizes/costs are unmeasured. |
| [Toccata inline ZK](https://github.com/kaspanet/docs/blob/0ac77d043a802fc8196abfd5812ac2afbd97a2b9/content/docs/toccata/inline-zk.mdx) | Adapt separation of proof, continuation and actual payout checks. |
| [vProgs settlement](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/covenant/src/settlement.rs), [Kaspa research](https://github.com/kaspanet/research/blob/c923faca11a49148fa7d912d27ce00197a5c5a4a/vProgs/main.tex) | Study settlement/availability boundaries. Defer lane/runtime/composition dependencies; reject development-mode proofs as evidence. |
| [Orchard nullifiers](https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/src/note/nullifier.rs) | Defer note/nullifier/key construction; native outpoint consumption is sufficient only for this public single claim. |
| [Aztec nullifier context](https://github.com/AztecProtocol/aztec-packages/blob/551aa413aec7c497886b567d83674f6e7edfae2f/noir-projects/fnd/noir-contracts/contracts/protocol/aztec_sublib/src/nullifier/utils.nr) | Adapt domain binding and pending/settled distinction. Defer trees and discovery. |
| [RAILGUN JoinSplit](https://github.com/Railgun-Privacy/circuits-v2/blob/0aa2d13763a9fcfbb7b7ea9c02e004e71f1394bb/src/library/joinsplit.circom) | Separate authorization, ranges, balance and bound public terms. Its License.md supplies no license; copy no circuit code. |
| [Monero RingCT](https://github.com/monero-project/monero/blob/160e21504aed2a9b6dfdba0970517161383b04e5/src/ringct/rctSigs.cpp) | Adapt explicit range/balance obligations; defer confidential values and ring signatures. |
| [MWEB light clients](https://github.com/litecoin-project/litecoin/blob/ec1b6489a900d09cf5991e220dce089c77a232a2/doc/mweb/light-clients.md) | Adapt explicit recovery data inventory; defer scanning and light-client privacy claims. |

The [existing Kaspa work survey](../../research/existing-kaspa-privacy.md)
remains bounded; A1 does not establish that no comparable implementation exists.

## Threats, objections and acceptance gates

Principal risks are inconsistent generated constants, successor/script or branch
substitution, accepting two competing spends, lost parameters, false chain
observations and fee-induced lockup. Public amounts, recipient, instance,
state linkage and timing reveal this lifecycle. Groth16 setup, host integrity,
SHA256 and non-PQ BN254 remain assumptions; [PQ issue #19](https://github.com/olafweller/kaspa-privacy-initiative/issues/19)
is separate. No anonymity or private-value-conservation claim is made.

The [matrix](../poc-a1-threat-test-matrix.md) and
[implementation plan](../poc-a1-implementation-plan.md) define later gates.
Reject/revisit this proposal if a branch cannot enforce exact successor/payout
bytes within limits, the fixed-fee exit is unaffordable, recovery requires
original services, a malicious parameter manifest can pass review, or stateful
consensus permits duplicate accepted spending. Widening to recurring transitions,
new owners, notes, sponsors or pending exits requires another explicit design
review. This ADR neither accepts ADR-0001 nor authorizes A1 code or funding.
