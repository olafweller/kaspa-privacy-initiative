# Local work package results — 2026-10-17

The specification, role/economic model and positive real composition experiment
are complete. This is **not** a funded shielded payment trial. Final measured
values and artifact integrity are recorded in the [machine-readable result](evidence/compatibility.json)
and [artifact archive](evidence/local-compatibility-artifacts.tar.gz).

## Findings

1. The model enforces the complete principal lifecycle, pending deposits, current
   nullifiers, sender change, unpaid exits/fees and separately funded permission
   rent. It permits owner recovery of an uncredited deposit without double credit
   or refund. These are model constraints, not native implementation claims.
2. Bob uses his own model keys and accepted public output records to discover,
   decrypt, verify and request the next spend. No Alice/executor secret database
   is used. Test fixtures and the ideal proof oracle do not establish privacy.
3. A real local wallet preimage/sum proof composes through a fixed adapter,
   reference batch and aggregate, and passes the local native script against the
   fixed captured endpoint. The four receipts are real and SDK-verified with
   development mode disabled. No new native submission occurs.
4. Missing/wrong inner evidence aborts; a host-requested rejection also aborts.
   The current recursive syscall cannot be treated as a proved invalidity/no-op
   classifier. This remains a blocker before a funded private trial.
5. A real proof carried in a new lane payload needs an intent digest excluding
   proof bytes; binding that wallet proof to the final native ID would otherwise
   be circular. The measured fixture uses an already-existing public native ID.

## Measured outcome

All 24 model tests pass, including 64 seeded conservation/replay vectors. The
original evidence run contained 23 tests; the review regression adds full-state
atomicity at the `u64` principal-plus-rent boundary. The regression failed before
the fix: an overflowing payout had already marked its claim paid and reduced
reserves. The full output sum is now checked before any economic mutation; the
exact maximum output succeeds and overflowing outputs leave all state unchanged.
The model's native-payout result is explicitly simulated, not a new chain payment.

| Real main-chain proof | Seconds | Padded cycles | User cycles | Retained receipt bytes |
| --- | ---: | ---: | ---: | ---: |
| Synthetic wallet | 63.12 | 65,536 | 26,068 | 223,418 |
| Public transaction adapter with wallet assumption | 282.87 | 524,288 | 209,640 | 223,650 |
| Reference batch | 123.53 | 131,072 | 38,438 | 223,772 |
| Reference aggregate | 125.45 | 131,072 | 45,553 | 223,930 |

Whole four-proof run: **595.96 seconds (9.93 minutes)**, exit zero; maximum
individual-process RSS **4,793,748 KiB (4.57 GiB)**. These are measurements on
four Cloud CPU threads, not aggregate concurrent RSS or client-device benchmarks.
Every receipt was SDK-verified against its exact program. The aggregate uses the
fixed official resolve control identity and passes local native script execution
against the captured endpoint; a wrong endpoint is rejected. No native broadcast.

One additional isolated wallet repetition measured **60.99 seconds** proving,
61.18 seconds for the measured job, and **1,459,284 KiB (1.39 GiB)** maximum
individual-process RSS. This is a fifth generated receipt used to isolate wallet
memory, not a fifth layer or a second candidate. Identical inputs give the same
public journal; proof bytes need not be identical.

Matched execution profiles on the same native input: baseline **173,954** user
cycles vs adapter **209,640**, an increase of **35,686 (20.51%)**. The extra wrapper
crosses a padding boundary from `po2=18` to `19` (262,144 to 524,288 padded cycles).
The delta includes decoding, binding and the composition syscall; it is **not**
a measurement of a complete ordinary cryptographic receipt verifier inside the
guest. Recursive resolution and wallet proving add separate work.

The retained binary receipt sizes are SDK serialization, not a chosen final lane
encoding. A roughly 223 KB wallet receipt is already significant against native
transient byte/mass limits; no private-operation throughput or fee estimate is
inferred until the complete payload/settlement is encoded and measured.

Four actual execution-abort controls record inflated arithmetic, missing wallet
assumption, wrong wallet journal and a host-forged rejection request. Changing
the real wallet journal also fails SDK verification. These are local enforcing
layers, not additional native node rejection or a proven invalid-operation no-op.

## Limits of representativeness

The wallet relation checks one synthetic preimage and `u64` sum, not hidden note
membership/ownership, nullifiers, recipient/ciphertext correctness or their full
state bindings. The adapter also executes an existing **public** deposit relation;
its private arithmetic hash is not a new economic claim integrated with that
account. This measures composition compatibility, not full private enforcement.

All work ran on the existing Cloud CPU environment, logically representing wallet
and outer-prover roles in one harness. It does not measure a phone/browser wallet,
a real local-user network boundary, timing anonymity or final L1 proof encoding.
The ideal reference model's valid-bad-valid behavior does not close the measured
cryptographic invalidity blocker. Only the later reviewed implementation and full
fresh native payout can qualify the proposed funded experiment.

The recommendation is to continue an **unfunded** investigation of enforced
invalid-proof handling and the complete private statement/payload, using the
existing RISC Zero route as the first candidate and one specialized Groth16 route
as an unmeasured comparison. See [sources](SOURCES.md) and [proposal](TN10-PROPOSAL.md).
