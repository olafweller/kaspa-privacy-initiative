# Roadmap

This roadmap is intentionally research-first. Phases are research gates, not delivery promises. No state architecture or scaling path has been accepted.

## Phase 0 — Public foundation

**Goal:** create a credible open research home.

Deliverables:

- repository structure;
- principles;
- threat model;
- security invariants;
- candidate architecture document;
- existing-work inventory;
- contributor/AI workflow;
- initial GitHub issues.

Exit condition: a technically literate contributor can understand the idea, the unknowns, and the safety bar without speaking to the initiator.

## Phase 1 — Existing-work and feasibility map

**Goal:** learn what Kaspa can already do and what has already been built.

Tasks:

- map Toccata live primitives;
- inspect current vProgs state;
- locate and inspect public Kaspa shielded-pool work;
- review the Kaspa Research privacy proposal;
- compare Orchard, Aztec, RAILGUN, Monero, and MWEB patterns;
- collect Kaspa core/community developer feedback.

Exit condition: ADR-0001 can compare candidate architectures with concrete upstream references rather than assumptions.

## Phase 2 — Architecture decision + executable model

**Goal:** choose the smallest architecture worth testing.

Deliverables:

- ADR-0001 state architecture;
- draft note/commitment/nullifier model;
- state-machine model or simulator;
- executable value-conservation tests;
- explicit trust assumptions.

Exit condition: the design can be attacked on paper and in tests before substantial testnet code exists.

## Phase 3 — PoC A: fund-safety path

**Goal:** demonstrate the basic private-value lifecycle using test KAS under a documented model.

Target flow:

```text
deposit
-> private claim
-> private value-conserving transfer
-> nullifier/double-spend protection
-> authorized exit
-> test KAS withdrawal
```

Required tests:

- unauthorized withdrawal fails;
- duplicate spend fails;
- wrong state root fails;
- malformed proof fails;
- value inflation fails;
- stale/replayed proof fails.

Exit condition: documented tests demonstrate the required properties in a reproducible testnet experiment using real proofs. Passing tests does not establish cryptographic correctness or production security.

## Phase 4 — PoC B: failure and decentralization

**Goal:** test recovery and exits after loss of the default operator.

Experiments:

- stop the normal prover;
- replace the prover;
- rebuild required state on a clean machine;
- recover a wallet from documented backup material;
- test censorship/liveness behavior;
- test state/witness corruption handling.

Exit condition: failure assumptions are measured instead of merely claimed.

## Phase 5 — Privacy analysis

**Goal:** move beyond "the circuit hides the amount."

Study:

- deposit/withdrawal correlation;
- timing leakage;
- amount uniqueness;
- note discovery;
- RPC leakage;
- transaction broadcast;
- wallet fingerprints;
- anonymity-set metrics.

Exit condition: privacy claims are explicit and evidence-based.

## Phase 6 — Developer and wallet prototype

**Goal:** make the protocol usable without exposing users to cryptographic details.

Potential UX:

```text
Public balance
Private balance
Shield
Private send
Private receive
Unshield
Privacy warnings
```

Exit condition: a testnet user can use the system safely without manually constructing proofs.

## Phase 7 — Economics, audit, legal-operational design

**Goal:** determine what a sustainable production project would require.

Tasks:

- benchmark real operating costs;
- evaluate fee/funding models;
- design treasury isolation;
- commission independent cryptographic/security review;
- obtain specialist legal advice for intended operational roles;
- establish private vulnerability reporting;
- design bug bounty and incident response.

Exit condition: no unresolved critical security or operational questions are being hidden behind "decentralized" marketing language.

## Phase 8 — Mainnet candidate

Only consider mainnet after:

- stable specification;
- mature testnet history;
- independent audit(s);
- reproducible builds/test vectors;
- clear exit/recovery model;
- clear operational/legal model;
- documented upgrade process;
- community review.

A mainnet launch is not a roadmap requirement. If research finds that the architecture is unsafe or unsuitable, the correct outcome may be to stop or redesign.
