# Accelerated BN254 backend qualification

Local unfunded follow-up to the [PR37 comparison](../groth16-comparison/RESULTS.md).
See the [predeclared limits](PLAN.md), [ADR 0009](../../docs/adr/0009-accelerated-bn254-qualification.md)
and [results](RESULTS.md). No new setup, wallet circuit, privacy protocol or TN10
transaction. The old comparison and its archive remain unchanged.

## Candidate and adapter

`substrate-bn` 0.6.0 from `risc0/paritytech-bn`, resolved commit
`22108fe8c6ea1ebc1358fc4fd6854a6bf46e3509` (documented tag
`v0.6.0-risczero.0`), is tested against the same SDK/r0vm 3.0.3 and custom
guest toolchain as PR37. Both guest dependency locks retain the appropriate
baseline versions; the classifier preserves native `01b532e` and vProgs pins.
The patch resolves `risc0-bigint2` 1.4.14. Our direct-Cargo build advertises
`RISC0_FEATURE_bigint2`, as the normal risc0-build 3.0.x invocation does; actual
compatibility and acceleration are established separately by execution/profile.

The small smoke guest exercises actual field/group/pairing APIs from runtime
input. Its captured pprof has dynamic samples in `sys_bigint2_3/4/5`, not merely
linked symbols. [inspect_profile.py](inspect_profile.py) reads the public pprof
schema with Python's standard library and reports sampled stacks. Those counts
are overlapping executor diagnostics, not syscall invocation counts or proven gas.

The classifier retains PR37's checked canonical Arkworks proof deserialization,
including curve/subgroup checks and exact reserialization. A private conversion
adapter transfers already checked field/point coordinates and canonical public
scalars to substrate-bn. Its raw projective constructors do not perform validation
and must never receive unchecked submitted points. Static key points remain the
exact prevalidated, image-pinned PR37 constants. The standard Groth16 pairing
equation uses existing library arithmetic; no curve, pairing or subgroup routine
is implemented here. Arkworks remains the native differential reference.

## Reproduce

Activate the existing [build environment](../groth16-comparison/README.md), with
development mode absent and fresh output names. No proving parameters are read
by these qualification commands; only the existing public verification data.

```bash
cargo +1.91.0 build --locked --release --manifest-path poc/takeover/Cargo.toml --bin kpi-takeover-host
bash poc/accelerated-bn254/build.sh SETUP_FROM_PR37 NEW_PROGRAMS
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host accelerated-bn254 reference SETUP_FROM_PR37 WALLETS_FROM_PR37 NEW_REFERENCE

# Use the existing process-group watchdog for every actual guest run.
python3 poc/groth16-comparison/run_bounded.py 600 NEW_MEASUREMENT \
  env RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm \
  .local/ci-target/release/kpi-takeover-host accelerated-bn254 profile \
  NEW_PROGRAMS FIXTURES_FROM_PR37 SETUP_FROM_PR37 NEW_RESULT valid-invalid-valid practical
```

The practical command enforces 32M cycles. Only the separately labelled one-off
calibration uses `calibration` and the 900-second watchdog, enforcing 128M cycles.
`profile` supports the unchanged authentication/malformed/replay fixtures with
the practical cap; a resource failure cannot count as an expected rejection.
All complete journals are compared against a native Arkworks-derived reference.
The main journal is additionally checked in a separate process against the
original independently retained expected root/IDs/outcomes/balances.

`pin NEW_PROGRAMS` writes the new image identity before execution. `profile`
requires the compiled program to match that identity. A changed expected image
is rejected before execution. Any future receipt must be verified against this
independently expected image, not an image claimed by the receipt itself.

The actual practical run fails its declared cycle cap; calibration completes.
Therefore **no outer proof is attempted**, and there is no receipt-verification
claim. A future proof experiment needs an explicit practical-budget decision
and full-sequence adversarial qualification first. The original one-hour outer
proof limit remains unchanged. No proof command is exposed in this experiment
because that execution prerequisite was not met.

Native tests: `cargo +1.91.0 test --locked --release --manifest-path poc/takeover/Cargo.toml`
and `cargo +1.91.0 test --locked --release --manifest-path poc/takeover/Cargo.toml -p kpi-accelerated-bn254`.
