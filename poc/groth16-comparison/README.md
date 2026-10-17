# Specialized BN254/Groth16 wallet comparison

Local unfunded follow-up to [PR36](../proof-classification/RESULTS.md), under
[ADR-0008](../../docs/adr/0008-specialized-groth16-comparison.md). This is a
specialized wallet circuit, **not** a Groth16 wrapper around a RISC Zero receipt.
It is not a complete privacy circuit or an accepted TN10 settlement experiment.

## Identical small predicate

The circuit retains SHA-256(secret), SHA-256(the four little-endian u64 values),
input > 0, exact input = pay + change + fee, explicit 64-bit ranges and the
binding of public pay/fee fields. It also computes SHA-256 of the complete
570-byte canonical intent with the original domain tag. The same 96-byte journal
is packed into four BN254 scalar public inputs. Other intent fields, including
the opaque delivery bytes, cannot be replaced without changing that statement.

Native payloads still use intent || u32 proof length || actual proof bytes.
The identity field now contains a domain-separated hash of the circuit-specific
VK. The circuit shape is independent of that hash, avoiding a setup/intent
circularity. Native v1 IDs bind full proof bytes; the same local fixed ordered
fixture, proxy balance and deterministic outcomes are retained.

Arkworks 0.5 performs checked canonical point/subgroup decoding and actual
Groth16 verification inside the outer RISC Zero guest. The exact VK and prepared
VK are compiled into that program. Preparing parameters is a public deterministic
optimization; the host recomputes them from VK and requires byte equality.
The guest loads those immutable, prechecked constants without repeating their
subgroup validation. Submitted operation proofs always retain checked canonical
curve/subgroup decoding. The program image binds the exact parameter bytes.
There are no host validity flags or optional recursive assumptions.

## Setup and retained data

This is a one-party research setup generated with fresh OS entropy, not a
production ceremony or independent security audit. No RNG seed or trapdoor
scalars are serialized. Public proving parameters are kept locally and hashed;
the published verification artifacts contain the small VK/prepared VK and proofs.
Reproduction with a fresh setup creates a different key/program identity.

Synthetic secret/value witnesses are deliberately public test fixtures. Real
wallet witnesses would remain local; the classifier receives only public intents,
proofs and native transaction preimages. Opaque 128-byte delivery records do not
establish recipient encryption/spendability. No note membership, authorization,
nullifier, actual native backing/payout or independent recovery is implemented.

## Budget

The agreed classifier execution limit is **32,000,000 cycles** for the complete
three-operation sequence. The outer proof-production limit is **3,600 seconds**.
Profile first; a resource failure never counts as an authenticated rejection.
`run_bounded.py` measures and terminates the whole process group at its wall
budget. Setup and wallet measurements use their own 1,800-second ceilings.
The outer proof is attempted only after a successful bounded profile.

## Reproduce

Use the existing [pinned build/toolchain prerequisites](../proof-classification/README.md).
Keep development mode absent and use new directories:

```bash
export CARGO_TARGET_DIR="$PWD/.local/ci-target"
cargo +1.91.0 build --locked --release --manifest-path poc/takeover/Cargo.toml --bin kpi-takeover-host
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host groth16 setup SETUP_NEW
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host groth16 wallet SETUP_NEW WALLETS_NEW
bash poc/groth16-comparison/build.sh SETUP_NEW PROGRAMS_NEW
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host groth16 fixtures SETUP_NEW WALLETS_NEW FIXTURES_NEW
RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm \
  .local/ci-target/release/kpi-takeover-host groth16 profile PROGRAMS_NEW FIXTURES_NEW PROFILE_NEW valid-invalid-valid
```

Only after the profile fits, use `groth16 prove PROGRAMS FIXTURES PROOFS_NEW`
through the 3,600-second process-group runner, then invoke `groth16 verify` in
a separate process against the independently retained expected fixture. The
verifier compares the root, every native ID/outcome and final counter, and rejects
a changed journal. This is independent software invocation, not an independent
human audit or actual L1 acceptance/settlement proof.
