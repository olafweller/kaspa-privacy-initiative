# Contributing

Kaspa Privacy Initiative is currently a research project. At this stage, finding a broken assumption may be more valuable than adding code.

## A simple way to participate

1. Read [README.md](README.md), the [architecture comparison](docs/adr/0001-state-architecture.md), and the [security invariants](SECURITY-INVARIANTS.md).
2. Browse [open issues](https://github.com/olafweller/kaspa-privacy-initiative/issues). Start with `priority-high` research, or `good first issue` for smaller documentation work.
3. Comment on a relevant issue with sources, objections, or an approach. Use [Discussions](https://github.com/olafweller/kaspa-privacy-initiative/discussions) if you are unsure where an idea belongs.
4. For a change, fork this repository, create a branch in your fork, edit the files, and open a pull request against `main`. Small documentation changes can be made with GitHub's browser editor.
5. Explain your reasoning and any security/privacy impact. Run `python3 scripts/check_docs.py` when working locally; the same check runs on pull requests.

You do not need permission to ask a question or submit a proposal. Comment before starting substantial implementation work so assumptions and overlapping work are visible. A pull request proposes a change; it does not automatically change the accepted protocol.

Keep `.env`, credentials, private keys, personal wallet material, and local test data out of issues, commits, and pull requests. Use the private reporting channel in [SECURITY.md](SECURITY.md) for sensitive vulnerabilities.

## Current research priorities

- Verify the exact current Kaspa verifier, covenant, sequencing, and resource-budget constraints.
- Review A/B/C and their permissionless exit/recovery assumptions.
- Map existing components and their reuse, licensing, and trust assumptions.
- Define deposit/transfer/pending-exit/payout accounting and nullifier replay rules.
- Identify practical privacy leakage and confidential-proving requirements.

Production cryptography is not the next contribution target. The existing-work map and architecture proposal need review before substantial implementation.

## Valuable contributions

We welcome:

- Kaspa/Toccata architecture review;
- ZK and cryptographic review;
- privacy-system research;
- attack analysis;
- state/recovery analysis;
- PoC code;
- wallet research;
- economic analysis;
- benchmarks;
- documentation improvements;
- legal-operational questions;
- reproducible experiments.

## Before implementing a major idea

1. Search the repository for related work.
2. Check [research/existing-kaspa-privacy.md](research/existing-kaspa-privacy.md).
3. Open or reference an issue.
4. For architecture changes, create an ADR proposal.
5. State assumptions explicitly.
6. Prefer established cryptographic primitives over new constructions.

## Evidence hierarchy

Technical arguments should ideally be supported by one or more of:

- protocol specifications;
- primary-source documentation;
- code references;
- tests;
- benchmarks;
- reproducible PoCs;
- formal reasoning;
- independent security analysis.

## AI-assisted contributions

AI tools and agents are welcome for research, coding, testing, documentation, and review.

Contributors remain responsible for the content they submit.

For security-critical code:

- generated code must be understood by a human reviewer;
- generated tests are not proof of security;
- cryptographic constructions must not be invented casually;
- uncertain claims must be marked as uncertain;
- source links should prefer primary documentation.

See [AGENTS.md](AGENTS.md).

## Pull requests

A useful PR should explain:

- what problem it addresses;
- what assumptions it makes;
- what changed;
- how it was tested;
- whether it affects a security invariant;
- whether an ADR is required.

## Experimental-code warning

Do not encourage the use of experimental code with real funds.

Mainnet deployment is not an acceptable shortcut for testing.

## Security reports

Do not publish exploit details for code that might affect deployed funds. See [SECURITY.md](SECURITY.md).

## Contributor identity

Contributors may participate under real names or pseudonyms. Technical contributions are evaluated on their substance.

## Contribution terms

Original contributions intended for inclusion use [Apache-2.0](LICENSE), unless explicitly agreed otherwise before inclusion. Identify third-party sources and required notices. Be respectful of other contributors; critique assumptions and evidence rather than people.
