# Proof-phase diagnostics

Local unfunded follow-up to the [PR #39 results](../outer-proof-128m/RESULTS.md).
The owner resumed the [deferred work](../outer-proof-128m/STATUS-HANDOFF.md).
The [predeclared plan](PLAN.md), committed as `47ed371`, preserves the classifier,
SDK, statement, segment configuration and original research outcomes.
The [results](RESULTS.md) retain five verified partial receipts and measured costs;
the complete classifier receipt remains unproduced.

Use the official RISC Zero 3.0.3 APIs demonstrated in
[client.rs](https://github.com/risc0/risc0/blob/v3.0.3/risc0/zkvm/src/host/api/client.rs)
and [tests.rs](https://github.com/risc0/risc0/blob/v3.0.3/risc0/zkvm/src/host/api/tests.rs).
No SDK dependency, guest or cryptographic arithmetic is changed.

`export` first checks PR #39's full qualification reports, fixtures and expected
journal through its existing gate. The supported SDK executes the same program,
saves its actual segment assets and compares retained temporary trace bytes.
The complete session claim is checked against the independently pinned image
and expected journal as **execution output, not a cryptographic proof**.

`segment`, `lift` and `join` each call one supported proof API, save the returned
receipt before verification and check its seal with development mode disabled.
Lift claims must equal their segment claims. Join inputs must have matching
adjacent system-state commitments; the result must match the expected joined
claim. Actual altered seals and claims must fail cryptographic verification.
`verify` repeats checks on the five partial receipts in a separate process.

The mid-session segments are associated with the workload through the trusted
pinned SDK execution/export and hashed assets. Their integrity does **not** prove
membership in a cryptographically composed complete classifier session. In
particular, a pair of middle segments does not establish the initial program
image or full expected journal. No financial privacy, reserve backing, native
settlement or full-classifier receipt is established by these diagnostics.

## Run once

Use the [existing pinned environment](../accelerated-bn254/README.md), with
development mode absent. Reuse public PR #39 fixtures/qualification data; no
proving key, wallet secret, new setup or RPC connection is needed.

```bash
cargo +1.91.0 build --locked --release --manifest-path poc/takeover/Cargo.toml --bin kpi-takeover-host
RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm \
  python3 poc/proof-phase-diagnostics/run.py \
  .local/ci-target/release/kpi-takeover-host PROGRAMS FIXTURES EXPECTATIONS \
  QUALIFICATION OLD_TRACES NEW_ATTEMPT_DIRECTORY
```

The runner's aggregate clock starts before export and includes all phases,
startup and verification. It stops at the first failed/limited stage without
retrying or changing limits. Each phase is an isolated process group under the
same CPU/address-space/RSS limits as PR #39. Completed artifacts survive later
failures; only a completed verification checkpoint counts as verified progress.

Per-phase start/checkpoint/resource files record observed costs. CPU sampling
tracks own process counters by PID/start time without double-counting reaped
children; short-lived process exit transitions can still be missed. Kernel
wait4 accounting is retained separately. RSS sums can double-count shared pages
and miss peaks. Cgroup counter interval differences are environment-wide; missing
pressure interfaces are explicitly recorded as unavailable. Neither logs nor
execution-segment counts are interpreted as completed proofs.

`test_resources.py` exercises failure propagation and whole-process-group timeout
handling with a sleeping descendant, without running any prover. These unit
tests use deterministic auxiliary cgroup-counter files so they also run on CI
hosts with a different cgroup hierarchy; process groups, /proc sampling and
address-space limits remain real. The actual diagnostic runner requires and
records the real declared environment's cgroup interfaces.
