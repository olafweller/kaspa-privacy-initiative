# Recursive public-account adapter

Local review resumed by the owner on 2026-10-17. Workbranch:
`codex/takeover-local-review`, based on main `335fbca`. The original imported
source checkpoint is commit `b4cb2bb`. The historical
[paused handoff](STATUS-HANDOFF.md) remains a record of the earlier task.
That local-review authorization initially covered retained public data only.

**Subsequent authorization, 2026-10-17:** after completion of that local review,
the owner instructed continuing with the fresh TN10 rehearsal. See
[live rehearsal](LIVE-REHEARSAL.md). The local-review boundary below describes
the completed checkpoint, not a renewed request for permission. The fresh
rehearsal has now completed through confirmed native payout, after an observed
175-blue-score stop gap and clean public reconstruction.

The [final review](FINAL-REVIEW.md) and [five-criterion feasibility conclusion](../../docs/based-app-feasibility-2026-10-17.md)
record completion of this scoped investigation and read-only evidence checks.
Development now focuses on [shielded native KAS](../../docs/shielded-kas-next.md).

This experiment reuses the native-value account relation as one serial SMT
resource, then uses the pinned vProgs batch and aggregate verifiers. It has no
private notes, privacy, new asset or general resource scheduler. See
[plan](PLAN.md), [ADR-0005](../../docs/adr/0005-long-gap-recursive-takeover.md)
and [local review](LOCAL-REVIEW.md).

## Repeat local checks

Use Rust 1.91.0 and the native prerequisites described in
[CI](../../docs/CI.md). From the repository root in this Cloud image:

```bash
source /workspace/.onboarding/activate.sh
cargo test --locked --release --manifest-path poc/takeover/Cargo.toml
cargo build --locked --release --manifest-path poc/takeover/Cargo.toml --bins
cargo build --locked --release --manifest-path poc/lane-completeness/integration/Cargo.toml
bash scripts/ci_fast.sh
```

Build programs from source with the hash-checked official tools reused from
PR31. Choose a new program directory; the script refuses to replace an old one.
The host `wrap` command combines the guest ELF with the pinned v1compat kernel.

```bash
bash poc/lane-completeness/bootstrap.sh
CARGO_TARGET_DIR="$PWD/.local/takeover/guest-target" \
  bash poc/takeover/build-guests.sh .local/takeover/programs-NEW
python3 poc/takeover/check_retained.py .local/takeover/replay-NEW \
  --program-dir .local/takeover/programs-NEW
```

The capture check exercises the prepare executable and the retained native
validator. It checks the two contiguous public intervals, prior state/tip
continuity, identical original application outcomes, omission against the fixed
endpoint and a tampered native body. It also prepares a combined interval from
the two original captures: 55 selected-chain blocks, four lane transactions,
initially zero balance, ending at six test-KAS spendable with a four-test-KAS
withdrawal claim. These are historical public inputs. Preparation and the Rust
receipt callbacks are not cryptographic proof verification.

For a real local recursive proof, using those prepared inputs:

```bash
RISC0_PROVER=ipc RISC0_SERVER_PATH=/workspace/scratch/kpi-lane-tools/r0vm \
RAYON_NUM_THREADS=4 python3 poc/takeover/measure.py \
  .local/takeover/proof-NEW-run .local/ci-target/release/kpi-takeover-host \
  bundle .local/takeover/replay-NEW/combined .local/takeover/programs-NEW \
  .local/takeover/proof-NEW
```

The runner compares each real guest journal against preparation, resolves the
transaction/batch assumptions, checks the official resolve control identity and
checks the resulting receipt in the native script engine. That engine uses a
local accessor for both the derived commitment and the fixed commitment from
the saved capture, and rejects a wrong commitment. Missing/wrong receipt and
expired-lane execution failures are retained separately from script rejection.
None of these local checks broadcasts or establishes current chain acceptance.

The imported empty-batch receipts can also be verified without a prover:

```bash
.local/ci-target/release/kpi-takeover-host verify-retained \
  .local/takeover/gate-02 .local/takeover
```

That last command requires the imported archive. A fresh clone does not contain
its ignored artifacts. The historical gate's host binary and its sources differ
from the new bundle runner; never treat the old gate as evidence for the new
transaction path.

## Historical local-review boundary

No new wallet, funding, transaction, stop/restart of the node or VPS experiment
belongs to this local review. The subsequently completed fresh TN10 rehearsal separately established
actual bootstrap/UTXO binding, confirmed deposits, a gap over 100 blue scores
below native expiry, public replay in a clean directory, recursive settlement
and actual authorized native payout; see the linked live report. Passing local checks alone does not satisfy
the repository's complete-rehearsal requirement. The old funded instances and
six-test-KAS PR32 balance remain untouched.
