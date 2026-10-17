# Remote CUDA qualification preparation

Owner authorized merging PR #40 and preparing this package without renting or
deploying a GPU. PR #40 is merged as `e7ea15e8009b8f6ef3aaa34b3cec17fbfc3eb5cd`.
No paid provider call, full-classifier proof, new setup or TN10 transaction is
included. Preparation is locally testable; live deployment remains separate.

## Fixed experiment

Use exactly PR #40's exported segments 24/25, same classifier and five proof API
calls (two segment proofs, two lifts, one join). Pin the independently verified
CPU claim digests and input hashes in the CPU comparison verifier. Returned GPU
proof bytes may differ; claims and verification conditions must match.

Build upstream RISC Zero v3.0.3 commit
`14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6` with its committed Cargo.lock, CUDA and
disabled development mode, targeting Ada compute capability 8.9. Record the new
prover binary hash. Do not change guest, VK, proof fixtures, proof options or
the program image. Prefer one on-demand RunPod L40S / 48 GB, with actual quote,
driver, CPU, RAM, VRAM and availability checked before rental.

One attempt: 120 seconds hardware/setup checks; segment limits 900 seconds each;
lift limits 450 seconds each; join 600 seconds; final CPU comparison 120 seconds.
All phases, first-use initialization and verification share **3,600 seconds**.
Use four available logical CPU IDs, four compute threads and a sampled 12 GiB
summed process RSS ceiling. CUDA reserves large virtual address ranges, so the
CPU experiment's 12 GiB RLIMIT_AS is not applied to the CUDA process. This is an
explicit new GPU memory policy, not a reinterpretation of the CPU measurements.
Record host RSS, virtual memory and GPU process memory separately. Require
evidence of CUDA activity associated with each proof phase's process group;
missing telemetry is an inconclusive qualification, not a speedup claim.

## Transport, lease and retention

Expose only an authenticated fixed-job HTTPS-proxied API: arm guard, start once,
poll status, retrieve completed checkpoints. No arbitrary commands, uploads,
URLs or client-selected programs. Persist a one-attempt marker on the volume;
service restart must not rerun a proof. Use short HTTP responses and polling.

Use an external watchdog on a durable CPU host independent of both Codex Cloud
and the GPU Pod. It reads an absolute lease derived from provider creation time,
maintains an authenticated guard heartbeat, retrieves/checks saved result bytes
and stops the specific Pod at completion or the absolute deadline. A systemd
unit restarts it after failure/reboot. The Pod separately kills proof groups at
their deadlines. Neither helper creates, starts or deletes paid resources.

Do not rely on RunPod's removed stop-after/terminate-after flags. Preserve results
on a volume that survives Pod stop, not ephemeral container disk. Stop compute
even if retrieval fails; keep the volume for recovery. Pod deletion follows only
after external artifact retrieval and independent CPU verification. Stopped volume
storage still bills; document its retention/cleanup and actual charges separately.

Planning: one GPU, at most two hours from provider creation through setup,
diagnostics and retrieval, proposed USD 5 usage ceiling excluding top-up/taxes.
The actual quote must fit that envelope. API/provider failures can defeat a stop;
never advertise a guaranteed billing cap based on untested control code.

## Preparation evidence and remaining live gates

Test fixed-job authentication, duplicate starts, controller disconnect, timeout
group killing, interrupted-state recovery, archive validation, CPU claim binding
and mocked provider stop/read-back without a GPU. Clearly distinguish simulation
from actual CUDA execution. Validate the recipe as far as this CPU-only environment
allows; report compiler/image/network/disk limitations rather than claiming a build.

Before live launch: review the concrete quote and image digest, configure required
Cloud domains/scoped secrets, provision an external watchdog host, confirm its
live heartbeat/lease read-back, validate persistence and complete an authenticated
connection check. CUDA build/runtime, GPU activity, actual provider stop behavior
and costs remain unqualified until exercised on the real rental.
