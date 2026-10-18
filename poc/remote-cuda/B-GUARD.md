# B guard preparation — 2026-10-18

The independent guard is installed and its credential-free host checks pass.
The real guard loop is **disabled/inactive**. No GPU, real RunPod lease, provider
mutation, proof job, TN10 transaction or host reboot was performed. The operator's
later read-only provider check and the header maintenance are recorded below;
Codex did not repeat that provider request or read the account credential.

## Identity and management route

The owner verified B as `vmi3641034.contaboserver.net` / `13.140.166.15`, separate
from TN10/gateway `vmi3633138.contaboserver.net` / `194.163.162.11`.
This Cloud task confirmed exit 0 and B's exact FQDN through:

```bash
VPS_ADMIN_TOKEN="$TN10_RPC_TOKEN" node .local/codex-cloud-tn10/admin/vps-exec.mjs --command '/usr/local/bin/kpi-b-ssh hostname -f'
```

Subsequent installation commands used the same client and wrapper, sequentially.
No second executor, new Cloud secret, VPN, SSH binding or network rule was added.
The owner prepared the pinned SSH host key and source-restricted login; the SSH
private key remains on TN10 and its contents were not inspected or copied.

This is only an administration route. Once separately authorized, configured
and activated, B's local Python/systemd guard reads its local lease and credentials,
writes backups on its local disk and contacts RunPod REST/the exact Pod HTTPS
service itself. It contains no dependency on the Cloud task, TN10 gateway, SSH
wrapper or laptop. B availability, clock, disk and direct HTTPS access to those
services remain operational dependencies. The operator subsequently reported a
successful read-only provider GET; stop/write permissions and the actual Pod
proxy remain unqualified.

B root and administrators able to obtain B root remain trusted operators. They
can technically read credentials and archives or change/stop the guard. SSH
restrictions and file modes do not protect against a malicious administrator.

## Installed state

Initial installed source: `0ed4cb0b465f863f03b06ab3ef102234528996bc` on PR #42.
The later header maintenance changes `common.py` and the focused control test;
use its new source/hash record below for the current runtime.
The sole unit change adds `StateDirectoryMode=0750`, preserving the prepared
state permissions at later activation. No guard algorithm or CUDA image changed.

| Location | Contents / permission |
|---|---|
| `/opt/kpi-remote-cuda` | Root-owned `0755`; eight root-owned `0644` Python files |
| Runtime Python files | `common.py`, `watchdog.py`, `make_lease.py` |
| Qualification/support files | `qualify_guard.py`, `test_remote.py`, `service.py`, `worker.py`, `package.py` |
| `/var/lib/kpi-cuda-guard` | `kpi-cuda-guard:kpi-cuda-guard`, `0750`, local ext4 |
| `/etc/systemd/system/kpi-cuda-guard.service` | Root-owned `0644`; verified, loaded, **disabled/inactive**, PID 0 |
| `/etc/kpi-cuda-guard.env` | Root-owned `0600`; initially comments only; account credential later provisioned by the operator on B only |

The dedicated system account is UID 995/GID 986 with `/usr/sbin/nologin`.
As that user, state is writable; code/unit files are not writable and the
root-only environment file is not readable. Systemd reads that file as manager
when the service is activated later. No production `lease.json` exists.

The host reported Python 3.12.3, systemd 255, synchronized time and
85,807,165,440 available bytes (about 79.9 GiB) under `/var/lib` before setup.
At initial installation all source hashes matched its manifest. The later
header-maintenance record tracks the current hashes separately. There was no
pre-existing guard path, account, environment file or unit to overwrite.
All 38 pre-existing B KPI unit states/PIDs are unchanged; TN10 remained active
with PID 43275. No old trial data, wallet or credential contents were inspected.

## Focused qualification on B

Both checks ran as `kpi-cuda-guard`, not root, with a cleared environment and
new test/temporary directories on the actual state filesystem (device 2049):

```text
/var/lib/kpi-cuda-guard/qualification-20261018-1792319377741807705/
```

- The separate-process recovery rehearsal passed. It seeded a truncated copy
  and stale completion record, repaired the archive, then checked reuse and the
  original retrieval grace in another Python process. The saved copy is 51
  bytes with SHA-256
  `094e4e30fb8a7f2110c182ec03f992590249c174efc4eee58e2fe57f3c0b7d25`;
  no archive temporary files remained. This is public simulated data, not a proof.
- All **13 control tests passed**. They cover same-size corruption, failed
  atomic replacement, terminal backup recovery, backup failure and stalled
  request deadlines, stop acknowledgment/read-back, authentication, single
  attempt/restart behavior, archive validation and a real short process-group
  timeout with credential stripping. Provider/job responses are simulated;
  real provider-stop behavior is not established.
- `systemd-analyze verify --man=no` passed without starting the unit. Final
  read-back confirmed inactive/disabled status, permissions, source hashes,
  absent production lease and unchanged old services/node.

No broad project, Rust, Docker or CUDA build was run. Host qualification,
permission/read-back checks, evidence hashes and documentation links are the
checks appropriate to this update. Commits use `[skip ci]` to honor the owner's
explicit no-broad-build instruction; this does not claim a fresh full CI run.

Retained evidence: [summary](evidence/b-guard-2026-10-18/summary.json),
[installation](evidence/b-guard-2026-10-18/installation.json),
[qualification](evidence/b-guard-2026-10-18/qualification.json),
[test log](evidence/b-guard-2026-10-18/control-tests.log),
[before](evidence/b-guard-2026-10-18/preflight.json) and
[after](evidence/b-guard-2026-10-18/postflight.json) snapshots. The parent
[manifest](evidence/manifest.json) records their sizes and hashes.

## Application-header maintenance

The operator reported that a real `GET https://rest.runpod.io/v1/pods` initially
returned 403 with "The site owner has blocked access based on your browser's
signature." The same credential/permissions returned HTTP 200 and zero Pods
after adding the honest application headers `User-Agent: kpi-remote-cuda/1.0`
and `Accept: application/json`. These live observations and the operator's
13-test result are owner-reported, not re-run by Codex. They establish reported
read access only; real stop/write permissions remain untested.

Git now contains the exact patched B `common.py`, SHA-256
`5ed5815ae1177f5915852477d270110f3768bd6b61ff5ebd5833b62526e549c3`.
Codex confirmed the B bytes/hash without overwriting that runtime file. The B
reinstallation source must be this patched Git version, not the original
installation snapshot or `common.py` extracted from the earlier CUDA image.
The B
recovery source `/opt/kpi-remote-cuda/common.py.before-user-agent-20261018`
remains at original SHA-256
`841a0670ec027616cab4d6c0c9cd2a7ce842322489319dfde5062b6638da0a83`.
The diff consists only of the two headers: Authorization, Content-Type, TLS-only
URLs, redirect refusal, ten-second default timeout and body limit are unchanged.

One regression was added to the original thirteen tests. It checks the actual
constructed headers, fake bearer authentication, content type, default timeout,
redirect handler and refusal of plain HTTP, using a mocked opener. All **14
tests and the separate-process recovery rehearsal pass on B** as the dedicated
service user in a fresh state-partition directory. Only `test_remote.py` needed
deployment by Codex. The real environment file was never opened; tests used a
cleared environment without the account credential. The guard remains
disabled/inactive, PID 0, with no real lease.

The current [maintenance evidence](evidence/b-header-maintenance-2026-10-18/summary.json)
retains the [new host hashes](evidence/b-header-maintenance-2026-10-18/source-after.json),
[test results](evidence/b-header-maintenance-2026-10-18/control-tests.log),
[operator report](evidence/b-header-maintenance-2026-10-18/operator-report.json)
and [artifact-binding audit](evidence/b-header-maintenance-2026-10-18/artifact-bindings.json).
Initial installation/qualification records remain unchanged historical evidence.
See [PREPARATION.md](PREPARATION.md#guard-source-versus-published-image) for the
deliberately separate published-image source binding.

## Before a later rental and activation

1. Obtain the separately agreed rental release and actual one-L40S quote,
   availability and storage charges. Preserve one attempt, at most 7,200 seconds
   from provider creation and 3,600 diagnostic seconds. USD 5 remains a planning
   envelope including retention, not a guaranteed provider bill.
2. The operator reports the RunPod account credential is now provisioned **only
   on B** in the root-owned `0600` environment file; Codex checks metadata only.
   Configure/confirm a fresh scoped
   `KPI_GPU_TOKEN` is shared with the later Pod and destination-scoped Cloud
   configuration; the account credential never goes to Cloud, the GPU container,
   Git, command arguments or logs. No credentials are requested in this PR.
3. Use the already published immutable CUDA image from
   [PREPARATION.md](PREPARATION.md). After separately authorized Pod creation,
   obtain the real creation timestamp/resources/quote and write the valid lease
   to `/var/lib/kpi-cuda-guard/lease.json`, readable by the service account.
   Never promote the rehearsal's simulated lease from its test subdirectory.
4. Only then enable/start the guard on B, check its heartbeat/deadline against
   the actual Pod and finish the scoped Cloud HTTPS credential check. Live
   provider schema, independent stop/read-back, persistence, CUDA activity and
   CPU receipt verification belong to the separate rental qualification.

## Recovery after a later controller or gateway loss

The running guard uses B-local state and its independent stop timer even when
Cloud, the gateway or laptop disappears. Once real artifacts exist, backups are
under `/var/lib/kpi-cuda-guard/artifacts/`, with hash-named archives and
`latest-artifact.json`. A terminal backup is recognized only after saved size,
SHA-256 and durable atomic storage checks. The absolute deadline still applies
if backup fails; the retained Pod volume is the separate fallback.

When management access is restored, retrieve the selected B archive and its
metadata through the trusted operator path, check its hash/size and use the
bounded unpack/independent CPU verification commands in [START.md](START.md).
A saved archive or simulated stop is not receipt verification or a billing
confirmation. Real volume cleanup/deletion is a later separately authorized
step after results have been retrieved and verified.

## Live lease activation — 2026-10-18

The owner created Pod `qaxhwjd6e1b4bg`; Cloud then verified it through B and
activated the existing unit (enabled, active/running, PID 498115). The provider
reports creation at `2026-10-18T11:13:48.199Z`, giving an immutable lease deadline
of `2026-10-18T13:13:48.199Z` (15:13:48.199 Europe/Amsterdam). The independent
guard begins stop/retry at 13:12:48.199Z, one minute earlier. This is a scheduled
stop mechanism, not evidence that the provider has already accepted a stop.

The authenticated Pod status was `idle`, with fresh guard heartbeat and the exact
lease digest. No start endpoint or proof job was invoked. Provider fields confirm
one NVIDIA L40S, 188 GiB RAM, 16 vCPUs, 90 GB container disk, 10 GB `/workspace`,
USD 1.09/hour and the previously published immutable image digest. NTP is synced.

The actual REST schema required a focused B-only `provider.py` adapter: request
`includeMachine=true` and read `machine.gpuTypeId`; parse the provider's UTC
creation timestamp as well as the previous ISO/numeric fixtures. GPU identity
is obtained from the provider, never inferred from the template. Redirect refusal,
TLS checks, ten-second timeouts, bounded reads and application headers remain.
All 15 control tests passed locally and as the B service user on the state
partition. Existing source versions were backed up before atomic installation.
The CUDA image was not changed or rebuilt; this adapter is guard-host code only.

Storage lease rates are conservative rounded planning inputs from the owner's
reference pricing, not independently returned provider quotes: USD 0.014/hour
active and USD 0.0028/hour stopped, with 24-hour retention. The planned total is
USD 2.2752; actual billing/cleanup remains separate. Live stop/write permissions
are still untested. Cloud still lacks the exact Pod network/credential binding;
no proof start is authorized by this activation task. Actual CUDA qualification
and CPU receipt verification remain subsequent work. Filtered observations and
source hashes are in `evidence/live-guard-2026-10-18/activation.json`.

## Completed CUDA qualification — 2026-10-18

Following separate owner authorization, B started the fixed single attempt with
6,665 seconds remaining. Two segment proofs, two lifts and one join completed in
8.40 seconds (worker total). All five phases recorded process-matched GPU activity.
The independent Cloud CPU verifier checked all five seals against the pinned
PR40 claims and rejected seal/claim mutations, with development mode disabled.
Results and the original hash-checked archive are preserved on B.

The guard stopped the Pod after its terminal-backup grace period. Independent
provider GET read-back confirmed `desiredStatus=EXITED` at 11:24:13Z (13:24:13
Europe/Amsterdam), well before the lease deadline. The unit exited normally.
No lease extension, extra attempt, Cloud secret/domain change, full-classifier
proof, TN10 transaction or volume deletion occurred. The remaining milestone is
the full classifier receipt; this five-partial-proof qualification does not
establish its end-to-end proving cost. Retained volume storage and actual billing
reconciliation remain separate. See `evidence/gpu-qualification-2026-10-18`.

## Complete classifier receipt and independent stop — 2026-10-18

A separately authorized attempt used new Pod `wzozsg2nej95tb`, a separate
`kpi-cuda-full-guard.service` and `/var/lib/kpi-cuda-guard/full-20261018-01`.
The previous qualification lease/Pod/evidence were not reset. The complete
classifier receipt was produced within a 256-second worker job and independently
verified on Cloud CPU, including wrong-image/journal/seal rejection. B retains
that report in `results` and the durable original archive in `artifacts`.
Provider GET confirmed EXITED at 11:49:24Z; the guard exited normally after its
terminal grace. No Cloud secret/domain was added and no proof retry occurred.
Both stopped Pods' 10GB volumes remain; billing/cleanup are separate. See
[FULL-RESULTS.md](FULL-RESULTS.md) for the exact statement, measurements and scope.
