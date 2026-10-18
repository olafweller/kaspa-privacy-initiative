# B guard preparation — 2026-10-18

The independent guard is installed and its credential-free host checks pass.
The real guard loop is **disabled/inactive**. No GPU, real RunPod lease, provider
request, proof job, TN10 transaction or host reboot was performed.

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
services remain operational dependencies; live provider connectivity was not
tested in this preparation.

B root and administrators able to obtain B root remain trusted operators. They
can technically read credentials and archives or change/stop the guard. SSH
restrictions and file modes do not protect against a malicious administrator.

## Installed state

Installed source: `0ed4cb0b465f863f03b06ab3ef102234528996bc` on PR #42.
The sole unit change adds `StateDirectoryMode=0750`, preserving the prepared
state permissions at later activation. No guard algorithm or CUDA image changed.

| Location | Contents / permission |
|---|---|
| `/opt/kpi-remote-cuda` | Root-owned `0755`; eight root-owned `0644` Python files |
| Runtime Python files | `common.py`, `watchdog.py`, `make_lease.py` |
| Qualification/support files | `qualify_guard.py`, `test_remote.py`, `service.py`, `worker.py`, `package.py` |
| `/var/lib/kpi-cuda-guard` | `kpi-cuda-guard:kpi-cuda-guard`, `0750`, local ext4 |
| `/etc/systemd/system/kpi-cuda-guard.service` | Root-owned `0644`; verified, loaded, **disabled/inactive**, PID 0 |
| `/etc/kpi-cuda-guard.env` | Root-owned `0600`; comments only, no credentials provisioned |

The dedicated system account is UID 995/GID 986 with `/usr/sbin/nologin`.
As that user, state is writable; code/unit files are not writable and the
root-only environment file is not readable. Systemd reads that file as manager
when the service is activated later. No production `lease.json` exists.

The host reported Python 3.12.3, systemd 255, synchronized time and
85,807,165,440 available bytes (about 79.9 GiB) under `/var/lib` before setup.
All installed source hashes match the installation manifest. There was no
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

## Before a later rental and activation

1. Obtain the separately agreed rental release and actual one-L40S quote,
   availability and storage charges. Preserve one attempt, at most 7,200 seconds
   from provider creation and 3,600 diagnostic seconds. USD 5 remains a planning
   envelope including retention, not a guaranteed provider bill.
2. Provision the RunPod account credential **only on B**, through the owner's
   secure mechanism into the root-owned `0600` environment file. A fresh scoped
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
