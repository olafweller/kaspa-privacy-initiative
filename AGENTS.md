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
6. create/update an ADR;
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
- create/update the ADR;
- note newly introduced trust assumptions.

## Initial Codex bootstrap tasks

When this repository is first opened in Codex, do the following before major coding:

1. Validate the repository tree and Markdown links.
2. Create a concise `git status` baseline.
3. Review the primary Kaspa sources linked in `research/kaspa-toccata-vprogs.md`.
4. Map public Kaspa repositories for any shielded-pool, note, nullifier, ZK, or exit implementation and record exact files/branches/commits if found.
5. Turn `docs/INITIAL-ISSUES.md` into GitHub issues when GitHub access is available.
6. Draft ADR-0001 comparing the three candidate state architectures in `docs/ARCHITECTURE.md`.
7. Do **not** begin production cryptography until the existing-work map and ADR-0001 are reviewed.

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
