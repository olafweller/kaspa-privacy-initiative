# Offline result — 2026-10-13

**The offline cryptographic omission gate passed. Canonical TN10 enforcement is
not yet established.** Both real RISC Zero succinct receipts verify independently.
The adapted vProgs settlement covenant, executed by the actual Kaspa script
engine, accepts the ten-operation transition and rejects the seven-operation
transition against the same externally fixed full-interval anchor. It also rejects
using the partial proof while claiming the full lane tip.

The positive attack control accepts the partial proof when the fixture accessor
is replaced with the executor's fabricated endpoint. The result therefore tests
the anchor binding, rather than an operation-count guard or successful replay.
There is no expected operation count in the proving relation.

## Milestones and concrete evidence

| Milestone | Outcome / evidence |
| --- | --- |
| Inspect latest KPI and Kaspa/vProgs before implementation | KPI `ccbdfbc` matches fetched origin/main. Four upstream heads are pinned in [PLAN](PLAN.md) and [environment.json](evidence/offline/environment.json). Docs/code journal-length discrepancy and upstream build failures were identified. Sutton transcript was unavailable; no statement is attributed to it. |
| Ten deterministic operations | Public 15-byte payloads on namespace `KPIL`; SHA-256 state fold; four accepting blocks, unrelated traffic, one empty app block and reversed body arrival order. [Kaspa fixture](evidence/offline/kaspa-fixture.json), [guest input](evidence/offline/input.json). |
| Supported TN10 publication route | Source-level route verified: ordinary v1 fee-funded user-lane transactions and reference `activity_transaction`. [Runbook](TN10-RUNBOOK.md) pins exact builder/RPC files. No live node, funding, signing or broadcast was run; first-touch bootstrap is still an implementation gate. |
| Canonical-order reconstruction | Relative to synthetic accepted-order records only. Enumerate the full stream including coinbase before lane filtering. Python independently reproduces all block commitments, final lane tip and state. [Independent result](evidence/offline/independent-executor.json). No observed TN10 canonical interval is claimed. |
| Real proving and covenant verification | Retained [full receipt](evidence/offline/full.receipt.bin), [partial receipt](evidence/offline/omitted.receipt.bin), raw ELF and trusted-kernel ProgramBinary. Image `0881c8caf405ccaf72c41e3c8a0a3a7dd48a4aaf55f040c4de2d759a6c4226f1`. Native `OpChainblockSeqCommit` and `OpZkPrecompile` execute; no development receipt or redeem. [Native results](evidence/offline/reverification.json). |
| Omit operations 3, 6, 9 | Partial receipt is valid; same-interval settlement rejects with `ZkIntegrity("Verification failed")`. Full-tip forgery rejects too. Replacing the external anchor with the partial endpoint accepts the partial receipt, isolating the authenticated-endpoint dependency. |
| Independent executor / additional negatives | Separate Python implementation imports no guest/application Rust code. Six negatives reject omissions, reordered accepted IDs, missing bodies, payload corruption, wrong start tip and altered SMT sibling. [Negative evidence](evidence/offline/independent-negative-checks.json). Rust relation tests pass: malformed preimages/SMT, order/duplicates, start tip, lane encoding/span and integer boundary operations. [Test log](evidence/offline/relation-tests.log). |
| Evidence and costs | Both receipts, journals, actual synthetic settlement bodies, verifier errors, resource observations and artifact hashes retained. No KAS spent. [Generation resources](evidence/offline/proof-generation-resources.json), [successful verification resources](evidence/offline/verification-resources.json), [hash manifest](evidence/offline/sha256.json). |

The native suite has two expected acceptances (full interval and fabricated-anchor
partial control), twelve expected rejections, plus successful bounded verification
and underbudget rejection. Wrong old/new state, lane/covenant, canonical anchor,
orphan anchor, successor-state replay, claim/seal corruption and continuation
value change are included. The final verification process exits successfully.
This is script verification with a supplied synthetic UTXO, not full economic
transaction validation, mempool acceptance, UTXO membership or an on-chain spend.

## Measured resources

Four CPU cores, 16 GiB memory limit, AMD EPYC 9V74; official local
`r0vm 3.0.3`, no GPU or cloud prover. See the environment file for exact observations.

| Measurement | Observed value |
| --- | --- |
| Combined two-proof generation process wall time | 922.762 s (15.38 min), including the initial native check that failed on the recursive control pin |
| Generation user/system CPU time | 3,612.903 / 5.023 s |
| Maximum waited-process RSS | 9,578,828 KiB (~9.14 GiB); Linux rusage maximum individual process, not sum of simultaneous processes |
| Full / partial phase durations, inferred | ~456.9 / 466.2 s from process start and receipt-file timestamps; about one-second epoch resolution, not SDK per-proof timings |
| Full / partial receipt bytes | 223,930 / 223,930 |
| Journal bytes | 352 each |
| Full native verification | Approximately 33–36 ms in this run |
| Full covenant script units / compute budget | 25,006,391 / 2,500 |
| Redeem / signature script bytes | 557 / 223,662 |
| Estimated settlement transaction bytes | 223,897 |
| Compute / transient / storage mass | 474,267 / 895,588 / 0 grams |
| Default relay fee floor before fee inputs | 47,426,700 sompi (0.474267 test KAS), estimate only |
| Actual funding / fees / broadcasts | None / zero / none |

The measured one-input body fits pinned TN10 mass limits **before adding fee
inputs**. It preserves its synthetic covenant value and pays zero fee, so it is
not a relay-ready transaction. Fee inputs, signatures, change/storage mass and
actual relay policy must be measured for a future authorized live trial. The
generation resource file has exit code 101 because the original running harness
still used the upstream recursive control pin after creating both valid receipts.
Those same unchanged receipts were subsequently verified successfully with the
recorded monolithic adaptation; no mock proof or re-proving was substituted.
Fresh reproduction with the final code records SDK per-proof timings in its
report. Retained [phase timestamps](evidence/offline/proof-phase-timestamps.json)
make the inference in this original run explicit.

## Failures and adaptations

- RISC Zero's older Rust 1.88 toolchain cannot build current Kaspa crates requiring
  1.91+. The official 1.97 guest toolchain built successfully; [failure log](evidence/failures/rust-1.88.log).
- Artifact-host policy and GitHub LFS retrieval failed. The exact official
  recursion ZIP was already embedded in the downloaded r0vm release. Its SHA-256
  matches upstream `744b999f…f4d8849`; the supported local artifact path works.
- Pinned vProgs and Rusty Kaspa do not compile together unchanged: the removed
  `EngineFlags.covenants_enabled` field requires adaptation. [Build failure](evidence/failures/upstream-compatibility.log),
  [exact patch and provenance](vendor/covenant/ORIGIN.md).
- The independent executor caught a fixture bug: an empty app block advanced its
  last-touch score. The fixture now preserves the score and cross-checks each
  lane-derived anchor against the full native active-lane SMT root.
- A raw ELF failed RISC Zero v3 ProgramBinary parsing. Packaging with the trusted
  v1compat kernel follows the existing vProgs implementation;
  [failure](evidence/failures/unwrapped-guest.log).
- The upstream covenant's fixed `resolve.zkr` pin rejects an assumption-free
  monolithic lift receipt; [native failure](evidence/failures/recursive-control-id.json).
  This experiment pins the exact official `lift_rv32im_v2_20.zkr` control ID.
  Native allowed-root, image, empty-assumptions, proof and journal checks remain.
  Other segment shapes are unsupported, and the covenant is explicitly adapted.
- Serializing the omitted synthetic transaction exposed the builder's initial
  sigop-count commitment. Both persisted v1 bodies now carry the sized compute
  budget; [serialization failure](evidence/failures/partial-transaction-serialization.log).

## Remaining risks and next gate

This establishes the tested verifier's conditional enforcement against synthetic
KIP-21 anchors. It does not establish that an observed TN10 canonical lane interval
can be collected, proven and settled end to end. The fixture accessor, artificial
acceptance stream and dummy covenant/outpoints do not authenticate an actual
Kaspa chain. A future trial needs independently validated chain anchors, real
lane proofs/full accepted bodies, correct bootstrap, current relay/fee checks,
explicit funding/broadcast authorization and confirmation evidence.

First-touch/non-inclusion bootstrap, expiry/reactivation, live reorg handling,
pruning/archive and witness availability remain open. The retained guest supports
a short already-active lane and this exact proof shape. Completeness of a chosen
interval does not force latest-anchor selection, timely settlement, miner
inclusion or executor progress. Independent reconstruction does not itself prove
censorship resistance. There are no privacy, shielded-fund recovery, production
soundness or RFC-0001 acceptance claims. [Adversarial review](ADVERSARIAL-REVIEW.md)
records the assumptions; [preservation checks](evidence/offline/preservation-check.json)
confirm invariants, RFC-0001, A1 and earlier evidence are unchanged.
