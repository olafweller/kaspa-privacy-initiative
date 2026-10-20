# Six-receipt recovery lifecycle — proof-package preparation

PR56 was merged as `2010684bc40c482e69f0994229385a0a1e0ece78` after its focused
review at `cfee7e5`. This package adds the producer and bounded orchestration for
its corrected six-batch public corpus. The reviewed guest, wallet circuit, VK,
proof bytes, native restrictions, public inputs and exact journals are unchanged.
There is no new setup, private witness export, native funding or TN10 broadcast.

## Fixed experiment and success conditions

Order: deposit, credit-transfer, bob-exit, bob-reconcile, alice-exit,
alice-reconcile. Deposit and both reconciliation batches retain segment limit
`2^16`; credit-transfer and both exits retain `2^20`. All retain 160M user cycles.
All six were measured as multi-segment sessions; the expected final receipt
control remains the independently fixed official Join control.

The producer saves any returned candidate immediately, before stats or verification.
Each final receipt is checked in a separate trusted CPU process for its fixed
program ID, exact 352-byte journal, actual seal/control identity, disabled dev
mode and absence of unresolved assumptions. The existing fifteen cryptographic
mutation controls run for each genuine receipt. The native verification helpers
are reused from PR56 without changing their enforcement.

After each exit receipt, the real receipt must authorize its actual native
permission issuance. The permission ID and signed payout ID must match the
corrected next batch, and the payout must pass the pinned native script engine.
Both forms retain semantic negative controls: eight per exit plus the zero-reserve
output attack for full drain. B's independent control repeats receipt and native
checks using the prequalified package, never an executable from GPU results.
"Independent" means separate processes and trusted B verification, with the same
reviewed implementation; it does not mean an independently developed verifier.

The native verifier embeds the fixed public inputs, expected states and templates.
It does not read the build machine's PR55 corpus paths. A Rust regression compares
the embedded fixtures byte-for-byte with PR56's regenerated corpus; CPU/container
startup checks exercise both embedded native payout contexts. Those contexts
contain synthetic permission UTXOs and chain anchors: startup acceptance is not
receipt-authorized issuance or actual chain acceptance.

## Preparation checks and image

[Package identity](evidence/package-identity.json) pins executables, public archive,
runtime source and policies. [Deployment](deployment.json) records the immutable
image after publication. The Dockerfile reuses the already qualified official
RISC Zero 3.0.3 CUDA prover by digest and binary hash; kernels are not rebuilt.
The image is built and CPU-smoked on GitHub, preserving local disk space. Neither
the build nor startup check calls a provider or starts proving. CUDA execution of
this new workload remains to be demonstrated during a separately released run.

```bash
source /workspace/.onboarding/activate.sh
cargo +1.91.0 test --locked --release --manifest-path poc/recovery-proof/Cargo.toml
python3 poc/recovery-proof/check_package.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s poc/remote-cuda -p test_recovery.py -v
python3 poc/remote-cuda/recovery_package.py restore /new/trusted-package
```

The tests include actual subprocess directory contracts for all fourteen steps,
partial/candidate preservation, fixed targets and segment profiles, continuity
mutations, guard gating, and an external timer that kills later descendants even
if its controller dies. Synthetic stand-ins test orchestration only. No new outer
receipt or positive genuine-receipt permission issuance has been run in preparation.

## Concrete run and boundaries

Follow [runmanifest.json](runmanifest.json) and [START.md](START.md). One L40S,
one attempt, at most 3,600 seconds jointly for all six proofs, compression, CPU
checks and both native checks, and at most 7,200 seconds rental from actual Pod
creation. One external process-group timer encloses the complete sequence. No
batch gets another hour and no automatic retry or budget increase is allowed.
Completed and candidate receipts survive a later failure.

Require more than 3,960 seconds remaining at start: the proof hour, B's 60-second
stop lead, and 300 seconds planned transfer margin. This margin is not a guarantee
of network transfer. B's unchanged independent guard enforces the absolute lease,
backs up durable archives, confirms provider EXITED, and allows deletion only
after verified external preservation. GPU telemetry must show matching-process
CUDA activity for each batch. Cryptographic, CUDA and operational outcomes are
reported separately; partial/candidate sets never become a full experiment success.

The USD5 allowance is a planning limit requiring a current GPU/storage quote,
not a guaranteed provider bill cap. No rental/proof release is granted by this
preparation. B credentials remain in the existing root-only env file; the
Cloud → TN10 → B path remains installation/control only. No new Cloud secrets,
domains, live B lease, provider action or TN10 transaction is needed here.

Even successful receipts would prove this local synthetic context. A fresh
actual TN10 instance, real accepted captures and new proofs remain necessary.
The old PR54 reserve is unchanged. Independent user custody, data availability
and withdrawal after original-service shutdown remain separate live gates.

## B archive correction after review of 1059dea

The result extractor now reuses the existing `staged_archive.py` helper. It bounds
the compressed read (64 MiB) and the entire gzip expansion (256 MiB) before tar
processing, including hidden PAX/GNU extension data and padding. Existing hash,
canonical path, regular-file, duplicate, member-count and per-file/visible-content
limits remain enforced. Invalid archives create no extraction directory.

The four focused regressions exercise the actual CLI, an isolated installation
of the pinned B client files, and small PAX/GNU cases that must fail before
`tarfile.open`. Compressed-size and digest rejection happen before gzip processing.
The `trustedBClientFiles` manifest explicitly includes the helper dependency.
See the [extraction tests](../remote-cuda/test_recovery_extract.py).

The image, public archive, binaries and proof workload remain unchanged. The
corrected controller and its archive helper are B-side dependencies, not GPU
image contents. The original qualification/identity is preserved under
[pre-archive-fix-1059dea](evidence/pre-archive-fix-1059dea/README.md); original image
publication remains evidence for that same immutable image. Current B bindings
are recorded separately from that image's copied runtime sources.

The same four regressions passed on actual B as `kpi-cuda-guard`, including the
isolated client import and real extraction CLI. Installed sources and results
are recorded in [B qualification](evidence/b-client-archive-qualification.json).
The guard stayed disabled/inactive; no credentials, provider or proof operation
was used. This qualifies the B extractor, not native receipts or a GPU run.
