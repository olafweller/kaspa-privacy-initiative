# Project Principles

These principles describe the intended direction of the Kaspa Privacy Initiative before the final protocol architecture is known.

## 1. Native KAS

The privacy system should use native KAS as the underlying economic asset.

We do not intend to create a separate privacy token.

## 2. Optional privacy

Kaspa may remain transparent by default. Users should voluntarily choose whether to hold and transact in a shielded domain.

## 3. Self-custody

Users must control their own keys and funds.

No company, foundation, server operator, maintainer, or project steward should custody user assets as a requirement of the protocol.

## 4. No privileged withdrawal authority

There should be no permanent administrator capable of:

- taking shielded user funds;
- freezing a valid user balance;
- approving or denying otherwise-valid withdrawals;
- creating unbacked claims.

Valid protocol rules and proofs should determine validity.

## 5. No permanent admin keys

Temporary testnet controls may manage development infrastructure, but must not bypass reserve accounting, proof verification, authorization, or withdrawal conditions. They must not create privileged access to user reserves.

A deliberately weaker mock must be identified as a separate simulation. It cannot claim to satisfy the security invariants or demonstrate permissionless exits.

A production design should not depend on a permanent founder or operator key.

## 6. Open protocol

The protocol specification should be public.

Anyone should be able to study it, implement it, audit it, build a wallet, and run compatible infrastructure.

## 7. Multiple implementations

The protocol should ultimately be larger than a single repository or team.

Independent implementations are a feature, not a threat.

## 8. No founder ownership of the protocol

Initiating the project does not create permanent control over protocol rules or user funds.

Reputation may influence discussion; it must not create cryptographic authority.

## 9. Sustainable development is legitimate

Open, community-driven, and decentralized do not mean unpaid.

Developers, researchers, auditors, maintainers, coordinators, and project stewards may be compensated for valuable work.

## 10. No permanent founder rent

Compensation should be tied to work, responsibilities, grants, milestones, or transparent governance — not to an irrevocable lifetime claim on protocol activity merely for being an early founder.

## 11. User funds and development funds are separate

A development treasury must never be confused with or gain discretionary control over shielded user reserves.

The backing pool exists for users. Development funding exists for development.

## 12. Minimize governance

Where possible:

```text
protocol rules > governance decisions
```

Governance should coordinate evolution, not authorize individual transactions or control private balances.

## 13. Privacy by cryptography

Privacy should not depend primarily on promises, log deletion, trusted databases, or honest centralized servers.

## 14. Assume powerful observers

The threat model should consider adversaries able to analyze:

- the public Kaspa ledger;
- deposit and withdrawal amounts;
- transaction timing;
- network metadata;
- wallet behavior;
- exchange/KYC information;
- long time horizons.

## 15. Wallet privacy matters

Perfect circuit privacy can be undermined by a poor wallet.

The user experience must help users avoid obvious correlation and metadata mistakes.

## 16. Safety before liveness

When trade-offs are unavoidable, infrastructure failure should stop or delay progress before it enables theft, inflation, or unauthorized spending.

## 17. Security before growth

A large anonymity set on top of broken cryptography is not success.

Independent review and audit take priority over adoption targets.

## 18. Testnet before mainnet

Experimental implementations remain on test networks until the architecture and critical code have received serious independent review.

## 19. Public technical decisions

Important architecture decisions should be documented publicly, preferably through Architecture Decision Records (ADRs).

## 20. Arguments over authority

Technical decisions should be supported by reasoning, specifications, tests, benchmarks, proofs, and security analysis — not follower counts, KAS holdings, titles, or seniority.

## 21. AI is a tool, not a security authority

AI agents may research, prototype, test, review, and accelerate development.

AI output does not replace independent expert review of production cryptography and custody-critical logic.

## 22. No unnecessary reinvention

Before designing new primitives, study and reuse well-understood audited ideas where they fit.

New cryptography requires a very high justification bar.

## 23. Protocol over personalities

No individual should become technically necessary for the continued operation of the system.

The project succeeds when it can continue without its original contributors.

## 24. Financial privacy is the product

The core goal is useful, robust, permissionless privacy for native KAS — not speculation around a new asset.
