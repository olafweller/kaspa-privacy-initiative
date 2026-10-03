# A0 proof statement and existing-work review

**Scope:** one terminal claim, for a local native-test-KAS reserve experiment. This is not a shielded payment protocol, an accepted Candidate A architecture, or a new note/nullifier construction. See [the A0 experiment report](poc-a0.md) for execution results and the actual network evidence boundary.

## Statement

The private witness is one uniformly sampled 32-byte authorization secret `s`. Circuit setup fixes:

- `C = SHA256(s)`, the claim's public authorization commitment;
- a canonical context prefix containing the protocol/version label, TN10 genesis identifier, unique claim/state identifier, native input reserve amount `R`, recipient script including its version, native payout `A`, explicit fee buffer `F`, and the terminal-transition marker.

The circuit proves both equations:

```text
SHA256(s) = C
SHA256(context_prefix || s || outpoint_txid_32 || outpoint_index_LE32) = T
```

`T` is a public tag supplied with the proof, not a trusted verifier result or a standalone signature/MAC scheme. The Groth16 relation jointly binds it to the fixed claim, fixed transaction terms, private secret, and actual reserve outpoint. It is used to ensure the dynamic context participates in hash constraints rather than becoming unused public inputs.

The outpoint becomes known after funding. Separating the initial claim commitment from the second hash avoids circularly committing the funding transaction to its own transaction ID. There is no hash-preimage computation by the script and no publication of `s` in the spending witness.

Public field elements, in verifier order, are:

| Position | Meaning | Circuit range |
| --- | --- | --- |
| 0 | transaction-ID bytes 0–15, interpreted little endian | 128 bits |
| 1 | transaction-ID bytes 16–31, interpreted little endian | 128 bits |
| 2 | outpoint index, little endian | 32 bits |
| 3 | tag bytes 0–15, interpreted little endian | 128 bits |
| 4 | tag bytes 16–31, interpreted little endian | 128 bits |

Each field is canonically serialized as a 32-byte BN254 scalar for the precompile. The circuit decomposes its scalar into bits and requires every bit above the stated width to be zero. Hashes are split losslessly into limbs; no 256-bit digest is reduced modulo the scalar field. The dynamic hash suffix is exactly 36 bytes. The prefix is serialized as:

```text
ASCII "KPI-A0/TN10/terminal/v1" || 0x00
|| TN10_genesis_hash32 || random_claim_state_id32
|| R_LE64 || A_LE64 || F_LE64
|| recipient_SPK_byte_length_LE32 || recipient_SPK_bytes
|| 0x01
```

`recipient_SPK_bytes` is the consensus `OpTxOutputSpk` encoding: two-byte big-endian script version followed by the script bytes. The harness implements this byte encoding because upstream's `SpkEncoding` trait is private. The fixed-length hashes/integers and explicit script length remove concatenation ambiguity. Changing a fixed prefix byte or `C` requires a different circuit-specific verification key.

The proving/verification key is specific to this single claim's constants. This deliberately inefficient choice keeps A0 narrow; it is not a recommendation for multiuser setup or protocol key management. The reserve redeem script pins the exact compressed verifying key. It must not accept a caller-selected key, program, or claim commitment.

## What actually binds a payout

The proof alone does not establish that an output exists or pays the correct amount. The locking script checks the actual transaction: one reserve input, one payout output, exact input amount, exact output amount, and full recipient script/version. It constructs the outpoint public fields directly from `OpOutpointTxId` and `OpOutpointIndex`; the spender does not supply those fields. The circuit's fixed prefix commits to the same terms, and the script commits to that circuit's verifying key. Therefore a mismatch in either layer rejects.

There is no successor reserve or pending withdrawal in this terminal experiment. State is the current reserve UTXO plus its pinned claim terms. Successful settlement consumes that UTXO and fully pays its one outstanding claim. Kaspa's UTXO-set membership checks, not the SHA256 tag or a custom nullifier, prevent a second spend. The local harness supplies its own UTXO entry: even `TransactionValidator` with `Full` flags cannot establish that this outpoint currently exists or remains unspent in TN10's UTXO set. Repeating an identical valid transaction against the supplied entry therefore passes locally. Actual node UTXO-set lookup and spend processing are required to reject an already consumed outpoint; that live boundary must be tested separately.

Accounting is explicitly:

```text
Before: user liability = A; user backing = A; separate fee buffer = F
        reserve input R = A + F, checked integer arithmetic
After:  payout = A; fee = F; liability = 0; remaining user reserve = 0
```

The fee buffer is not counted as spendable user value. No value is debited into an unpaid intermediate exit. A0 assumes this is the only claim against this reserve; it does not establish a private supply commitment, multiuser liability accounting, deposit issuance, transfer conservation, or recovery after all services disappear. Funding the same script multiple times creates distinct UTXOs; each proof binds its actual outpoint. Independent deployment must use fresh claim/state identifiers and secrets.

The fixed domain distinguishes differently configured A0 instances. A genesis identifier in the circuit is an application constant, not a consensus assertion of the current chain's identity: the script has no genesis-introspection opcode. An identical state/outpoint/script replicated on a fork or independently reproduced environment is not excluded by this documentary domain identifier alone. Do not claim absolute cross-chain replay resistance.

## Reused cryptography and assumptions

The experiment uses Groth16 over BN254 through Arkworks `0.6.0`, as supported directly by Kaspa's tag `0x20`. It reuses the [Arkworks SHA256 constraint gadget at release v0.6.0](https://github.com/arkworks-rs/crypto-primitives/blob/ba00127bf673d93d73a3e8bf969cb9eeced20d12/crypto-primitives/src/crh/sha256/constraints.rs), under MIT/Apache-2.0 terms, rather than implementing SHA256 constraints. The native witness preparation uses SHA-256 and must agree byte-for-byte with the circuit.

Groth16 has a circuit-specific trusted setup. Local ephemeral setup is acceptable evidence for this test, but is not a secure multiparty ceremony or production parameter provenance. Setup compromise can defeat authorization. The key, constants, libraries, verifier implementation, random-number generator, and canonical encodings are all part of the experiment's trusted computing assumptions. Fresh randomness is required for setup, the secret, and proving; no deterministic publicly known secret should control actual funds.

BN254 pairing assumptions and Groth16 are not post-quantum secure. SHA256 does not make the combined construction post-quantum secure. A small circuit is easier to inspect, but neither passing tests nor this review proves cryptographic correctness.

The public chain sees funding and payout amounts, recipient script, timing, the fixed verification key, proof, tag, and outpoint. The claim commitment is a circuit constant bound through the verification key, not separately serialized in this transaction. This one-claim construction provides no demonstrated anonymity or unlinkability. Local proving keeps the witness inside the local process; hosted proving would disclose it to that service unless a separately reviewed confidential proving design were used. Proof and tag bytes must never be mistaken for encrypted note delivery or a recovery archive.

## Existing-work comparison before implementation

The existing repository research notes were read first. The following additional source inspection was performed for A0 on October 3, 2026. These are targeted source reviews, not audits or reproduced deployments. No code from the mature payment protocols was imported.

| Source reviewed | Finding relevant to A0 | Reuse/adapt/reject decision |
| --- | --- | --- |
| [Kaspa inline ZK guide, `0ac77d0`](https://github.com/kaspanet/docs/blob/0ac77d043a802fc8196abfd5812ac2afbd97a2b9/content/docs/toccata/inline-zk.mdx) | Proof verification and actual output validation are separate obligations within the covenant spend. | Adapt the direct proof-plus-introspection pattern. |
| [Kaspa Groth16 precompile, `01b532e`](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/groth16/mod.rs) and [field parsing](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/fields/mod.rs) | Compressed Arkworks proof/key, canonical 32-byte scalar inputs, key arity checks, trailing-byte rejection and metering. | Use this actual consensus implementation and its ABI. |
| [Kaspa ZK SDK, same commit](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/zk-sdk/src/zk_to_script/builder/commit/groth16.rs) | Its Groth16 builder wraps RISC Zero receipts/image IDs rather than being a generic custom-circuit prover. | Do not confuse its RISC Zero wrapper with the generic BN254 precompile. Direct Arkworks encoding is smaller for A0. |
| [vProgs settlement, `f9b84a8`](https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/covenant/src/settlement.rs) | Contains real-proof and development settlement paths; larger runtime/lane scope. | Study boundaries; reject development verification as A0 evidence. No runtime dependency. |
| [Kaspa research draft, `c923fac`](https://github.com/kaspanet/research/blob/c923faca11a49148fa7d912d27ce00197a5c5a4a/vProgs/main.tex) | Computational dependencies/composition are a broader architecture than one terminal claim. | Defer full vProgs; this experiment cannot decide whether the future protocol needs it. |
| [Orchard nullifiers, `616a669`](https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/src/note/nullifier.rs) | Nullifiers derive from dedicated key material, note randomness and commitment; consensus uniqueness is a separate obligation. | Do not replace Orchard-style note nullification with an improvised hash. Use native UTXO consumption for this expressly narrower experiment. |
| [Aztec nullifier context, `551aa41`](https://github.com/AztecProtocol/aztec-packages/blob/551aa413aec7c497886b567d83674f6e7edfae2f/noir-projects/fnd/noir-contracts/contracts/protocol/aztec_sublib/src/nullifier/utils.nr) and [nullifier leaf](https://github.com/AztecProtocol/aztec-packages/blob/551aa413aec7c497886b567d83674f6e7edfae2f/noir-projects/fnd/noir-protocol-circuits/crates/types/src/abis/nullifier_leaf_preimage.nr) | Application siloing, authenticated settled state and pending state are distinct; hints require kernel validation. | Bind domain/current state, but defer nullifier-tree and pending-state machinery. |
| [RAILGUN JoinSplit, `0aa2d13`](https://github.com/Railgun-Privacy/circuits-v2/blob/0aa2d13763a9fcfbb7b7ea9c02e004e71f1394bb/src/library/joinsplit.circom) | Authorization hashes public signals including bound parameters; circuit separately checks membership, nullifiers, output ranges and balance. | Apply the lesson that authorization must bind settlement terms. Do not copy its circuit: [License.md](https://github.com/Railgun-Privacy/circuits-v2/blob/0aa2d13763a9fcfbb7b7ea9c02e004e71f1394bb/License.md) says no license is provided. |
| [Monero RingCT implementation, `160e215`](https://github.com/monero-project/monero/blob/160e21504aed2a9b6dfdba0970517161383b04e5/src/ringct/rctSigs.cpp) | Range proofs, commitment balance and spend authorization are distinct checks. | Keep explicit integer/accounting checks; do not import RingCT/ring-signature infrastructure into this fixed public withdrawal. |
| [Litecoin MWEB light-client notes, `ec1b648`](https://github.com/litecoin-project/litecoin/blob/ec1b6489a900d09cf5991e220dce089c77a232a2/doc/mweb/light-clients.md) | Server-side view-key filtering reveals ownership and amounts; client-side reconstruction has data requirements. | No scanning implementation is justified for A0; make no wallet-recovery or network-privacy claim. |

Some linked documentation sites were unavailable through the workspace's network policy. Exact Git source was used for the comparison where available. This limited review did not establish that no other Kaspa privacy implementation exists; the repository's [existing-work map](../research/existing-kaspa-privacy.md) remains a bounded survey.

## Why this proof path

Generic Groth16 verification is already present in the pinned node, and a two-hash authorization circuit avoids introducing a guest runtime or bespoke cryptographic primitive. RISC Zero Succinct is a valid separate candidate but entails a guest image, receipt/control parameters and a larger toolchain. Halo 2, Orchard's note system, Monero's RingCT and MWEB are not native substitutes for Kaspa's current verifier ABI. This spike selects none of them for the eventual KPI protocol.
