# Open Research Questions

The initiative should treat these as questions to answer, not conclusions to defend.

The [local receipt-classification follow-up](poc/proof-classification/RESULTS.md)
executes valid-invalid-valid processing, but needs 880 proof segments; no outer
receipt or actual accepted-lane integration is demonstrated. Affordable proved
classification, full private note rules and complete native budgets remain open.

The [specialized comparison](poc/groth16-comparison/RESULTS.md) demonstrates small
real wallet proofs, while in-guest verification exceeds its agreed 32-million-cycle
cap. Which maintained verifier backend and declared practical budget can produce
the complete outer classification receipt without weakening the statement?

The [concrete accelerated backend](poc/accelerated-bn254/RESULTS.md) is compatible
and completes the same sequence in 117.47M cycles, measured under a separate 128M
calibration cap. Should a new practical 128M experiment qualify full adversarial
execution and attempt one real outer proof within the unchanged one-hour cap?
The original 32M result and absence of any outer receipt remain unchanged.

That [128M phase has now run](poc/outer-proof-128m/RESULTS.md): all 24 full/narrow
execution cases pass, but one real proof job reaches its one-hour stop without
returning a receipt. Which segment-proving/compression work and memory/cache
behavior dominate the bounded prover cost? The complete cost remains unknown;
do not infer total proving throughput from execution time or claim a receipt.

The [bounded phase diagnostics](poc/proof-phase-diagnostics/RESULTS.md) now retain
five real partial receipts, independently reverified: two full segments cost
415-421 seconds each, lift 33-34 seconds and join 36 seconds. Can the official
pinned CUDA prover qualify these same assets at a suitable cost before another
full attempt? Full-session proof costs and GPU compatibility remain unmeasured.

The [A0.5 terminal reserve experiment](docs/poc-a0.md) and its retained-key/native-RPC
adapter test one narrow proof-authorized payout. They do not answer the open
private-state, independent-recovery or anonymity questions. [Draft A1 PR #22](https://github.com/olafweller/kaspa-privacy-initiative/pull/22) adds local/native-synthetic successor-liability evidence and qualification repairs; full G5 and live G6 remain unclosed/unexecuted respectively. Fixed-fee exit liveness is tracked in [issue #23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23).
Live outcome and remaining validation gaps belong to that evidence report.

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

- Can users exit without cooperation from a privileged operator?
- What exact Kaspa L1 covenant/script verifies or consumes the result of an unshield proof?
- What exact public inputs must be bound to that proof?
- How does a valid proof cryptographically authorize the corresponding native KAS payout?
- What information must a user retain to prove ownership later?
- Can the same exit be independently constructed after every normal operator/prover has disappeared?
- What data must come from L1, what may come from independently reconstructable protocol history, and what must the user retain privately?
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

## Public based-app native-value integration follow-up

The [2026-10-17 source map](poc/native-value/MAPPING.md) identifies existing
Deposit/Withdraw actions, delegate reserve scripts and permission claims. The
bounded experiment is [ADR-0004](docs/adr/0004-public-based-app-native-value.md).
Outstanding questions remain: scalable proof composition beyond the fixed
monolithic circuit, data availability and takeover after pruning/reorg, a stated
progress policy (no mandatory latest checkpoint was found), private authorization
and confidential execution. Passing the public cycle would not resolve them.

The [recursive adapter review](poc/takeover/README.md) now isolates composition
from those open questions. A coarse public state resource can exercise the
reference recursive interface locally; it does not establish scalable private
state, true native expiry, missing-history recovery or guaranteed exits. A fresh
long-gap TN10 rehearsal has now [completed through native payout](poc/takeover/LIVE-REHEARSAL.md)
after a 175-blue-score stop gap. This narrows that empirical question for the
tested same-owner/node public replay; it leaves the above recovery and privacy
questions open.

## After the public Based App feasibility milestone

The [five-criterion integration question](docs/based-app-feasibility-2026-10-17.md)
is answered positively for the recorded public TN10 experiments. It does not
close P01-P03 in full or private note/nullifier, financial-privacy, discovery,
exit-fee and recovery questions. The [next work package](docs/shielded-kas-next.md)
prioritizes these private-protocol requirements against the existing issues;
new public runtime/operator infrastructure needs a demonstrated purpose.

## Questions exposed by the first shielded local package

The [proposed private statement](docs/rfc/0002-shielded-payment.md) asks how to
prove invalid-proof rejection without an executor skip flag or whole-batch-only
halt; how to bind a wallet intent without circularly including its own proof's
native transaction ID; how to retain proof/ciphertext availability within native
mass limits; and how every supported funded deposit gets an authenticated credit
or recovery path. The ideal model and real small composition test are different
evidence layers. Complete note/ownership/nullifier/encryption constraints,
permissionless fees, migration and independent recovery remain open.
