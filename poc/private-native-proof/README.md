# Fixed four-batch local lifecycle proof package

PR50's original preparation records are retained in
[preparation-pr50](preparation-pr50/evidence/qualification.json). Its first
[released rehearsal](gpu-2026-10-18/README.md) failed before proof generation.
The current runner creates the `proofs` and `cpu` parent directories required
by the unchanged Rust executable. A new real-subprocess regression exercises
all nine stages with synthetic filesystem-only stand-ins. The corrected runtime
requires a new image digest; the guest, wallet proofs, public package and compiled
producer/verifier bytes remain unchanged.

Software preparation after merged PR49 (`08bd96d`). No GPU rental, proof execution,
funding, native broadcast or provider action is included. The guest, wallet VK,
actual wallet proof bytes, expected journals and native policy remain those
reviewed at `b44956e`. PR48 evidence is preserved.

The package carries exactly `deposit`, `credit-transfer`, `exit`, `reconcile`,
in that order. Complete 352-byte journals agree on each predecessor/successor
state root and lane tip, covenant/relation identity and lane key. Exact inputs,
program and journals are checked against fixed hashes, then against the compiled
PR49 target checks without executing the guest. There are no wallet secrets or
setup/proving parameters in this outer-prover package.

## Identities and files

[Package identity](evidence/package-identity.json) binds source files, archive,
policy and executables. Producer and verifier are separately named copies of the
**same unchanged reviewed PR49 executable**, with independent compiled expectations;
the alias does not constitute an independently implemented verifier. Verification
runs in a separate process, and again from a trusted CPU/B copy after download.
No GPU-supplied executable or GPU-selected expectation is trusted.

[Run manifest](run-manifest.json) gives the fixed scope, image/configuration,
limits, ordered jobs, result paths and release conditions. [Deployment](deployment.json)
records the published immutable registry digest after publication. A local Docker
image ID is distinct from that registry digest. The prior PR47 image has another
job and must not be substituted. The base CUDA prover remains the previously
qualified official SDK3.0.3 build; this preparation does not rebuild it.

## Whole-job deadline and partial results

`lifecycle_worker.py` invokes ONE `worker.run_phase` for the complete runner.
The runner sequentially creates each receipt, verifies it in a separate CPU
process, and verifies native permission issuance/restricted payout for the genuine
new exit receipt. All compression and these checks remain in the same process
group. The 3,600-second deadline is shared, not restarted for each batch.

The reused independent timer outside the proof group is backed by a **GNU
`timeout --signal=KILL` process**, supervising the entire group. It survives loss
of the controlling service. Its timeout is the remaining aggregate allowance,
never more than 3,600 seconds including startup. The runner does not detach its
prover/verifier children. Credential-free local tests actually kill a hung later
stage and descendant, retain a completed earlier synthetic artefact, and verify
that the external timer still works after its controlling process is killed.
No proof is produced by these tests.

The reviewed producer saves candidate receipts before further verification.
Periodic snapshots retain completed/candidate receipts, stage files, stdout,
resources and CUDA samples when a later stage fails. No automatic retry occurs.
A failure or missing CUDA evidence cannot become full qualification. CUDA activity
is attributed to matching group processes separately within each proof stage;
short/missing telemetry remains inconclusive even if receipts verify.

The unchanged B guard independently backs up archives with hash/size/atomic-write
checks and confirms provider `EXITED`; its absolute rental deadline does not wait
for downloads or Cloud. B needs neither Cloud, TN10 gateway nor a laptop at runtime.
Preparation neither installs a new guard nor activates a loop or lease.

## Independent CPU and native verification

Restore the trusted package before any later rental:

```bash
python3 poc/remote-cuda/lifecycle_package.py restore /path/to/new-trusted-package
```

Returned archives are data. Use the hash recorded by B's guard, reject unsafe tar
members, and never execute files from the returned archive:

```text
python3 lifecycle_control.py extract ARCHIVE NEW_DIRECTORY EXPECTED_ARCHIVE_SHA256
python3 lifecycle_control.py verify TRUSTED_PACKAGE EXTRACTED_DIRECTORY NEW_VERIFICATION_DIRECTORY
```

Every returned receipt/candidate is verified against the compiled new program,
fixed join control, exact journal and no unresolved assumptions, with development
mode disabled. The executable also runs actual cryptographic tamper controls.
A partial set produces partial verified results and a failing CLI exit status.
Full success requires all four receipts AND genuine exit-receipt native issuance
and restricted payout verification. Native state/permission script checks use
PR49's lane-restricted adapter, not the old unrestricted settlement construction.
An old PR48 receipt cannot stand in for any new lifecycle target.

These native checks use **synthetic UTXOs/anchor fixtures**. Even a successful future
four-receipt run is a local proof/native-script rehearsal, not canonical TN10
acceptance, a funded wallet or a production privacy/security claim. The retained
PR49 native/accounting regressions, single pending exit, single sufficient reserve
per exit, positive change and fixed transaction shape remain unchanged.

## Future operational sequence — not released here

1. Review the immutable image, workload/package identities and local qualification.
2. Separately release one actual L40S quote within the existing USD5 planning
   limit, including storage. Maximum rental is 7,200 seconds from actual Pod
   creation; maximum aggregate proof group is 3,600 seconds; one attempt.
3. Through Cloud → TN10 → B, confirm B's clock/storage and existing guard source
   hashes. Install the trusted CPU client/package separately from guard state.
   Keep account credentials only in B's root-only env file; use its existing
   service token. Add no Cloud secret/domain or runtime dependency on the gateway.
4. Read back actual Pod creation/resources/image digest and exact service scope.
   Bind one fresh lease and new `/workspace/kpi-private-native` state. Start only
   with fresh independent guard heartbeat and more than 3,660 seconds remaining.
5. Preserve/archive results on B; independently verify trusted CPU/native paths,
   record each proof's timing/RAM/VRAM and matching-process CUDA evidence.
   The B recheck is an independent post-download audit, not another GPU proof job.
6. On every outcome confirm provider `EXITED`. Keep storage until external
   preservation is checked; after verified preservation remove only this attempt's
   Pod/storage and confirm deletion. Record actual runtime/charges; USD5 is a
   planning limit, not a guaranteed provider invoice cap.

Nothing here grants the rental/proof release. No TN10 transaction is in this job.
