# Approved 128M outer-proof experiment

Declared before the new qualification executions and proof job, 2026-10-17.
The owner explicitly approved 128,000,000 execution cycles and one real outer
proof attempt with a 3,600-second whole-process-group ceiling, after the existing
full adversarial sequences pass. No extra permission step between these stages.
PR37's original 32M failure and PR38's separate calibration remain unchanged.

## Fixed statement and identity

Reuse the existing wallet circuit, VK, proofs, operation fixtures and unchanged
PR38 classifier. Expected image, retained before this new experiment:
`397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.
Do not derive an expected identity from a receipt. Verify source/artifact hashes
against the published PR38 archive. No guest code change or setup is planned.

## Resources and stop conditions

- Every qualification execution: **128,000,000 cycles / 900 seconds**.
- Build jobs: at most 1,800 seconds each; Rust/Rayon threads 4.
- Exactly one real outer-proof attempt after qualification: **128,000,000
  execution cycles / 3,600 seconds for the whole job**, including all segment
  proving, lifting/joining, compression/resolution and receipt checks/saving.
- CPU affinity restricted to logical CPUs **0,1,2,3**, within the observed
  environment quota of 4 CPU-seconds/second. Set Rayon/OMP thread budgets to 4.
- Memory: **12 GiB per-process virtual address-space hard limit**, inherited by
  children, and **12 GiB summed process-group RSS stop threshold** sampled every
  200 ms. Summed RSS can double-count shared pages; it is not physical cgroup
  accounting. The environment separately enforces a 16 GiB cgroup memory cap.
- On wall/RSS expiry, kill the whole process group and retain the last completed
  stage. Allocation/OS/IPC/cycle failures also stop the attempt. No automatic
  retry, higher budget, easier statement, development mode or fake receipt.
- Log actual affinity, limits, sampled memory peak, maximum individual process
  RSS, whole-job CPU/wall usage, execution cycles/segments, proof stages and any
  concrete failure. A diagnostic sample is not an exact memory maximum.

## Qualification and acceptance

Run all existing full valid-invalid-valid, replay, changed-public-input and
malformed-then-valid fixtures. Retain all five authentication controls and eight
malformed-only controls. Require exact journals from the Arkworks reference and
the original expected main sequence. Resource failures never count as rejection.

Once these pass, produce a real succinct RISC Zero classification receipt with
development mode disabled and no supplied/unresolved assumptions. Verify in a
separate process against the fixed independently expected image and exact
journal: ordered root, initial state, every operation ID/outcome/balance and final
state. Actual cryptographic verification must reject a tampered journal and a
wrong expected image. Artifact consistency alone is not receipt verification.

Local/unfunded only. No new setup, wallet proof generation, private-note circuit,
TN10 transaction, signing key or native payout. Preserve all earlier artifacts.
