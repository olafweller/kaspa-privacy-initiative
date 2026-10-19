# PR55 targeted Astra review response

Reviewed head: `5d09e2fafce85b024dacb7ef372a33d9a7323c4a`.
The two corrections change the receiving interface and CI integration only;
wallet cryptography, VK, terminal native policy and old guest are unchanged.

## Shared receiving details

`init` now exports exactly `schema`, `domain`, `owner`, `incoming`. The native
key is still generated and retained locally, but its public key is not included
in the file shared with the sender. The Rust file-creation test and a real CLI
init both assert that exact four-field allowlist, preventing extra metadata or
an accidental payout key from being reintroduced.

The rehearsal obtains Bob's native destination only from his later public exit
result. It checks the returned payload against the actual wallet operation and
native key, operation ID and expected prior state root before constructing the
fixture transaction. It does not read Bob's native secret. The actual wallet
EXIT proof continues to bind its destination. Reusing that native destination
in later exits and other correlation remain separate privacy questions.

## Historical CI integrity

Restore `.github/workflows/code.yml` exactly to the merged PR54 version, SHA256
`3210289fa84d93591cee5b2cb9a01183554edd798b52733cd2c01d1e3efbbaa3`.
Do not change the historical source-hash file or its checking code. The existing
Rust job still discovers/tests the recovery binary automatically.

New `.github/workflows/user-recovery.yml` builds the actual CLI binary and runs
its offline checks, including the receiving allowlist, and the original TN10
preparation integrity check. It uses the same pinned native source/Rust and
read-only repository permissions, without runtime credentials or live actions.

## Evidence

The original local fixture, logs and manifests remain available. The reviewed
runmanifest and original evidence manifest are additionally copied under
`evidence/review-fix`. The active runmanifest describes the corrected source and
local executable. Fresh post-fix local results and the focused regression logs
are retained separately in that directory, never substituted for old execution.

This correction does not authorize merge, a new guest/proof statement, outer
proving, rental, funding or TN10 broadcasts. PR55 remains open for a targeted
review of these changes.

Post-fix validation: all 19 Rust tests, the receiving allowlists, all 11 CLI
negative controls and the complete local fast-check script pass. The fresh
[rehearsal](evidence/review-fix/local/qualification.json) completed in 185.21 seconds
with four real wallet proofs and the two actual native-script fixtures, paying
Bob 4 and Alice 6 test-KAS principal plus separate permission refunds. Final
user reserve/private/unpaid-exit liabilities are zero. These remain local
fixtures with no new outer proof or TN10 activity. See [check summary](evidence/review-fix/checks.json).
