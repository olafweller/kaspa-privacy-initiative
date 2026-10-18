# ADR-0012: bounded private-note state/settlement integration

Status: Accepted for owner-authorized local implementation and execution-only
qualification, 2026-10-18. No rental, native funding or TN10 broadcast is included.

## Decision

Preserve PR44's LOCAL-NO-FUNDING artifacts as a historical baseline. The next
circuit targets a distinct kaspa-testnet-10 rehearsal domain: pinned testnet
genesis, a new lane and a fixed fresh unfunded pool nonce, specified byte-for-byte
in `poc/private-note-chain/domain.json`. The domain excludes wallet VK and native
program/covenant identities, avoiding circular key/image derivation. A later
fresh pool must use a new nonce and requalify its identities. No migration or
coexistence of old/new domains is allowed by this experiment.

Reuse the exact existing wallet relation with this new domain, and the existing
ordinary accelerated BN254 pairing backend. Check all fourteen packed public
inputs against Arkworks. Keep fixed key data validated before compilation, all
untrusted proof encoding/curve/subgroup checks, independently expected image IDs
and actual verifier-returned failure for invalid operations. No custom arithmetic.

Separate local wallet proving from guest/application execution; public parameters
may be saved/reloaded, while secret backups remain owner-local and are never sent
to an outer prover. Require a restored-wallet discovery/subsequent-spend check
before any future native rehearsal.

Integrate current spentness, note updates, pending deposits and exits into an
atomic state transition. Bind the state preimage to the previous root and fold
all native lane IDs/payloads, including rejected ones. Reuse the existing reference
transaction/batch/aggregate ABI and Succinct settlement route rather than a new
outer Groth16 conversion. Native deposit/payout claims are valid only if checked
at actual accepted-input/covenant/permission enforcement points; a host fixture
inside a proof cannot substitute for those checks.

## Qualification and stop rule

Declare 128,000,000 cycles and 900 seconds per selected complete execution-only
scenario, four CPU threads, development mode disabled. Pin guest identity before
execution. Timeouts and resource failures are failures, never successful attack
rejections. If the profile is exceeded, preserve the actual last stage and stop
that qualification branch without silently raising the budget. No full outer
proof attempt, paid infrastructure or native transaction occurs in this package.

Deliver actual measurements, security self-review, remaining native bindings and
a concrete GPU proposal only where measured suitability supports one. Four-leaf
capacity, whole-note exits, zero app fees and experimental one-party setup remain;
source/reuse review and all security invariants from ADR0011 still apply.
