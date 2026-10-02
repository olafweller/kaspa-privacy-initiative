# Economics and Sustainable Funding

**Status:** research. No fee model has been selected.

A community-driven protocol still needs sustainable development, audits, infrastructure, documentation, and long-term maintenance.

The objective is not "nobody earns money." The objective is:

> **People can be paid for providing value without creating a permanent owner of user funds or the protocol.**

## Costs the protocol may need to cover

- Kaspa L1 transaction fees;
- proof generation;
- execution/state infrastructure;
- data availability / witness infrastructure;
- wallet development;
- cryptographic engineering;
- independent security audits;
- bug bounties;
- documentation and education;
- project coordination/stewardship;
- legal and operational review;
- long-term maintenance.

## Candidate funding mechanisms

These are options to research, not commitments.

### 1. Shield fee

A small fee when native KAS enters the shielded domain.

Potential benefits:

- simple to account for;
- funding grows with adoption.

Potential problems:

- discourages entry into the anonymity set;
- large deposits may pay disproportionate amounts if percentage-based;
- may create regulatory/operational questions depending on who controls revenue.

### 2. Unshield fee

A small fee when value exits to transparent KAS.

Potential benefits:

- does not reduce the initial incentive to build private balances;
- may encourage longer-lived private activity.

Potential problems:

- users should never feel economically trapped in the shielded domain;
- exit fees must not undermine permissionless withdrawal.

### 3. Per-private-operation fee

Fees for execution/proving of private transactions.

Potential benefits:

- aligns revenue with infrastructure cost;
- may support permissionless provers.

Potential problems:

- fee metadata can affect privacy;
- payment flow must not reveal private value;
- complex fee markets can create centralization pressure.

### 4. Permissionless prover/executor market

Independent providers compete to execute/prove work for users or the protocol.

The protocol should prefer designs where a specific provider is replaceable.

### 5. Development treasury

A transparent treasury funds:

- core development;
- research grants;
- audits;
- bug bounties;
- wallet work;
- documentation;
- project stewardship.

The treasury must be technically and legally distinct from shielded user reserves.

### 6. Grants and donations

Useful for early research and PoC stages before a production fee mechanism exists.

## Founder / steward compensation

The initiator or project steward may be compensated for full-time or part-time work if the community or funding structure considers that work valuable.

The important distinction is:

```text
compensation for work != permanent ownership rent
```

A healthy model could pay a steward a transparent budget or grant while allowing future governance to change that compensation without affecting the protocol or user funds.

## What this project currently rejects

- a new speculative privacy token as the primary funding mechanism;
- a premine or founder allocation of such a token;
- custody of user KAS by a development company;
- a permanent founder right to a fixed share of all protocol activity;
- hidden fee extraction.

## Fee-design questions

Any proposed fee mechanism should be evaluated for:

1. sustainability;
2. user cost;
3. privacy leakage;
4. incentive alignment;
5. spam resistance;
6. centralization risk;
7. governance capture;
8. impact on anonymity-set growth;
9. whether users can self-prove/self-host without paying a service provider;
10. legal/operational implications.

## PoC policy

The first technical PoCs should avoid embedding a permanent economic model.

Prove safety and privacy mechanics first. Economics can then be tested against a concrete architecture rather than imagined in the abstract.
