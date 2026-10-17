# Paused handoff: completed PR #39 research package

**Paused by the owner, 2026-10-17.** The authorized closing work is to preserve
this handoff, finish and merge [PR #39](https://github.com/olafweller/kaspa-privacy-initiative/pull/39),
then pause. Do not start proof diagnostics, another full proof attempt, a new
wallet setup, private-note implementation or TN10 transactions without a new
owner instruction. No automatic restart or reminder is scheduled.

## Recovery point

- Repository: `olafweller/kaspa-privacy-initiative`; PR branch: `codex/outer-proof-128m`.
- Completed experiment/evidence revision before this documentation-only closure:
  `2966bb1eb1452a88d71c2a8fb0bceb1491fb9dd4`.
- Main before PR #39: `99d35099d6640108db76a5ba6db8eff18d2b79d3`, incorporating PR #38.
- After integration, recover from the actual merge commit recorded on PR #39
  (`merge_commit_sha` after `merged: true`), rather than an unmerged test-merge ref.
- The closure adds pause documentation only; it does not change the classifier,
  host implementation, proof fixtures, measured results or evidence archive.

## Confirmed outcome

All 24 retained execution controls passed under the approved 128M-cycle profile:
11 full sequences, five specific authentication-abort controls and eight
malformed-only cases. The main valid-invalid-valid sequence has outcomes
`[0, 3, 0]`, 117,473,222 user cycles and 121 **executed** segments. Expected
complete journals and input/program identities were checked.

The one real succinct-proof job stopped at its 3,600-second whole-process-group
limit. It returned no candidate or completed outer receipt. Consequently the
separate cryptographic receipt-verification tests, including wrong-image and
tampered-journal rejection, remain unrun. The last confirmed checkpoint is the
completed execution profile; counts of proven segments, lift and join completions
are unknown. The measured 3.92 CPU-hours and 9.19 GiB sampled peak summed RSS do
not identify the bottleneck or predict completion time. See [results](RESULTS.md).

The original 32M failure and PR #38's separately labelled calibration remain
unchanged. This is a completed execution qualification and bounded negative
proof-production result, not a completed full-classifier proof or financial
privacy demonstration. The work was local and unfunded.

## Preserved evidence

- [Public evidence archive](evidence/local-outer-proof-artifacts.tar.gz):
  1,011,185 bytes; 254 regular members.
- Archive SHA-256:
  `eb39eb23d6dd7da2f55a45711fbcac2acaad844dee94e30e2a91d6f6705a1710`.
- [Manifest](evidence/comparison.json) and [evidence guide](evidence/README.md):
  exact program, VK, wallet proofs, operation fixtures, expected journals,
  qualification outputs, failed-job checkpoints, logs and resource measurements.
- Unchanged expected classifier image:
  `397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.
- [Predeclared plan](PLAN.md), [ADR 0010](../../docs/adr/0010-approved-128m-outer-proof.md)
  and [pinned build environment](../accelerated-bn254/README.md).

The public inputs suffice for qualification and work with the retained wallet
proofs; wallet secrets and the large wallet proving key are not needed. No
credential or private proving parameters are included. Local `.local/outer-proof-128m/`
files are retained as additional working data, but recovery must use GitHub and
the committed archive, not assume that this Cloud session or its build cache survives.
At closure inspection no active project executor or prover remained; an old
defunct `r0vm` process is not running proof work.

## Deferred next step

After a new owner instruction, first read this handoff, the results and the
manifest. The proposed follow-up is targeted profiling of actual segment proving,
lift and join in the same pinned environment, with explicit per-step checkpoints
and immediately saved, cryptographically verified intermediate results. Inspect
retained locations before claiming that any compatible intermediate proof exists;
an execution trace alone is not proof progress.

Predeclare selected probes and aggregate/per-probe resource limits before running
them. Astra proposed at most one additional aggregate hour with the existing CPU
and memory limits; that proposal is deferred, not authorization to run during
this pause. Do not retry the uninstrumented full job or silently raise a budget.
Partial proofs would not close the final gate: a complete succinct receipt,
separately verified against the independently expected image and exact journal.
