# Bounded remote CUDA qualification — preparation

This package prepares one local-equivalent GPU comparison of the five proof
phases retained in [PR #40](https://github.com/olafweller/kaspa-privacy-initiative/pull/40),
merged as `e7ea15e8009b8f6ef3aaa34b3cec17fbfc3eb5cd`. No GPU has been rented,
no provider mutation or CUDA execution is claimed by this preparation. The
operator's later read-only provider GET is recorded in [B-GUARD.md](B-GUARD.md).
Follow [START.md](START.md) before a later paid deployment.

The independent guard is installed on the former A1 role-B VPS,
`vmi3641034.contaboserver.net`, separately from the TN10/gateway host. Its unit is
disabled/inactive, with no real lease. The operator has provisioned the account
credential on B only; its value was not inspected. The separate-process
recovery rehearsal and all fourteen control tests pass as the dedicated service
user on B's actual state filesystem. Existing trial data/services are preserved.
See [B host preparation](B-GUARD.md) for evidence, permissions and remaining gates.

## Fixed question and acceptance conditions

Can the official CUDA prover produce **the same two segment proofs, two lifts
and one join** as PR #40 within the declared resources? Preserve its classifier
image, input bytes, exported segment traces, proof options and CPU claim digests.
The classifier image is
`397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.
The different prover binary has its own recorded hash. Proof bytes need not match.

1. Build the pinned upstream CUDA prover, with development mode disabled.
2. Establish actual use of the single L40S by each proof phase's process group.
3. Save every receipt immediately; retain partial results on failure.
4. Verify all five receipts cryptographically, mutation controls, fixed CPU claims
   and join continuity with the existing CPU verifier in a separate process.
   An explicit incomplete-run command verifies available receipts while reporting
   their count; it cannot satisfy the strict five-receipt comparison.
5. Retrieve the results and repeat that comparison independently on the CPU host.
6. Record initialization, per-phase wall time, CPU time, sampled host RSS/virtual
   memory and VRAM, actual rental duration, stop confirmation and provider charges.

These remain **partial proofs of two middle segments**, not a complete classifier
receipt binding the program image to its final journal. The comparison pins the
trusted PR #40 export and CPU claims. There is no new wallet setup, full private-note
circuit, private witness upload, full-classifier attempt or TN10 transaction.

## Implementation and limits

| Component | Responsibility |
|---|---|
| `package.py` | Check all 107 original archive members; prepare public inputs, CPU baseline and pinned policy |
| `build_cuda.sh`, `Dockerfile`, `build_image.sh` | Build RISC Zero 3.0.3 at its exact source revision for Ada `sm_89`; assemble service image |
| `service.py`, `worker.py` | Authenticated fixed HTTPS job, persistent one-attempt marker, bounded process groups and checkpoints |
| `watchdog.py`, `kpi-cuda-guard.service` | Independent durable-host heartbeat, artifact backup and provider stop/read-back |
| `make_lease.py` | Read actual provider creation time, quote and resources; never create/start a Pod |
| `control.py` | Short HTTPS start/status/fetch requests; independent CPU verification of downloaded results |
| `check_cpu_compare.py`, `test_remote.py` | Real CPU receipt checks and explicitly simulated transport/watchdog tests |
| `check_image.py` | CPU-only service startup, source/binary hashes, driver dependency, authentication and lease binding; no proof job |

One GPU, one attempt; **3,600 seconds aggregate diagnostic time**, including
first-use CUDA initialization, all five APIs and final comparison. Phase ceilings:
hardware preflight 120 seconds, segment 900 each, lift 450 each, join 600, CPU
comparison 120. The aggregate deadline wins. Four logical CPUs and four compute
threads; sampled summed process RSS stops above 12 GiB. Unlike the old CPU run,
there is no virtual-address-space limit: CUDA reserves large virtual ranges.
Record this explicit policy difference when comparing measurements. Hardware
metadata also captures available CPU affinity and visible cgroup-v2 CPU/memory
limits; unsupported cgroup fields are reported as null, not invented. No budget is
automatically increased and a resource failure is not a successful proof result.

Prefer one RunPod on-demand L40S with 48 GB VRAM, at least four vCPUs and 32 GB
host RAM, 90 GB container disk and a 10 GB persistent volume mounted at
`/workspace`. The provider mount path and an observed Linux mount must match
before proof work; live persistence still needs qualification. The absolute lease
ends at most two hours after **provider creation**, not service startup. The guard
requests stop one minute early using a timer independent of GPU status/download
requests, or after a terminal checkpoint has been backed up
and a 60-second retrieval grace has elapsed. Pod-local process deadlines remain
effective if the controller disconnects. The external guard survives Codex loss
and GPU-container loss, provided its own host and provider API remain available.

The proposed USD 5 usage envelope excludes credit top-up and taxes. Both active
storage and up to 24 hours of stopped-volume retention are counted by the lease
validator. It is a planning constraint, **not a guaranteed billing cap**: a provider
or watchdog failure can prevent stop. Stopping compute is not deleting storage.
Remove the Pod/volume only after external backup and CPU verification; reconcile
the actual bill. The owner-supplied USD 1.09/hour reference must be replaced by
the actual quote before rental. At that reference, two hours of compute plus
100 GB active storage and 24 hours of 10 GB stopped storage is about USD 2.28,
using USD 0.10/GB-month active and USD 0.20/GB-month stopped, 720 hours/month.
This is not a measured proving cost or current availability claim.

## Trust and unqualified live behavior

Only public research assets go to the GPU. The GPU operator can withhold or alter
results; independent receipt verification protects the accepted claim, not
availability, billing or host telemetry. Never extend this setup to private
wallet witnesses without a separate privacy design. The provider account key
stays on the independent watchdog host; Codex and the GPU receive only the
scoped service token. Provider responses may contain secrets: helpers serialize
only selected lease/status fields, not full Pod responses.

The actual RunPod proxy, response schema, Pod stop, persistence, driver/runtime,
CUDA activity and VRAM are untested until the live rental. NVML may report host
PIDs while `/proc` exposes container PIDs. The worker requires matching process
evidence; a mismatch is an inconclusive qualification, not a CUDA speedup.
First-use kernel JIT is included in the first proof phase and is not separately
timed; server/hardware startup is separately recorded.

See [source pins](UPSTREAM.md), [adversarial review](ADVERSARIAL-REVIEW.md),
[preparation evidence](PREPARATION.md) and the [authorized plan](PLAN.md).
