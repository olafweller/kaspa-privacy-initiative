# Based App feasibility — Cloud/TN10 status and handoff

**Updated: 2026-10-17 (Europe/Amsterdam). Real proof generated in Cloud;
valid settlement confirmed on TN10; wrong-state variant rejected by the node.**

The owner authorized continuing PR31, remote VPS work, TN10 test-KAS funding and
broadcasts for this integration, plus commit/push to the existing workbranch.
That supersedes the 2026-10-13 publication-only authorization. Mainnet, real
funds, a production architecture and merging the PR remain outside this task.
Repository documents stay English; owner communication stays Dutch.

## Current resumption point

- Workbranch: `codex/lane-completeness-poc`, draft PR31. Final adapter source:
  `1fe49134b22dcf06d6a41c51d1be2759ede03c78`. Exact upstream revisions,
  artifact/source hashes and execution locations are retained in
  [Cloud/TN10 evidence](evidence/cloud-tn10/).
- Existing Cloud root access to `vmi3633138` works. Keep using that authenticated
  terminal and localhost node RPC; no laptop, external RPC, VPN or new listener
  is required. Node `kpi-tn10`, version 2.1.0, network `testnet-10`, synced with
  UTXO index, PID 43275. Do not restart it for these finite project jobs.
- Isolated VPS project: `/opt/kpi-pr31-cloud-20261017`. Its funded test-fee wallet
  key stays there, mode 0600; never copy it into evidence, chat or the repository.
- Current trial: `trial-2026-10-16T23-25-52-928Z-9510ed7d`, three public KPI
  operations in 33 real selected-chain blocks. Rust and Python agree on every
  selected ID, app state, lane tip and end commitment. Same-anchor omission fails.
- This path captures real input first, profiles guest execution without a proof,
  bootstraps the matching fixed-circuit catch-up covenant, then rechecks the
  profile with the actual covenant ID before real proving. Profiling is not
  cryptographic evidence. No development receipt or development redeem is used.
- Valid settlement: `ad65b24e74d8e4f2d225089265bac635357d88b51a84a34e20f7a6f66c551d67`. The node rejected
  `32483de8122c25246507c47e32d0f4679e388bc8b02d6b3cbdb48de0af7aad0d` with `ZK Integrity: Verification failed`.
  The old outpoint is spent and the continuation preserves the covenant ID and
  one test-KAS. Receipt: 223,930 bytes; proving: 446.427 s; peak individual RSS
  about 9.13 GiB. This is a real succinct proof, not a development receipt.
- Original 25 evidence files remain byte-identical. The optional lift-19 feature
  changes only the covenant manifest/script among the original source snapshot;
  its default/offline build still uses lift-20. Other recorded sources are
  unchanged. Failed trials and their funded outputs are preserved.

Read [current results](RESULTS.md), [upstream reuse](integration/UPSTREAM-REUSE.md),
[commands and stage boundaries](integration/README.md), and
[adversarial review](ADVERSARIAL-REVIEW.md). Do not replay a historical trial.
Inspect submission intents and actual node outcomes after any transport error.
The finite input/bootstrap/settlement VPS jobs have completed; real proving ran
in Cloud. There is no unfinished experiment job to resume. Saved public captures/receipts support replay without the wallet key.

The smallest next KPI property after this integration is authenticated native
KAS deposit/exit accounting and a confirmed authorized payout, reusing canonical
bridge components. The public SHA-256 fold has no notes, nullifiers, shielded
value, deposit or exit implementation. A general proving/runtime path must also
replace this experiment's fixed circuit-shape limitation. No privacy or full
RFC-0001 architecture acceptance follows from this toy integration.

## Historical offline checkpoint — 2026-10-13

The material below records the earlier offline checkpoint and its then-proposed
next experiment. Its authorization/status statements are historical; use the
current resumption point and results above for further work.

## Status of the seven intended milestones

The primary status applies to the full intended milestone, including its real
L1 context. Demonstrated offline components are identified separately. The
categories are *Demonstrated with real evidence*, *Implemented but not fully verified*,
*Simulated or mocked*, *Not started* and *Blocked*. An unattempted TN10 trial is
not evidence that Kaspa does not support the functionality.

| # | Intended milestone | Primary status | What exists / what is missing |
| --- | --- | --- | --- |
| 1 | Publish ten test operations in a dedicated KPI lane | **Not started** | Ten synthetic v1 transactions use namespace `KPIL`. The publication route is documented from upstream source. No TN10 publication, funded inputs, live publication client or acceptance evidence. A namespace is not an exclusively reserved lane. |
| 2 | Reconstruct and authenticate canonical Kaspa ordering through KIP-21 | **Simulated or mocked** | Rust and Python compute real KIP-21 hashes and SMT commitments over an artificial accepted sequence. The chain anchor and selected-chain visibility come from a fixture accessor. No live collector, independently validated TN10 headers or real RPC witnesses were tested. |
| 3 | Execute every operation deterministically | **Demonstrated with real evidence — offline** | Rust, the proven guest and the separate Python executor process the same ten fixture operations to the same state. This demonstrates the small public application, not execution of ten actually published KPI operations on TN10. |
| 4 | Produce a real proof binding the complete interval, old state and new state | **Implemented but not fully verified** | Two real RISC Zero succinct proofs exist and verify. They bind state, lane tips and the derived seqcommit. **This offline component is demonstrated with real evidence.** Binding to an actual canonical TN10 interval and correct live bootstrap remains unverified. |
| 5 | Reject settlement when three operations are omitted while claiming the same complete interval | **Implemented but not fully verified** | The real local Kaspa script engine accepts ten operations and rejects the proof omitting 3/6/9 against the same full fixture anchor. Claiming the full tip with the partial proof also fails. **This offline component is demonstrated with real evidence.** No mempool, consensus or TN10 settlement acceptance/rejection was tested. |
| 6 | Independently reconstruct and process the interval with a second executor | **Implemented but not fully verified** | Python imports no application/guest Rust code and reproduces every fixture block commitment and final state; six negative checks reject as expected. **This offline component is demonstrated with real evidence.** Both executors use the same synthetic source file; independent TN10 retrieval, a separate node and operator loss were not tested. |
| 7 | Test native-KAS deposit/exit integration on TN10 | **Not started** | No deposit, reserve, withdrawal or exit logic exists in this lane PoC. A0/A1 are separate experiments; their payouts do not demonstrate this based-app integration. |

Further work awaits authorization. Live execution also requires node/RPC access,
data capture, bootstrap and fee validation. None of those open points has been
established as a protocol-level blocker.

## What was built and tested

The application updates a SHA-256 state for each recognized numbered payload.
The fixture contains four accepting blocks, ten app operations, unrelated lanes
and a block with no app activity. Bodies deliberately appear in reverse arrival
order. Reconstruction uses the supplied accepted sequence: enumerate the entire
stream, including coinbase, before filtering to the application lane.

The monolithic guest parses v1 preimages, recomputes transaction IDs, processes
payloads and derives lane tips and the final commitment. Unknown payloads are
application no-ops but remain in the lane commitment. The 352-byte journal carries
old/new state and tip, end seqcommit, covenant ID and fixed domain fields.
The tx/batch identity fields are domain constants here, not recursive vProgs
guests. The proof relation has no mandatory count-to-ten check.

The covenant is copied from vProgs and **adapted**, rather than tested unchanged:
the removed `EngineFlags.covenants_enabled` field is adapted and the fixed
recursive `resolve.zkr` pin is replaced with the official monolithic
`lift_rv32im_v2_20.zkr` pin. The Kaspa verifier still checks the allowed control
root, guest image, empty assumptions and exact journal binding.
See [provenance and patch](vendor/covenant/ORIGIN.md).

The positive attack control is essential: the seven-operation proof **is accepted**
when the local accessor returns the executor's fabricated end commitment.
Rejection against the full anchor therefore depends on the cryptographic binding,
not a host check that simply prohibits seven operations.

**`accepted: true` in this evidence means local script acceptance only.**
Block hash, covenant ID, outpoint and UTXO are synthetic. `settlement_id` is the hash
of an artificial transaction, not a TN10 acceptance receipt. GHOSTDAG/PoW, actual
chain selection, real UTXO spentness, full economic transaction validation,
mempool and block acceptance were not tested.

## Code, revisions and evidence for resumption

**Git:** the experiment and original checkpoint used KPI baseline
`ccbdfbc7b5d2f601089e9dc5254719c523a64010`. Publication uses branch
`codex/lane-completeness-poc`, based on the subsequent `main` update in PR #30.
The owner has authorized publishing this previously untracked directory and an
English handoff as a draft PR. Find its implementation snapshot with:

```sh
git log -1 --format='%H %s' -- poc/lane-completeness
```

The draft is a review artifact, not architecture acceptance or authorization for
a live trial. Preserve the entire directory, including proof binaries and failed
runs; lockfiles and source hashes do not replace an external backup.

| Inspected upstream source | Pinned commit |
| --- | --- |
| kaspanet/rusty-kaspa | `01b532e8b553523216471682649693af92f0fd16` |
| kaspanet/vprogs | `f9b84a863a7c7c20586a9cf947550475e894f72e` |
| kaspanet/kips | `e4ae2332117b5cb68bd6188e065ef885b6d17939` |
| kaspanet/docs | `0ac77d043a802fc8196abfd5812ac2afbd97a2b9` |

These are the source revisions inspected for the first task, not a fresh upstream
review during publication. The Sutton transcript was unavailable during that
experiment. The subsequent [Sutton feedback note](../../research/technical-discussion-michael-sutton-based-apps-2026-10.md)
records the owner's report of the discussion, not an approved transcript or
endorsement. It was added after the experiment baseline and does not retroactively
validate the PoC.

| Files, relative to this directory | Purpose / evidence boundary |
| --- | --- |
| [common/src/lib.rs](common/src/lib.rs), [guest/src/main.rs](guest/src/main.rs) | Application rules, parsing, lane relation, journal and proven entrypoint. |
| [host/src/main.rs](host/src/main.rs) | Fixture generator, local accessor, real prover, settlement builder and negative script checks. |
| [independent_executor.py](independent_executor.py), [check_independent.py](check_independent.py) | Separate reconstruction and six negative checks. |
| [vendor/covenant/ORIGIN.md](vendor/covenant/ORIGIN.md), [compatibility.patch](vendor/covenant/compatibility.patch) | Provenance, exact adaptations and limitations; upstream tests were not run. |
| [Cargo.lock](Cargo.lock), [guest/Cargo.lock](guest/Cargo.lock), [source hashes](evidence/source-sha256.json) | Locked dependencies and local source snapshot. |
| [kaspa-fixture.json](evidence/offline/kaspa-fixture.json), [input.json](evidence/offline/input.json) | Synthetic accepted records, bodies, witnesses and guest input. |
| [full.receipt.bin](evidence/offline/full.receipt.bin), [omitted.receipt.bin](evidence/offline/omitted.receipt.bin), journals, `guest.raw.elf`, `guest.program.bin` in `evidence/offline/` | Real proofs, exact journals and guest/kernel program. Image ID: `0881c8caf405ccaf72c41e3c8a0a3a7dd48a4aaf55f040c4de2d759a6c4226f1`. |
| [reverification.json](evidence/offline/reverification.json), [verification-resources.json](evidence/offline/verification-resources.json) | Successful final verification, exit code 0; two positive/twelve negative cases plus budget checks. |
| [independent-executor.json](evidence/offline/independent-executor.json), [negative checks](evidence/offline/independent-negative-checks.json), [Rust test log](evidence/offline/relation-tests.log) | Independent fixture execution and retained test results. |
| [generation resources](evidence/offline/proof-generation-resources.json), [phase timestamps](evidence/offline/proof-phase-timestamps.json), [failure log](evidence/failures/recursive-control-run.log) | Both real proofs were generated; the process then exited 101 on the old recursive control pin. Those same receipts subsequently verified successfully with the adapted pin. |
| [sha256.json](evidence/offline/sha256.json), [preservation-check.json](evidence/offline/preservation-check.json) | The checkpoint rechecked 25 evidence files and 24 source/lock files without mismatches. Preservation records refer to the original experiment baseline: A1, invariants, RFC-0001 and historical evidence were unchanged by that experiment. The subsequent RFC update on main belongs to PR #30, not this PoC change. |
| [RESULTS.md](RESULTS.md), [PLAN.md](PLAN.md), [TN10-RUNBOOK.md](TN10-RUNBOOK.md), [ADVERSARIAL-REVIEW.md](ADVERSARIAL-REVIEW.md) | Detailed results, source inspection, publication route and assumptions. The runbook is not an executed live trial. |

Measured: 922.762 seconds for both proofs on four CPU cores, approximately 9.14 GiB
maximum individual-process RSS; 223,930 bytes per receipt; approximately 35 ms
native verification; 25,006,391 script units. The synthetic settlement has
compute/transient/storage mass 474,267/895,588/0 and an estimated fee floor of
47,426,700 sompi **before fee inputs**. Actual fees paid: zero. These are not TN10
cost measurements. Per-proof times are inferred from timestamps rather than
retained SDK timers.

## Open technical risks

- **Authentic L1 anchor:** the most important missing link. A consistent JSON file
  or agreement between two public RPC replies does not itself establish a canonical
  chain. An independently synchronized, consensus-validating node must supply the
  anchors and selected-parent context; lane witnesses must match them.
- **Live import is absent:** the host calls `fixture(dir)` on every start, including
  `verify`, and writes files. Python explicitly requires synthetic fixtures. The
  current CLI cannot directly consume a TN10 capture. After future authorization,
  run verification on a copy, never on the retained evidence. The final complete
  `run-offline.sh` pipeline was not rerun from a cold start after all fixes; the
  final standalone verifier was run successfully.
- **Bootstrap/interval:** only an already-active lane, a short span (at most 100
  blue-score units) and supported collapsed inclusion witnesses. First touch,
  non-inclusion, expiry/reactivation and transition from a real covenant are absent.
- **Consensus and liveness:** reorgs are accessor checks only; no live rollback,
  pruning/archive test, witness-server loss, fee bumping or confirmations. A
  namespace may contain unrelated traffic. Completeness of a chosen interval
  does not force latest-anchor selection, miner inclusion or progress.
- **Proof/covenant:** fixed monolithic control ID; other segment shapes are not
  validated. Source adaptations and soundness assumptions require external review.
  Passing tests are not a cryptographic correctness proof or a security audit.
- **Economic integration:** fee inputs, change, funded transaction mass and relay
  policy are unverified; zero-fee synthetic bodies cannot be broadcast as prepared.
  Native deposit/exit, shielded funds, privacy and permissionless exits are unproved.

## Historical next-experiment proposal — recorded 2026-10-13

**First replace the artificial anchor with a read-only capture of one real, short
TN10 user-lane interval containing at least one accepted transaction.** Use an
existing active lane; do not publish new operations, deploy a covenant or integrate
deposits/exits. This is a limited test of milestone 2, not completion of 1, 4 or 5.
Live capture/import code still needs to be written and requires the next
experimental authorization. Nothing in this proposal is being executed now.

**Question:** can we obtain the complete relevant accepted order and lane witnesses
and check their commitments against actual canonical TN10 anchors?

**Success criteria:**

1. An owned or independently operated, fully synchronized node validates TN10;
   start/end blocks are selected-chain blocks within the usable window. A second
   independently operated source confirms the same stable interval.
2. Retain full accepted bodies and global `merge_idx`, context and start/end SMT
   witnesses, with node versions, block hashes and header seqcommits.
3. Two reconstructors derive the actual lane tips and exactly the authenticated
   end commitment supplied by the validating node.
4. Omitting an accepted lane transaction or changing order/payload produces a
   commitment mismatch against **the same** end anchor. Do not repair an attack
   by recomputing the expected anchor from modified executor data.

**Failure:** a stable, completely retrieved node capture produces different
commitments; an omitted/changed transaction still validates against the same real
anchor; or the required supported witness/RPC route does not work. Missing access,
incomplete sync, pruning or a reorg produces an **inconclusive / operationally
blocked** result, not evidence of a cryptographic defect.

After that experiment, propose ten actual KPI publications separately, followed
by full/partial real proofs and TN10-assessed settlement. Funding and broadcast
remain explicitly subject to authorization. Native-KAS deposit/exit belongs to
a later separate experiment. This checkpoint makes no censorship-resistance or
RFC-0001-acceptance claim.
