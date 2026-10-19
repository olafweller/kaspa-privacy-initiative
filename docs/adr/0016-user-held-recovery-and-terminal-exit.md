# ADR-0016: user-held recovery and a terminal reserve exit experiment

Status: Local implementation for review, 2026-10-19. No rental, outer proving,
funding, broadcast, migration or production policy is authorized by this package.

## Question and decision

PR54 completed the actual TN10 lifecycle under trusted operator custody. Prepare
user-side commands runnable on a separately administered machine, deterministic
public-history replay, and the missing exact-reserve/full-exit native path.
Keep every historical program, image, script, receipt and evidence byte intact.

Reuse the existing wallet circuit, setup parameters, VK, encrypted deliveries,
nullifiers and native permission/delegate verifier. No new cryptography or admin
key is introduced. Independently supplied accepted state roots authenticate a
snapshot/replayed result; a snapshot's own root or a server's claim is insufficient.
A trusted current chain checkpoint, complete data and available replacement
execution/proving/fee services remain necessary. Offline replay does not select
Kaspa's canonical chain or establish checkpoint freshness.

The terminal experiment admits one authorized exit exactly matching one selected
reserve. It uses three inputs (permission, that reserve, sponsor) and **two**
outputs (recipient including permission-rent refund, sponsor change). No zero-valued
reserve output is created. The existing upstream permission verifier already
handles zero expected delegate change. A thin native prefix fixes lane, shape,
reserve outpoint/SPK/amount, terminal consumption, unbound sponsor input, and absence
of covenant/delegate outputs. Sponsor top-ups remain valid; only authorized
principal is discharged. State rent stays in its separate covenant.

This policy is additive, in a host-only local relation with a separate tagged
commitment. It is NOT installed into the old guest or old live permissions. Its
permission-issuance tests use explicit synthetic covenant-bound UTXOs, not a new
outer receipt. A future guest integration must commit this policy under a new
program identity, qualify issuance with genuine proofs and use a fresh instance;
the old live reserve is not silently upgraded. Concurrent exits and combining
reserves remain outside this step.

## Alternatives

A zero-value delegate output adds a UTXO without backing and relies on transaction
policy unnecessarily. A sponsor-funded positive delegate change obscures whether
the original principal can be fully drained. Removing native checks or adding an
operator rescue key violates the invariants. Merely replacing `>` with `>=` in
accounting leaves the old native positive-change restriction in force.

## Custody and falsifiable completion

Only the user's machine creates/stores the backup and native key; exchange public
receiving details and public operation bytes. This Cloud can qualify fresh test
wallets in separate processes but cannot demonstrate independent administration.
That remains a user-operated follow-up, not a passing local-test assertion.

The local package must reconstruct the exact committed public state, detect
missing/changed history, discover only decryptable current unspent notes, bind
exit authorization to the user's local native key and verify its real wallet
proof. A local terminal native payout must either pass all actual input scripts
and reconcile to zero user liabilities/reserve, or fail at a specified enforcing
layer. Missing history, wrong root, stale/nullified claims and dependencies must
never be called a successful recovery. N-user shutdown recovery on TN10 remains
open until independently administered users actually exit after original services
are unavailable.
