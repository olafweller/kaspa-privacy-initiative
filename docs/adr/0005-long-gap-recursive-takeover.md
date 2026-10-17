# ADR-0005: Recursive public-account takeover experiment

Status: Accepted for isolated TN10 research only, 2026-10-17.

PR31/32 demonstrate bounded native lane/value integration, not continued exits
after long inactivity. Their fixed lift circuit and 100-score adapter bound are
not general runtime mechanisms. The owner authorized the proposed follow-up.

Reuse the reference vProgs per-batch/aggregate verifiers, real recursive receipt
resolution, native covenant and permission bridge. First qualify composition
without funding. A small transaction adapter may represent the retained complete
public account map as one SMT resource; it must preserve authorization,
single-credit, checked sompi accounting and binding to accepted native IDs.
This avoids building another scheduler or lane implementation.

Reject lane-expiry metadata inside the guest until inactivity/reset continuity
is separately authenticated. Test an idle gap exceeding the old 100-score bound
but below actual native expiry. Replacing the old constant with an arbitrary
large bound in the funded guest is rejected as an answer to recursive integration.

Fresh instance only, test-KAS only, no admin upgrade or privileged exit. The
existing six-test-KAS balance is not migrated or described as recovered.
Use a clean executor process with public replay data and separate fee capability;
report its shared host/node and archive dependence explicitly. A state root
cannot recover missing data. Passing this gate would not select the production
architecture or establish privacy, independent-node corroboration, pruning,
arbitrary downtime or guaranteed progress. RFC-0001 remains open.

See [execution plan](../../poc/takeover/PLAN.md). Existing research on Orchard,
Aztec, RAILGUN, Monero and MWEB identifies authenticated history and user keys as
recovery inputs; none supplies a drop-in Kaspa proof/DA mechanism. Reuse the
established RISC Zero composition here, with no new cryptographic primitive.

## Observed qualification, 2026-10-17

The [fresh rehearsal](../../poc/takeover/LIVE-REHEARSAL.md) completed native deposit,
recursive credit, clean public reconstruction, withdrawal after a 175-blue-score
observed stop gap, recursive settlement and confirmed native payout. Native
fixed-endpoint omission and bridge/replay controls were rejected; remaining
reserve matches account balance. This qualifies this isolated public instance,
not independent recovery, expiry, privacy or a production architecture.
