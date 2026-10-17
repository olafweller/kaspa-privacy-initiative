# Local proof-byte classification

Bounded, unfunded follow-up to [PR35](https://github.com/olafweller/kaspa-privacy-initiative/pull/35),
under [ADR-0007](../../docs/adr/0007-local-proof-classification.md).
This is a synthetic arithmetic/preimage relation and proxy balance, not shielded
KAS, native reserve accounting or a complete private-payment circuit.

## Construction

The wallet proves a checked `u64` input = payment + change + fee and one preimage.
Its 96-byte journal binds the canonical intent digest, secret commitment and
value commitment. The intent includes a fixed local network/pool/version, nonce,
wallet image, effect/fee, fee recipient, output commitments and two opaque
128-byte delivery records. Those records are bound synthetic bytes, not tested
note encryption. No economic secrets are sent to the classifier.

The 570-byte intent excludes proof serialization. The full operation is
`intent || proofLength:u32le || canonicalSdkReceipt`. The receipt is generated
after the wallet image is known. The outer guest computes the actual native v1
ID from the operation and canonical native transaction rest preimage. This avoids
requiring the wallet proof to bind to a transaction ID that contains itself.

The sequence is bound to a fixed public fixture commitment over all native IDs
and their order. The classifier journal exposes that commitment, initial proxy
balance, all IDs/outcomes and balance after each operation. A verifier must
compare the commitment with its independently expected fixture. This is **not**
a new L1 acceptance proof: the native shells use nonexistent dummy inputs, no
signature keys and a dedicated unfunded lane. Replacing the fixture commitment
with a real authenticated accepted-lane endpoint remains integration work.

`Receipt::verify_with_context`, with development mode disabled, executes as
ordinary guest computation. There is no `env::verify`, optional proof assumption
or host validity flag. Only a bounded succinct Poseidon2 SDK receipt profile is
allowed: at most 240,000 receipt bytes, eight control-path siblings and supported
raw cycle exponents 14 through 24. Reduced seal/control/path field words are
checked before SDK code that asserts those bounds. Decoding rejects trailing
bytes and requires canonical round-trip serialization.

Outcome codes: 0 accepted; 1 bad intent/envelope; 2 bad receipt encoding/profile;
3 failed cryptographic verification; 4 replay/insufficient current proxy balance.
Malformed **submitted** proof bytes get an outcome. Missing or substituted bytes
against an unchanged fixture endpoint halt authentication. An intent replay is
detected in this finite batch; it is not implemented note/nullifier spentness
across batches or versions.

## Reproduce

Use the pinned native/RISC Zero prerequisites from [PR35](../shielded-design/README.md).
`RISC0_DEV_MODE` must be absent. Build the host and use new directories throughout:

```bash
export CARGO_TARGET_DIR="$PWD/.local/ci-target"
cargo +1.91.0 build --locked --release --manifest-path poc/takeover/Cargo.toml --bin kpi-takeover-host
bash poc/proof-classification/build.sh PROGRAMS_NEW
RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm RAYON_NUM_THREADS=4 \
  .local/ci-target/release/kpi-takeover-host classifier prepare PROGRAMS_NEW FIXTURE_NEW
RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm \
  .local/ci-target/release/kpi-takeover-host classifier profile PROGRAMS_NEW FIXTURE_NEW PROFILE_NEW valid-invalid-valid
```

Use `poc/takeover/measure.py PREFIX COMMAND...` to retain wall time, maximum
individual-process RSS and stdout/stderr without environment/credential values.
The profiler has a 4,294,967,296-cycle research ceiling after the initial
268,435,456-cycle ceiling was reached. A limit error is never a proven invalid
operation. The `prove` command is available but was not run on the measured
880-segment sequence; see [results and the proof-cost blocker](RESULTS.md).
Proof generation is manual;
CI exercises host compilation and deterministic parser/format tests only.

Compare the full proxy payload and native estimated bytes/compute/transient
masses with pinned consensus parameters. The delivery size, fee input shell and
receipt codec are explicit experimental choices, not a chosen production format.
Storage mass and actual fee/admission need authenticated UTXO/node context.

The machine-readable evidence and hash-checked artifact archive are retained in
[evidence](evidence/README.md). `classifier reuse PROGRAMS OLD_WALLETS NEW_FIXTURE`
reverifies and reuses existing wallet receipts without regenerating them.
`classifier check FIXTURE NEW_CHECKS` derives malformed-receipt fixtures and runs
real-seal mutation tests. `classifier verify PROGRAMS FIXTURE PROOFS` is available
to check a later outer receipt against the exact expected root, IDs and outcomes;
no such outer receipt is claimed by this package.
