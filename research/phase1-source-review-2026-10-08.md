# Phase 1 source review — 2026-10-08

Step 1 research input for P01/P02/P03, P10/P12 and issues #19/#23. No architecture selected, RFC comparison changed, implementation started or third-party demo reproduced. Every table is provisional.

## Evidence and method

- Default heads and recursive Git trees were resolved through the GitHub API. Selected raw source files were checked against their Git blob IDs. Exact commit/file links are in the individual notes; official specification/advisory pages are dated by this review where no immutable pin exists.
- [Kaspa primitives and vProgs](kaspa-toccata-vprogs.md) distinguish implemented consensus, relay policy, data retention, prototype components and full-runtime research.
- [Kaspa privacy survey](existing-kaspa-privacy.md) records search terms, inspected candidates, actual code, author-reported transactions, simulations and unavailable sources. Public transaction references were not resolved against testnet in this review.
- [Orchard](zcash-orchard.md), [Aztec v5.2.0](aztec.md), [RAILGUN V2](railgun.md), [Monero](monero.md) and [MWEB](litecoin-mweb.md) each contain a component table: potentially reusable, adaptation needed, risks and still to prove. This is source inspection, not an audit, license grant or proof of safety.

The primary KASperience social page could not be read; mirrored claims are explicitly unverified. No attributable PhantomPool specification was recovered from the bounded KasRanks search. MurrayWiki's full pool source is announced for a later release. These are follow-up requests, not reasons to infer architecture or keep searching indefinitely.

## Full-goal questions supported by the comparison

The following are **interpretations and open research questions**, grounded in the linked protocol notes, not implementation decisions.

| Topic | Existing mechanisms / Kaspa boundary | What remains to establish |
| --- | --- | --- |
| Sender/receiver/amount privacy | Orchard/RAILGUN use hidden membership spends; Monero uses rings; MWEB exposes spent output identifiers. Native KAS UTXO amounts and entry/exit outputs remain public. | Threat model for chain, network, service and wallet observers; quantify which links and amounts are actually hidden. |
| Low activity / common anonymity | A shared tree supplies candidates, not traffic. Public call shapes, fee funding, timing and denomination/version partitions narrow candidates. | Privacy for a lone/new user; padding/batching delay and cost; cross-shard transfers without identifying lanes. |
| Notes / conservation / spentness | Membership, authority, ranges, balance and duplicate rejection are separate relations. Kaspa's ZK opcode verifies the selected program, not the intended economic rules. | Native sompi semantics; hidden liabilities plus exact reserve/exits/fees; atomic nullifier updates and domain binding. |
| Contention and scaling | Independent proving can run in parallel; accepted roots/nullifiers and a shared reserve still constrain settlement. Indexed trees and batches reduce some costs. | Proving time/memory, L1 compute/storage/transient mass, witness refresh and actual conflict rates. No throughput claim from verifier-base cost alone. |
| P12 discovery | Orchard trial decryption, Aztec tags/handshakes, RAILGUN encrypted events and MWEB dual keys offer different tradeoffs. Querying a server can reveal wallet interests. | Local key separation, complete discovery including unknown senders, metadata backups and private retrieval under hostile servers. |
| P10 recovery / pruning | Roots authenticate; they do not reconstruct ciphertexts, leaves or nullifier history. Monero/MWEB retain different data from Kaspa. | Authenticated ordered data or recoverable snapshots plus updates, persistent ciphertexts and independent sources after all preferred operators disappear. Distinguish spendable-balance restore from full history. |
| Fees / permissionless operation (#23) | Shielded fee transfers or sponsor payments can avoid a user's public fee input; exit outputs, fees and relay traffic remain observable. RAILGUN separates relay policy from consensus and has a public fallback. | Independent prover/artifact access; dynamic fees authorized in conservation; service-free exit without introducing a user-wallet link or privileged withdrawal. |
| Cryptography / migration (#19) | Kaspa has Groth16 and RISC0 tags. PQ signature experiments concern authorization; classical note commitments/key exchange can still compromise privacy. Orchard's repaired circuit history shows verifier versions matter. | Evaluate proofs, signatures, commitments and encryption separately, including recorded-ciphertext exposure. Define liability-preserving user-authorized migration and replay domains; no assumed automatic PQ safety. |

## Review boundary and follow-up

Fund safety, independent recovery, privacy and scale are simultaneous acceptance conditions. A recoverable but linkable or unusably serialized system does not satisfy the goal. No component has been declared ready merely because code or tests exist.

Next research/review must resolve exact retained data, economic bindings, effective anonymity and resource limits before implementation. Step 2 will compare RFC alternatives against this evidence only after approval of stoppoint 1; this document contains no preliminary architecture recommendation. P01/P02/P03 remain open, and no GitHub issue status/comment was changed.
