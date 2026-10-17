# Sources and reuse

This comparison reuses the [PR35 mature-protocol review](../shielded-design/SOURCES.md),
the [PR36 verifier review](../proof-classification/SOURCES.md) and the same native
v1 hashing/mass implementation. No new note/nullifier/encryption construction
or restricted RAILGUN circuit is imported. Orchard, Aztec, RAILGUN, Monero, MWEB
and prior Kaspa privacy experiments remain requirements/recovery references.

On 2026-10-17 current upstream heads were rechecked: Arkworks Groth16
`8f0904a7d7a2c8945bf770bdd3c2081e0be1941a`, vProgs
`f9b84a863a7c7c20586a9cf947550475e894f72e`, Kaspa
`f7d7877363fb97c2ec6871be0e8cbc351d44df10`, Kaspa Research
`c923faca11a49148fa7d912d27ce00197a5c5a4a`. Tested libraries are the locked
**Arkworks 0.5** tree, RISC Zero **3.0.3**, compatible native **01b532e** and
the same pinned vProgs; current upstream heads are not substituted silently.

## Primary implementations inspected and reused

- Arkworks `ark-groth16` 0.5.0 `generator.rs`, `prover.rs`, `verifier.rs`,
  `data_structures.rs`: circuit-specific setup/proof and actual prepared-key
  pairing verification. No receipt compression/wrapper is used.
- `ark-crypto-primitives` 0.5.0 `crh/sha256/constraints.rs`: standard SHA-256
  R1CS gadget; all original hashes and complete intent binding retained.
- `ark-r1cs-std` 0.5.0 `uint8.rs`, integer, Boolean and field conversions:
  64-bit witness ranges and matching host/gadget packing of the exact journal.
- `ark-bn254` 0.5.0 `curves/g2.rs`: maintained correct-subgroup test, referencing
  [2022/352](https://eprint.iacr.org/2022/352). The prototype does not implement
  its own pairing or subgroup primitive. An actual outside-subgroup point is a
  negative fixture, never a fallback accepted point.
- `ark-serialize` checked canonical decoding: applied to every submitted proof;
  fixed byte length, no trailing bytes and exact reserialization required.
- RISC Zero `risc0-groth16` 3.0.5 verifier inspected as an implementation
  comparison: it also uses Arkworks prepared pairing verification. It is not
  claimed as an implemented faster backend or a third proof architecture.

Arkworks dependencies use their existing MIT/Apache-2.0 licensing and are pinned
by Cargo.lock. The new circuit is this repository's direct translation of its
small synthetic predicate, not copied mature privacy circuit code. Exact source
hashes and public parameter/program identities are retained with the evidence.
