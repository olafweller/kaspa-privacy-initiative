# Reuse review — 2026-10-19

Rechecked the ten monitored heads in [source-refresh](evidence/source-refresh.json).
Kaspa/vProgs/research, Orchard, RAILGUN, Monero and MWEB match the PR55 review.
Aztec advanced to 660f5f5; the previously reviewed note-interface path returns
404 at that head. Retain the previously pinned source/review for its distinction
between constrained authorization/nullification and wallet helpers. No claim
about that moved interface at the new head is made; no Aztec code is imported.

Revisited retained primary Toccata based-app documentation, native permission
and delegate balance source at f9b84a8, Orchard nullifiers/encrypted discovery,
RAILGUN note decoding, Monero authorization/conservation and MWEB scan-data
requirements. Retain the source/reuse conclusions of [PR55](../user-recovery/SOURCES.md).
The exact-reserve branch is native permission policy, not a new cryptographic
construction. Reuse upstream's terminal rent refund and zero delegate-change
branch unchanged. No restricted circuit code, pairing or encryption is copied.

The relation is a separate derivative of PR49's reviewed common relation, so old
source hashes, guest identity, receipts and actual TN10 evidence remain intact.
Changes are limited to versioned state/journal domains, exact-reserve admission,
matching native policy, payout shape and reserve removal. The detailed enforcing
boundaries and alternatives are in [ADR-0017](../../docs/adr/0017-integrated-recovery-native-guest.md).

The follow-up review correction changes only native fixture funding outpoints
and adds whole-history input-uniqueness qualification. It reuses the existing
canonical v1 parser and hash helper; it adds no wallet, cryptographic, native
policy or guest subsystem. The source/reuse decisions above remain unchanged.
