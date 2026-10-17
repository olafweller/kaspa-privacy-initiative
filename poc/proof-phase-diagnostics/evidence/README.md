# Public phase diagnostics

The [manifest and measured outcome](comparison.json) and
[public artifact archive](local-phase-artifacts.tar.gz) retain the completed
bounded diagnostics, including the pre-proof integration failure and repair.
The original PR #39 archive remains unchanged.

- Archive: **2,001,456 bytes**, **107** checked regular members.
- SHA-256: `01107d542cb0c333ec509362de59bbb6c402a4d243c13f13954f485e3c256cfc`.
- Reporting/source snapshot: `757ae8f`; proof-producing host: `ca9b186`;
  original execution export: `bdee079`.
- Original aggregate diagnostic clock: **1,058.525 seconds**, under 3,600 seconds.

The archive contains two real segment receipts, their two real lifted receipts,
one actual joined receipt, per-artifact verification checkpoints and the
separate-process verification result. It also retains selected new trace bytes,
selected old temporary trace samples, all segment metadata/hashes, unchanged
program/input/expected journal, logs, resource/cgroup interval reports, SDK/prover
identities and selected source/locks. No wallet secret, proving parameters or
credential is included. The full-classifier receipt remains unproduced.

Receipt/source files are associated with the recorded producing revisions; the
source snapshot in the manifest can include later reporting/collection code.
Every regular archive member is read back against its declared hash and size.
Extract only checked regular relative paths. The selected trace bytes reproduce
the segment probes through the supported SDK; the wider original qualification
data is retained in the referenced PR #39 archive.

Cryptographic integrity of the five partial receipts is distinct from full
classifier membership: the trusted pinned execution/export associates these
middle segments with the workload, while no cryptographically composed path
from the independently expected initial image to final journal is claimed.
See [results and measurement limitations](../RESULTS.md).
