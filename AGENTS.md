# AGENTS.md

Instructions for Codex and other AI agents working in this repository.

## Mission

Help the Kaspa Privacy Initiative determine whether native KAS can support a trust-minimized, optional shielded domain with strong privacy and permissionless exits.

The current goal is **research and testnet validation**, not mainnet launch.

## Non-negotiable constraints

1. Do not create or propose a new privacy token unless explicitly asked to research that alternative.
2. Treat native KAS backing as the core asset model.
3. Do not deploy experimental privacy code to mainnet.
4. Do not use real funds in PoCs.
5. Do not add privileged admin withdrawal paths as a convenience.
6. Do not invent new cryptographic primitives when established designs can be studied or reused.
7. Do not describe unreviewed code as secure.
8. Do not treat passing tests as proof of cryptographic correctness.
9. Preserve the invariants in `SECURITY-INVARIANTS.md`.
10. Important architecture changes require an ADR.

## Current research posture

Do not assume that vProgs is required.

Do not assume that vProgs is unnecessary.

The primary architectural question is:

> What is the minimal architecture for shielded native KAS using current Toccata primitives, and which parts actually require a based-app/vProgs architecture?

Toccata primitives are live. vProgs is an evolving reference runtime and remains early/prototype infrastructure. Verify current upstream state before making implementation assumptions.

## Research-first workflow

Before writing a new subsystem:

1. inspect current Kaspa docs and upstream repositories;
2. inspect existing Kaspa privacy experiments;
3. inspect mature privacy protocols for analogous components;
4. state the problem and security assumptions;
5. compare candidate solutions;
6. create/update an RFC for open design questions and record resolved decisions in an ADR;
7. only then prototype.

## Source quality

Prefer in this order:

1. protocol specifications;
2. official upstream repositories;
3. official technical documentation;
4. peer-reviewed papers / formal research;
5. maintainer statements;
6. community discussion.

Do not turn an unverified social-media claim into a repository fact.

## Existing-work rule

Before implementing notes, nullifiers, private state, proving, exits, or wallet scanning, inspect:

- Kaspa Toccata docs;
- `kaspanet/vprogs`;
- `kaspanet/research`;
- Zcash Orchard;
- Aztec;
- RAILGUN;
- Monero;
- Litecoin MWEB.

Document what is reused, adapted, or rejected.

## Security-critical coding

For code touching value conservation, proof verification, nullifiers, withdrawals, commitments, Merkle/state roots, or key derivation:

- use explicit integer/range semantics;
- test boundary values;
- test malformed inputs;
- test replay/double-spend behavior;
- test stale/wrong-root proofs;
- test cross-state/cross-lane replay;
- add property tests where practical;
- keep unsafe assumptions visible in comments and docs;
- never weaken a check just to make a demo pass.

## Safety vs liveness

Prefer a design that safely halts over a design that continues while accepting unverifiable state.

A missing prover, server, or executor may reduce liveness. It must not enable theft or inflation.

## AI self-review

For every significant implementation task, perform a second-pass review from an adversarial perspective:

- How could this mint value?
- How could this spend twice?
- How could this release reserve KAS incorrectly?
- How could this leak sender/receiver/amount?
- What happens if a dependency disappears?
- What happens on reorg or stale state?
- What hidden trust assumption was introduced?

## Documentation discipline

When architecture changes:

- update `docs/ARCHITECTURE.md`;
- update affected open questions;
- update the threat model if necessary;
- update the relevant RFC and record decisions in an ADR;
- note newly introduced trust assumptions.

## Current agent priorities

1. Work from the public GitHub issues and the current RFCs/ADRs rather than recreating bootstrap work.
2. Keep Kaspa/Toccata/vProgs research evidence current, source-grounded, and pinned to exact upstream files/commits where practical.
3. Prioritize the open architecture and feasibility work in P01-P03 before substantial cryptographic implementation.
4. Preserve the invariants in `SECURITY-INVARIANTS.md`. Do not weaken or reinterpret an invariant silently; any proposed change must be explicit and reviewed.
5. Keep facts, interpretations, hypotheses, and unverified claims clearly separated.
6. Before implementing notes, nullifiers, proving, exits, wallet scanning, or private state, inspect the relevant mature protocol designs and current Kaspa work first.
7. Use test KAS only for experiments. Do not deploy experimental protocol code to mainnet or use real funds.
8. Treat passing tests as evidence about the tested implementation, not as proof of cryptographic correctness or production safety.
9. For every significant implementation, perform an adversarial second-pass review covering inflation, double spending, unauthorized exits, stale/replayed state, privacy leakage, dependency failure, and hidden trust assumptions.
10. Keep documentation, RFCs/ADRs, threat model, and security assumptions synchronized with implementation changes.

## Definition of a useful first PoC

A first PoC is useful if it falsifiably demonstrates:

```text
test KAS deposit
-> private claim
-> private value-conserving transfer
-> double-spend prevention
-> authorized exit
-> native test KAS withdrawal
```

It does not need a polished wallet, token, DEX, governance system, or mainnet deployment.
