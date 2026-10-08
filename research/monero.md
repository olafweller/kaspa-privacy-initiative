# Monero

**Reviewed: 2026-10-08.** Selected upstream implementation and primary research; no wallet/node run. Monero is a native privacy system, not a shielded-pool implementation to transplant.

## Source facts

[Transaction construction][M1] creates one-time output keys and key images. RingCT's [verification implementation][M2] combines CLSAG authorization, confidential commitments, range proofs and balance checks; [types][M3] make the public fee and proof components explicit. A key image is a spend marker bound to the secret behind a ring member. Ring membership, key-image uniqueness and confidential value conservation solve different problems.

[Wallet scanning][M4] uses view/spend key roles, output derivations and encrypted amount information. View tags reduce work before full checks. Incoming viewing authority does not provide all information needed to determine outgoing spentness: key images or spending authority are also relevant. A restore height trades scanning cost against the risk of omitting older funds.

The official [pruning description][M5] distinguishes retained transaction base data from prunable signature/proof data. Output discovery and spend markers therefore have different retention needs from full proof revalidation. **Interpretation for P10/P12:** define which authenticated data remains sufficient for balances, which requires an archive, and what a seed backup cannot recover. Do not assume Kaspa's pruning makes the same split.

## Privacy, fees and scaling

Native XMR transfers do not require a separate transparent-domain reserve exit; this does not solve KPI's covenant release problem. Fees remain public. The relevant sender ambiguity is the input ring with sampled decoys, not every historical output on the chain. Confidential amounts and one-time receiver keys complement that mechanism.

**Interpretation:** default privacy encourages activity, but wallet fingerprints, timing and decoy quality still narrow candidates. Parallel verification does not enlarge a ring or remove double-spend state. Proof/transaction aggregation, if adapted, would need its own measured resource and anonymity analysis.

## Known attacks and lessons

Primary papers on [historical traceability][M6] and a [wallet decoy-selection bug][M7] show how low-mixin history and implementation behavior can undermine nominal anonymity. Their studied periods and attacks are historical; this review does not apply those success rates to today's Monero. The lesson is to measure wallet behavior and effective candidate sets, rather than reporting a configured anonymity-set size as achieved privacy.

CLSAG, curve commitments and key exchange are classical. Current Kaspa tags do not directly expose Monero's entire verifier. Re-proving its rules inside a supported VM is a hypothesis with new costs and assumptions, not a checked integration.

## Component assessment — provisional

| Building block | Potentially reusable | Adaptation needed | Risks | Still to prove for KPI |
| --- | --- | --- | --- | --- |
| Confidential commitments / ranges [M2][M3] | Hidden amounts with bounded conservation | Sompi semantics and supported backend | Overflow; unmatched commitment sums | No inflation at transfers, fees or native exits |
| Key images / authorization [M1][M2] | Spend marker tied to secret authority | Choose actual note/ring model and replay domain | Decoy confusion; duplicate markers | Unauthorized and repeated spends fail |
| One-time keys / scanning [M1][M4] | Receiver privacy and scan/spend separation | Kaspa ciphertext history and wallet format | Restore-height omission; view-key leakage | Complete local discovery and spentness recovery |
| Retained base data [M5] | Separate recovery from bulky proof retention | Explicit Kaspa archive/authentication plan | Missing proof history or ciphertexts | Clean recovery after pruning and service loss |
| Effective anonymity analysis [M6][M7] | Wallet-distribution and fingerprint tests | Optional-domain, low-activity traffic model | Nominal set overstates privacy | Sender/receiver/amount privacy under adversarial observations |
| Native fee/accounting model [M2][M3] | Public fee balanced against hidden values | Covenant reserve and permissionless exit | Public fee funding links; stuck reserve | Native KAS release without default prover or public-wallet linkage |

**Open:** licensing and backend compatibility, long-term archives, network-observer protection, and migration preserving both funds and privacy. Monero is a useful counterpoint to pool-based anonymity, not evidence that rings are the best KPI model.

[M1]: https://github.com/monero-project/monero/blob/7778a369afdb788af245ba5ac4d5b17d5a2cc4c5/src/cryptonote_core/cryptonote_tx_utils.cpp
[M2]: https://github.com/monero-project/monero/blob/7778a369afdb788af245ba5ac4d5b17d5a2cc4c5/src/ringct/rctSigs.cpp
[M3]: https://github.com/monero-project/monero/blob/7778a369afdb788af245ba5ac4d5b17d5a2cc4c5/src/ringct/rctTypes.h
[M4]: https://github.com/monero-project/monero/blob/7778a369afdb788af245ba5ac4d5b17d5a2cc4c5/src/wallet/wallet2.cpp
[M5]: https://www.getmonero.org/resources/moneropedia/pruning.html
[M6]: https://arxiv.org/abs/1704.04299
[M7]: https://arxiv.org/abs/2408.05332
