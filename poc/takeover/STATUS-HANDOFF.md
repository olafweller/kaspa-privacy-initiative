# Paused handoff: PR merges and recursive takeover preparation

> Historical checkpoint from the previous task. The owner resumed local
> development/review in this task on 2026-10-17, stopping before new TN10
> transactions. See the [current README](README.md) and
> [local review](LOCAL-REVIEW.md). The original archive remains unchanged;
> pause-time facts below are not statements of the current branch/test status.

**Paused by the owner, 2026-10-17 06:56 UTC. Do not resume execution without a
new instruction.** The pause permits repository/log inspection and preservation
only. No new experiment, proof generation, funding or transaction was performed
while producing this handoff. Repository documents remain English; communication
with the owner remains Dutch.

## Repository and confirmed PR status

- Workspace: `/workspace/kaspa-privacy-initiative`.
- Local branch: `codex/long-gap-takeover`.
- HEAD: `773b1edfcbb1d5e76079895a231d02aa2eded365`, a merge incorporating main.
- Last fetched `origin/main`: `335fbca8103e28af9ba15aedfd56d22350b1cbd2`.
  HEAD's tracked tree equals that fetched main tree; the takeover additions are
  untracked local files. There were no modified tracked files at pause.
- [PR31](https://github.com/olafweller/kaspa-privacy-initiative/pull/31) is confirmed
  **merged**, 2026-10-17 01:17:00 UTC, squash commit
  `0167b04fd3598b30b470f92f458c3f1ffe19f404`, reviewed head
  `68100588133175442dab2b0a56ed6d784dc015ea`.
- [PR32](https://github.com/olafweller/kaspa-privacy-initiative/pull/32) is confirmed
  **merged**, 2026-10-17 01:20:54 UTC, squash commit
  `335fbca8103e28af9ba15aedfd56d22350b1cbd2`, reviewed head
  `d52ce08a10f78f0441a9a265fb0c4a427239296b`.
- GitHub metadata was queried again read-only at pause. PR32 had first been
  retargeted to main; the PR31 squash conflicts were resolved retaining the exact
  reviewed `aeb4828` content tree. Final PR32 Code checks run `38990211428` and
  Documentation checks run `38990211458` succeeded before merging. PR31's
  corresponding successful runs were `38982493088` and `38982493347`.
- The takeover branch/additions have **not been pushed or committed**. No new
  takeover PR exists. Original PR branches and historical source commits remain.

The previous handoffs' statements that PR31/32 are drafts/not merged describe
their earlier checkpoint and are superseded by the confirmations above.

## Preserved local work

All new work is under `poc/takeover/` plus
`docs/adr/0005-long-gap-recursive-takeover.md`; it remains work in progress.

- [PLAN](PLAN.md) and ADR-0005: proposed active-lane long-gap experiment, scope
  and explicit exclusion of true expiry, pruning, privacy and independent nodes.
- `common/`: adapts the retained PR32 public account action relation to one coarse
  SMT resource and reference transaction journals. This is serial public state,
  not a new general lane/scheduler subsystem.
- `transaction-guest/`: small transaction guest using that action adapter.
- `batch-guest/`: reference per-batch verifier plus an in-guest rejection of
  `lane_expired`. `aggregate-guest/` uses the reference aggregate entrypoint.
- `host/src/main.rs`: executed synthetic compatibility gate, then extended with
  a finite public-bundle proving command. The extended bundle command is compiled
  but has **not run**.
- `host/src/bin/prepare.rs`: public capture-to-batch preparation, reusing PR31's
  native validator. Compiled, **not executed or qualified**.
- `host/src/bin/build.rs`: adapted PR32 native builder with actual recursive guest
  identities and the new state root. Compiled, **not executed on the VPS**.
- `vendor/covenant/`: reference resolve-pinned covenant with the recorded API
  compatibility adaptation only. Four production/two test references to the
  removed `EngineFlags.covenants_enabled` field become defaults in Kaspa 2.1.0.
  The official fixed resolve control ID is retained; old funded instances and
  PR31's separate lift-pinned source are untouched.
- Four lockfiles pin the compatible Kaspa source; `measure.py` records finite
  process costs without environment variables.

Existing logs/artifacts are preserved at
`/workspace/kaspa-privacy-initiative/.local/takeover/`. This ignored directory is
not published by Git. `pause-status.json` records the pause observations and
`pause-inventory.json` inventories the source/log/artifact bytes available at
pause. A separate local archive under `/workspace/handoffs/` preserves this work
and these public artifacts, including this handoff. Do not assume a clone of
main contains either the untracked sources or these ignored artifacts.

## What actually passed

These are observations from **existing logs**, not tests rerun during the pause.

1. Batch guest build: `build-batch.log`, finished in 25.19 seconds. Aggregate
   guest build: `build-aggregate.log`, finished in 3.41 seconds. Transaction guest
   build: `build-transaction4.log`, finished in 6.39 seconds. Wrapped programs
   remain in `.local/takeover/{transaction,batch,aggregate}.program.bin`.
2. `gate-02/complete.json` and measured exit code 0 establish a **real synthetic
   empty-batch composition gate**: one batch proof, then an aggregate proof using
   that batch receipt as its one assumption. SDK receipt/journal verification and
   the local native Kaspa script-engine check passed. Development mode was absent.
3. Missing inner receipt was rejected during aggregate execution, as asserted by
   the gate. Its detailed error text was not separately retained; the completion
   flag/exit code and executed source record the check. This is an execution-layer
   rejection, not a TN10 transaction rejection.
4. Gate batch: image
   `fac3707f1e6bf1c5363a2b968545bc5c361934a48a376b8083d4c14247a61f70`,
   one 65,536-cycle segment, 273-byte journal, 223,772-byte receipt, 58.655 seconds.
   Gate aggregate: image
   `14bedaace438fe568000405a947909bcdd7df82e8458bc3a87e6d85bdfdab166`,
   one 131,072-cycle segment, 352-byte journal, 223,930-byte receipt, 120.071 seconds.
   Its control ID matches reference resolve:
   `53a7b23d07f99e5d5685e85874f5181e8486aa267a0ae607ffe9ba47c8bdda4a`.
5. Whole gate: 179.001 seconds, maximum individual-process RSS 1,495,860 KiB;
   `gate-02-run.resources.json`. Local script usage was 25,006,417 units.
6. The latest expanded host/common build completed successfully in 11.42 seconds:
   `build-pipeline.log`. This includes prepare/build/bundle code. Formatting was
   applied to the two local packages. No unit/security regression suite or CI for
   this new work has run. The latest tree is not declared secure or trial-ready.

The native engine check used a **synthetic local accessor** supplying the derived
commitment. It is neither a live TN10 anchor check nor actual settlement. The
empty batch contains **zero user transactions**; it does not establish the full
transaction-proof → batch-proof connection. No new transaction-guest proof,
deposit, withdrawal, long-gap takeover or native payout was performed.

The gate's exact executable was retained as `gate-02/executed-host`, SHA-256
`dfd3057c707f303d8e0ac02a65efdc846f71a7494addf4d1562883f79eab04c8`.
`executed-main.rs` retains the gate-only source before the bundle extension;
`execution-source.json` was captured after the gate and contains snapshot hashes.
It is not a committed build manifest or independently established reproducible
source-to-binary provenance. The current source/executable has since changed;
do not equate the latest bundle runner with the executed gate binary.

## Failed attempts and corrections

Retain all listed logs. Build/start failures are **not protocol rejections**.

| Existing log | Observed failure / subsequent change |
| --- | --- |
| `build-host.log`, `build-host2.log` | Offline resolution lacked `workflow-dom`; a newly introduced dependency followed current Kaspa master. |
| `pin-update.log` | Requested package was absent from the current lockfile; no successful pin update in that attempt. |
| `build-host3.log` | Four obsolete `covenants_enabled` API fields prevented compiling the unadapted reference covenant. A separate compatibility copy now retains resolve and uses the current API. |
| `build-host4.log` | Multiple nested workspace roots; explicit workspace exclusions added. |
| `build-host5.log` | Dependency resolution moved to master `f7d78773`, requiring Rust 1.95. Re-pinned to `01b532e8` with Rust 1.91.0; `pin-final.log` records the change. |
| `build-host6.log` | Missing explicit `vprogs_core_types` / `vprogs_l1_utils` dependencies in the adapted builder; added before successful builds 7/8. |
| `build-transaction.log` | An unintended default feature pulled OS-dependent `errno` into the guest; disabled default features on the extra Kaspa hashes dependency. |
| `build-transaction2.log`, `build-transaction3.log` | Attempted to call private ExitSink methods; replaced with the public StandardSpk encoder and canonical amount encoding. Build 4 succeeded. |
| `gate-01-resources.log` | `/usr/bin/time` unavailable; the test executable did not start. Added the Python measurement wrapper. |
| `gate-01-run.stderr.log` | Gate chose the wrong JSON nesting for a bare lane input; exited before proof generation. Fixed before the successful fresh `gate-02`. |

An earlier documentation-link check found the copied covenant provenance still
linked absent `live19.patch`. The provenance was rewritten for the resolve copy;
the complete docs check has **not been rerun**. A final adversarial second-pass
review, source/artifact reconciliation, security tests and publication remain.

## Processes, VPS and credentials

Read-only Cloud `ps` at pause lists **no project/proving/build/measurement/admin
terminal processes**. The successful gate and latest build are finished.

No takeover-stage VPS unit, wallet, funding or transaction was started. The only
VPS action in this phase was an earlier read-only check: uid 0, `kpi-tn10` active,
Node 22.22.3, about 11.7 GiB available RAM and 771 GiB free disk. That earlier
snapshot is not a fresh process check at pause. The VPS process list/node status
was deliberately not queried again for this handoff. The normal node is expected
to remain running; do not stop or restart it. Historical PR32 finite jobs were
already reported complete in their own retained results.

Use the existing root admin WSS connection and localhost TN10 RPC only when work
is explicitly resumed. `TN10_RPC_TOKEN` is a configured secret; wallet keys remain
only on the VPS. No credentials or actual wallet-key contents were read, copied
or included in this handoff/archive.

## First unfinished step, after explicit resumption

Review and exercise the new prepare/bundle/transaction adapter using **retained
public captures first**. Verify the coarse-resource wire format, prior-state
binding, exact journals, authorization/no-op behavior, missing/wrong inner
receipts and state/tip continuity. Reconcile actual executed source/binary hashes
and complete adversarial review before treating the new path as qualified.

Only subsequently consider a fresh small TN10 instance, confirmed deposit,
original-executor stop, a measured gap greater than 100 blue scores while still
natively active, clean public replay, new authorized withdrawal, real recursive
settlement and payout. That is the planned experiment, **not an achieved result**.
There is no transaction or proof job to resume and no reason to rebroadcast any
old trial. The existing six-test-KAS PR32 balance has not been recovered or moved.

True lane expiry, independent human/operator or node corroboration, pruning/data
loss recovery, privacy and mandatory progress remain open. The displayed
cybersecurity warning supplies no specific triggering operation; its cause was
not established. No filter bypass was attempted. Preserve work and stay paused.
