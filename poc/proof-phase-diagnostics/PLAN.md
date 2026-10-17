# Bounded proof-phase diagnostics

Owner resumed the deferred PR #39 follow-up on 2026-10-17. This plan is committed
before any new guest execution or proof diagnostic. Starting point: merged
`ed7aa2b2a2d900315fe53ca0f25b9dde0eee80a9`.

Reuse the unchanged wallet circuit, VK, wallet proofs, fixtures, expected journal,
classifier image `397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`,
RISC Zero SDK/r0vm 3.0.3 and segment limit po2=20. No full-proof retry, new setup,
private-note implementation, funding or TN10 operation is included.

## Selection and stop limits

The retained PR #39 logs place the first pairing between user cycles 16,090,400
and 40,494,407. Select **zero-based segments 24 and 25** from the same full
valid-invalid-valid execution. Before proving, require both to have po2=20 and
their cumulative user-cycle intervals to lie within that pairing interval.
Keep all segment indices, user-cycle boundaries, serialized asset hashes and the
complete execution journal. Record the session claim and original program/input
hashes. These execution assets are not proofs.

| Step, in execution order | Maximum wall seconds |
| --- | ---: |
| Export unchanged full execution / inspect retained trace matches | 120 |
| Prove segment 24 and save / verify returned receipt | 900 |
| Lift segment 24 and save / verify returned receipt | 450 |
| Prove segment 25 and save / verify returned receipt | 900 |
| Lift segment 25 and save / verify returned receipt | 450 |
| Join adjacent lifted receipts and save / verify result | 600 |
| Separate-process verification of all retained receipts | 120 |

The **aggregate maximum is 3,600 wall seconds**, including execution export,
startup, verification and gaps between stages. The per-step sum is 3,540 seconds,
leaving 60 seconds for orchestration. Each step uses the lesser of its table
limit and remaining aggregate time. Stop the branch at the first failure or
resource timeout; later steps are marked not attempted. No retry or budget
transfer raises a declared per-step limit. A failed stage never erases an already
saved artifact, and unverified artifacts do not count as verified progress.

Use CPU affinity 0-3, four Rayon/OMP/OpenBLAS threads, hard 12 GiB per-process
address-space limit and sampled 12 GiB summed group-RSS stop threshold, as in
PR #39. Record observed CPU quota and cgroup memory cap. Each phase runs in an
isolated process group, killed as a whole on termination. Sample own process CPU
counters keyed by PID/start time; retain wait4 usage separately. Record cgroup
memory events and CPU/memory pressure interval differences, not lifetime counters
as if attributable to this job. Sampling and environment-wide attribution limits
remain explicit.

## Proof checks and interpretation

Inspect the known prior proof-output and temporary segment locations. The retained
`/tmp/.tmpdSt2cX/*.bincode` files are candidate execution traces, not reusable
proofs; compare their hashes with fresh SDK-exported assets. Only a genuine,
cryptographically verified compatible receipt counts as existing proof progress.

Use the supported SDK `ApiClient::execute`, `prove_segment`, `lift` and `join`
APIs. No custom proof/curve arithmetic. Persist each returned receipt immediately,
then verify its seal with development mode disabled. Match lift claims to their
segment claims and join claims to both inputs, requiring adjacent state continuity.
Retain exact claim digests and seal-corruption rejection checks, and repeat
verification in a separate process when the prerequisite stages finish.

The middle-segment receipts prove partial VM transitions, not the initial image,
complete ordered journal or full classifier. Their workload association is recorded
through the trusted pinned SDK execution/export and asset hashes; no full-session
cryptographic composition is claimed. Preserve the full succinct receipt as the
open milestone. Keep the original 32M failure, calibration and one-hour PR #39
timeout intact. Report measured phase costs separately from any extrapolation,
including fresh-process initialization and variation between segments.

## Pre-proof integration correction

The first export completed, but a host file lookup failed before its first
`prove_segment` call or started checkpoint: SDK `AssetRequest::Path` exports
`segment-N`, whereas the adapter expected `N.bincode`. Preserve that failure.
Normalize the already exported, hash-checked bytes into explicit adapter paths;
do not execute the guest again. One explicit guarded `--repair-preflight`
continuation may proceed, charging file-lookup time to the same segment budget
and all inspection/build/repair time to the **original** 3,600-second clock.
No proof API has yet run; no proof/resource failure may be retried through this
exception. The continuation itself has no second repair path.
