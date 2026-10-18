# Source/reuse review — 2026-10-18

The current upstream heads of Kaspa docs/vProgs/research, Orchard, Aztec,
RAILGUN contract/engine and Litecoin still match the 2026-10-17 source review.
Monero advanced to `183b5e962401092ba6e1ea1a2e4774800851f693`; its current
`src/ringct/rctSigs.cpp` was downloaded and inspected for distinct range/balance/
authorization enforcement. Nineteen prior pinned primary files were hash-checked
and the relevant selected contents reread before this implementation. See the
copied source evidence and the detailed existing review in
[shielded-design/SOURCES.md](../shielded-design/SOURCES.md).

- Kaspa Toccata/native Succinct and vProgs: retain the transaction/batch/aggregate
  backend, authenticated ordering and 352-byte native aggregate ABI. The 167-byte
  PR43 classifier journal is not a drop-in replacement. New note-state guest
  identities and deposit/payout facts must be integrated and proved later.
- Orchard: separate hidden membership, authorization, nullifier derivation and
  current spentness; trial-decrypt and reconstruct/check commitments before
  accepting a receipt. No Orchard circuit/curve construction or security result
  is copied into this SHA/Groth16 experiment.
- Aztec: actual constrained nullifier derivation is required; an unconstrained
  helper or a caller-supplied marker cannot authorize economic consumption.
- RAILGUN: old membership anchors are different from current nullifier state;
  conservation and encrypted scan data are separate obligations. The inspected
  circuits-v2 license supplies no license: no circuit source is copied.
- Monero: spending authority, range/balance and duplicate-consumption checks have
  separate enforcing layers. No rings/key-image construction is transplanted.
- Litecoin MWEB: encrypted scan data and recovery are necessary but do not by
  themselves provide hidden input membership. No MWEB implementation is copied.
- Existing Kaspa privacy work: the pinned depth-two withdrawal membership example
  is useful prior art, not complete hidden transfer/conservation/state or native
  payout binding. No third-party pool is assumed safe or reproduced on chain.

Implementation uses the pinned Arkworks SHA256 R1CS/Groth16 libraries under their
MIT/Apache licenses, RFC2104's standard HMAC composition, RustCrypto crypto_box
sealed boxes (existing X25519/XSalsa20-Poly1305), sha2/hmac and OS randomness.
No custom curve/pairing/encryption primitive or Poseidon parameter set is added.
The concrete experimental protocol composition and security assumptions are in
[ADR-0011](../../docs/adr/0011-local-private-note-wallet.md). Proof-bound ciphertext
bytes do not amount to a proof of encryption correctness; recipient checks are
required and covered at their actual layer.
