> **Separate follow-up, 2026-10-17 UTC:** [PR32 native-value results](../native-value/RESULTS.md)
> add a real public 10/4/6 deposit/withdrawal/payout cycle and native same-anchor
> omission rejection. PR31's scope/results below remain their historical milestone.
> Its derived acceptance nonces/public archive have lossless corrections with
> [recorded provenance](evidence/cloud-tn10/integer-correction.json); original RPC
> and binary proof bytes are unchanged. No old trial was repeated.

# Cloud/VPS TN10 integration — 2026-10-17

**A real KPI execution proof generated in Codex Cloud settled on TN10. The node
rejected the same proof with a different claimed new state, and confirmed the
valid continuation.** This dated section
supersedes the historical offline status below. No development receipt is used.

The code for the final profile-before-bootstrap path is commit
`1fe49134b22dcf06d6a41c51d1be2759ede03c78`. The preceding adapter commits and all
failed attempts are retained. See [runtime and exact upstream revisions](evidence/cloud-tn10/runtime.json),
[reuse decisions](integration/UPSTREAM-REUSE.md), and
[remote reproduction](integration/README.md).

## What already runs without the laptop

Codex Cloud uses the existing authenticated root webterminal on
`vmi3633138.contaboserver.net`; the VPS runs the unchanged `kpi-tn10` node and
uses its localhost wRPC. Read-only inspection established version 2.1.0,
`testnet-10`, synchronized state and a UTXO index. Local JSON wRPC supports the
full accepted-chain stream and lane witnesses; no additional public RPC, VPN,
listener or network-policy change was needed. The node remained PID 43275.

Cloud builds the pinned adapter and runs the independent Python checker and
real RISC Zero CPU prover. Finite VPS systemd jobs construct/sign/submit and
observe transactions, continuing after the webterminal disconnects. The VPS has
6 CPUs, about 18 GiB RAM and 772 GiB free disk; it needs no Rust installation.
Cloud has 4 CPU cores and a 16 GiB memory limit. The existing VPS Node/SDK and
native node binary hashes are retained. The remote test-wallet key remains mode
0600 inside the mode-0700 project directory, never in evidence or chat.

The owner supplied 10,000 **TN10 test-KAS**, exactly `1,000,000,000,000` sompi,
in transaction `a93ab8a5d17d4b254bf28fd35422d50d65df15190dbcc6a2b091026f7df3ce21`.
No mainnet or real-fund operation was performed.

## Final trial input and checkpoint

Trial: `trial-2026-10-16T23-25-52-928Z-9510ed7d` on the VPS under
`/opt/kpi-pr31-cloud-20261017`. Lane:
`4b353df600000000000000000000000000000000`.
The seed is outside the measured interval. Operations 1, 2 and 3 are ordinary
signed v1 user-lane transactions; unknown payloads remain deterministic no-ops
in the unchanged guest relation. The relation has no required operation count.

| Item | Actual identifier / result |
| --- | --- |
| Seed | `03e4a93c376e3aed81096b2cacb798447337a5f8ae5042b6e3ed211a23b39b6e` |
| Operation 1 | `e591738ac54f2abe0c00d55e80ca84c95929daad8b21683bbf4d93483300245a` |
| Operation 2 | `31ee2b1f659b06b4b5276c8ccb695564f01c373be5196595fe6c561787c88d38` |
| Operation 3 | `cf319b1b8d85113c4d2b8aff5aab4f6a15889a38c29cb51f0ee4959001fe5619` |
| Start block | `9c784f6d59317708a7fe8b99d92043c6a20248f560f24c16f1afe75b0cb0410b` |
| End block | `96e3c2cd62aacf3715a97ef4f23a2d889290c76e20dd659ff4633f043d60e559` |
| Complete interval | 33 selected-chain blocks, three accepted lane transactions |
| Derived end lane tip | `7a71eaa94cbba2e30040e08003b116811112c2a040efecab85df0c389818cfd8` |
| Derived end seqcommit | `957d30928d987f2c7fa50b85d1ad6a8bc2de66d9375e9079a849ef209a73bacd` |
| KPI public state | `2c056837bb51248de9c75454b20abf4f4d4efe10c62af9349c54abdfda4c8117` |
| Catch-up bootstrap | `ca97ea8f8795124bfad5231f720758193668e90d4c2ff946f5b629750846031b` |
| Covenant ID | `e6788864cc27af8807de23dbcd8ec63523af6d78bf700c916f4a2ab40f0b949a` |

Rust/native helpers and the independent Python implementation agree on all
ordered transaction IDs, state, lane tip and the real node's end commitment.
Omitting a lane transaction or substituting an activity ID fails against the
unchanged anchor. Eight Python adversarial checks pass for this capture and
eight for the initial native-lane capture. The native capture also exercises
same-block reordering; this three-operation capture has no same-block pair,
so its corresponding Rust control explicitly reports **not exercised**.
Two same-capture implementations are not two independent nodes/operators.

Before bootstrap, the execution-only profiler measured one `po2=20` segment.
After inserting the actual covenant ID, a second execution profile confirmed the
same circuit. These measurements create no proof. The matching fixed lift-20
covenant was selected at bootstrap; the original guest image remains
`0881c8caf405ccaf72c41e3c8a0a3a7dd48a4aaf55f040c4de2d759a6c4226f1`.

The bootstrap is a deliberate catch-up checkpoint at the known seed tip and
initial public state, created after retaining the inputs. It does not prove a
complete arbitrary bootstrap history, first-touch or a deposit protocol.

## Real proof and actual node settlement

[Final node result](evidence/cloud-tn10/settlement-result.json) and
[accepted transaction](evidence/cloud-tn10/settlement-accepted.json) record:

| Check | Actual result |
| --- | --- |
| Real succinct proof | 223,930 bytes; 352-byte journal; SDK verified; development mode absent |
| Real proving time | 446.427 s, four Cloud CPU cores; process exit 0 |
| Maximum individual-process RSS | 9,571,132 KiB, approximately 9.13 GiB; not aggregate concurrent RSS |
| Guest execution | One segment, 1,048,576 padded cycles; 471,889 user cycles |
| Invalid signed settlement | `32483de8122c25246507c47e32d0f4679e388bc8b02d6b3cbdb48de0af7aad0d` |
| Invalid result | Node rejected: `failed to verify the signature script: ZK Integrity: Verification failed` |
| Valid settlement | `ad65b24e74d8e4f2d225089265bac635357d88b51a84a34e20f7a6f66c551d67` |
| Accepting selected-chain block | `dfe2081a9b66903a85dc599287facd2199a972b65e7e3bc1d8044626db3b24b1` |
| Actual settlement fee | 59,474,875 integer sompi, 0.59474875 test-KAS |
| Continuation | Output 0 is a live UTXO with the same covenant ID and 100,000,000 sompi (one test-KAS) |
| Old bootstrap UTXO | No longer present; actually spent by the confirmed continuation |

The invalid transaction retained the same real receipt and claimed a different
new state; its fee inputs were signed for that body. An unrelated admission
failure would not have counted. The valid transaction passed actual native
mempool and consensus/script validation and was observed in accepted order with
ten selected-chain confirmations, followed by a successor-UTXO query. This is
more than local script acceptance. It remains one owner-operated node's network
observation; no second independent node/operator corroborated it.

The proof's exact journal also matches the independently reconstructed public
state/tip/seqcommit and actual covenant ID. [Receipt](evidence/cloud-tn10/full.receipt.bin),
[journal](evidence/cloud-tn10/full.journal.bin),
[proof costs](evidence/cloud-tn10/proof-report.json),
[resource measurement](evidence/cloud-tn10/live-proof-resources.json),
[negative rejection](evidence/cloud-tn10/invalid-settlement-rejected.json),
[raw settlement RPC](evidence/cloud-tn10/settlement-rpc-records.json.gz) and the
[complete public trial archive](evidence/cloud-tn10/successful-trial-public.tar.gz)
are retained. No wallet key is included. Node PID remained 43275; no node
restart, configuration change or new public interface was used.

This proves the scoped public KPI fold can consume real accepted lane input and
advance its funded TN10 covenant under a real execution proof, while a forged
successor state fails proof verification. It does not prove a shielded system,
permissionless recovery or arbitrary runtime compatibility. No withdrawal or
terminal user payout exists in this state-continuation experiment.

## Retained failures and limits

| Attempt | Observed result / response |
| --- | --- |
| 1 | Seed confirmed; bootstrap admitted. Observation from a volatile sink saw a reorg. A later UTXO query found the one-test-KAS bootstrap output unspent. Preserved, never rebroadcast. |
| 2 | Bootstrap and all three operations confirmed, but the interval spanned 110 blue-score units, outside the unchanged guest's 100-score bound. Fresh identity; shorter observation waits, same guest constraints. |
| 3 | Real succinct proof verified in the SDK: 223,930 bytes, 237.191 s, about 4.58 GiB maximum individual-process RSS. Its lift-19 circuit did not match the deployed lift-20 pin; local script budget evaluation rejected before any settlement submission. |
| 4 | A new lift-19 deployment's deeper SMT path required lift-20. An execution-only profile identified the mismatch. Its incompatible proving process was deliberately stopped; the partial-run resource file is not a completed proving-cost measurement. |
| 5 | Actual-input profiling selected lift-20 before bootstrap; a real proof then settled, and the wrong-state variant was rejected, as recorded above. |

The supported circuit remains fixed in each covenant, not executor-selected.
The optional lift-19 feature creates a different script/identity; it cannot
upgrade the earlier funded lift-20 outputs. Both use official circuit identities,
with unchanged allowed-control-root, image, empty-assumptions and journal checks.
For a general runtime, reuse a compatible established recursive proving path
instead of assuming one monolithic circuit size handles every workload.

Across all attempts, 23 confirmed transactions paid 67,962,000 sompi in fees
(0.67962 test-KAS). Four failed-trial covenants retain one test-KAS each; the
confirmed continuation retains one more. The fee wallet has 999,432,038,000
sompi. These amounts sum exactly to the original test funding; see
[test-wallet accounting](evidence/cloud-tn10/test-wallet-accounting.json).
No privileged cleanup/withdrawal path was added.

All 25 historical evidence files are byte-identical. Of the 24 original source
hashes, 22 remain identical; the covenant manifest/script have the explicit
optional live-circuit feature. Default historical behavior stays lift-20; exact
original sources remain in commit `902cbe9`. Failure archives, original live
receipt, cancelled-run diagnostics and hashes are retained under
[evidence/cloud-tn10](evidence/cloud-tn10/).

Still outside scope: a live partial receipt and its on-chain omission rejection
(the live omission check reconstructs commitments; the historical offline partial
receipt test remains separate), ten live publications (this trial uses three), shielded
notes/transfers, nullifiers, native-KAS deposit/exit accounting, private value
conservation, permissionless exits, full vProgs recursion/composability,
first-touch/expiry, continuous reorg rollback, independent-node corroboration,
operator-loss recovery and post-pruning data retrieval. Those are absent
implementations or unexecuted experiments, not demonstrated Kaspa blockers.
RFC-0001 remains open and no production/security/privacy claim is made.

---

# Historical offline result — 2026-10-13

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
