# Shielded native-KAS first work package

Local design/model/compatibility work authorized after PR33 and merged PR34.
**This is not a working shielded TN10 payment protocol.** It delivers a proposed
statement, visible/private data contract, executable economic/role model,
adversarial tests, a real local proof-composition measurement and one conditional
funded-trial proposal. No new TN10 transaction or earlier wallet key is used.

Start with [RFC-0002](../../docs/rfc/0002-shielded-payment.md),
[visibility](VISIBILITY.md), [source/reuse decisions](SOURCES.md),
[measured results](RESULTS.md) and the [TN10 proposal](TN10-PROPOSAL.md).
[ADR-0006](../../docs/adr/0006-shielded-design-local-work-package.md) accepts only
this bounded local experiment. Production construction and funded trial remain
review decisions; RFC-0001 and all security invariants stay open.

## What is implemented

- `model.py`: native principal plus funded/uncredited deposit claims, opaque notes,
  local sender/recipient roles, current nullifiers with historical membership
  anchors, sender change, unpaid exit/fee claims, explicit external permission-rent
  funding and exact payout/refund checks. Every supported funded deposit can be
  credited or recovered by its owner exactly once in the model.
- `test_model.py`: adversarial examples plus 64 reproducible conservation vectors.
  Failures change rejection records, not economic state. Two separately valid
  proofs sharing an old anchor cannot both spend a note.
- `compat`: synthetic preimage/value wallet guest and a pinned adapter reusing the
  existing public-account relation; a local host composes real receipts through
  reference batch/aggregate guests and the native script engine. No new covenant
  is broadcast or funded. The private payment circuit itself is unimplemented.

The proof registry in the Python model is an **ideal functionality**, not a
cryptographic verifier or a safe host validity flag. Model SHA/HMAC IDs are not
an accepted commitment/nullifier design. PyNaCl sealed boxes and authenticated
receiving addresses exercise discovery/role separation with public test fixtures;
no production note/key/encryption format is selected. General reorg, pruning,
independent recovery, migration and practical anonymity are not model results.

## Repeat the model

From the repository root:

```bash
python3 -m pip install --target .local/shielded-design/python -r poc/shielded-design/requirements.txt
PYTHONPATH=.local/shielded-design/python python3 -m unittest discover -s poc/shielded-design -p 'test_*.py' -v
PYTHONPATH=.local/shielded-design/python python3 poc/shielded-design/run_model.py
```

CI installs this local dependency and runs the tests, plus Python syntax checks.
Rust CI builds/checks the host changes. It does not rebuild guests, generate
proofs, exercise native RPC, fund a trial or establish privacy. Cache restoration
only reuses build outputs; `cargo test --locked` remains authoritative.

## Repeat the local compatibility experiment

Install the pinned toolchain/native prerequisites described in
[CI](../../docs/CI.md) and the [public adapter](../takeover/README.md). Use new
output directories. The guest builder uses the same official toolchain and
v1compat kernel as PR33 and fixed lockfiles retaining compatible native `01b532e`.
It derives the wallet program image and embeds it in the adapter source; this
is an unfunded local pin, not an upgrade to any existing covenant.

```bash
cargo +1.91.0 build --locked --release --manifest-path poc/takeover/Cargo.toml --bin kpi-takeover-host
CARGO_TARGET_DIR="$PWD/.local/shielded-design/guest-target" bash poc/shielded-design/compat/build.sh .local/shielded-design/programs-NEW
RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm RAYON_NUM_THREADS=4 \
  python3 poc/takeover/measure.py .local/shielded-design/run-NEW \
  .local/ci-target/release/kpi-takeover-host wallet-compat \
  PREPARED_PREFIX REFERENCE_PROGRAMS .local/shielded-design/programs-NEW \
  .local/shielded-design/result-NEW
```

`PREPARED_PREFIX` is the one-transaction prefix from the retained PR33 public
artifact archive; `REFERENCE_PROGRAMS` contains its hash-checked original
transaction/batch/aggregate programs. Verify the [PR33 manifest](../takeover/evidence/tn10-rehearsal.json)
before extracting to a fresh directory. The current artifact archive also retains
the exact prepared input and program/source snapshots used by this experiment.
All synthetic preimage/test-key values are intentionally public fixtures.

For a separate wallet peak-memory run and matched execution-cycle profiles:

```bash
RISC0_PROVER=ipc RISC0_SERVER_PATH=/path/to/pinned/r0vm RAYON_NUM_THREADS=4 \
  python3 poc/takeover/measure.py .local/shielded-design/metrics-NEW \
  .local/ci-target/release/kpi-takeover-host wallet-metrics \
  PREPARED_PREFIX REFERENCE_PROGRAMS COMPAT_PROGRAMS FIRST_RESULT \
  .local/shielded-design/metrics-result-NEW
```

The extra run generates one repeated wallet receipt, not another outer proof or
candidate implementation. It measures wallet memory separately and profiles the
same public native input with/without the composition wrapper. The delta includes
wrapper decoding/binding plus the syscall; it is not full cryptographic receipt
verification implemented as ordinary guest computation.

## Outcome and next decision

The positive four-proof route works locally and the host cannot simply request
that a valid wallet operation be skipped. Missing/wrong inner evidence aborts;
it is not an enforced invalid-operation no-op. The next unfunded decision is how
to prove both valid and invalid operation outcomes at a practical cost. Full
private relations, noncircular L1 payload, ciphertext availability/binding and
authenticated funded-deposit recovery also require review before the proposed
Alice/Bob funding. See the exact results and acceptance criteria above.
