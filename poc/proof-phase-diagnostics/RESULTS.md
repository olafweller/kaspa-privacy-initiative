# Measured segment, lift and join costs

**The bounded diagnostics completed and retained five real, independently
reverified partial receipts.** The two measured segment proofs each take about
seven minutes on the declared four-CPU configuration. Lift and join take about
34-37 seconds each. This identifies segment proving as the largest measured
phase cost in this selection; it does not complete the full-classifier milestone
or establish a pure CPU bottleneck.

## Retained workload and limits

The [plan](PLAN.md) was committed as `47ed371` before execution. Reuse the exact
wallet circuit/VK/proofs, operation fixtures and classifier image
`397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.
The SDK is 3.0.3; the unchanged r0vm SHA-256 is
`2acdf550f9aca4d05b74072463e4ed307c3824309c754a5cb5f93aa84f3390e6`,
matching PR #39. No guest, cryptographic arithmetic, setup or transaction changed.

The existing qualification gate checks all 24 retained reports/input identities.
One new supported SDK execution exports 121 actual segment assets and again
matches the expected full 167-byte journal, session claim and 117,473,222 user
cycles. That is execution evidence, not a full-session proof. The 120 full
segments have po2=20; the final short segment has po2=17.

Selected zero-based segments lie within the first pairing interval:

| Segment | User-cycle interval [start, end) | Trace bytes | po2 |
| --- | --- | ---: | ---: |
| 24 | [23,572,404, 24,543,857) | 154,065 | 20 |
| 25 | [24,543,857, 25,514,292) | 157,461 | 20 |

CPU affinity is 0-3, with four Rayon/OMP/OpenBLAS threads and a four-CPU cgroup
quota. Retain the 12 GiB per-process address-space limit, sampled 12 GiB summed
group-RSS stop threshold and observed 16 GiB environment cgroup cap. Every phase
has a separate process group and explicit limit under the aggregate 3,600-second
clock. No stage reaches its resource/phase/aggregate stop.

## Completed measurements

API wall times include the SDK's fresh subprocess startup and internal work.
Phase wall additionally includes host prechecks, receipt saving/verification,
mutation controls and runner cleanup/sampling. CPU is kernel wait4 user+system
usage for each normally completed process group; separate own-process samples
are retained for comparison. RSS is sampled summed process memory, not a precise
physical-memory measurement or whole-environment peak.

| Phase | API wall s | Whole phase s | CPU s | Peak summed RSS GiB | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Prove segment 24 | 421.258 | 421.472 | 1,649.130 | 9.165 | Real segment receipt verified |
| Lift 24 | 34.075 | 34.362 | 128.386 | 1.396 | Same claim, real succinct receipt verified |
| Prove segment 25 | 415.263 | 415.505 | 1,629.426 | 9.165 | Real segment receipt verified |
| Lift 25 | 33.322 | 33.513 | 126.568 | 1.396 | Same claim, real succinct receipt verified |
| Join 24-25 | 36.293 | 36.756 | 129.162 | 1.417 | Adjacent transition span verified |
| Separate-process verification | n/a | 0.407 | 0.360 | 0.011 | All five partial receipts reverified |

The initial export phase takes 2.830 seconds, including 2.555 seconds in the SDK
execute call. The successful diagnostic continuation takes 942.189 seconds.
The **original aggregate clock totals 1,058.525 seconds (17m 38.5s)**, including
initial export, the preserved pre-proof file-lookup failure, inspection, rebuild
and repair. No second guest execution or failed proof call is retried.

The environment memory-max counter increases by 466 during segment 24 and by
zero during the later phases. OOM and OOM-kill counter deltas are zero throughout.
These are environment-wide interval observations, not exclusive job attribution.
CPU/memory pressure interfaces are unavailable and explicitly recorded as such.
Memory/cache effects remain possible; CPU activity alone does not isolate cause.

## What was actually proven

Two 281,314-byte serialized segment receipts, two 223,154-byte lifted receipts
and one 223,154-byte joined receipt are saved immediately after their API returns.
Each seal verifies with development mode disabled. Altered seal and claim data
are rejected by actual cryptographic verification, repeated in the separate
verification process. Lift claim digests match the segment claims. The two
segment system-state commitments are contiguous, and the join claim equals the
expected composition of those verified inputs.

These are **partial middle-of-session proofs**. Their association with the fixed
workload is recorded through the trusted pinned SDK execution/export and frozen
asset hashes. They do not cryptographically compose the path from the initial
program image to the full expected journal. Do not use them as a full-classifier
receipt, a native settlement proof, a privacy result or a completed note circuit.
The original full-receipt wrong-image and tampered-journal tests remain unrun;
the new partial-receipt mutation checks do not replace those tests.

The known PR #39 output/temp locations contain no returned receipt to reuse.
There are 121 old temporary bincode traces; none is byte-identical to the new
SDK exports. Preserve their hashes and two selected old samples without claiming
proof progress or interchangeability. The diagnostics use fresh, hash-frozen
SDK-exported assets, not those unqualified old traces.

## Preserved integration failure

The first export succeeded, but the adapter expected FileSegmentRef-style
`N.bincode` filenames while `AssetRequest::Path` returned `segment-N`. The next
host invocation failed in 0.207 seconds before its proof-start checkpoint or any
proof API call. The runner stopped and preserved the error, reports and outputs.

The explicit [pre-proof correction](PLAN.md#pre-proof-integration-correction)
normalizes the already exported, manifest-hash-checked bytes. The continued run
retains the original aggregate deadline and subtracts the failed lookup time
from the same segment phase budget. It does not retry a proof or resource failure,
change the selected workload, add time or erase the initial negative result.
Proof-producing host source is `ca9b186`; initial export source is `bdee079`.

## Interpretation and recommendation

Segment proving accounts for about 89% of the summed five measured proof-API
wall times. Both selected full segments have similar costs. Lift and one valid
join complete substantially sooner. This supplies actual verified checkpoints
and phase costs where PR #39 only retained the execution checkpoint and timeout.
It does **not** reveal how many segments that earlier job proved before stopping.

An explicitly conditional illustration: 120 full segments at the mean measured
prove-plus-lift API cost would take about **15.1 hours**, before joins and the
short final segment. This is not a measured whole-run completion time or an
approved budget. These API probes start fresh processes; a full job may reuse
initialization/caches or differ in parallel scheduling, memory pressure, segment
mix and recursion behavior. Do not multiply these costs into a throughput claim.

**Recommendation:** before another full proof attempt, qualify the pinned SDK's
official CUDA proving path on these same retained segment assets, followed by
the same lift/join and independent verification checks. The
[SDK 3.0.3 CUDA feature](https://github.com/risc0/risc0/blob/v3.0.3/risc0/zkvm/Cargo.toml)
covers the relevant rv32im and recursion circuits, but compatibility and speedup
on a suitable GPU environment remain unmeasured. This is a proposed execution
environment experiment, not a new wallet-proof architecture or assumed fix.
No GPU qualification, longer full job or additional trial is started here.

Keep the original 32M failure, PR #38 calibration and PR #39 one-hour negative
full-proof result intact. The full succinct receipt, independently verified
against the expected image and exact journal, remains the gate before expanding
the private-note relation. All work stays local and unfunded, with no new TN10
transaction. See the [public evidence](evidence/README.md) and
[adversarial self-review](ADVERSARIAL-REVIEW.md).
