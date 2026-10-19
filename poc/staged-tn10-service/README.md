# Staged TN10 GPU service preparation

This package completes the service/image preparation following reviewed PR52.
It does **not** release native funding, broadcasting, GPU rental or new proving.
See [deployment.json](deployment.json), [runmanifest.json](runmanifest.json) and
the [qualification evidence](evidence/qualification.json).

## Fixed workload, arriving one stage at a time

Retain the reviewed PR52 host executable, guest, VK, wallet relation and native
restrictions unchanged. The CUDA executable is the previously qualified RISC
Zero 3.0.3 binary. The new image contains the trusted host/program/public trial
and Python service. The new staged package contains **no** wallet backup, native
private key, wallet setup parameters, provider credential, synthetic producer or
fixed chain input. The unchanged qualified base image also retains its historical
public PR40 diagnostic inputs/binary under `/opt/kpi/package`; this service does
not select or execute that workload. Its CUDA build metadata is checked there.

Inputs arrive in this order: deposit → credit-transfer → exit → reconcile.
Each next public input depends on actual preceding native acceptance and is
frozen using the existing [TN10 preparation](../private-native-tn10/README.md).
The trusted B controller stores the target locally and approves its SHA256
before uploading the corresponding four-file public archive. Server/GPU-returned
metadata never supplies the independently expected target.

The only uploaded files are `guest.program.bin`, `input.bin`, `journal.bin` and
`target.json`. The service checks archive hash, exact filenames, duplicates,
regular-file type, bounded decompression, each asset hash, trial/stage, the fixed
guest/join, complete journal, cycle/segment settings and the shared hour limit.
The shared gzip reader checks **all** decompressed bytes before tar parsing,
including PAX/GNU extension metadata, headers and padding. Uploads allow at most
8 MiB compressed / 16 MiB expanded and four logical members. Returned evidence
allows 64 MiB compressed / 256 MiB expanded and 2,048 logical members; its
compressed file read is bounded too. Existing file/hash/journal checks remain.
Extraction never executes or trusts an uploaded program: the guest bytes must
match the reviewed program SHA; the host executable comes from the image.

## Persistent attempt and external supervision

Use one persistent `/workspace/kpi-staged-tn10` directory. The main process holds
an exclusive file lock; a second mutating service cannot open the same state.
The state records approved/received targets, results and the immutable lease.
The reviewed `run_stage.reserve()` supplies the durable attempted/completed
ledger, journal continuity and deadline. The first accepted stage starts the
**single 3,600-second deadline**, including all proof/compression/CPU work and
waiting for subsequent chain checkpoints. Later arrivals, connections and service
restarts cannot reset it. Every accepted stage is consumed before spawning.

The fixed child command runs beneath external GNU timeout, using the existing
process-group/CUDA sampler. The prover and separate CPU verifier inherit that
group. Completed/candidate receipts are saved immediately by the unchanged
producer. The actual directory parents exist before either Rust process starts.
Process-group identity (PID, start ticks and boot ID) is recorded before proving;
a durable launch gate prevents an unregistered child starting after restart;
an active-service restart kills only the matching saved group and terminates the
attempt as interrupted. Cleanup is repeated on every interrupted restart, so
process loss after persisting the interruption but before the kill cannot skip
the kill on the next restart. PID/start-time/boot-ID checks remain in force.
Waiting restarts retain progress/deadline and require a
fresh B heartbeat. A lost HTTP response does not cancel/repeat the accepted job.

The service checks for an actual `/workspace` entry in Linux mountinfo. Docker
bind/volume mounts can share their parent's device ID, so `Path.is_mount()` alone
is insufficient. Local container qualification exercises persistent volume
restart. Actual provider volume identity/capacity still requires B preflight.

## B guard and management

The existing B guard is unchanged. It still uses `/v1/configure`, `/v1/guard`,
`/v1/status` and `/v1/artifacts`. The service stays `waiting` between batches;
that is not terminal completion. After all four jobs, failure, interruption or
deadline expiry, it returns the corresponding terminal state. The guard backs
up partial/final archives and separately confirms provider EXITED, with its
absolute stop beginning 60 seconds before the two-hour lease limit.

B remains independent of Cloud, the TN10 gateway and the owner's computer at
runtime. Those machines are management paths. The account key remains only on B
in the existing root-only envfile; only the existing GPU service token reaches
the service. No new Cloud secrets or allowed domains are needed. B root remains
a trusted operator; this does not isolate credentials from that administrator.

For later installation, preserve relative module layout, for example:

```text
/opt/kpi-staged-tn10/remote-cuda/   trusted client/verifier + unchanged common/guard dependencies
/opt/kpi-staged-tn10/private-native-tn10/run_stage.py
/opt/kpi-staged-tn10/package/       restored trusted public package
/var/lib/kpi-cuda-guard/            existing independent guard state
```

This does not create another chain executor or guard loop. The B client sends
only fixed GPU requests; the local verifier runs only its trusted executable.
No installation or host configuration change is performed in this PR.

## API and B commands

Run behind the established RunPod HTTPS proxy; application port 8080 is internal.
Every route requires `Authorization: Bearer <existing service token>`. Tokens are
not request arguments, serialized state, image layers or logs. The B client uses
TLS verification, redirect refusal, timeouts and the honest application User-Agent.

| Route | Purpose |
| --- | --- |
| `POST /v1/configure` | One immutable Pod/creation/deadline/price/storage/trial/policy lease |
| `POST /v1/guard` | Existing B heartbeat; less than 30s old before any stage starts |
| `POST /v1/targets` | B approves `{trial, stage, targetSha256}` for the next stage |
| `POST /v1/stages/STAGE` | `application/gzip` public package; target/package hash headers |
| `GET /v1/status` | Durable ledger, scope, policy, progress and archive hash |
| `GET /v1/artifacts` | Hash-checked partial/final public evidence archive |

There is no arbitrary command, guest, filename, reset or generic `/v1/start`
route. Identical duplicate uploads return the original attempt; conflicting,
out-of-order or concurrent starts are refused without a second executor.

Use `staged_control.py` **on B**, with its existing token supplied to the process
environment by the established root-managed mechanism. Never place a token/key
on the command line or read/print the envfile to discover its contents.

```text
staged_control.py status   --lease LEASE --package TRUSTED_PACKAGE
staged_control.py approve  --lease LEASE --package TRUSTED_PACKAGE --stage CASE --target TRUSTED_TARGET --expected-target-sha SHA
staged_control.py submit   --lease LEASE --package TRUSTED_PACKAGE --stage CASE --archive PUBLIC_TGZ --expected-target-sha SHA
staged_control.py download --lease LEASE --package TRUSTED_PACKAGE --output NEW_BACKUP_DIR
staged_verify.py TRUSTED_PACKAGE SAVED_ARCHIVE TRUSTED_TARGET_INDEX NEW_CPU_OUTPUT
```

The target index maps stage names to local `targetPath` and `targetSha256`.
The external CPU verifier ignores executable/expectation files returned by the
GPU. It checks exact independent targets, real receipts and existing crypto
negatives in separate processes. Partial verified results remain partial. Use
the actual new exit receipt with PR52's signed settlement/payout builders and
native context between stages; no fixture receipt may stand in for that input.

The lease has the existing ten public provider fields plus `workloadScope`,
`trial` and `packagePolicySha256`. Unknown fields are refused, so it cannot be
used as a carrier for account credentials. Read back the actual Pod's immutable
image, scope, resources, creation time and fresh volume before arming work.

## Qualification and remaining release

Local tests drive the real HTTP handler, same directory structure, actual
subprocesses, external timeout, process loss/restart, durable outputs and the
unchanged B guard with **simulated** provider answers. Synthetic producers copy
retained real receipts instead of proving; trusted CPU receipt verification is
actually executed both in the child and again against the external archive.
The synthetic helpers are not included in the production image.

The CPU image check compares application bytes, reviewed runner, host/program/
policy and CUDA executable, checks linking, authenticated startup, persistent
restart and actual retained receipt verification. It starts no proof job, calls
no provider and cannot establish actual matching-process CUDA use. Publication
re-pulls the exact registry digest and repeats these checks.

The [run manifest](runmanifest.json) retains one L40S, one attempt, 160M cycles per
batch, one aggregate hour, two hours from actual Pod creation, no retries or
extensions, and USD5 planning including the actual quote/storage. USD5 is not a
provider bill guarantee. Leave transfer/stop margin and preserve/CPU-verify
external copies before deleting a future Pod/storage. Actual B installation,
fresh native preflight, custody and separate live release remain unperformed.

The current image source commit is recorded in
[publication provenance](evidence/publication.json), with the exact digest in
[deployment.json](deployment.json). The follow-up commit records publication
metadata/documentation only; its runtime sources remain identical to the image
source commit and are checked by `evidence/source-sha256.json`. The historical
PR52 manifest remains unchanged; use this supplemental manifest for the reviewed
service binding, followed by actual-chain preflight and separate live release.

## Focused Astra correction

The two reproduced PR53 findings and their fixes are recorded in
[correction review](evidence/correction-review.md). The original reviewed
`71575ad` reports, source bindings and manifests are retained under
[evidence/history/pr53-71575ad](evidence/history/pr53-71575ad/qualification.json).
The public host/guest package is unchanged; only the service/image plumbing and
B archive parser change. No live execution release is added.
