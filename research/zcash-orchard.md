# Zcash Orchard

**Reviewed: 2026-10-08.** Primary specifications and selected source at the pins below; no code imported or executed. These are comparison inputs, not a security endorsement or a choice of KPI architecture.

## Source facts: notes, commitments and spends

An Orchard note contains a recipient, a 64-bit value, `rho` and a random seed. The seed derives commitment randomness and `psi`; the commitment binds the note fields. The nullifier implementation is `Extract_P([mod_r_p(PRF_nk(rho) + psi)] K + cm)`. Its relation to the committed note and spending authority must be proved, rather than letting a spender choose an arbitrary nullifier. Duplicate rejection is an additional consensus rule. See the [note implementation][O1], [protocol specification][O2], [nullifier implementation][O3] and [design rationale][O4].

An Action pairs a spend with an output; dummy spends/outputs obscure actual use within the declared bundle shape. Spend authorization and binding signatures enforce different responsibilities. Binding verification connects value commitments and the public `valueBalance` to conservation; membership alone would not do this. [Action design][O5], [bundle code][O12].

The [key hierarchy][O6] separates incoming viewing, full viewing and spending authority. An incoming view alone does not grant spending or complete outgoing-history knowledge. The [commitment tree][O7] is an ordered depth-32 tree with anchors; the nullifier set records spent notes separately. A valid old membership witness is insufficient if its nullifier is already spent.

## Discovery and recovery: P12 / P10

The [encryption implementation][O8] and [scanner][O10] provide a model for trial decryption followed by reconstruction and commitment checks. The actual [compact-block schema][O9] carries Orchard nullifiers, commitments, ephemeral keys, shortened ciphertexts and tree metadata. This supports incoming discovery, spend detection and witness updates; full transaction data is needed for information omitted from compact messages, including memos.

**Interpretation for KPI:** independent recovery needs keys, authenticated ordered commitments, nullifiers, ciphertexts and a way to rebuild witnesses. A root authenticates a state; it does not reconstruct the leaves or encrypted messages. Lightwallet service availability is a separate assumption from proof soundness. Kaspa's pruning behavior cannot inherit Zcash's history distribution merely by copying Orchard's note design.

## Fees, exits, anonymity and scaling

The public bundle balance permits value to cross between shielded and transparent domains. Transparent withdrawals expose destination and value at that boundary. A transaction funded wholly from shielded value need not add a transparent fee-paying input; fees and transaction shape remain observable. [ZIP 317][O11] prices logical actions, not the hidden transfer amount. Padding therefore has a cost.

**Interpretation:** an ordered shared pool gives notes a common membership universe, but effective anonymity depends on activity, timing, amount leakage at entry/exit and wallet behavior. A large historical tree does not guarantee privacy for a lone depositor. Splitting pools by asset, circuit version or shard can reduce candidates. Action aggregation amortizes overhead; it does not eliminate root ordering or nullifier conflicts. No Kaspa throughput figure follows from Orchard's deployment.

## Known failure and migration lesson

The official [Orchard security advisory][O13] documents an underconstrained variable-base scalar-multiplication gadget that enabled counterfeiting and related authorization failures. The repair changed circuit/verifier versions; historical exploitation could not simply be ruled out from shielded chain data. This is a historical vulnerability, not a claim that the reviewed repaired implementation remains vulnerable. The [changelog][O14] distinguishes legacy, post-NU6.2 and post-NU6.3 circuit versions.

**Lesson:** boundary tests and public aggregate reserve accounting cannot replace circuit soundness or preserve individual entitlements after an unsound circuit. Migration requires explicit old/new verifier domains, liabilities and withdrawal rules. Orchard's Pallas/Vesta cryptography is classical; neither the whole protocol nor a migration path is post-quantum by default. Kaspa's current verifier tags do not directly accept Orchard Halo2 proofs.

## Component assessment — provisional

| Building block | Potentially reusable | Adaptation needed | Risks | Still to prove for KPI |
| --- | --- | --- | --- | --- |
| Notes and separated keys [O1][O6] | Hidden values; view/spend separation | Native KAS units and domain-separated keys | Viewing-key exposure; incomplete backups | Receiver discovery and restoration without spending-key disclosure |
| Commitment/nullifier relation [O3][O4] | One authorized spend marker per note | Supported proof backend and pool/version binding | Underconstraints; cross-pool replay | Range checks, uniqueness and authorization in the actual circuit |
| Shared tree and spent set [O7] | Membership witnesses and duplicate detection | Kaspa ordering, reorgs and accepted roots | Stale roots; concurrent spends | Atomic current-state nullifier updates with acceptable contention |
| Compact scan [O8][O9][O10] | Local decryption and witness rebuilding | Authenticated archives after Kaspa pruning | Missing/censored ciphertexts; query linkage | Clean independent restore after all default services disappear |
| Bundle conservation / exits [O2][O12] | Explicit balance and authorization relations | Integer sompi and covenant-bound native outputs | Redirected payout; hidden liabilities | Internal private transfers and exact native withdrawals conserve value |
| Action fees / padding [O5][O11] | Fees funded from private value | Kaspa mass, relay policy and permissionless provers | Fee-payer linkage; low-activity fingerprints | Usable exit under fee changes without a public wallet link |
| Circuit migration [O13][O14] | Explicit verifier versioning | Recoverable old-pool liabilities and future cryptography | Legacy value stranded; forged state imported | Safe migration without privileged withdrawals or weakening invariants |

**Open hypothesis:** Orchard's note/nullifier relationships could be adapted to a Kaspa-supported proof system. That would be a new circuit and integration to review, not reuse of Orchard's security result. Licensing, proving cost, anonymity under low activity and P10/P12 remain open.

[O1]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/src/note.rs
[O2]: https://github.com/zcash/zips/blob/3af03aa3ad991874d86b8cf35919bc9b4671e8ba/zips/zip-0224.rst
[O3]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/src/note/nullifier.rs
[O4]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/book/src/design/nullifiers.md
[O5]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/book/src/design/actions.md
[O6]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/book/src/design/keys.md
[O7]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/book/src/design/commitment-tree.md
[O8]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/src/note_encryption.rs
[O9]: https://github.com/zcash/librustzcash/blob/b0ebed292204377ada53905add1c4b425965c280/zcash_client_backend/lightwallet-protocol/walletrpc/compact_formats.proto
[O10]: https://github.com/zcash/librustzcash/blob/b0ebed292204377ada53905add1c4b425965c280/zcash_client_backend/src/scan.rs
[O11]: https://github.com/zcash/zips/blob/3af03aa3ad991874d86b8cf35919bc9b4671e8ba/zips/zip-0317.rst
[O12]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/src/bundle.rs
[O13]: https://github.com/zcash/zcash/security/advisories/GHSA-ghc3-g8w4-whf9
[O14]: https://github.com/zcash/orchard/blob/616a669df8c9a59c33d47064d3ce04b25d026b2e/CHANGELOG.md
