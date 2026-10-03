# ADR-0003: A1 finite successor reserve and independent terminal exit

**Status:** Proposed — G0 specification closed; acceptance remains project review.
Design only: no A1 implementation, setup, funding or broadcast. G1–G6 are unexecuted.

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
branch costs before the final setup/funding (an unfunded qualification build may
be discarded). Fixed fees can later become inadequate:
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
output count/order, amounts, complete scripts and absent output covenant metadata.
KIP-20 lineage is not used as a substitute for those checks.

Neither circuit context contains its own resulting VK or script hash. S1 does
not commit to S0's hash or a future funding outpoint. S0 commits only to the
already built S1 SPK. Outpoints remain dynamic proof inputs; this avoids a
setup/script/funding-ID cycle. A manifest hash authenticates no spend by itself.

## Frozen proof statement and canonical encoding

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

The selector is a separate witness byte, never part of the context serialization.
The following G0 specification freezes its meaning, the verifier ABI and the
construction/inspection/recovery contracts. G2 must falsifiably implement them;
the specification is not evidence that an A1 script has executed successfully.

## G0: selector, witness and mandatory execution

All three reserve/payout SPKs have **version 0**. S0 and S1 are standard P2SH:
full introspection bytes `0000 || aa20 || Blake2b256(redeem) || 87` (37 bytes,
35 script bytes). Use the unkeyed upstream Blake2b-256 construction. The fixed
recipient is standard Schnorr P2PK: `0000 || 20 || xonly_pubkey32 || ac`
(36 bytes, 34 script bytes). Its recovery key must produce that exact public key.
No unknown SPK version, caller-selected VK, alternate verifier or admin branch.

### Selector bytes and dispatch

| Path | Accepted raw selector element | Context stage / mode | Immutable key |
| --- | --- | --- | --- |
| S0 continuation | exactly one byte `00` | `00 / 00` | `VK_0c` |
| S0 direct terminal | exactly one byte `01` | `00 / 01` | `VK_0t` |
| S1 terminal | exactly one byte `01` | `01 / 01` | `VK_1t` |

Empty bytes are **not** the continuation selector. Raw byte equality determines
dispatch; do not apply OP_IF or numeric equality directly to the witness selector.
For S0, after an entry `OP_DEPTH 4 OP_NUMEQUALVERIFY`, the mandatory dispatch is:

```text
OP_DUP <literal byte 00> OP_EQUAL OP_IF
    OP_DROP
    CONTINUE_0_CHECKS_AND_VERIFY
OP_ELSE
    <literal byte 01> OP_EQUALVERIFY
    TERMINAL_0_CHECKS_AND_VERIFY
OP_ENDIF
```

For S1: `OP_DEPTH 4 OP_NUMEQUALVERIFY <literal byte 01> OP_EQUALVERIFY
TERMINAL_1_CHECKS_AND_VERIFY`. The S0 dispatch framing is byte-exact
`74 54 9d 76 01 00 87 63 75 [continue body] 67 51 88 [terminal body] 68`;
S1 framing is `74 54 9d 51 88 [terminal body]`. OP_EQUAL generates the only
boolean consumed by OP_IF. The original selector is consumed in either arm.
There is no final unconditional OP_TRUE, early successful return, or alternate
path around a body. Each body must execute all of its output checks and its own
literal VK followed by Groth16 verification. Finishing merely true without that
execution fails G2, even if an upstream engine would accept such a script.

Equivalent **push-opcode encodings producing the same element bytes are
permitted**, subject to native push-only/size/budget rules. No extra
signature-script minimal-push restriction is added. The adapter emits shortest
pushes, but that is a serialization preference, not a safety boundary. Thus
`01 00`, `4c 01 00`, `4d 01 00 00` all select continuation; `51`, `01 01`,
`4c 01 01`, `4d 01 00 01` all select terminal. `00` as an opcode produces an
empty element and rejects. Noncanonical *element values* remain forbidden.

Golden selector oracle (with otherwise valid matching branch proof/transaction):

| Element hex | S0 result | S1 result |
| --- | --- | --- |
| `00` | continue | reject |
| `01` | terminal | terminal |
| empty; `80`; `02`; `81`; `ff`; `0000`; `0100`; `0080`; `0180`; `0001` | reject each | reject each |

The rejected set deliberately includes false/negative-zero encodings and values
that OP_IF treats as true. Exhaust all 256 one-byte values and representative
multi-byte values in G2. A selector that chooses a legitimate branch with a
proof from another branch must fail that branch's immutable VK verification.

### Witness ABI and stack trace

Signature script executes exactly **five pushes**, in this order (bottom first):

| Push position | Element | Length / rule |
| --- | --- | --- |
| 0 | `T_hi_Fr` = `T[16:32]` followed by zero16 | exactly 32 bytes, canonical BN254 Fr, 128-bit range |
| 1 | `T_lo_Fr` = `T[0:16]` followed by zero16 | exactly 32 bytes, canonical BN254 Fr, 128-bit range |
| 2 | compressed Groth16 proof | exactly 128 bytes; validated point/serialization encoding, no trailing bytes |
| 3 | branch selector | exactly one byte from the path table |
| 4 | exact current-state redeem script | exact artifact bytes and length `len(D0)` or `len(D1)`, checked by P2SH |

There are no witness outpoint limbs, public-input count, VK, mode, C, recipient,
fee or successor arguments. The upstream VM requires a push-only signature
script. P2SH authenticates/pops the last element and invokes the redeem with
main stack `[T_hi_Fr, T_lo_Fr, proof, selector]` and empty alternate stack.
Entry depth 4 rejects extra/missing elements before any branch verification.

Every body starts with main `[T_hi_Fr,T_lo_Fr,proof]`. Require proof length 128
using OP_SIZE / OP_NUMEQUALVERIFY, then OP_TOALTSTACK. Require both remaining
elements' lengths 32 without changing their order (OP_SIZE checks low, then
OP_OVER / OP_SIZE checks high, then OP_DROP discards that duplicate). The
verifier enforces canonical field encodings; the circuit enforces upper bits
zero. Do not accept shorter script-number encodings of Fr scalars.

Derive index from input 0 with OP_OUTPOINTINDEX, encode to 8 bytes with
OP_NUM2BIN and append zero24; derive txid via OP_OUTPOINTTXID using upstream
`Hash::as_bytes()`, split `[16:32]` then `[0:16]`, append zero16 to each. Do not
reverse displayed hash hex speculatively. These script-derived scalars, not
witness assertions, populate the first three verifier inputs.

```text
Before OP_ZKPRECOMPILE, main stack bottom -> top:
[T_hi_Fr, T_lo_Fr, index_Fr, txid_hi_Fr, txid_lo_Fr,
 05, proof128, matching_VK424, 20]
Alternate stack: empty (proof retrieved with OP_FROMALTSTACK)
Verifier pop order: tag20, VK, proof, count5,
 txid_lo_Fr, txid_hi_Fr, index_Fr, T_lo_Fr, T_hi_Fr
Verifier public order: [txid_lo, txid_hi, index, T_lo, T_hi]
After successful verification: main [01], alternate empty
```

`05` above is the *element* encoding the fixed input count, emitted by OP_5
(`55`). Verifier tag is the raw element `20`, emitted `01 20`, and verifier
opcode is `a6`. Each VK has six `gamma_abc_g1` elements: one constant plus five
public inputs. S0 embeds **both** `VK_0c` and `VK_0t`; S1 embeds `VK_1t`. None
comes from the witness. Branch epilogue is `55 6c 4d a8 01 [VK424] 01 20 a6`.
Returning OP_ZKPRECOMPILE's true result leaves exactly one main element; all
branch scratch items must be consumed. Native script-boundary clearing of the
alternate stack is not permission to hide leftover witness items there.
G2 traces must inspect it before the redeem boundary clears it.

### Canonical byte examples and rejection vectors

Notation `x{n}` means exactly n repetitions; brackets name exact opaque artifact
bytes, not an extra serialized field. For any generated accepted branch:

```text
20 [T_hi_Fr32] 20 [T_lo_Fr32] 4c 80 [proof128]
 01 00                                  # S0 continue
 PUSH(D0)

20 [T_hi_Fr32] 20 [T_lo_Fr32] 4c 80 [proof128]
 51                                     # S0 or S1 terminal
 PUSH(D0 or D1)
```

`PUSH(D)` uses shortest size encoding: for 256..65535 bytes,
`4d || len(D)_LE16 || D`; no serialization of a separate length element.
Scalar pushes are `20`, proof push `4c80`. For the continuation context vector
below, the first 66 bytes are
`20 4331dae1d419f006d37bac1a4e5894df00000000000000000000000000000000
20 a552c701f0f1a1c25622cb95ea966c8c00000000000000000000000000000000`.

A completely specified **encoding-only**, intentionally invalid scaffold is:
`20 00{32} 20 00{32} 4c80 00{128} 0100 0151` (200 bytes), or terminal variant
`20 00{32} 20 00{32} 4c80 00{128} 51 0151` (199 bytes). Here D=`51` is an
unsafe OP_TRUE placeholder, **not an A1 script**; neither example may be funded
or count as a positive verification control. A literal real A1 proof/redeem
golden transaction cannot exist before G2 setup. G0 freezes serialization and
selector positives; G2 must retain one fully literal successful vector per
branch, with proof, VK, redeem and all transaction/UTXO bytes.

| Mutation of a matching valid G2 vector | Mandatory rejecting layer |
| --- | --- |
| Remove each of five elements separately | P2SH or entry depth/shape; never successful |
| Insert an extra empty/nonempty element at each position | P2SH or entry depth; no hidden alt-stack allowance |
| Swap proof/selector, proof/tag, selector/redeem, or high/low tag | Shape/selector/P2SH or actual verifier; high/low control must use unequal limbs |
| Supply empty or any forbidden selector bytes above | Raw dispatch equality |
| Tag size 0,16,31,33,64; scalar >= Fr modulus; nonzero upper 128 bits | Script length, canonical verifier parsing, or circuit range respectively |
| Proof size 127/129, malformed point, trailing proof bytes | Script length or real Groth16 parsing/verification |
| Continue proof with terminal selector, terminal proof with continue selector, S0 proof at S1 | Matching branch's immutable Groth16 VK (make outputs match selected branch first) |
| Push caller VK/count/mode or derived outpoint limbs | Entry depth, not a witness-selected statement |
| Same selector bytes via alternate push encodings | Positive, if native resource rules pass |

### Mandatory transaction constraints

Before verification each selected body checks actual input count 1, current
input index 0 and input value `R_i`; actual output count and every ordered
output value and full SPK equal the accounting table. Every output's
OP_OUTPUTAUTHORIZINGINPUT must equal -1, which tests **absence** of metadata;
testing only a zero covenant ID is insufficient. The expected reserve input
also has `covenant_id=None`, checked at funding and recovery; OP_INPUTCOVENANTID
maps None to zero and cannot by itself distinguish None from Some(zero).

Common redeem envelope checks are transaction version 1 (OP_TXVERSION), native
subnetwork 20 zero bytes (OP_TXSUBNETID), gas 0 (OP_TXGAS), payload length 0
(OP_TXPAYLOADLEN), lock time 0 (OP_TXLOCKTIME). These checks may precede dispatch
without disturbing the four witness elements. The dispatch framing above
omits these stack-neutral checks, not their mandatory execution.
Sequence and exact compute budget are treated separately below. Full native
validation remains necessary; a supplied local UTXO does not prove live spentness.

## G0: independently checked context vectors

The encoding above is frozen as `KPI-A1/TN10/finite/v1`, with a terminating NUL.
Offsets (zero based) are: label/NUL 0..21; genesis 22..53; instance 54..85;
stage 86; mode 87; C 88..119; R 120..127; L 128..135; B 136..143;
fee 144..151; next_R 152..159; next_L 160..167; next_B 168..175;
output_count 176; output records begin 177. Each record is exactly
`u64LE value || u32LE full_SPK_length || full_SPK || 00`, with no alignment.
Full SPK length includes the two version bytes; context stage/mode are raw u8,
not script-number encodings or selector opcodes. Reject trailing data, truncated
fields/records, unknown version/stage/mode, lengths inconsistent with records,
nonzero metadata marker, S1 continue, nonzero terminal next-state fields and
count/order/value/SPK disagreements with the frozen branch terms.

The codec vectors use the illustrative amounts above; instance=`00..1f`;
public test secret=`20..3f`; C=
`72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084`;
dynamic txid=`40..5f` in `Hash::as_bytes()` order and index=7 (`07000000`).
Recipient full SPK is
`00002079be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac`.
Synthetic successor full SPK is `0000aa20 || aa{32} || 87`.
These public test-only values must never control funds; the synthetic successor
is a codec fixture, not evidence of an A1 key/script construction.

Golden complete contexts (concatenate hex lines, no spaces or newlines):

```text
S0 continue (276 bytes):
4b50492d41312f544e31302f66696e6974652f763100
f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370
000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
0000
72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084
00512e3f0000000000ca9a3b000000000087930300000000002d310100000000
00a02526000000000046c32300000000005a62020000000002
00a0252600000000250000000000aa20
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa8700
0084d7170000000024000000000020
79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac00

S0 terminal (226 bytes):
4b50492d41312f544e31302f66696e6974652f763100
f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370
000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
0001
72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084
00512e3f0000000000ca9a3b000000000087930300000000002d310100000000
00000000000000000000000000000000000000000000000001
0024fd3d0000000024000000000020
79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac00

S1 terminal (226 bytes):
4b50492d41312f544e31302f66696e6974652f763100
f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370
000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
0101
72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084
00a02526000000000046c32300000000005a620200000000002d310100000000
00000000000000000000000000000000000000000000000001
0073f4240000000024000000000020
79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac00
```

| Branch | SHA256(context) | T = SHA256(context \|\| s \|\| txid \|\| index_LE32) |
| --- | --- | --- |
| S0 continue | `0af7df62cf63215e4c4388f114c3582a737996978c2b976451205664a0fe6ed5` | `a552c701f0f1a1c25622cb95ea966c8c4331dae1d419f006d37bac1a4e5894df` |
| S0 terminal | `37dfc0262dfc6ba7c9cbade0539b8c1337cb1fe7f5412874ecb6e2752f2ff3e2` | `7b9be40d74dd86c8165f3e860192e3825d3375777ecc4cc44d1e78402a45a4b4` |
| S1 terminal | `4ed80e53e56a98bdbd2f6a4b039b6dbaedd054351258a47c4b9a2fb4d26c1583` | `419ab03e0da84cdd65519e5fc02d1492f49655ef44adb01bf9dbf03853e5d91e` |

Independent G0 calculations on 2026-10-03: Python 3.12.3 used
`struct.pack('<7Q', R,L,B,fee,next_R,next_L,next_B)` and separate
`struct.pack('<QI', value,len(spk))` per record plus hashlib; Node v22.22.3
assembled manually transcribed field hex (`R0=00512e3f00000000`,
`R1=00a0252600000000`, `P0=0024fd3d00000000`, `P1=0073f42400000000`),
independently concatenated the three rows and used `node:crypto` SHA256.
Neither imported a KPI encoder nor the other calculation's generated bytes.
Lengths, C, all context hashes and all T values agreed. OpenSSL 3.0.13 separately
hashed Python's context bytes and agreed (hash cross-check only, not a third
independent serializer). Future implementation must test these fixed expected
values rather than regenerate its expectations with its own encoder.

Golden negative context corpus uses `C0` = the complete S0-continue bytes above,
with the following exact single-byte replacements; suffix s/txid/index stays
unchanged. Python and independent literal Node calculations also agreed on
these tags. The original continuation constraints/VK remain fixed in G2:

| Negative bytes | Expected original-context tag oracle T' (must reject) |
| --- | --- |
| `C0[87] := 02` (unknown mode) | `ebe7a11139890da093c561b8eacb29aa5afcbc8a64a0845fa6bddc39f0280b84` |
| `C0[86] := 01` (S1 continue forbidden) | `05299d3cbc51595cca3b85309546a7382598ff058f43c1120c19daaf68fa8640` |
| `C0[190] := 01` (successor version 1) | `0fab892f5af61ff60b33adc119772d9d3b279952386d1c306088d7d340673c8d` |
| `C0[226] := 01` (present output metadata marker) | `910bfe668bef282e6aaa02064e1d2c81de1882e0c9a22e2a13b19e8026c8b11a` |
| `C0[242] := 78` (recipient key byte changed from 79) | `729a917d85a7946600734e1ea684b695f27ce754f12f3b712c9a8cc14bac9557` |

These are negative **against the frozen original context**, not proofs that a
different setup cannot authorize its own different terms. Decoder negatives
also include `C0 || 00`, `C0[0:275]`, `C0[185:189] := 24000000`, and
`C0[176] := 01`; reject the trailing/truncated/length/count disagreement rather
than silently reparsing it. For all three contexts add integer-endianness,
genesis/instance/C/each amount/output-order mutations using an independent tag
oracle in G2; randomized foreign-VK failure alone is not this coverage.

## G0: dependency graph and artifact inspection

The complete construction graph, before any funding, is:

```text
fixed S1 terminal terms/context -> S1 constraint system -> PK_1t/VK_1t
 -> S1 redeem D1 -> full S1 SPK
 -> S0 continuation terms/context (exact full S1 SPK)
 -> S0 continuation constraint system -> PK_0c/VK_0c

fixed S0 terminal terms/context -> S0 terminal constraint system -> PK_0t/VK_0t

(VK_0c, VK_0t, exact S0 branch/output terms) -> S0 redeem D0 -> full S0 SPK
 -> funding transaction/outpoint -> dynamic S0 public inputs/proofs
 -> accepted continuation body/outpoint -> dynamic S1 public inputs/fresh proof
```

R/L/B/fees/W/C/recipient/instance/genesis are fixed first. No circuit commits to
its **own** VK/redeem/SPK, nor to the future funding txid. S1 contains no S0
artifact hash. A manifest may list hashes after artifact creation, but **no
whole-manifest hash is subsequently inserted into any circuit or script**.
Artifact-index hashes and reviewer receipts authenticate distribution only.
Signed planned funding may supply pre-funding dynamic inputs; it is never a
setup constant. S1 txid is recomputed from the actual accepted continuation,
not an assumed precomputed proof-dependent transaction ID.

### Human manifest and machine schema

One readable manifest prints network/genesis, protocol/encoding version,
instance (state ID), C, recipient address **and full SPK**, owner consent to
fees, all integer R/L/B/E/W/P/f values/equalities, stage/mode/selector per branch,
ordered outputs/metadata, exact contexts, five input names/ranges, three key
identities and construction edges. Also print envelope policy, budgets,
resource/fee assumptions, chain-data source/retention, recovery inventory and
source/build pins. Decimal sompi and hex bytes both appear; no private witness.

Machine artifact contract `kpi-a1-artifacts/v1` is frozen by this field table.
JSON transport is UTF-8, no duplicate/unknown keys, no NaN/float monetary values.
Unsigned integers are canonical decimal strings (`0` or nonzero-leading decimal)
with declared widths; hex is lowercase, even length, without `0x`.

| Record / field | Required type and contents |
| --- | --- |
| `schema`, `protocol`, `network`, `genesis_hex`, `instance_hex`, `claim_commitment_hex` | Exact schema/label/TN10; last three 32-byte hex values |
| `recipient` | `{address, spk_version:"0", spk_hex}`; full SPK and decoded standard P2PK must agree |
| `states` | Exactly keys `s0`,`s1`; each `{stage,R,L,B,redeem,spk_hex}`; stage u8, amounts bounded u64/MAX_SOMPI; redeem is artifact descriptor |
| `branches` | Exactly `s0_continue`,`s0_terminal`,`s1_terminal`; each `{stage,mode,selector_hex,fee,next_R,next_L,next_B,outputs,context_hex,context_sha256,relation_id,r1cs,pk,vk}` |
| Each `outputs[]` | Ordered `{index,value,spk_hex,covenant:null}`; widths u32/u64; lengths derived from decoded SPK |
| `relation_id` | Exact `sha256-preimage-and-outpoint-tag/v1`; branch ID ties to context, not an opaque user name |
| Artifact descriptor | `{path,bytes,sha256}`; relative safe path, u64 decimal byte count, SHA256 of exact binary bytes; `r1cs` additionally has `format:"KPI-A1/R1CS/v1"` |
| `abi` | `{verifier_tag_hex:"20",public_inputs:["txid_lo128","txid_hi128","index_u32","tag_lo128","tag_hi128"],scalar_bytes:"32",proof_bytes:"128",vk_bytes:"424",witness_order:["tag_hi","tag_lo","proof","selector","redeem"]}` |
| `envelope` | `{tx_version:"1",subnetwork_hex:zero20,gas:"0",payload_hex:"",lock_time:"0",sequence_policy:"relative-lock-disabled",compute_budgets:{s0_continue,s0_terminal,s1_terminal}}`; budgets u16 |
| `pins` | `{kpi_source_commit,rusty_kaspa_commit,rust_toolchain,target,cargo_lock_sha256,dependency_versions,sdk_archive_sha256,node_archive_sha256,build_commands,checker_source_commit}` |
| `inspection` | `{normalized_r1cs_sha256:{s0_continue,s0_terminal,s1_terminal},script_disassembly_sha256,checker_report_sha256,setup_observation_receipt_sha256}` |
| `recovery` | `{source_id,network_genesis_hex,retention_start_hash,retention_policy,locator_schema:"kpi-a1-locator/v1",private_backup_items,public_artifact_items}`; public source ID contains no credentials |

`W` is branch output 1's value in continuation; `P0/P1` are terminal output 0
values; E=R. No independent contradictory duplicates of these derived values.
All null fields are explicitly null, not omitted. Budgets/artifact hashes/source
commits are **required concrete values for generated bundles at G2/G4**, not
invented G0 artifacts. Unknown/missing values block that bundle's qualification.
The public human manifest is rendered from the independently checked machine
record and compared against the owner's separately recorded intended terms.

### Second-reviewer procedure (not just proof success)

1. Start from the owner's intended recipient, amounts, C and state ID, not
   generator-provided expected results. Independently check exact integer
   equations/ranges with wide integers and manually check recipient decoding.
   Independently encode all three contexts using a checker with no imports from
   the production encoder/compiler; compare bytes and golden vectors.
2. On a clean offline build, inspect the exact pinned circuit source and compile
   each branch. Export a normalized sparse R1CS: variable 0 is one, variables
   1..5 are public ABI order, remaining variables are witnesses; ordered A/B/C
   rows use sorted `(variable_index,canonical_Fr32)` coefficients, no duplicate
   terms, exact counts and no witness assignments. Define the export binary
   as `KPI-A1/R1CS/v1\0 || public_count_LE32 || variable_count_LE64 ||
   constraint_count_LE64`, then each ordered row's A,B,C with
   `term_count_LE64 || (index_LE64 || coefficient32)*`. Coefficients are canonical
   Fr; export zero terms omitted and duplicate coefficients added in Fr.
   An independently written checker evaluates/compares these matrices, counts
   and public-variable allocation with a second compile from reviewed source.
3. Inspect that both SHA256 relations are constrained: secret has 32 byte
   witnesses; C and **every byte** of each branch context are constants in the
   SHA256 gadget; hash suffix uses the constrained txid/index; public limbs have
   exactly the declared ranges/order. The reviewed source-to-R1CS map identifies
   context constant byte offsets and constraints. An independent generic R1CS
   evaluator and original-key one-field context/range negatives supplement
   source review; witness-generating code or a successful proof is insufficient.
   R/L/B arithmetic is an inspected **fixed-term relation**, not a claim of
   variable balance constraints in this circuit.
4. Independently parse/disassemble D1 then D0, reconstruct their expected
   templates and P2SH/full SPKs, and compare exact bytes. Check entry depth,
   raw selector control flow, all output/envelope checks, proof/scalar widths,
   outpoint derivation/order, literal count/tag and three exact VKs. Check every
   successful control-flow path ends in its corresponding verifier. Mutate
   each generated constant, script, embedded VK, branch mapping and descriptor;
   the checker must reject even when the generator produces self-consistent
   replacement hashes and a proof under its replacement key.
5. Parse PK/VK with validated compressed Arkworks encoding, no trailing data;
   require PK's embedded VK equal the script's VK and six gamma_abc elements.
   **A VK is opaque: hashes, equal PK/VK and successful proofs cannot prove it
   came from the intended R1CS.** The second reviewer must supervise/reproduce
   the final setup run in the clean pinned environment, witnessing the exact
   inspected R1CS supplied to setup and hashing its resulting PK/VK immediately.
   Preserve a public receipt binding branch/context/R1CS/build/PK/VK hashes.
   Reject unwitnessed imported setup artifacts. Random setup output need not
   equal a separate fresh setup; R1CS and script reconstruction must agree.
   Erase setup randomness after the witnessed run; it is never recovery data.
   This is still trusted single-party experimental setup, not an independent
   mathematical proof of CRS correctness or an audited multiparty ceremony.
6. Hash every exact binary and source/build input with SHA256, inspect the
   resulting signed/offline reviewer receipt and independently replicate the
   approved bundle before funding. Compare D0/SPK/R0 to the actual funding
   output and D1/SPK/R1 to the accepted continuation. Self-reported manifest
   checksums do not authenticate a funded reserve by themselves.

Toolchain baseline: Rust **1.91.0**, pinned rusty-kaspa
`01b532e8b553523216471682649693af92f0fd16` (v2.1.0), Arkworks BN254/FF/
Groth16/relations/r1cs-std/crypto-primitives/serialize/snark **0.6.0**, SHA2
**0.10.9**, x86_64-unknown-linux-gnu. SHA256 gadget source pin remains
`ba00127bf673d93d73a3e8bf969cb9eeced20d12` from A0. A0's Cargo.lock SHA256 is
`dae6cd7a3a4af67b740762a89b247f24500ec2a74ee983fcf14be9ffc5562364`;
future A1 must retain its **own** exact lock and compiler/checker source commits
and build-command hashes, not mislabel A0's lock as an A1 build.
SDK v2.1.0 archive SHA256:
`ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124`;
Linux-amd64 node archive SHA256:
`5ba61c05c013a4856491a8a17666fa73f7bd2aecbfed8affe8ffdc077361dad8`.
These are [A0's retained artifact pins](../../scripts/setup_a0_tn10.sh), not new
A1 downloads/build measurements. Binary provenance and node sync are separate.

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

### G0 recovery: spendability versus lineage/accounting

**A — Terminal spendability** of a known authenticated current S1 UTXO needs
the private claim secret s; independently retained PK_1t, VK_1t, D1, full S1
SPK/context/terms and pinned proving/validation software; and current S1's exact
txid/index/value/SPK/metadata plus native validation context. These suffice to
generate a fresh S1 proof without the S0 transition history. The recipient
recovery key is additionally required to control/spend the resulting P2PK payout
and is mandatory in this experiment's user backup, although it is not a witness
to the reserve Groth16 proof. Independently validate SHA256(s)=C and recovered
recipient pubkey=the fixed SPK. Neither original prover access nor setup toxic
waste is needed. A hash of a missing PK does not suffice.

**B — Lineage/accounting recovery** must establish that this S1 is the accepted
continuation of the designated S0, that W/fc were settled exactly once, and that
S0 and S1 are never double-counted. An unrelated deposit to the same S1 address
can be spendable under the same D1 but does not prove this lineage. Matching
address, amount, block inclusion or mempool acknowledgement alone cannot pass B.

The experiment uses an independent TN10 node **with UTXO index**, plus an
independently retained acceptance/body archive. A UTXO index is not a historical
spender index and an ordinary pruning node is not a permanent archive. Before
any S0 funding, start the archive at an independently observed selected-chain
checkpoint preceding funding, and record its hash/blue score/DAA score and
source identity. Verify completeness through a declared horizon; notifications
may accelerate discovery but cannot replace gap-free replay. Retain every
acceptance page, referenced accepted transaction body and removal event needed
from that checkpoint; never depend on a final original-host export.

Starting locator `kpi-a1-locator/v1`, retained outside the original host before
continuation, contains `{network:"testnet-10",genesis_hex,instance_hex,
s0_txid_hex,s0_index,s0_amount,s0_spk_hex,s0_covenant:null,
scan_start_hash,scan_start_blue_score,scan_start_daa_score,
artifact_index_sha256}`. Integers follow the manifest's canonical widths/strings.
The accepted funding body and checkpoint provenance are independently retained
as soon as funding accepts. Its outpoint must match the signed planned funding
locator; otherwise stop and reconcile before continuation. No saved S1 pointer
is required. This locator is documented user/public backup state, not an
undocumented local database.

Concrete discovery procedure:

1. Authenticate the independent artifacts/reviewer receipt and S0 funding
   output (exact full SPK/R0/None). Check independent node binary provenance,
   TN10 genesis, sync status and index availability. Freeze a scan horizon H
   (selected-chain block hash and scores). The range is from the pre-funding
   checkpoint through H in selected-chain acceptance order, **including DAG
   mergeset accepted transactions**, not a timestamp/address query.
2. Preferred native route: pinned
   [getVirtualChainFromBlockV2](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/rpc/service/src/service.rs#L1367)
   with `startHash=cursor`, `dataVerbosityLevel=Full` (3),
   `minConfirmationCount=0` for complete initial discovery. It returns
   added/removed chain hashes and accepted transaction bodies grouped under
   accepting chain headers. Require full inputs, signatureScript, computeBudget,
   outputs/SPK/covenant, version, lockTime, subnetworkId, gas, payload and
   storageMass, not optional-field defaults. Confirm Full conversions in
   [verbosity mapping](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/rpc/core/src/convert/verbosity.rs)
   and [body retrieval](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/rpc/service/src/converter/consensus.rs#L531).
   Native RPC acceptance is a node assertion backed by that node's validated
   consensus, not a standalone cryptographic light-client proof.
3. Pagination is cursor based, not client page-number based. Server bounds
   added data by `10 * mergeset_size_limit` (2480 merged blocks at TN10 10 BPS);
   removed blocks are not subject to that bound. Require one processed acceptance
   group per returned added hash. Advance only to the **last fully processed
   added hash**, persist cursor/pages atomically in the independent archive,
   and query again until H is reached. Deduplicate by accepting hash/txid;
   repeated cursor with missing groups or no progress before H is a gap/error,
   not end of history. Catch up from H to the latest head before proving.
   Reconcile the head if H was removed; never skip the gap.
4. Fallback native v1 route:
   [getVirtualChainFromBlock](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/rpc/service/src/service.rs#L725)
   (`includeAcceptedTransactionIds=true`) supplies accepted IDs, not bodies.
   Join them to an independent archive indexed `txid -> exact body, containing
   block hash, accepting block hash`. Populate that index from native
   [getBlocks](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/rpc/service/src/service.rs#L534)
   with `lowHash`, `includeBlocks=true`, `includeTransactions=true`, including
   mergeset bodies. Its range includes lowHash and is bounded by mergeset limit
   +1 plus sink anticone; deduplicate the inclusive lowHash, continue from the
   final range hash while the queried sink is not yet present. If the sink is
   returned, fetch/process the entire page including its anticone, finish that
   range, and do not use an appended anticone hash as the next range cursor.
   Check progress/coverage against the chosen horizon.
   A body's containing block need not be its accepting block. Use the acceptance
   ID set to select bodies; getBlock(accepting hash) alone is insufficient.
   Missing body fields/history are a failed source, never a lossy REST default.
5. For each accepted body, recompute native txid and full transaction hash;
   preserve exact serialized body and SHA256. Scan inputs for **the exact S0
   txid/index**. Check its authenticated UTXO context, selector and proof through
   pinned Full validation; require continuation outputs 0=S1 SPK/R1/None and
   1=recipient/W/None, one input, two outputs, fixed envelope and exact fee fc.
   Reconstruct L1/B1/E1 and accepted W/fc independently. Derive S1 locator from
   this body's txid and output index 0; don't search by address alone. If the
   accepted spend is direct terminal, verify P0 and record terminal state, not S1.
   Multiple currently accepted conflicting S0 spends are a hard failure.
6. Query indexed current UTXOs for S0/S1/recipient addresses and filter exact
   derived outpoints, full SPKs, values and None metadata. S0 must be absent when
   S1 is present. If S1 is already spent, extend the same accepted-body scan for
   its exact outpoint, validate terminal payout P1/f1 and record terminal state.
   Unknown spentness, missing body, unexplained disappearance or contradictory
   observations halts recovery accounting. An independent source's current
   unspent S1 is still enough for A only if its locking terms are authenticated;
   it does not turn missing lineage into a successful B result.
7. Apply `removedChainBlockHashes` first: remove their acceptance-derived
   transitions/payout credits and restore the prior state, retain old bodies as
   observations, and replay added groups. Anchor cursor back to a surviving
   common checkpoint. If S0 becomes unspent again, return to S0; if a different
   continuation accepts, derive its actual S1 outpoint and reprove. Recheck
   acceptance plus current UTXOs immediately before exit and after the declared
   confirmation window. Do not retain both versions of backing or pay twice.

V1/v2 RPC pagination/body retention must be exercised at G4/G5; source inspection
is not a live compatibility test. In particular txid is not a checksum of the
entire body: pinned
[v1 hashing](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/hashing/tx.rs#L207)
excludes signature script and mass commitments (including compute budget).
Recompute/check those fields and the full hash separately; correct txid alone
does not authenticate proof bytes, compute budget or storage mass.

Pruning/absence fallback: first use an independent archive retaining the entire
required range and its validated acceptance observations, then another
independent indexed archive node. Configure enough retention before the run;
pruning proofs cannot reconstruct removed bodies or keys. If no gap-free
accepted lineage remains, **B fails** and no recovery-success claim/funding gate
passes. Report that independently authenticated current S1 may still permit A;
do not substitute address matching, a newly generated setup or original-host
access. Remote archival assertions retain explicit observation trust even if
two endpoints agree. G5 includes archive corruption, pagination gaps and
original-host-independent restore tests.

### G0 experiment topology (defined now; do not await node sync)

| Role | Responsibilities and allowed retained data |
| --- | --- |
| Original machine A | Inspect/setup/build unfunded artifacts, create S0 funding and S0→S1 only in later authorized G6; original witness/prover/storage unavailable to recovery |
| Clean recovery machine B | Fresh checkout/build pinned software; independently retained approved public bundle; user-private claim/recipient backup; S0 locator only for abrupt loss; independently discover S1 and generate a new terminal proof |
| Chain/archival machine C | Independently operated indexed TN10 node + acceptance/body archive started before funding, accessible to B after A disappears; separate storage, credentials and failure domain from A |

The currently pinned local TN10 node is syncing; **nothing in G0 waits for or
changes that process**. Prefer its fully synced, locally validated chain data
once available. To use it as C, it must be independently available after A's
complete loss (place it on C or replicate to an independently operated node
and start its own archive before the experiment). A node on A that goes down
with A cannot be C in the abrupt-loss test. A clean directory/container on A
alone does not demonstrate machine-loss recovery. If independently validated
local data is not available at G6, remote indexed/archival observations require
an explicit recorded trust route; there is no implicit fallback declaration.
Concrete machine IDs/endpoints/binary hashes/retention checkpoints are G5/G6
run records, not credentials or claimed running infrastructure in this ADR.

Orderly test: C observes/archives S0→S1 acceptance; disable A/network access to
A; B fetches its own bundle/backup/C data, discovers accepted S1, freshly proves
and validates/exits. Abrupt test: kill/disconnect A immediately after independent
C observes S1 acceptance **before A records S1 or exports a pointer/body**;
B starts with S0 locator + independent history and must reach the same result.
Use separate S0-direct and S1-continuation instances and test reorg/loss between
acceptance and discovery. Measure <=30 minutes to fresh locally Full-validated
terminal transaction after prerequisites, with builds/sync separately reported;
live G6 uses <=10-minute acceptance window and >=120-second later recheck under
the predeclared >20 accepting-block blue-score-distance policy. These are
experiment thresholds, not finality guarantees. No saved terminal proof passes.

## G0 provisional fee and resource policy

For branches j=`0,c,1`, measure final serialization/mass before funding.
Let `U_j` be executed script units for the pinned script/proof path. Select finite
u16 budget `b_j = ceil(11*U_j / (10*10000))` (10% execution headroom; conservative
without spending the native free allowance). Revalidate with that commitment.
Reject if u16 overflow or any branch/block mass limit fails. This is a
qualification policy, not an introspected exact-budget restriction.

Let `M_j` be upstream normalized overall mass (compute/storage/transient) of
that fully validated candidate, and `N_j=max(compute_j, normalized_transient_j)`
the pinned relay fee mass. Let r be the actual relay minimum in sompi/kg;
`relay_j=min(MAX_SOMPI, floor(N_j*r/1000))`, replacing a zero result by r,
matching pinned node policy. Default r=100000, **100 sompi/gram**, not 1.
Record actual node configuration and check standard P2SH/P2PK output policy.

Obtain an explicitly selected fee-estimator bucket (normal bucket is the A1
baseline), with corroborating independent observations. Express its conservative
upper rate q in exact rational sompi/normalized gram (round a reported floating
rate upward, never silently round down); let q also cover `r/1000`. Fix:

```text
f0 >= max(relay_0, ceil(5 * q * M_0 / 4))
fc >= max(relay_c, ceil(5 * q * M_c / 4))
f1 >= max(relay_1, ceil(5 * q * M_1 / 4))
B_required = max(f0, fc + f1)
B0 >= B_required + ceil(B_required / 10)   # owner-refundable credit headroom
R0 = L0 + B0; B1 = B0 - fc; R1 = (L0-W) + B1
P0 = R0-f0; P1 = R1-f1
```

All calculations use checked wide integers/rational ceilings and native amount
bounds. These are **pre-funding rules** with 25% quoted-rate headroom, not an
economic liveness guarantee. Actual fixed f values can exceed the calculated
minimum but require explicit owner consent and only consume B. Require quotes
<=5 minutes old and repeat the relay/estimator/headroom checks immediately
before funding. Fee choice changes context/setup/script/SPK; iterate unfunded
qualification builds until the final exact candidates pass all three checks.
The illustrative 20-million fees are not frozen funding authorization or a
guarantee of headroom (at ~172000 grams and 100 sompi/gram, 25% policy headroom
already requires ~21.5 million sompi). Preserve surplus fee credit as liability.

No fee bump, sponsor input, principal haircut or admin rescue. If policy becomes
unviable **before** funding, rebuild/reinspect/requalify a new unfunded instance.
If a fixed fee becomes insufficient **after** funding, record a liveness failure
and halt submission under that policy; wait for viable policy only with the
same safety rules. Do not weaken outputs/VK/balance/metadata to force acceptance.
Relay acceptance and block inclusion are not consensus fund-safety proofs.

### Independently verified upstream limits and estimate

Rechecked 2026-10-03: local clean rusty-kaspa checkout, upstream default HEAD and
v2.1.0 tag all resolve to `01b532e8b553523216471682649693af92f0fd16`.
Official docs/vProgs/research default heads still equal the source pins in the
existing-work table below. Astra's user-supplied review is an input; the following
numbers were independently read/calculated from upstream and merged A0 evidence.

| Property | Pinned source / result |
| --- | --- |
| SPK execution version | [VM](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/lib.rs#L76): max known version 0; [unknown version path](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/lib.rs#L655) accepts without execution. A1 fixes 0, including successor. |
| Stack/script/element/counted ops | [VM constants and execute_script](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/lib.rs): combined main+alt 244 elements; each script <=1000000 bytes; element <=1000000 bytes; counted non-push ops <=1000000 per script (not a compute allowance). |
| Signature and output size | [Parameters](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/params.rs#L675): signature script <=250000 bytes/input, output raw script <=10000 bytes. Redeem is carried in input witness; output is 35-byte P2SH. |
| TN10 block masses / byte prices | [TESTNET_PARAMS](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/params.rs#L650): compute/storage/transient 500000/500000/1000000; tx byte 1 gram, full output-SPK byte 10 compute grams; transient 4 grams/estimated tx byte ([mass source](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/mod.rs)). Block aggregate limits are not per-script budgets. |
| v1 budget | [Units](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/units.rs): u16; 100 grams/budget unit, 100 script units/gram, 9999 free script units/input. Mass bills committed budget, not measured usage. |
| VK and proof sizes | [Groth16 parser/tests](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/groth16/mod.rs): G1=32, G2=64 compressed bytes; VK=32+3*64+8+6*32=424; two `4da801` literal pushes=854; proof=32+64+32=128. Canonical parsing/trailing rejection are native verifier behavior. |
| Verifier cost | [Tag](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/tags.rs) + [VK metering](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/groth16/mod.rs): 140000 grams + 6*250000 script units /100 = **155000 grams**, excluding surrounding stack/script work. S0 executes one verifier, not both. |
| Relay fee / standardness | [Mempool checks](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/check_transaction_standard.rs), [default config](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/config.rs): standard outputs version 0; P2SH classic sigops <=15; default r=100000 sompi/kg; compute/normalized-transient fee floor. |

Estimated S0 redeem: 854 bytes of VK pushes + approximately 350–750 bytes for
two output-check/ABI bodies and common dispatch/envelope = **1.2–1.6 KiB**;
conservative qualification ceiling **2 KiB**. S1 terminal approximately
650–850 bytes. Signature script adds 198 bytes for S0 continue (or 197 terminal)
plus redeem push prefix and redeem bytes; five literal element pushes. Expected
peak combined stack <=12 and counted ops <250 under this template; first G2
trace must disprove/confirm, not infer from byte size. A0 redeem was 576 bytes,
VK 424, proof 128 and actual used units 15501434 in
[merged A0 measurements](../../poc/a0/evidence/local-run.json); those are **A0**
measurements only.

With one verifier and 10% budget headroom, b around 1705–1800 is plausible;
committed execution mass roughly 170500–180000 grams, plus ~1.6–2.5 KiB
estimated transaction size and <=730 output-SPK mass for continuation. Expected
compute remains roughly 173000–184000, transient roughly 6400–10000 grams,
well below block limits if measurements agree. Storage is value dependent:
for the illustrative amounts and standard None-metadata SPKs (plurality 1),
pinned C=10^12 integer formula estimates continuation
`floor(C/R1)+floor(C/W)-floor(C/R0)=3119`, direct terminal 18, S1 terminal 50
storage grams. Recompute using exact native contextual calculation; this is
not an actual populated A1 transaction measurement or a universal small-value
bound. Small reserves/outputs can exceed storage limits even with short scripts.

No source-level hard protocol blocker found. **G2/G4 remain unmeasured.** First
implementation falsification test: construct S1 first, then actual D0 with two
VKs; exercise all three real-proof paths against populated version-0 UTXOs in
the pinned Full validator and metered VM. Capture raw script/witness bytes,
complete execution log (only public stack data), peak main+alt/count/bytes,
verifier count/key/tag, U_j, b_j, all three mass dimensions and relay policy.
Demonstrate all witness/selector negatives and permitted push equivalents.
If any path bypasses a mandatory body, fails the finite budget/2-KiB estimate,
or cannot fit native limits, stop and review: a size-estimate miss is not itself
a protocol blocker, but a proved native limit/semantic incompatibility is.
Do not increase limits, claim G2 success or fund while resolving it.

## G0 enforcement-layer map

| Important field | Circuit | Redeem script | Native consensus | Adapter / inspection / recovery |
| --- | --- | --- | --- | --- |
| Current txid/outpoint index | Dynamic SHA256 tag; 128/128/32-bit public ranges | Derives exact input-0 outpoint limbs | Looks up unspent input, rejects duplicate/missing/spent outpoints | Recompute ID; discover/authenticate actual funding/S1 locator; local supplied entry alone cannot prove spentness |
| Spending txid / full transaction body | No commitment to spending txid | No full-body hash condition; actual listed outputs/envelope checked | Native ID/hash rules | Recompute both ID and full hash; check excluded proof/budget/storage fields; archive acceptance separately |
| Input sequence | Not in proof relation | No exact sequence restriction | Relative-lock rules as applicable | Normal emission u64::MAX; distinct-ID replay uses u64::MAX-1, both relative-lock disabled. Other sequences not claimed script-forbidden |
| Recipient | Full fixed SPK in context hash | Every payout full SPK equality | Native script execution when payout is later spent | Decode SPK/address and test recovery-key control independently |
| R/L/B/W/P amounts | Fixed context bytes bound, **not variable arithmetic proof** | Actual input R, exact ordered output values | Checked monetary/input-output limits; nonnegative miner fee | Independently check fixed integer conservation/ranges/owner fee consent; recovery derives settled liabilities |
| Successor SPK | Exact previously built full S1 SPK in continuation context | Output 0 full byte equality, including version 0 | Creates corresponding UTXO; P2SH later authenticates D1 | Rebuild D1/SPK/key; verify lineage from accepted S0 spend |
| f0/fc/f1 | Fixed context fee byte binding | Exact single input/output totals imply fixed fee | Input value >= output total; miner fee difference | Check B-only charge, relay estimate/headroom and no post-funding change |
| Input/output count and order | Fixed output records hashed | 1 input, current input 0, output count 2 or 1, indexed equality checks | Generic limits, duplicate-input ban | Inspect template and final decoded fields |
| Covenant metadata | Output absent flag fixed in context | Output authorizing input=-1, not zero-ID test | Validates any present binding; does not force A1 continuation | Funding/current input None inspection; accepted successor/payout None verified; input None cannot be proved from zero-ID introspection alone |
| Stage/mode/selector/branch | Stage/mode fixed in each key's context | Strict raw selector, immutable matching VK/count/tag | Executes P2SH/version-0 VM and real precompile | Independently inspect mapping; no witness mode field; recovery accepts only finite graph |
| Instance/state ID/domain/genesis | Fixed context, C and secret/tag relation | Pinned branch VK via P2SH; no chain-genesis opcode | No application instance/genesis-label assertion | Verify actual TN10 independently; copied identical fork state outside cross-chain claim |
| SPK version / VK / verifier | Circuit-specific setup | Full output SPKs version 0; embedded VKs; tag20; no witness key | Version 0 executes; unknown version may bypass; compressed parsing/real Groth16 | Funding version-0 validation; witnessed setup and script inspection required |
| Compute budget | Not bound | No budget introspection or exact-value check | v1 u16 commitment, metered limit and compute mass | Select/freeze finite qualified per-branch budget, preserve SDK roundtrip; budget variation within consensus limits is not an unauthorized payout |
| Transaction version | Not context field | OP_TXVERSION=1 | Toccata version/compute field rules | Exact SDK roundtrip; no v0 downgrade |
| Subnetwork/gas/payload/lock time | Not context fields | Native subnetwork zero20, gas0, payload length0, lock0 | General subnetwork/gas/lock/size rules (not all A1 restrictions automatically) | Verify final serialized fields, recovery and native validation context |
| Storage mass / acceptance / chain history | Not proof statement | No history availability assertion | Contextual mass and native acceptance/UTXO state | Correct storage commitment; independent archive, pagination/reorg reconciliation; RPC assertion trust explicit |

Budget, sequence, input-metadata inspection, archive completeness and setup
provenance must not be described as additional consensus-enforced A1 conditions.
Different encodings or permitted sequence/budget variations can change full
transaction bytes without redirecting funds under the specified output rules.

### G0 adversarial second pass

| Question | Design finding / unresolved execution evidence |
| --- | --- |
| Could this mint value? | Fixed R=L+B and exact accepted outputs/fees conserve entitlement; independent integer/compiler inspection is required. Fixed-context hash binding is not a variable-arithmetic proof. G1/G2 must reject inconsistent generated terms. |
| Could it spend twice? | Same-state proof can remain statelessly valid; only native current-UTXO acceptance supplies single spend. G3 races/reorg tests remain mandatory. |
| Could it release reserve incorrectly? | Raw selector equality, all matching output checks and literal matching VK/tag are necessary. Version-0 funding/successor identity prevents unknown-version bypass. G2 path traces/mutations and actual verifier remain pending. |
| Could it leak private relationships? | Amounts/recipient/outpoints/lineage/timing are public. Claim secret remains local; a hosted prover would learn it. No private accounting or anonymity claim. |
| What if dependencies disappear? | Independently retained PK/artifacts, private backup and C data allow the planned fresh proof; loss of PK or accepted lineage without replicas fails the corresponding gate. No substitute setup/toxic waste/host pointer. |
| What about reorg/stale state? | Acceptance-group removals undo credits/state together; derive current outpoint and reprove after reconciliation. Current address match cannot validate lineage. G3/G5 rollback/pagination tests pending. |
| What hidden trust appeared? | Opaque CRS needs supervised setup provenance; single-party setup, reviewed compiler/checker, endpoint/archive observations and fixed-fee viability remain explicit assumptions. Self-consistent hashes/proofs cannot eliminate them. |

This second pass found no source-level hard blocker, but it does not establish
cryptographic correctness or production safety. G0 closes the specification;
future qualification must still test the listed assumptions and failure modes.

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
