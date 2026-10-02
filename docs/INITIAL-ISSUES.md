# Initial Research Backlog

The P01–P15 identifiers below are proposal IDs, independent of GitHub issue numbering. The [live issue tracker](https://github.com/olafweller/kaspa-privacy-initiative/issues) holds current discussion and progress. Draft research notes do not close a task whose experimental acceptance criteria remain unmet.

## Published tasks

| Proposal | GitHub issue |
| --- | --- |
| P01 | [#1: Map current Kaspa primitives for a shielded KAS PoC](https://github.com/olafweller/kaspa-privacy-initiative/issues/1) |
| P02 | [#2: Locate and review existing Kaspa shielded-pool implementations](https://github.com/olafweller/kaspa-privacy-initiative/issues/2) |
| P03 | [#3: Review ADR-0001 and choose a state architecture for the first PoC](https://github.com/olafweller/kaspa-privacy-initiative/issues/3) |
| P04 | [#4: Define the minimal note model](https://github.com/olafweller/kaspa-privacy-initiative/issues/4) |
| P05 | [#5: Define nullifier requirements](https://github.com/olafweller/kaspa-privacy-initiative/issues/5) |
| P06 | [#6: Define value-conservation proof statement](https://github.com/olafweller/kaspa-privacy-initiative/issues/6) |
| P07 | [#7: Define shield/deposit mechanism](https://github.com/olafweller/kaspa-privacy-initiative/issues/7) |
| P08 | [#8: Define permissionless exit/unshield mechanism](https://github.com/olafweller/kaspa-privacy-initiative/issues/8) |
| P09 | [#9: Prover failure experiment design](https://github.com/olafweller/kaspa-privacy-initiative/issues/9) |
| P10 | [#10: State availability and recovery specification](https://github.com/olafweller/kaspa-privacy-initiative/issues/10) |
| P11 | [#11: Compare proof systems available to the first PoC](https://github.com/olafweller/kaspa-privacy-initiative/issues/11) |
| P12 | [#12: Wallet note-discovery research](https://github.com/olafweller/kaspa-privacy-initiative/issues/12) |
| P13 | [#13: Practical privacy leakage analysis](https://github.com/olafweller/kaspa-privacy-initiative/issues/13) |
| P14 | [#14: Sustainable funding options](https://github.com/olafweller/kaspa-privacy-initiative/issues/14) |
| P15 | [#15: Legal/operational review questions before mainnet](https://github.com/olafweller/kaspa-privacy-initiative/issues/15) |

New to the project? Try [the documentation review task](https://github.com/olafweller/kaspa-privacy-initiative/issues/16).

## P01 — Map current Kaspa primitives for a shielded KAS PoC

**Labels:** `research`, `architecture`, `kaspa`, `priority-high`

**Question:** What can be built today with live Toccata primitives, and what genuinely requires based-app/vProgs infrastructure?

**Acceptance criteria:**

- link exact upstream code/docs;
- list usable primitives;
- list unstable/missing components;
- propose the smallest realistic TN10 architecture.
- distinguish source inspection from real-proof TN10 validation and pin a compatible dependency/toolchain set.

---

## P02 — Locate and review existing Kaspa shielded-pool implementations

**Labels:** `research`, `privacy`, `kaspa`, `priority-high`

Map public Kaspa privacy implementations/branches/commits.

**Acceptance criteria:**

- exact repository paths/commits;
- what is implemented;
- what is demo-only;
- trust assumptions;
- privacy properties;
- exit mechanism;
- reusable components.

---

## P03 — Review ADR-0001 and choose a state architecture for the first PoC

**Labels:** `architecture`, `adr`, `priority-high`

Compare:

1. one-state-UTXO covenant pool;
2. sharded/native covenant state;
3. based-app/vProgs shared state.

Evaluate against security invariants and current Kaspa capability.

The [draft ADR](adr/0001-state-architecture.md) is Proposed. Review its objections, real-proof budgets, reserve/output bindings, and independent recovery/exit gates before recording acceptance. Do not infer acceptance from publication or the recommended investigation order.

---

## P04 — Define the minimal note model

**Labels:** `privacy`, `zk`, `architecture`

Describe the minimum private data needed for value, ownership, randomness, recipient delivery, and safe nullification.

Do not invent cryptography before reviewing Orchard/Aztec/RAILGUN patterns.

---

## P05 — Define nullifier requirements

**Labels:** `security`, `privacy`, `zk`

Specify desired properties:

- deterministic for the rightful spender;
- unique per spendable resource;
- not linkable to the originating public commitment by outsiders;
- duplicate rejection;
- bound to the correct protocol/domain.
- specify authenticated spent-state updates, duplicate rejection within and across batches/shards, and any historical note-anchor policy.

---

## P06 — Define value-conservation proof statement

**Labels:** `security`, `zk`, `poc`, `priority-high`

Write the exact statement the first PoC proof must enforce, including ranges, fees, and state binding.

**Acceptance criteria:**

- explicit integer/range equations for deposits, private transfers, withdrawal requests, pending exits, completed payouts, and allowed fees;
- unpaid exits remain user liabilities after note consumption;
- separate reserve rent and externally sponsored fees from spendable backing;
- bind actual reserve continuation and payout amount/destination, not only private commitments;
- cover duplicate deposits, partial exits, replay, overflow, and underpaid/diverted payouts;
- preserve I-1, I-2, I-7, and I-12 without changing the invariants.

---

## P07 — Define shield/deposit mechanism

**Labels:** `architecture`, `kaspa`, `poc`

Describe how native test KAS becomes backing for a private claim and how the public commitment is created.

---

## P08 — Define permissionless exit/unshield mechanism

**Labels:** `architecture`, `security`, `kaspa`, `priority-high`

Answer whether a valid user can exit without cooperation from a designated operator.

Specify pending-exit accounting, exact payout bindings, witness availability, and any escape path. Every path must enforce authorization, conservation, and single spend; an admin key is not a recovery mechanism.

---

## P09 — Prover failure experiment design

**Labels:** `security`, `liveness`, `poc`

Design a test where the default prover disappears and an independent environment reconstructs enough state to continue or exit safely.

---

## P10 — State availability and recovery specification

**Labels:** `architecture`, `security`

Define what must be public, replicated, reconstructable, or user-backed-up.

Cover commitments, nullifiers, encrypted delivery, witnesses, retained L1 history, pruning/archives, backups, and deterministic reorg recovery. Demonstrate a clean independent rebuild and a valid exit; a root or a safe halt alone does not meet I-10.

---

## P11 — Compare proof systems available to the first PoC

**Labels:** `zk`, `research`

Compare at least current Kaspa/vProgs RISC Zero/Groth16 paths and any viable specialized-circuit alternative.

Avoid selecting a proof system without benchmarks and verifier constraints.

Distinguish real proofs from development-mode receipts/redeems. Document setup assumptions, key/image pinning, and whether local or outsourced proving exposes private witness data.

---

## P12 — Wallet note-discovery research

**Labels:** `wallet`, `privacy`, `research`

Review encrypted note delivery and private scanning approaches from Orchard/Aztec/RAILGUN.

---

## P13 — Practical privacy leakage analysis

**Labels:** `privacy`, `security`

Model timing, amount, RPC, network, and wallet-correlation risks around shield/unshield activity.

Include outsourced prover/executor access to private witnesses and public lane payload/resource-access patterns. Separate cryptographic confidentiality from measured anonymity.

---

## P14 — Sustainable funding options

**Labels:** `economics`, `research`

Compare shield fees, unshield fees, private-operation fees, prover markets, grants, and treasury models.

Keep user reserve funds isolated from development funding.

---

## P15 — Legal/operational review questions before mainnet

**Labels:** `legal-question`, `operations`

Produce a question set for specialist counsel covering software publication, custody/control, hosted frontends, hosted proving, fee collection, and treasury operations.

Do not treat the issue discussion as legal advice.
