# Codex: Start Here

This repository is intentionally documentation-heavy before code-heavy.

The first job is to **reduce uncertainty**, not to generate a large codebase.

## First session

1. Read:
   - `README.md`
   - `PRINCIPLES.md`
   - `SECURITY-INVARIANTS.md`
   - `AGENTS.md`
   - `docs/ARCHITECTURE.md`
   - `docs/INITIAL-ISSUES.md`

2. Check current upstream Kaspa sources listed in:
   - `research/kaspa-toccata-vprogs.md`
   - `research/existing-kaspa-privacy.md`

3. Produce a short findings note answering:

   - Which Toccata primitives are live and callable today?
   - Which vProgs interfaces are currently usable versus unstable?
   - Is a shielded-pool implementation already public in a Kaspa repository?
   - What is the smallest realistic TN10 PoC architecture?

4. Draft `docs/adr/0001-state-architecture.md` from the ADR template.

5. Do not write production cryptographic code yet.

## When GitHub access is available

Convert the proposed work in `docs/INITIAL-ISSUES.md` into GitHub issues and add labels such as:

- `research`
- `architecture`
- `security`
- `privacy`
- `kaspa`
- `zk`
- `poc`
- `economics`
- `wallet`
- `legal-question`

## First coding target

Only after the existing-work review and ADR-0001:

Build the smallest testnet experiment that can demonstrate fund conservation, private state transition, double-spend prevention, and permissionless withdrawal using test KAS.
