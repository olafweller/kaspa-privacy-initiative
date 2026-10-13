# KIP-21 lane completeness PoC

Separate public-data experiment for KPI; see [implementation plan](PLAN.md),
[offline results and costs](RESULTS.md),
[adversarial review](ADVERSARIAL-REVIEW.md) and [TN10 publication runbook](TN10-RUNBOOK.md).
No shielded funds, notes, wallet keys, funding or broadcast code. RFC-0001 stays
open; A1 and historical evidence are unchanged.

The application folds ten numbered operations into a SHA-256 state. It uses a
valid four-byte user-lane namespace. Synthetic Kaspa accepted-order fixtures
include unrelated traffic and an empty app block; body arrival order is reversed.
The guest parses v1 transaction preimages, recomputes IDs, applies operations and
derives KIP-21 lane tips and final SMT inclusion using official Kaspa crates.

This is a monolithic RISC Zero guest. It needs no scheduler, cross-app runtime,
recursive tx/batch receipts, private state or full-vProgs composition. Its journal
uses the exact production vProgs 352-byte ABI, with two fixed relation-domain
slots in place of recursive guest identities. The production covenant pins this
guest's image. [Vendor provenance](vendor/covenant/ORIGIN.md) records the small
EngineFlags compatibility adaptation and an exact monolithic lift control-ID pin;
all journal/proof/anchor checks are retained. The upstream recursive `resolve.zkr`
pin rejects a real receipt without assumptions. This covenant therefore supports
the observed single-segment `lift_rv32im_v2_20.zkr` shape only.

Retained validation: full receipt accepted; omission of 3/6/9 against the same
full-interval anchor rejected; partial receipt under its fabricated anchor
accepted as a control. Both receipts are real and verified. Two-proof generation
took 15.38 minutes and ~9.14 GiB maximum process RSS on four CPU cores. This
demonstrates fixture-relative enforcement, not an observed canonical TN10 result.

The decisive test verifies a real seven-operation receipt, then tries to settle
it against the same externally fixed full-interval seqcommit as the full receipt.
The verifier must reject. As a positive attack control, a verifier given the
executor's fabricated endpoint accepts the partial receipt. This demonstrates
why the canonical L1 anchor is necessary. Matching executor outputs alone is
insufficient evidence.

## Reproduce

Linux x86_64, Rust 1.91+, Python 3.11+, curl, tar and rustup are required. Install
`requirements.txt` in your preferred Python environment. The experiment used four
CPU cores and a 16 GiB memory limit; see retained resource measurements.

```sh
cd /workspace/kaspa-privacy-initiative/poc/lane-completeness
python3 -m pip install -r requirements.txt
bash bootstrap.sh
bash run-offline.sh evidence/reproduced
```

`bootstrap.sh` downloads two official GitHub release archives, verifies their
recorded hashes and links a task-specific RISC Zero Rust toolchain. It obtains the
exact recursion ZIP from the official prebuilt r0vm binary, checks its upstream
SHA-256 and supplies it through `RECURSION_SRC_PATH`. No package source is patched
for artifact retrieval. This also works when the RISC Zero artifact host or GitHub
LFS are unavailable. The local r0vm IPC server produces real CPU succinct receipts;
no cloud prover is used. `RISC0_DEV_MODE` must be absent, even if set to `0`.

Both Cargo lockfiles pin the inspected Kaspa/vProgs revisions; all builds use
`--locked`. The guest raw ELF is packaged with RISC Zero's trusted v1compat kernel,
following vProgs' `api/src/elf_binary.rs`. Retained evidence includes both forms,
receipt/journal binaries, synthetic Kaspa records, native transaction bodies,
verifier results and hashes. No trusted setup is generated for the succinct path.

For quick inspection, without proving again:

```sh
python3 independent_executor.py evidence/offline/kaspa-fixture.json
python3 check_independent.py evidence/offline/kaspa-fixture.json
target/debug/kpi-lane-host verify evidence/offline evidence/offline/guest.raw.elf
```

`verify-full` can check the full receipt alone. `verify` checks the entire native
negative/control suite using the saved receipts and writes `reverification.json`.
It does not generate proofs or use RPC. The initial generation process produced
both valid receipts but failed on the upstream recursive control pin; the final
successful verifier report uses the explicit monolithic adaptation. Resource
files and failure logs retain that distinction.

The native Rust tests reject malformed preimages/proofs, duplicate/reordered
indices, reordered blocks, wrong start tips, invalid lane encodings and excessive
spans. They also exercise operation numbers zero and `u32::MAX` and deterministic
no-op payloads. Python independently reconstructs all accepted lane order, all
block commitments and final state, and runs six additional negatives.

## Scope

The accessor in this offline experiment is a fixture map. It supplies an
externally fixed synthetic root to the actual `OpChainblockSeqCommit` opcode and
real `OpZkPrecompile` verifier. It does not simulate GHOSTDAG, PoW, node sync,
canonical header validation, mempool acceptance or an actual TN10 settlement.
Fixture transactions have dummy outpoints and no fees; they cannot be broadcast.
Recorded mass/fee values apply only to the measured synthetic body, before fee
inputs. A live experiment must collect independently validated TN10 anchors and
witnesses and obtain explicit funding/broadcast authorization.

Only short intervals of an already-active lane are supported. First-touch
bootstrap, lane expiry/reactivation, long-term archives and live reorg handling
remain open. The state/root pins and proof artifacts do not supply payload
availability. There is no censorship-resistance, privacy, production-soundness,
shielded-recovery or architecture-acceptance claim.
