# Open Research Questions

The initiative should treat these as questions to answer, not conclusions to defend.

## 1. Minimal Kaspa architecture

- What can be implemented today using current Toccata primitives?
- What requires covenants?
- What requires on-chain ZK verification?
- What requires sequence commitments / based-app infrastructure?
- Which functions, if any, truly require full vProgs?
- Can a minimal privacy proof-of-concept be built before vProgs stabilizes?

Primary question:

> **What is the minimal architecture for shielded native KAS using current Toccata primitives, and which parts actually require a based-app/vProgs architecture?**

## 2. Existing Kaspa work

- Has a usable TN10 shielded-pool implementation already been built?
- Which public repository, branch, or commit contains it?
- What are its trust assumptions?
- Which privacy properties are already proven and which are only claimed?
- Can we collaborate with or extend existing work rather than duplicate it?

## 3. State model

- Should private value use a note-based UTXO model?
- How are note commitments structured?
- How are nullifiers derived?
- How is the commitment tree maintained?
- Which state is public, encrypted, local to wallets, or reconstructable?
- Can a new independent node reconstruct everything required to verify the system?

## 4. Fund safety

- Can a malicious prover ever violate fund safety, or only delay progress?
- Can an executor alter balances without producing an accepted proof?
- Can any invalid transition cause the pool to become undercollateralized?
- How is overflow, rounding, or value-conservation handled?
- What exact integer equations cover deposits, transfer fees, withdrawal requests, pending exits, completed payouts, reserve rent, and externally sponsored fees?
- How does consuming a note into an unpaid exit preserve the outstanding user liability?
- How are malformed or duplicate nullifiers rejected?
- How do note inclusion, authenticated spent-state updates, and settlement duplicate rejection fit together?

## 5. Exits

- Can users exit without cooperation from one specific operator?
- What information must a user retain to prove ownership later?
- Can exits work if the normal prover network disappears?
- Is an emergency exit path required?
- How can any escape path preserve the same authorization, conservation, and single-spend requirements?
- Can an exit path itself create a privacy leak or theft vector?

## 6. ZK system

Candidate technologies may include:

- Groth16;
- Halo 2-style circuits;
- RISC Zero / zkVM-based proving;
- recursive or aggregated proofs;
- another construction supported efficiently by Kaspa.

Evaluation criteria:

- soundness assumptions;
- trusted setup requirements;
- proof size;
- verification cost on Kaspa;
- proving time;
- memory use;
- mobile feasibility;
- aggregation/recursion;
- audit maturity;
- implementation complexity.

Also specify whether proving is local or outsourced, what private data a prover receives, and how a confidential application avoids exposing spend material to an executor.

## 7. Privacy properties

Which properties are targets?

- sender privacy;
- recipient privacy;
- amount privacy;
- balance privacy;
- note ownership privacy;
- transaction-graph unlinkability;
- private change;
- wallet note-discovery privacy.

What remains observable?

- shielding events;
- unshielding events;
- timing;
- public fees;
- public network metadata;
- possibly unique deposit/withdrawal values.

## 8. Metadata and network privacy

- What can an RPC provider learn?
- Can a wallet discover notes without revealing which notes it owns?
- Should a recommended wallet support Tor/I2P or other relays?
- Is transaction broadcast itself identifying?
- How do mobile/light clients avoid leaking their private state to a server?

## 9. Scaling and concurrency

- Does a simple covenant pool create one-UTXO contention?
- Can state be safely sharded without damaging privacy?
- Which bottlenecks would batching reduce, and which remain at serialized covenant settlement?
- What distinguishes executed, proved, settled, and withdrawable balances?
- How often must L1 settlement occur?
- Can proofs be aggregated asynchronously so proving is not on the user critical path?

## 10. State availability and recovery

- What data must remain available forever?
- What data may be pruned?
- Which data must a user back up?
- What happens if all common state servers disappear?
- Can anyone rebuild the required state from Kaspa plus public protocol data?
- What history must be archived after Kaspa pruning, and who can independently retrieve it?
- How are witness/state updates rolled back or rebuilt on a reorg?

## 11. Wallet design

- How are private notes discovered and decrypted?
- How is change handled?
- Can the wallet warn users about dangerous unshield patterns?
- How should privacy quality/anonymity-set information be presented?
- Can hardware wallets safely support spending?

## 12. Economics

- What costs exist for L1 transactions, proving, storage, execution, relays, audits, and maintenance?
- Should shielding/unshielding carry a development fee?
- Should proving be a permissionless market?
- Could fees create central control or harmful incentives?
- How do we fund independent audits and long-term maintenance?

See [ECONOMICS.md](ECONOMICS.md).

## 13. Governance and upgrades

- How can upgrades occur without giving maintainers control over user funds?
- Can old versions continue independently?
- What changes are merely implementation changes versus protocol changes?
- Which security invariants may never be relaxed through ordinary governance?

## 14. Legal and operational questions

- Which roles could be treated as operating a service rather than publishing software?
- How do custody, frontend operation, fee collection, treasury management, and hosted proving change the analysis?
- What legal review is needed before mainnet or receiving protocol revenue?

See [research/legal-operational-questions.md](research/legal-operational-questions.md).

## 15. AI development

- Which tasks can be safely accelerated by AI?
- Which security-critical decisions require specialist human review?
- How do we prevent AI-generated assumptions from silently becoming protocol design?
- Which invariants can be machine-tested, model-checked, fuzzed, or formally verified?
