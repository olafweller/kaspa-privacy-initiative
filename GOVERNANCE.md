# Governance

**Status:** early-stage coordination model. There is no DAO and no governance token.

## Current model

The Kaspa Privacy Initiative is currently coordinated by a project steward, with technical work conducted publicly through issues, pull requests, research notes, and Architecture Decision Records (ADRs).

The steward's role is to:

- keep the research organized;
- make unanswered questions visible;
- connect contributors;
- prevent scope drift;
- ensure important objections are documented;
- move work toward falsifiable experiments.

The steward does **not** gain cryptographic authority over user funds by holding this role.

## Technical decisions

Important architecture choices should use ADRs.

A strong decision should include:

1. the problem;
2. constraints;
3. candidate options;
4. security implications;
5. privacy implications;
6. operational implications;
7. evidence or prototypes;
8. objections;
9. the selected direction;
10. conditions that would justify revisiting it.

## Rough consensus, not popularity

The project should value technically substantiated objections even when they come from a minority.

Follower count, title, KAS holdings, donor status, or early-project status do not make an argument correct.

## Security-critical changes

Changes affecting reserve safety, authorization, proof verification, exits, or core cryptographic assumptions require a higher bar than ordinary documentation or UX changes.

The long-term process should require independent review and test vectors before such changes are recommended for production.

## No governance over individual funds

A future governance mechanism should coordinate software/protocol evolution and funding. It should not decide whether a specific valid user may transact or withdraw.

## No governance-token assumption

The initiative does not assume that token voting is necessary or desirable.

A future funding treasury may require governance, but that is separate from the protocol's user reserve.

## Forkability

Open specifications and multiple implementations should make disagreement survivable.

Where technically possible, users and developers should not be trapped by a single organization's software distribution or website.
