# Source refresh and reuse decisions — 2026-10-17

Before the model/compatibility prototype, current upstream heads and selected
primary files were read. Exact refs, URLs, byte lengths and SHA-256 digests are in
[evidence/source-review.json](evidence/source-review.json). Bounded prior Kaspa
privacy research was revisited, not declared exhaustive or reproduced on chain.
No restricted source code is imported into this prototype.

| Source | Inspected facts and pin | Reuse / adaptation / exclusion |
| --- | --- | --- |
| Kaspa docs and native verifier | Docs `0ac77d0`; native current head `f7d7877`, tested dependencies remain `01b532e`. Based App accepted ordering/settlement and native RISC0/Groth16 verification are distinct layers. | Reuse demonstrated backend/pins; do not assume a new native tree, private circuit, fee policy or archive guarantee. |
| vProgs and Kaspa Research | vProgs `f9b84a8`, research `c923fac`; selected batch verifier, host and draft specification inspected. Batch verifies journals/resources and folds even failed input IDs into activity. | Reuse reference batch/aggregate, control identity and native script. Full cross-app runtime draft does not supply KPI notes or an invalid-wallet-proof classifier. |
| RISC Zero | Actual SDK `3.0.3`, pinned guest `env/verify.rs`; current repo head recorded separately. `verify` adds a valid claim assumption, returns `Result<(), Infallible>`, and requires eventual resolution. | Measure wallet-to-outer composition. Do not interpret an absent assumption as a cryptographic `false` verdict permitting a no-op. |
| Orchard | Current `616a669`; note/nullifier/encryption sources and prior pinned book/spec review. Note commitment, rightful nullifier, hidden membership, authorization, ranges and conservation are separate requirements. Trial decryption must reconstruct/check commitments. | Reuse design obligations and separated wallet roles, not Halo2 security results or a new circuit by analogy. Exact note/key/encryption construction remains unselected. |
| Aztec | Current head `cfdcaf1`; prior pinned v5.2 source `49a5921` note interface read. Current same-path fetch returns 404, so the older source is explicitly a dated baseline. Unconstrained nullifier helpers are not proof constraints. | Reuse note/spentness/discovery lessons. Do not claim latest layout/API compatibility or adopt an entire runtime. |
| RAILGUN | Contracts `36bcf5e`, engine `6e2614d`, circuits `0aa2d13`; current pinned commitments, note code and license checked. Root history and current per-tree nullifiers are distinct. | Reuse conceptual conservation, scan-and-check and scoped spentness requirements. Circuit license says no license is provided; no circuit code copied. Model crypto uses separately licensed PyNaCl, not RAILGUN code. |
| Monero | Current `f8aba51`, selected RingCT verification plus prior wallet research. Authorization, range/balance and key-image checks are distinct; public fees and scanning assumptions matter. | Use as a privacy/leakage comparison. Do not transplant rings, claim a native Kaspa verifier, or claim anonymity from confidential amounts alone. |
| Litecoin MWEB | Current `ec1b648`, output-message fields and prior consensus/recovery note. Encrypted/masked values and scan data do not supply Orchard-style hidden input consumption. | Reuse scan/recovery/accounting questions. Identifiable spent outputs are not selected as KPI's hidden membership mechanism. |
| Existing Kaspa privacy work | `kaspa-xmss-covenants` current `6713eb0`: depth-two membership/nullifier circuit and demo deployment inspected; Argent `8751cc2` and KASSWORD `8af2e17` README source boundaries revisited. | Concrete membership is not full private conservation or current spentness/native payout binding. Claims without full source remain claims. No third-party pool safety or chain reproduction is inferred. |

## Proof combinations: at most two

1. **Leading local compatibility candidate:** local RISC Zero wallet statement ->
   fixed RISC Zero transaction adapter -> existing RISC Zero batch/aggregate ->
   fixed native covenant verifier. It reuses the already demonstrated composition
   and native control pins. The small measured relation is a preimage/checked-sum
   proxy, not a note circuit; receipt size, wallet hardware and invalidity handling
   can still make the complete route impractical.
2. **Comparison only:** a specialized BN254/Groth16 wallet circuit verified as
   ordinary computation inside the outer RISC Zero program, with the verifier
   result proved. This could return a deterministic valid/invalid result and may
   have different client costs, but requires an exact circuit/VK, setup and
   in-guest curve-verifier cost/format study. It is not implemented or benchmarked
   here; no speed or safety advantage is claimed. Kaspa's native Groth16 tag alone
   does not make it an automatically composed wallet proof.

Recommend route 1 for the next **unfunded verification/format investigation**, not
for immediate TN10 funding. The invalid-proof classifier, full private statement,
noncircular proof-carrying payload and authenticated deposit recovery must pass
review. If route 1 cannot meet these requirements at acceptable cost, investigate
route 2 against the same obligations. There is no third candidate or operator
network expansion in this work package.

## Cryptographic model boundary and rights

The Python model uses ordinary SHA-256/HMAC solely for opaque identifiers and an
ideal proof registry. Its formula is not a proposed production commitment/PRF.
PyNaCl 1.5.0 supplies existing Ed25519 signatures and sealed boxes for a logical
receiver demonstration; test keys are reproducible public fixtures, and this is
not the final receiving-address/note-encryption construction. No new primitive,
production security, post-quantum property or effective anonymity is asserted.
Sources were inspected for requirements/compatibility, not independently audited.
