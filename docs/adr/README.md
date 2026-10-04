# Architecture Decision Records

Architecture Decision Records (ADRs) record actual architecture/design decisions, their rationale, and their outcomes so the project does not depend on memory, personality, or social authority. Use [RFCs](../rfc/README.md) for open proposals, alternatives, evidence gathering, and unresolved design questions.

The RFC/ADR separation was introduced after the initial repository structure. Some early experimental records may not perfectly follow the newer convention. ADR-0002 and ADR-0003 retain their existing names, statuses, and experimental scope for now.

## File naming

```text
NNNN-short-title.md
```

## Status values

- Accepted
- Superseded
- Rejected

Early experimental records retain their existing status terminology under the transition note above.

## Rules

An ADR should:

- state the problem;
- list constraints;
- compare credible alternatives;
- identify security/privacy implications;
- cite evidence;
- record objections;
- explain why the decision was made;
- record its outcome and link to the originating RFC, when applicable;
- state what evidence would cause reconsideration.

Use [0000-template.md](0000-template.md).

## Records

- [ADR-0002: A0 terminal reserve-release experiment](0002-a0-reserve-release-experiment.md)
- [ADR-0003: A1 finite successor reserve and independent terminal exit](0003-a1-successor-reserve.md)

The open state architecture comparison is [RFC-0001](../rfc/0001-state-architecture.md).
