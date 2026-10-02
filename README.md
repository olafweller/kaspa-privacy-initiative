# Kaspa Privacy Initiative

> Researching permissionless, optional privacy for native KAS.

**Kaspa Privacy Initiative is an independent, community-led research initiative and is not an official Kaspa Core project.**

**Status:** early public research. No production protocol exists here yet. Do not use experimental code with real funds.

## Start here and help shape the research

The first public milestone is a feasibility and architecture review. Developers, researchers, security reviewers, and people who can identify a broken assumption are welcome. No state architecture, proof system, or production implementation has been accepted.

- Read the [candidate architectures](docs/ARCHITECTURE.md) and [proposed ADR-0001](docs/adr/0001-state-architecture.md).
- Challenge the [security invariants](SECURITY-INVARIANTS.md), [threat model](THREAT-MODEL.md), and [open questions](QUESTIONS.md) with evidence.
- Join the [welcome discussion](https://github.com/olafweller/kaspa-privacy-initiative/discussions/17) for ideas and questions, or use [Issues](https://github.com/olafweller/kaspa-privacy-initiative/issues) for concrete research tasks and corrections.
- Suggest a documentation change through a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for a short walkthrough.

Feedback is most useful when it identifies an assumption, links a specification or exact upstream file/commit, and explains what would validate or falsify the idea. You do not need a finished implementation to contribute.

## The idea

Kaspa is transparent by default. The Kaspa Privacy Initiative (KPI) explores whether native KAS can support a trust-minimized shielded domain where balances, transfer amounts, and ownership relationships are private, while remaining fully backed by native KAS. Permissionless entry, transfers, and exits are research targets, not implemented guarantees.

The long-term user experience could be as simple as:

```text
Public KAS  ->  Shield  ->  Private KAS  ->  Send privately  ->  Unshield  ->  Public KAS
```

The goal is **not** to create another cryptocurrency.

The goal is to make **native KAS optionally private**.

## Core concept

If 10,000 KAS is shielded, the public Kaspa network may see that deposit. Inside the shielded domain, however, later transfers should not require 5,000 public KAS to visibly move when a user privately pays 5,000 KAS.

Instead, native KAS remains locked under protocol rules while cryptographic state changes who can validly claim portions of that backing.

The fundamental accounting invariant is:

```text
total outstanding user liabilities <= native KAS reserved for users
```

Outstanding user liabilities include:

- spendable shielded value;
- valid withdrawal/exit claims that have been created but not yet paid.

Consuming a private note into a withdrawal request must not make the protocol forget that it still owes the user native KAS. That liability remains outstanding until the valid withdrawal/exit claim is paid.

Shielded notes or claims are therefore **not a new token**. They are private cryptographic claims on native KAS held under protocol-enforced conditions.

## What this project is

This repository is for:

- protocol research;
- threat modelling;
- candidate architecture design;
- comparison with existing privacy systems;
- testnet proof-of-concept work;
- open technical discussion;
- security, economic, governance, and legal-operational research.

It is not yet:

- a production privacy system;
- an audited protocol;
- a mainnet pool;
- a financial service;
- a wallet for real funds;
- a promise that any particular architecture will work.

## Why now?

Kaspa's Toccata programmability upgrade is live and provides important primitives including covenants, transaction introspection, zero-knowledge verification, and sequencing support for based applications. Full vProgs remain under active development as a shared-state execution/proving framework.

That creates a useful research question:

> **What is the minimal architecture for shielded native KAS using current Toccata primitives, and which parts actually require a based-app/vProgs architecture?**

We do not want to assume the answer in advance.

## Candidate architecture family

A simplified model looks like this:

```text
                 KASPA L1
                    |
              deposit native KAS
                    |
                    v
            settlement / covenant
                    |
          +---------+---------+
          |                   |
      locked KAS         public commitments
                              |
                              v
                     SHIELDED STATE
                              |
                     private transfers
                              |
                 commitments + nullifiers
                              |
                           ZK proof
                              |
                              v
                     updated state root
                              |
                           unshield
                              |
                              v
                         native KAS
```

The exact architecture is intentionally undecided. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## What must remain true

Regardless of architecture:

- no one may create unbacked shielded KAS;
- no note may be spent twice;
- no administrator may arbitrarily seize or freeze valid user funds;
- loss of a specific prover/operator should not allow theft;
- infrastructure failure should threaten liveness before it threatens fund safety;
- protocol rules should be independently verifiable;
- critical state should be recoverable or reconstructable without trusting one company.

See [SECURITY-INVARIANTS.md](SECURITY-INVARIANTS.md).

## Existing work first

We should not reinvent what already exists.

Before choosing an architecture, this project will map:

- Kaspa's current Toccata capabilities;
- the evolving vProgs runtime;
- existing Kaspa privacy experiments and claims;
- the recent Kaspa Research proposal for an optional privacy layer;
- mature privacy designs such as Zcash Orchard, RAILGUN, Aztec, Monero, and Litecoin MWEB.

See [research/README.md](research/README.md) and [research/existing-kaspa-privacy.md](research/existing-kaspa-privacy.md).

## First milestone

The first milestone is **not** a polished wallet.

It is a reproducible testnet experiment testing whether native KAS can enter a shielded state, change ownership privately, and exit again under the required accounting and authorization rules. Passing those tests would not prove cryptographic correctness or production security.

A second proof-of-concept should deliberately break infrastructure assumptions: for example, remove one prover or state-serving component and verify that another participant can recover or continue without risking user funds.

See [poc/README.md](poc/README.md).

## Project principles

In short:

- native KAS only;
- no new privacy token;
- privacy is optional;
- self-custody;
- no permanent privileged withdrawal authority;
- open specifications and open-source implementations;
- multiple independent implementations are encouraged;
- sustainable development funding is allowed;
- user funds and development treasury funds must remain separate;
- contributors may be paid for work, but there should be no permanent founder rent;
- minimal governance;
- security before growth;
- testnet before mainnet.

See [PRINCIPLES.md](PRINCIPLES.md).

## Current technical context

As of October 2026:

- Toccata is live on Kaspa mainnet.
- Kaspa documents covenants, transaction introspection, ZK verification, and sequencing support for based apps as live capabilities.
- vProgs is an evolving reference runtime for based computation and is still described as early/prototype infrastructure with APIs and architecture subject to change.

The [upstream evidence map](research/kaspa-toccata-vprogs.md) pins the sources reviewed on October 2, 2026 and distinguishes implemented primitives from unvalidated pool behavior. No real-proof TN10 round trip has been demonstrated by this project yet.

Primary sources:

- [Kaspa builder overview](https://kaspa.org/build)
- [Kaspa based-app documentation](https://github.com/kaspanet/docs/blob/main/content/docs/toccata/based-apps.mdx)
- [kaspanet/vprogs](https://github.com/kaspanet/vprogs)
- [Kaspa Research: Optional Privacy Layer for Kaspa](https://research.kas.pa/t/optional-privacy-layer-for-kaspa-similar-to-litecoin-mweb/522)

## Contributing

We especially welcome people who can challenge assumptions rather than merely agree with them.

Useful backgrounds include:

- Kaspa/Toccata engineering;
- zero-knowledge systems;
- privacy protocol design;
- wallet engineering;
- distributed systems;
- security review;
- economic mechanism design;
- legal and operational analysis.

AI-assisted contributions are welcome, but AI-generated security-critical code is not considered reviewed merely because it compiles or passes generated tests.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## Project stewardship

Initiated by **Olaf Weller**.

Current role: **initiator / project steward** — coordinating research, contributors, documentation, and the path toward a technically credible open protocol.

The long-term objective is that the protocol does not depend on Olaf, any founder, any company, or any single implementation.

## Important warning

Privacy protocols are difficult to design safely. A subtle cryptographic, circuit, wallet, state-availability, or exit bug can lead to privacy loss, theft, inflation, or permanently inaccessible funds.

Nothing in this repository should be treated as production-ready until it has passed substantial independent review and audit.

## License

Original repository documentation, tooling, and code are licensed under [Apache-2.0](LICENSE), unless explicitly stated otherwise. Linked upstream projects retain their own licenses. See [LICENSING.md](LICENSING.md).
