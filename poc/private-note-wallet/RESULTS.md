# Local wallet and application-kernel results — 2026-10-18

## Outcome and enforcement layers

Five actual BN254/Groth16 wallet proofs were generated and independently verified
in a separate CPU process with a pinned verification key. The circuit constrains
hidden input ownership and membership, HMAC economic nullifiers, positive u64
notes and integer conservation. The local kernel verifies these actual proofs
before atomic transitions. It keeps current nullifiers across batches, refuses
a distinct valid competing proof at an old permitted root and prevents both
credit and recovery from consuming the same pending deposit.

Bob discovers the accepted encrypted note using only his own keys and public
accepted data, validates its commitment and creates his exit proof. The logical
roles run in one local process; independent-machine or restored-wallet recovery
is not demonstrated. The exit stays covered by the reserve until an exact
fixture payout consumes its unique native-output reference. Final fixture
reserve and private liability are both 600,000,000 sompi.

Native deposit/payout authentication and the new outer state proof are absent.
There was no new GPU attempt, TN10 transaction, real KAS withdrawal or evidence
of effective anonymity. Fixture acceptance is not native consensus acceptance.

## Measured final wallet job

| Measurement | Result |
|---|---:|
| R1CS constraints | 774,582 |
| Public BN254 Fr elements | 14 |
| Canonical public statement | 410 bytes |
| Compressed wallet proof | 128 bytes |
| Encrypted output delivery | 185 bytes |
| Transfer wire operation (two outputs) | 908 bytes |
| Credit / exit-or-recovery wire operation | 723 / 538 bytes |
| Compressed proving parameters (not committed) | 156,435,376 bytes |
| Verification key | 712 bytes |
| Experimental setup | 13.175 seconds |
| Credit / transfer proof plus local CPU verification | 7.343 / 7.500 seconds |
| Competing spend / Bob exit / recovery proof plus local CPU verification | 7.953 / 7.347 / 7.171 seconds |
| Whole job wall time | 53.073 seconds |
| Peak kernel-reported process RSS | 2,619,203,584 bytes (2.44 GiB) |
| Compute threads / CPU affinity | 4 / CPUs 0–3 |

These are local CPU measurements including no mobile/network/native submission.
The approximately 149 MiB public proving parameters and experimental setup remain
practical wallet concerns. No outer-guest cycles or proof cost have been measured
for the new circuit's VK and 14 packed full-width inputs. Its small proof size
does not establish cheap in-VM verification or network capacity/fees.

Expected key identity:
`d45e8248eda25a6f6ec85b5074d0f7d217d29741c820c4d8ddfb2667675a5bf2`.
See [public report](evidence/public/report.json),
[whole-job resources](evidence/wallet-job-resources.json),
[separate proof verification](evidence/public/separate-verification.json),
[implementation pins](evidence/implementation-pins.json) and
[artifact hashes](evidence/manifest.json). Decoder and verifier-pin hardening was
completed after the timed proof-generation run without changing the circuit or
proof statement. The archived proofs were reverified using that final verifier;
its binary hash is not claimed as the timed generation binary's identity. The
final separate process took 0.055 seconds for all five proofs and its full set of
verification/state rejection controls before the two additional review controls;
this is not a zkVM verification timing.

## Validation

Nine focused tests pass: six circuit/recipient/encoding tests, two accounting
boundary tests and one separate-process replay of all five actual archived
proofs. The latter also uses a canonical subgroup-valid false pairing, an
on-curve wrong-subgroup G2 point, identity proof point, wrong expected VK,
unknown/trailing encoding and eight proof/statement/payload mutations.
Two further review controls change Bob’s actual exit destination to a different
nonzero destination and change a ciphertext while recomputing its public digest.
Both reach actual Groth16 verification and fail there, rather than failing a
payload consistency check. No setup or new proof generation is needed.
Unsatisfied real constraint systems test authority, membership, nullifier,
domain, conservation, output binding and overflow; valid boundary assignments
include values 2 and u64::MAX. Rejection checks compare unchanged state, then
apply the next valid operation. Resource failures never count as rejection.
Full inventory and remaining attack surfaces are in
[ADVERSARIAL-REVIEW.md](ADVERSARIAL-REVIEW.md); raw output is
[evidence/tests.log](evidence/tests.log).

## Remaining limitations and next gate

The four-leaf tree, one-input/two-output relation, whole-note exits, zero fees,
one-party setup, assumed authentic receiving addresses and unproved ciphertext
semantics are research restrictions. There is no production key ceremony,
security audit, migration design, persistent daemon, public data-availability
service or proved reorg/recovery policy. A malicious sender can produce an
undecryptable output and lose their own money; recipient checks must reject it
as a received payment. Deposit and exit values remain public, and this small
workload is highly correlatable. The public aggregate liability is not a claim
of hiding on/off-ramp totals.

The next bounded work is [NEXT-CHAIN.md](NEXT-CHAIN.md): qualify this new verifier
configuration, prove complete state/native bindings through transaction/batch/
aggregate, then a fresh TN10 deposit-to-actual-payout rehearsal. This package
allocates no additional GPU or native funds and leaves PR43 evidence unchanged.
