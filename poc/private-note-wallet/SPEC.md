# Local experimental statement/encoding v1

This is a concrete local experiment under ADR-0011, not an accepted production
note scheme. Only the hashed domain
`SHA256("KPI/LOCAL-NO-FUNDING/native-KAS/private-note-experiment-1")` is supported;
there is no native funding endpoint. All tags below include their final NUL byte.
No new cryptographic primitive or custom curve/encryption arithmetic is defined.

## Secrets and notes

A wallet samples independent 32-byte spending and X25519 incoming secrets from
OS randomness. An authenticated receiving address supplies the owner hash and
incoming public key; address authentication is an explicit out-of-band assumption.
Let `D` be the local economic domain, `sk` the spending secret, `epk` the incoming
public key, `v` positive u64 little-endian integer sompi and `rho` fresh 32 bytes.

```text
owner = SHA256("KPI-owner-v1\0" || D || sk || epk)
cm = SHA256("KPI-note-v1\0" || D || owner || epk || LE64(v) || rho)
nf = HMAC-SHA256(sk, "KPI-nullifier-v1\0" || D || cm)
node(left,right) = SHA256("KPI-node-v1\0" || D || left || right)
```

The fixed-depth-two tree starts with four all-zero leaves; accepted commitments
append left-to-right and must be nonzero/unique. The circuit hides the input note,
selected two path directions and siblings. A nullifier is note/authority-bound,
not an intent hash: root, index, batch and verifier ID are excluded from `nf`.
Current spentness persists over all accepted operations/batches. Another verifier
version is not automatically accepted; migration remains unspecified.

The circuit always constrains input-owner derivation. Spend kinds additionally
require positive input value, true membership and the exact economic nullifier.
Credit/recovery use a zero-valued inactive input and prove the registered deposit
owner's authority. Two output slots have explicit activity by kind: inactive
values/commitments/delivery fields are zero; an active note has positive value.
A transfer's two output commitments must differ. No dummy zero note is spendable.

All values are UInt64 constraints. Equality compares the full field values of
bounded limbs, not wrapping u64 arithmetic: input + deposit = outputs + exit +
fee. At most a few u64 limbs are summed, far below the BN254 scalar modulus.
App fees/fee recipient are explicitly zero in this first version; nonzero private
fees and native submission fees/rent/refunds are not implemented.

## Public statement: 410 fixed bytes

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 1 | Version = 1 |
| 1 | 1 | Kind: credit=1, transfer=2, whole-note exit=3, pending-deposit recovery=4 |
| 2 | 32 | Economic network/pool domain D |
| 34 | 32 | Expected verifier-key identity |
| 66 | 32 | Membership anchor |
| 98 | 32 | Economic nullifier, or zero for credit/recovery |
| 130 | 64 | Two output commitments |
| 194 | 64 | Two ciphertext SHA256 digests, zero for inactive slots |
| 258 | 32 | Authenticated native deposit output reference, or zero |
| 290 | 32 | Deposit recovery/credit owner, or zero |
| 322 | 8 | Deposit value LE64, or zero |
| 330 | 32 | Exact native exit/refund destination script hash, or zero |
| 362 | 8 | Exit/refund principal LE64, or zero |
| 370 | 32 | Fee recipient = zero |
| 402 | 8 | App fee LE64 = zero |

Encode consecutive <=31-byte chunks as little-endian Fr elements: 14 public
field elements. Each chunk is at most 248 bits, strictly below Fr, so no field
reduction aliases a 256-bit hash. The circuit constrains the packed public
limbs to all the public bytes. The verifier independently reconstructs the same
canonical bytes/limbs. VK identity is SHA256 of canonical compressed VK bytes;
the verified application state pins that identity. It is not a self-referential
constant embedded in its own key-generation circuit.

Proof encoding is Arkworks canonical compressed BN254 Groth16 (128 bytes), with
curve/subgroup validation and exact consumption. The proof-free public statement
is the intent; `intentId=SHA256("KPI-intent-v1\0" || D || statement)` excludes the
proof/native transaction ID. Actual native payload/ID binding belongs to the
future transaction adapter. Changes to any intent field change the public proof
inputs, even fields not needing another arithmetic predicate.

## Encryption and canonical operation

Plaintext is 137 bytes: version1 || D32 || owner32 || epk32 || valueLE64 || rho32.
Use the existing crypto_box sealed-box API: fresh ephemeral X25519 key and the
library's XSalsa20-Poly1305 sealed encoding. Each active ciphertext is 185 bytes.
The circuit binds output note commitments and ciphertext digests, while the
operation verifier recomputes digests from the actual ciphertext bytes.
Encryption correctness is not a circuit constraint: opaque malformed delivery
can burn the sender's own output. It must not count as a received payment.

The wallet trial-decrypts only public accepted records, enforces exact plaintext
version/length/domain, its expected owner/incoming key, positive amount, rebuilt
commitment and accepted-tree membership, and excludes its already-spent notes.
Viewing material alone cannot satisfy the spending-secret constraint.

Binary operation is statement410 || proof128 || active ciphertexts in slot order.
Sizes are credit723, transfer908 and exit/recovery538 bytes. No implicit lengths,
trailing bytes or optional fields; inactive commitments/digests/ciphertexts must
be zero/absent. Public JSON files are evidence/debug containers, not a replacement
for this binary protocol. Their parser rejects unknown fields.

## Local application transitions and native boundary

Canonical state includes the immutable verifier ID, ordered commitments, allowed
roots, current nullifiers, accepted ciphertext digests, unique native deposit
references/statuses, pending/paid exits, already-used native payout references,
reserve/private-liability counters and batch number. State serialization hashes
explicit little-endian counts/fields and sorted sets/maps, not a host JSON order.

Before commit, verify the actual pinned wallet proof, enforce a permitted anchor,
current unspentness, output uniqueness/capacity and exact deposit/refund lifecycle.
Only after all checks commit the cloned candidate state. A resource or invalid
proof rejection never partly appends notes/inserts nullifiers/debits liabilities.
Pending exits stay backed until exact independently authenticated payout facts
remove both reserve and liability. The same native payout reference cannot clear
two exits. Deposit credit and owner-authorized pending recovery consume the same
single pending record, preventing credit/refund races across batches.

The native-fact functions are explicitly test-fixture interfaces. No bare owner
signature or this fixture API is a production withdrawal path. These transitions
are not yet proved in a guest/native adapter. NEXT-CHAIN.md specifies that gate.
