# Approved 128M outer classification proof

**Owner-directed pause, 2026-10-17:** close PR #39 as the completed bounded
research result and resume only on a new owner instruction. See the
[pause handoff](STATUS-HANDOFF.md) for preserved evidence and the deferred next step.

Local unfunded successor to [PR38](../accelerated-bn254/RESULTS.md), following the
[predeclared plan](PLAN.md) and [ADR 0010](../../docs/adr/0010-approved-128m-outer-proof.md).
The owner explicitly approved full 128M adversarial qualification followed
directly by one actual outer-proof attempt with a 3,600-second whole-job limit.
Historical 32M results and the old 128M calibration are preserved unchanged.
The [results](RESULTS.md) record all 24 passing executions and the single proof
attempt's wall-limit stop without a receipt.
The [evidence manifest and public archive](evidence/README.md) retain exact
inputs, expectations, resources and the failed attempt.

## Retained statement and authentication

The wallet circuit/VK, two genuine wallet proofs, 702-byte operations, all native
IDs/ordered fixtures and guest classifier are unchanged. The required image is
`397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.
The host compares this independent expected identity against both the retained
identity file and the SDK-computed program image. Qualification verifies input
and program bytes against the published PR38 archive. No new setup is invoked.

`prepare` creates independent expectations before qualification/proving. The main
journal comes from the original expected root/IDs/outcomes/balances; all other
journals are derived from the retained Arkworks reference and checked against
explicit expected outcome/state vectors. All 24 existing full and narrow cases
must pass. Resource/IPC failure cannot stand in for a successful rejection.

`prove` checks those qualification reports and exact input/journal hashes, then
profiles and proves the whole valid-invalid-valid sequence. The SDK requests a
real **succinct** RISC Zero receipt, so required segment proving, lifting/joining
and compression/resolution are part of the same bounded process group. No
receipt wrapping of the wallet proofs, supplied assumptions or fake/development
receipt is used. The guest still executes actual BN254 verification itself.

`verify` runs in a separate process without needing the program/prover or wallet
proving parameters. It uses the independently expected image and exact expected
journal, verifies the actual succinct seal with development mode disabled,
requires successful exit and no unresolved assumptions, and invokes actual
receipt verification on a wrong expected image and five journal mutations.
Root, initial balance, operation ID, outcome and final balance are all covered.

## Resource enforcement

[run_resources.py](run_resources.py) confines children to logical CPUs 0–3 and
sets four Rayon/OMP/OpenBLAS threads. Each process inherits a hard 12 GiB virtual
address-space ceiling. A 200 ms process-group sampler enforces a separate 12 GiB
summed-RSS stop threshold. The host's cgroup separately has a 16 GiB cap and a
4-CPU quota. Summed RSS can count shared pages twice and samples can miss brief
peaks; the report distinguishes it from the kernel maximum individual-process
RSS and from physical cgroup usage.

[monitor_cpu.py](monitor_cpu.py) additionally retains cumulative `/proc` CPU
counters for the proof process group. A hard-killed parent may never reap its
prover child, so the parent's final `wait4` usage can omit that child's work.
The sampled cumulative counters and kernel accounting are reported separately;
sampling can miss exit transitions and must not be represented as exact totals.

The outer job gets 3,600 seconds total; every qualifying execution gets 900
seconds and 128M cycles. On a stop condition the runner kills the whole process
group and records wall/CPU/memory metrics. The host retains profile/prover-start/
error/completion files and the prover log records available completed stages.
There is no automatic retry or budget increase. The separate verifier is outside
proof production; the proof job already verifies and saves its completed receipt
before its own clock ends.

## Reproduce

Use the existing [pinned build environment](../accelerated-bn254/README.md), with
development mode absent. Public artifacts are sufficient; no proving key or
wallet secret is required. Use fresh output directories:

```bash
cargo +1.91.0 build --locked --release --manifest-path poc/takeover/Cargo.toml --bin kpi-takeover-host
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host outer-proof-128m prepare PROGRAMS FIXTURES SETUP NEW_EXPECTATIONS
RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm \
  python3 poc/outer-proof-128m/qualify.py PROGRAMS FIXTURES SETUP NEW_EXPECTATIONS NEW_QUALIFICATION

# Exactly one call, only after successful qualification.
python3 poc/outer-proof-128m/run_resources.py 3600 NEW_JOB \
  env RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm RUST_LOG=info \
  .local/ci-target/release/kpi-takeover-host outer-proof-128m prove \
  PROGRAMS FIXTURES NEW_EXPECTATIONS NEW_QUALIFICATION NEW_PROOF

# Only if the proof job produced the requested completed receipt.
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host outer-proof-128m verify \
  NEW_EXPECTATIONS NEW_PROOF NEW_VERIFICATION
```

This proves, if successful, a small synthetic value/preimage/full-intent predicate
and fixed local ordered classification. It does not add private-note ownership,
membership, nullifiers, authenticated note encryption, actual KAS backing,
independent recovery, accepted L1 ordering or native settlement. No new TN10
transaction or funded privacy trial is included.
