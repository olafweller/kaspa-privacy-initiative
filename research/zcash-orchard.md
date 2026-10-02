# Zcash Orchard — Research Notes

## Why study it

Orchard is a mature shielded-payment design with private notes, note commitments, nullifiers, viewing/spending key structure, note encryption, and Halo 2-based proofs.

We should study it for proven design patterns, not copy it mechanically into Kaspa.

## Relevant concepts

### Notes

Private value is represented as notes rather than public account balances.

### Commitments

Public commitments bind hidden note contents.

### Nullifiers

Orchard's nullifier design aims to prevent double spends while maintaining spend unlinkability. Its design documentation explicitly analyzes balance security, note privacy, spend unlinkability, and related attack properties.

### Key separation

Orchard separates responsibilities across key material for spending, viewing, and note encryption. This is useful when designing wallet scanning and optional viewing capabilities.

### Halo 2

Orchard uses Halo 2-oriented circuit design. That does not imply Kaspa should use Halo 2; verifier support, proving cost, aggregation, and upstream tooling matter.

## Lessons for KPI

- nullifier design is not a trivial `hash(note)` exercise;
- recipient spendability and malicious-sender edge cases matter;
- note encryption/discovery belongs in the protocol/wallet design;
- viewing-key semantics should be intentional;
- security properties should be written down before implementation.

## Questions before reuse

- Which Orchard data fields are essential for a pure KAS-value note?
- Which assumptions depend on Zcash consensus rather than the shielded protocol itself?
- Which parts would map cleanly to Kaspa's proof-verification environment?
- Can we reuse audited libraries or design ideas without creating incompatible proof costs?

## Primary sources

- https://zcash.github.io/orchard/
- https://zcash.github.io/orchard/design/nullifiers.html
- https://zcash.github.io/orchard/design/keys.html
- https://zcash.github.io/halo2/
