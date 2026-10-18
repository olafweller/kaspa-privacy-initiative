# Private-note proof software preparation — 2026-10-18

Software preparation is complete locally. Owner review with Astra in Chat is
pending. **No new private-state receipt, GPU rental, provider action, wallet
setup, guest calibration or TN10 transaction was performed.**

## Completed checks

| Check | Actual result |
|---|---|
| Separate producer / CPU verifier / native verifier builds | Rust 1.91.0, SDK 3.0.3, locked dependencies; all build |
| Focused Rust tests | 4/4 pass: frozen journal/official join, Fake rejection, separate resolve/join identities, resource errors not rejection evidence |
| Remote control / package tests | 21/21 pass, including 4 new private-package checks |
| Genuine archived PR43 receipt | Independent CPU claim/control checks pass; actual native precompile accepts join |
| Archived receipt negative controls | 7/7 actual native precompile rejections; CPU wrong image/control, seal, inclusion and journal mutation checks pass |
| Fixed new program/input/journal | Hash/image checks pass, without guest execution |
| CPU-only container | Build, exact source/binary/package binding, dynamic libraries, authenticated startup and immutable lease binding pass; unconfigured/unguarded starts reject |
| Old evidence | All 174 PR45 files and all 10 PR46 calibration files match their existing manifests |

The old archived receipt has a **167-byte proxy-classifier journal**. It only
qualifies the join/control/precompile integration and cannot demonstrate the new
private state or a 352-byte covenant settlement. The new native fixture's
positive/fifteen-negative campaign awaits the genuine new private receipt.

## Frozen artifacts

The [package identity](evidence/package-identity.json) binds reviewed source,
Cargo lock, exact public inputs, three separately built binaries and the
8,426,154-byte public archive. SHA256:

| Artifact | SHA256 |
|---|---|
| Public package archive | `eee8e803c93f9c87c94bddf368c4f9c577063ab78285a1e9c7cf527b03034a5e` |
| Producer | `8f890c3671b183d93c90070946b6cb510d562371aea29f47211cd48776211da0` |
| Independent CPU verifier | `5c20e03f3630420c3c91ac4118d0849af7c007d0c8e6ddbdf530a2e5ba5a9c83` |
| Native fixture verifier | `bce8e9866c1b0d4c99868bede571206e4ed442d2674a8bab1d6f7474e132fd07` |

Local image ID:
`sha256:37f6282885dbfce1bd97271203e809d2790a6981ceb79a27d29e2e315a4d75fc`.
Published immutable registry reference:
`ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:4bd54b3278b827e721f6633b8643020284820a2c4899a0269c5909a74cde5d09`.
Publication [workflow](https://github.com/olafweller/kaspa-privacy-initiative/actions/runs/39142070653)
succeeded. Anonymous manifest retrieval returned HTTP200 without account
credentials. The exact digest was pulled and CPU-smoke-checked both in CI and
locally; fixed source/binaries/target, libraries, authentication and lease
bindings pass. See [publication evidence](evidence/publication.json),
[published-image checks](evidence/published-image-smoke.json) and the
[deployment configuration](deployment.json). This does not qualify GPU execution.

The extra local pull initially exhausted this Cloud task's disk. Reclaiming only
unused Docker build cache resolved it; the repeated pull and smoke passed.
Repository data and retained experiments were preserved. No proof was attempted
or retried.

The inherited official CUDA prover remains byte-identical to PR43. Local CPU
container checks cannot execute its missing NVIDIA driver or qualify GPU usage.
No CUDA rebuild or new crypto backend was needed.

## What the owner and Astra should review

1. `src/lib.rs`: independently expected program/control/journal, official
   seal-control equality callback, allowed root, no assumptions/dev-mode path.
2. `src/bin/native.rs` and the additive vendored `SuccinctJoin` variant: exact
   relation-domain slots, prior state/lane/covenant/endpoint coupling, full
   1,000,000,000-sompi continuation, native semantic/verifier failure classification.
3. The private remote worker/package: exact frozen bytes, one fixed process,
   <=160M cycles, <=3,600s whole-job timer, no retries, no wallet secrets,
   independent B backup/stop and preserved <=7,200s lease boundary.
4. Artifact/source binding, CPU container checks and clear separation between
   the archived compatibility check and the future genuine private-state receipt.

## Remaining before rental / proof acceptance

Owner Chat review and a separate paid-run release; actual available L40S/storage
quote within the USD5 planning limit; fresh B time/disk/guard check, fresh Pod
lease from real creation, authenticated service binding and enough remaining time.
There is no current Pod or lease for this preparation. B/provider credentials and
services were not inspected or changed.

The future run must return a real Succinct receipt for image `20d8431e…`, the
expected join identity and exact 352-byte journal. Independently run both CPU and
native fixture verifiers, preserve the result on B, observe matching-process CUDA
activity and confirm provider EXITED by readback. Those future results, cost and
duration are not claimed here. Deposit lineage, Bob's exit/payout, canonical TN10
settlement, proved omission and full financial-privacy guarantees remain later
work as documented in [the package](README.md).
