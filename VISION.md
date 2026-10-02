# Vision

Kaspa provides fast, permissionless digital value transfer. Its transparent ledger also means that financial activity can remain publicly observable indefinitely.

The Kaspa Privacy Initiative asks a simple question:

> **Can native KAS gain strong optional privacy without requiring a new cryptocurrency, a trusted custodian, or a separate company-controlled network?**

## The desired experience

A future wallet could make the choice understandable to ordinary users:

```text
Public balance:   4,250 KAS
Private balance: 12,700 KAS

[ Shield ]
[ Send privately ]
[ Receive privately ]
[ Unshield ]
```

Users should not need to understand Merkle trees, commitments, nullifiers, witnesses, or ZK proof systems in order to use financial privacy safely.

## Optional, not mandatory

Kaspa does not need to become private by default for this vision to work.

The target is a voluntary privacy domain where users can choose to move KAS into stronger confidentiality, remain there for extended periods, transact privately, and later return to transparent KAS if they wish.

The privacy domain should become more useful as more people use it. A healthy system is not merely a one-shot mixer. It is a place where users can hold, receive, and transfer KAS privately over time.

## Native KAS, not a new coin

The shielded system should not create a speculative privacy asset.

A shielded claim should represent an enforceable private claim on native KAS locked under protocol rules.

The project therefore starts with a hard design preference:

> **No new token is required to obtain privacy for KAS.**

## Protocol over organization

The initiative may need maintainers, grants, auditors, infrastructure, funding, and coordination. Those are organizational needs, not reasons to make an organization technically necessary.

The protocol should aspire to survive:

- the disappearance of its original contributors;
- the failure of a particular website or wallet;
- the loss of a specific prover/operator;
- disagreement among maintainers;
- the emergence of alternative compatible implementations.

## Success criteria

The initiative succeeds if it can produce a design where:

1. native KAS can enter and exit under trust-minimized rules;
2. internal ownership and amounts can remain private;
3. double-spending and unauthorized withdrawal are cryptographically prevented;
4. no privileged party can seize valid user funds;
5. the system remains recoverable from public/reconstructable data and user-held secrets;
6. multiple independent implementations can follow the same specification;
7. development is economically sustainable without creating permanent founder control;
8. privacy claims are tested against realistic metadata and wallet-level attacks, not only cryptographic theory.

## A community standard, not a personality project

The initiator can coordinate, write, build, fundraise, and be compensated for useful work. But technical authority should come from specifications, proofs, reproducible experiments, code review, and security analysis — not from identity or social status.

The end state should be bigger than any individual.
