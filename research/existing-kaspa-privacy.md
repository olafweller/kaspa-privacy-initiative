# Existing Kaspa Privacy Work

**Reviewed: 2026-10-08.** Active public-source search and selected implementation review. Facts below concern inspected source; author-reported execution is explicitly separate. No third-party code was built/run, and no testnet receipt, node or explorer was queried. This is a bounded survey, not an absence or novelty proof.

## Search scope and official upstream

GitHub repository searches included `kaspa shielded`, `kaspa mixer`, `kaspa privacy`, `PhantomPool` and `user:kaspanet privacy`. Public repositories under KaspaKii, aglov413, biryukovmaxim, mrzeku2000XTTT, kasperience and KASRANKS were enumerated. Search indexing is incomplete; private code, arbitrary forks and unindexed discussions are outside this survey.

At the [pinned official research tree][E1], the eight-file tree contains Ghostdag, Prunality and the [vProgs draft][E2], not a shielded-pool implementation. In `kaspanet/kips`, all-state issue/PR searches for privacy/shielded returned no matches; `zk` returned [KIP-16 PR #31](https://github.com/kaspanet/kips/pull/31) and [transaction-version PR #41](https://github.com/kaspanet/kips/pull/41). This is only the recorded search scope, not a claim that no relevant KIP discussions exist.

The prior [optional-privacy forum discussion](https://research.kas.pa/t/optional-privacy-layer-for-kaspa-similar-to-litecoin-mweb/522), dated 2026-09-08, asks about native KAS privacy with Toccata. It is a feasibility discussion, not a deployed protocol. The [refreshed Kaspa map](kaspa-toccata-vprogs.md) documents the actual verifier/settlement interfaces.

## Public pool code: mrzeku2000XTTT

At `83e82c365931abeb79cdccde0a980b68c84fc577`, [withdraw.circom][E3] proves membership in a depth-two commitment tree, with public root and nullifier hash. It constrains commitment `Poseidon(nullifier, secret)` and nullifier `Poseidon(nullifier)`. This is concrete circuit code, not just a social claim.

The [deployment script][E4] places a particular proof, public inputs and verifying key in the redeem script. Its proof branch verifies those constants; its fallback branch accepts an owner's signature. It does not inspect withdrawal destination/value or update/check a current spent-nullifier set. **Interpretation:** the reviewed script alone does not prevent redirecting a spend; a published valid membership proof is not continuing spend authorization. The owner fallback also conflicts with KPI's no-privileged-withdrawal requirement. Neither conservation of arbitrary hidden amounts nor a full private-transfer lifecycle follows.

The script defaults to mainnet. It was read only and must not be used as a runnable KPI demo. The [privacy roadmap][E5] describes future work separately. Reuse remains conceptual pending rights/security review; no code imported and no runtime acceptance independently checked.

## Published design and execution claims: MurrayWiki

The project's [shielded-pool design page](https://pq.murraywiki.org/zk/shielded-pool), observed 2026-10-08, describes a fixed-denomination covenant pool, commitment/nullifier roots and Groth16 withdrawals. The author reports TN10 deposit/withdrawal cycles and publishes transaction links, including a withdrawal beginning `4f11ba23` and a later withdrawal beginning `e4cfff96`. It states the complete source will open with its kUSD framework release.

**Evidence boundary:** the design and transaction references are public; their native bodies, proof/output bindings and accepted spentness were not independently checked here. Reported mass/fees are measurements attributed to the author, not current consensus guarantees. Unknowns include full circuits, setup, transfer/conservation semantics, recovery after pruning, note discovery, low-activity privacy and permissionless exits. A stablecoin-focused design does not establish native KAS backing. No identity or implementation equivalence with mrzeku2000XTTT or KASperience is assumed.

## Requested leads: PhantomPool / KasRanks and KASperience

| Lead and dated source | What is attributable | What remains unknown |
| --- | --- | --- |
| PhantomPool / KasRanks; [KasRanks hub](https://kasranks.com) and [public organization](https://github.com/KASRANKS), inspected 2026-10-08 | The requested name was searched. Four public repositories were enumerated; [KASSWORD README][E7] describes wallet/vault functionality. No attributable PhantomPool specification/code or technical claim was recovered within this search. | Exact project identity, architecture, code, receipts, recovery and privacy. No architecture or safety inferred from the name or unrelated search matches. |
| KASperience; [author account](https://x.com/KASperiencexyz), with text available through a [third-party mirror](https://doublecrosswebzine.twstalker.com/giavviola), observed 2026-10-08; original post date unresolved | Mirrored author text claims a TN10 shielded pool using consensus ZK, no trusted setup, key-bound notes and independent exits; another passage describes adapting KA$H to native KAS. **Unverified social claims.** | Primary post unavailable; no matching full pool code/receipts independently established. The public [argent compiler][E6], pin `8751cc2`, documents covenant actors, not those shielded-pool claims. No assumed link to a similarly named stablecoin repository. |

The blocked primary social source and unavailable complete pool sources are bounded open points. A mirror is not primary technical evidence. These leads require attributable code/specifications or complete receipts before a reuse assessment.

## Other public candidates: code versus labels

| Candidate / pinned source | Source facts and author claims | Assessment / unverified boundary |
| --- | --- | --- |
| WarpSwap, `81de13a` [README][E8], [contract code][E9] | README places ZK privacy in a future phase. The inspected contract is an amount-minus-floating-point-fee function, not a shielded transition verifier. | Repository metadata saying ZK is not implemented privacy. No pool accounting or accepted lifecycle established. |
| SolCipher, `536825b` [README][E10], [send code][E11] | README claims transaction privacy/scale. The inspected UI constructs an ID from time/randomness and changes status with a timer. | This send path is simulated UI behavior; labels do not prove encryption, ZK, consensus acceptance or hidden-value conservation. No exhaustive audit of all files claimed. |
| STP mixer-concept, `d29d715` [README][E12] | Educational/community concept; the README distinguishes it from a financial product. | A mixer search match, not demonstrated native-KAS mixing code. |
| FORAY, `bf12559` [README][E13] | Anchors hashes of business records; records remain with the business. | Data confidentiality differs from sender/receiver/amount privacy and recoverable shielded funds. |
| firecash/vprogs-zkas, `d254eb1` [README][E14], [competing-prover test][E15] | Prototype bridge to a separate shielded Kaspa fork; README reports real GPU proving and says native activation remains pending. A competition test exists. | Source/test presence is verified, execution and safety are not. Separate-ledger backing is outside KPI's native-domain assumption; no alternative token is proposed. Study binding/competition ideas only. |

## Existing PQ and runtime evidence

The [PQ experiment note](kaspa-post-quantum-experiments.md) already pins KaspaKii's RISC0 signature benchmark, aglov413's script-verified signatures and biryukovmaxim's XMSS covenant. Their public repositories were revisited as search leads. Its source/author-receipt boundaries remain; earlier chain observations were not refreshed during this no-testnet review. PQ signatures do not establish a shielded pool, hidden-amount conservation or quantum-resistant note encryption.

The [vProgs component assessment](kaspa-toccata-vprogs.md#vprogs-components--provisional-assessment) separates scheduler, storage, settlement and withdrawal machinery from actual private-note rules. Historical payout-amount issue #77 remains a lesson in checking liabilities and all outputs, not an allegation against the repaired pin. KPI's A0/A1 are its own scoped reserve evidence, not reproduction of any third-party pool.

## Interpretation and next evidence

A concrete membership circuit is useful prior work, but full source and enforced native payout/spentness matter more than a privacy label. This survey cannot close [P02](https://github.com/olafweller/kaspa-privacy-initiative/issues/2)'s reproduction criteria under the present source-only authorization.

**Open:** obtain complete attributable sources/rights for the claim-only leads; inspect actual conservation, authorization, spentness and recovery formats; later reproduce only under separately authorized testnet scope. Compare the mature [protocol component tables](README.md) before implementing. No A/B/C recommendation or architecture choice is made in this step.

[E1]: https://github.com/kaspanet/research/blob/c923faca11a49148fa7d912d27ce00197a5c5a4a/README.md
[E2]: https://github.com/kaspanet/research/blob/c923faca11a49148fa7d912d27ce00197a5c5a4a/vProgs/main.tex
[E3]: https://github.com/mrzeku2000XTTT/kaspa-xmss-covenants/blob/83e82c365931abeb79cdccde0a980b68c84fc577/covenants/privacy_pool/withdraw.circom
[E4]: https://github.com/mrzeku2000XTTT/kaspa-xmss-covenants/blob/83e82c365931abeb79cdccde0a980b68c84fc577/covenants/privacy_pool/deploy_pool_demo.mjs
[E5]: https://github.com/mrzeku2000XTTT/kaspa-xmss-covenants/blob/83e82c365931abeb79cdccde0a980b68c84fc577/research/PRIVACY_ROADMAP.md
[E6]: https://github.com/kasperience/argent/blob/8751cc2ef559732cc66539eb354360dddc84bfb5/README.md
[E7]: https://github.com/KASRANKS/KASSWORD/blob/8af2e17b26bf9b2af8d974768fd65fccb10663a7/README.md
[E8]: https://github.com/brunec22/WarpSwap/blob/81de13a7f9adae19f751a205885d6e4acd25310f/README.md
[E9]: https://github.com/brunec22/WarpSwap/blob/81de13a7f9adae19f751a205885d6e4acd25310f/contract/src/lib.rs
[E10]: https://github.com/mja2001/SolCipher_KASPA/blob/536825b58f7b6bc0286725da902588aa1168c467/README.md
[E11]: https://github.com/mja2001/SolCipher_KASPA/blob/536825b58f7b6bc0286725da902588aa1168c467/solcipher%20/SendTransaction
[E12]: https://github.com/STP-KAS/mixer-concept/blob/d29d715bd66c961fa412fd75659cd2e6ce98dbfa/README.md
[E13]: https://github.com/Kaspathon/foray-kaspathon/blob/bf125593b335d1c9c73b73e6fdf2c492cee62b2e/README.md
[E14]: https://github.com/firecash/vprogs-zkas/blob/d254eb1b1912410d8e1f158a3c171091b9985a63/README.md
[E15]: https://github.com/firecash/vprogs-zkas/blob/d254eb1b1912410d8e1f158a3c171091b9985a63/examples/tn10-flow/tests/two_provers_contend.rs
