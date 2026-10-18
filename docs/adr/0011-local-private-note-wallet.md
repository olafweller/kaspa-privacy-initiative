# ADR-0011: bounded local private-note wallet and economic transitions

Status: Accepted for an unfunded local experiment, 2026-10-18, following owner
approval of the post-PR43 work package. Not a production construction or TN10
funding decision. RFC-0001 remains open; all security invariants are unchanged.

## Decision and scope

Implement real BN254/Groth16 wallet proofs using the existing Arkworks 0.5 stack.
Use established SHA-256 and RFC2104 HMAC-SHA256 gadgets, a binary depth-two Merkle
tree (four slots), one hidden input and two fixed output slots. This deliberately
small capacity covers credit 10 -> Bob 4 + change 6 -> whole-note Bob exit 4.
Unused slots are explicitly inactive zero-value padding, never spendable notes.
The public economic domain is local-only; no native funding/signing is enabled.

A note has owner hash, X25519 incoming key, u64 sompi value and 256-bit randomness.
The owner hash binds the spending secret and incoming public key. A domain-tagged
SHA256 commitment binds the complete note. Hidden membership and ownership are
constrained in the actual circuit. The economic nullifier is HMAC-SHA256 keyed
by the spending secret over the immutable economic domain and note commitment;
it excludes root, leaf index, intent and verifier version. It is therefore stable
for competing proofs from different permitted historical roots and batches.
All intermediates in conservation are bounded u64 limbs whose sum is below the
BN254 scalar modulus, so equality cannot hide integer carry/field wrap.

Use RustCrypto's existing crypto_box sealed-box implementation (X25519 /
XSalsa20-Poly1305), not new encryption arithmetic or restricted RAILGUN code.
Owner/encryption addresses are exchanged over an authenticated channel in this
experiment. Fixed-size ciphertext digests and all output commitments, fee/exit/
deposit fields, network/pool domain and verifier identity are bound to the public
wallet statement. Public bytes pack in at most 31-byte little-endian field limbs;
this injective representation does not reduce a 256-bit digest modulo Fr.

Encryption correctness is not proved inside this first circuit, as distinct
from binding the actual ciphertext bytes. Recipient acceptance requires successful
local decryption, canonical note parsing, matching owner/incoming key, commitment
reconstruction and membership in accepted public data. A malicious sender can
burn their own note with bad delivery; that is not a received payment. Viewing
material alone cannot authorize a spend. No claim of effective anonymity follows
from this one-depositor/one-payment workload.

A local application kernel verifies the real wallet proof before atomic state
updates. It maintains current nullifiers across batches, allowed historical
roots, single-consumption deposit credit/recovery states and backed unpaid exits.
Public private-liability totals change only at deposit/exit boundaries. Transfers
never require the executor to learn input leaf, witness, note values or keys.
This kernel is not yet a proved outer guest or a native deposit/payout oracle.
Native facts in its tests are explicitly authenticated-fixture inputs; a pending
exit is not a completed native payout. Fees are explicitly zero app fees for this
first relation; native costs require an external test sponsor in a later trial.

New wallet circuit/VK pins are recorded independently. PR43's image/receipt remain
an unchanged baseline; new outer program IDs are not inferred from old artifacts.
No new wallet witness is sent to B, a GPU, an RPC service or an external prover.
The local test wallet generates its own experimental secrets; they are neither
serialized to evidence nor user fund keys.

## Sources and alternatives

Review and exact upstream refs are in the package SOURCES.md and evidence. Reuse
Orchard's separation of membership/authorization/current spentness and recipient
commitment validation; Aztec's distinction between constrained and unconstrained
nullifiers; RAILGUN's root-history/current-nullifier separation; Monero/MWEB's
range, balance, scanning and data-availability lessons. Do not transplant their
curve-specific constructions or claim their security analyses for this adaptation.
SHA/HMAC is chosen for existing maintained primitive implementations and available
Arkworks gadgets, accepting cost. Poseidon/new permutation parameters, Orchard
Pallas/Halo2 and unlicensed RAILGUN circuits are not selected. This experimental
composition still needs independent cryptographic review before any funding.

## Next gates

Port meaningful attacks to circuit, real verifier, recipient and live state layers;
measure setup, wallet proving/verification, constraints, serialized operation and
RSS. Connect the new statement to transaction/batch/aggregate and native Succinct
verification in a subsequent bounded local proof-chain run, then a fresh TN10
rehearsal only after its full requirements are met. No GPU rental/transaction is
authorized by this local implementation step. No privileged native withdrawal
path, migration rule, general operator network or production capacity is added.
