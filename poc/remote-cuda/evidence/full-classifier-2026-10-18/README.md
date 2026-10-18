# Complete full-classifier GPU receipt evidence

One owner-authorized L40S attempt completed; the receipt was independently
verified on CPU and the provider stop was confirmed. See
[the measured results and limitations](../../FULL-RESULTS.md).

- `classifier-receipt.bin`: complete genuine succinct RISC Zero receipt,
  223,560 bytes, SHA256
  `9e68cda38325f673d00734433a1bd7b127fab20ac88f16aad948f2bec1492186`.
- `full-gpu-artifacts.tar.gz`: original durable B backup, 899,488 bytes,
  SHA256 `6bfb8b8851d6188ac7822ebc08fa309886c13da73f175bb70c8a27f275677969`.
  Includes all 116 returned public inputs/qualification files, profile,
  candidate/final receipt, journal, proof stats, hardware, process telemetry,
  phase stdout/stderr, resource report and completion markers.
- `independent-verification.json`: real separate CPU receipt verification;
  fixed image/exact journal, no unresolved assumptions, development mode off,
  wrong-image/five journal mutations/corrupted-seal rejection.
- `expected-statement.json`: independently retained full decoded journal.
- `measurements.json`: allocation, immutable image, proof/job times, resources,
  cycles, prover/verifier hashes and billing/retention limitations.
- `provider-stop-observation.json`: separate provider GET observed EXITED and
  the guard's stop confirmation; actual settled charges are unavailable.
- `artifact-manifest.json`: sizes/hashes for the public evidence files.

Reproduce with the trusted source/CPU verifier and fixed prepared input package:

```bash
python3 poc/remote-cuda/full_package.py NEW_TRUSTED_PACKAGE
python3 poc/remote-cuda/control.py unpack poc/remote-cuda/evidence/full-classifier-2026-10-18/full-gpu-artifacts.tar.gz 6bfb8b8851d6188ac7822ebc08fa309886c13da73f175bb70c8a27f275677969 NEW_RETURNED_DIRECTORY
python3 poc/remote-cuda/full_control.py verify NEW_TRUSTED_PACKAGE NEW_RETURNED_DIRECTORY TRUSTED_CPU_HOST EXPECTED_CPU_HOST_SHA256
```

The verifier hash is checked before execution. The recorded CPU verifier was
built from `df497f2` with the pinned Cargo lock/toolchain. A locally rebuilt
trusted verifier may have a different binary hash; independently establish that
local hash rather than deriving it from an untrusted returned artifact. Do not
set RISC0_DEV_MODE or substitute a GPU-written success report for CPU verification.
