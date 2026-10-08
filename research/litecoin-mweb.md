# Litecoin MWEB

**Reviewed: 2026-10-08.** Pinned Litecoin consensus/design documentation; no node or wallet run. MWEB is a native optional extension-block domain, not proof that equivalent application-level KAS covenants already exist.

## Source facts: commitments and spentness

The [consensus document][L1] specifies commitment balance, range proofs, kernels, unique input/output identifiers and UTXO validation. MWEB does not use an Orchard-style private-note nullifier set: spends consume identifiable outputs. [Kernel rules][L2] carry signatures, fees and peg-out information. Hidden amounts still require explicit bounded balance relations across peg-in and peg-out.

The [PMMR description][L3] and leaf set authenticate output structure and unspent positions. Cut-through can remove intermediate spent outputs. It reduces retained data, not knowledge already collected by a network observer.

## Discovery and recovery: P12 / P10

[Stealth-address design][L4] separates scan/spend keys and describes view tags and encrypted output information. Recipients reconstruct output keys and commitments before accepting funds.

The [light-client proposal][L5] explicitly warns that server-side filtering using the private view key reveals outputs and amounts to that server. Its compact-data approach aims at client-side filtering and independently verifiable UTXO retrieval. Treat the proposal as a design source, not evidence that every current wallet implements it.

**Interpretation:** a PMMR root or leaf-set digest cannot reconstruct unspent output data. Recovery needs authenticated compact outputs, the unspent positions, derivation information and keys. Restoring spendable unspent value is distinct from recovering complete historical activity; cut-through/pruning can remove the latter. KPI must define both expectations and cannot assume Litecoin's compact-data availability on Kaspa.

## Exits, fees, anonymity and scaling

Peg-outs publish destination/value information; kernel fees are public. Aggregation and cut-through obscure some transaction structure and reduce storage, but visible input/output use and observed timing still matter. The relevant anonymity model differs from private membership in a shared note tree.

The [weight specification][L6] bounds admitted resources; it is not a throughput benchmark. **Interpretation:** batching can amortize costs while creating fee, timing and batch-size fingerprints. A low-activity optional domain needs a separate privacy analysis regardless of compact historical data.

## Failure lessons and component assessment

The primary documents identify view-key server exposure, binding requirements and retention tradeoffs. This source review alleges no new current vulnerability. Curve commitments and stealth-key exchange are classical, and MWEB's verification rules are not directly equivalent to Kaspa's two ZK tags.

| Building block | Potentially reusable | Adaptation needed | Risks | Still to prove for KPI |
| --- | --- | --- | --- | --- |
| Commitment balance / kernels [L1][L2] | Explicit hidden balance plus public boundary accounting | Native sompi and covenant liabilities | Range failure; peg-out over-release | Exact conservation and authorized native withdrawal |
| UTXO identifiers / leaf set [L1][L3] | Authenticated current spentness | Determine privacy-compatible note/spend model | Visible input links; stale state | Double-spend prevention and required unlinkability together |
| Dual keys / view tags [L4] | Receiver discovery with reduced scan work | Kaspa note format and domain separation | Key leakage; incorrect reconstruction | Complete private scanning without trusted server filtering |
| Compact recovery data [L3][L5] | Authenticate independently fetched unspent state | Persistence and availability after Kaspa pruning | Root-only backup; lost ciphertexts | Clean restore after all preferred services disappear |
| Aggregation / cut-through [L1][L6] | Reduced storage and processing overhead | Preserve accepted-state and recovery evidence | Network observer retains links; lost historical data | Measured scale and privacy without deleting necessary recovery data |
| Peg-out / public fee boundary [L2] | Explicit native entry/exit accounting | Permissionless proving and fee funding | Amount/timing correlation; fee-wallet link | Independent exits with no privileged path |

**Open hypothesis:** compact authenticated recovery and scan-key separation can be useful even if MWEB's spend model is unsuitable. No model is selected; cryptographic migration, licensing and low-activity privacy remain to investigate.

[L1]: https://github.com/litecoin-project/litecoin/blob/ec1b6489a900d09cf5991e220dce089c77a232a2/doc/mweb/consensus.md
[L2]: https://github.com/litecoin-project/litecoin/blob/ec1b6489a900d09cf5991e220dce089c77a232a2/doc/mweb/kernels.md
[L3]: https://github.com/litecoin-project/litecoin/blob/ec1b6489a900d09cf5991e220dce089c77a232a2/doc/mweb/pmmr.md
[L4]: https://github.com/litecoin-project/litecoin/blob/ec1b6489a900d09cf5991e220dce089c77a232a2/doc/mweb/stealth-addresses.md
[L5]: https://github.com/litecoin-project/litecoin/blob/ec1b6489a900d09cf5991e220dce089c77a232a2/doc/mweb/light-clients.md
[L6]: https://github.com/litecoin-project/litecoin/blob/ec1b6489a900d09cf5991e220dce089c77a232a2/doc/mweb/weight.md
