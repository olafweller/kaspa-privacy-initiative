# Source/reuse review

This bounded follow-up reuses the [PR35 mature-protocol review](../shielded-design/SOURCES.md)
and its exact source hashes. No new note/encryption/nullifier subsystem or
restricted third-party circuit source is imported. Orchard, Aztec, RAILGUN,
Monero, MWEB and prior Kaspa privacy work remain design references, not
implementations demonstrated by this classifier.

Upstream heads rechecked on 2026-10-17: RISC Zero main
`3bbcd44d6459b9ef6ac0df3846dc9215514934e8`, tag v3.0.3
`14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6`; Kaspa
`f7d7877363fb97c2ec6871be0e8cbc351d44df10`; vProgs
`f9b84a863a7c7c20586a9cf947550475e894f72e`. The tested compatible native pin
remains **01b532e8b553523216471682649693af92f0fd16**. Current heads are not
substituted for pinned tested dependencies.

## Inspected primary implementations

- RISC Zero SDK **3.0.3**, `receipt.rs`: ordinary
  `Receipt::verify_with_context` verifies seal integrity and exact successful
  wallet image/journal claim with no unresolved assumptions.
- SDK `receipt/succinct.rs`, `receipt/merkle.rs`: fixed verifier context,
  Poseidon2 suite and control-root inclusion. The control path validates actual
  code against trusted context, not host verdicts.
- Locked `risc0-zkp` host **3.0.4**, guest **3.0.5**:
  `verify/read_iop.rs` field/length decoding, `verify/mod.rs`
  `read_slice_with_po2`, and `core/hash/poseidon2/mod.rs` reduced-word assertions.
  Both versions extract the raw seal word for the cycle exponent. The prototype
  preflights the permitted profile instead of relying on a guest panic catch.
- SDK `guest/env/verify.rs`: recursive syscall remains a validity assumption,
  not an arbitrary submitted-proof classifier; it is not used by this guest.
- Pinned native `consensus/core/src/tx.rs`: v1 inputs require
  `new_with_compute_budget`, not the legacy sigop constructor.
- Pinned native `consensus/core/src/mass/mod.rs`, `config/params.rs`,
  `constants.rs`: SDK size/compute/transient calculation, block limits
  500,000 compute and 1,000,000 transient, transient bytes factor four.
- Pinned vProgs `l1/utils/src/tx_id.rs` and KPI canonical rest parser:
  native v1 payload/rest hashing, compared with actual SDK transaction IDs.

The ordinary receipt verifier is reused unchanged. Serialization and
domain-separated experiment hashes are local interfaces, not new primitives
or production privacy constructions. Lockfiles retain exact dependency trees;
the two transitively locked verifier versions are not called byte-identical.

## Comparison retained for the next decision

Specialized BN254/Groth16 remains the sole second candidate. Compare the same
small relation, intent binding, actual submitted-byte classification,
malformed-point/encoding bounds and expected-order checks. Measure wallet and
outer verification costs, circuit/VK/setup provenance, security/license
assumptions and full native encoding. No performance advantage or setup
acceptability is established here. Admission changes instead require their
own authenticated completeness, censorship and availability argument.
