# Private-note Succinct GPU result — 2026-10-18

One owner-released L40S attempt produced a genuine Succinct receipt for the
unchanged private-note execution. Independent CPU verification passed on B and
again after recovery in Cloud. The actual local native script engine accepted
the positive fixture and rejected all fifteen negative variants. The independent
B guard stopped the Pod; authenticated provider readback confirmed `EXITED`.
After verified preservation on B and Cloud, the Pod and its local storage were
deleted, confirmed by GET404 and absence from the authenticated Pod list.

This closes the frozen private-state receipt and local native-integration gate.
It does **not** establish canonical TN10 deposit acceptance, settlement or payout.
No TN10 transaction, wallet setup, guest change or automatic retry occurred.

## Frozen claim and deployment

PR46 merged first as `9db923bb7d0e53ac199a362f85f6b1f63716af50`. PR47 was
retargeted to main, its resulting tree and eight green checks verified, then
merged as `d11e38d65f8c5d8309f332c0b7622acc12463020`. Its reviewed tree remained
`9fe787cd0291f5de66ca7ea9ca4584184ae9065a`. No runtime source or frozen artifact
was changed for this run. See the [pre-allocation release](evidence/pre-allocation-release.json),
[original package binding](../evidence/package-identity.json) and
[target](../target.json).

The provider read back the immutable image from [deployment.json](../deployment.json):
`ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:4bd54b3278b827e721f6633b8643020284820a2c4899a0269c5909a74cde5d09`.
The authenticated service scope was `FIXED_PRIVATE_NOTE_ONE_SUCCINCT_RECEIPT`,
with fresh idle state, the correct lease digest and a fresh independent guard
heartbeat. There were 7,132 seconds left at start, exceeding the 3,600-second
whole-job limit plus retrieval margin. One allocation and one start were used.

The proof covers synthetic pending-deposit credit → invalid transfer → valid
transfer, with the reference outcomes `[0, 1, 0]`. The program, wallet VK, proof
bytes, operation input, join control and complete journal stayed fixed:

| Binding | Value |
|---|---|
| Program image | `20d8431e18f42c6e337ab726f166914516e3ebcd70577e67d49e687737901f8b` |
| Join control | `7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e` |
| 352-byte journal SHA256 | `88ba872f3aca413a41b83e91ba40c4eb0b27eb9db31150b7af3d133bb6ccf22e` |
| Receipt SHA256 | `da7c485545c9bbdf08862e987cd5418aaf4eb7e64a833325951d19909150ce46` |

## Actual measurements

| Measurement | Result |
|---|---|
| GPU | One NVIDIA L40S, reported 46,068 MiB, driver 595.91.07, capability 8.9 |
| Provider allocation | 94 GB host RAM, 16 vCPUs; worker affinity four CPUs / four compute threads |
| Complete proof process group | **243.088 seconds**, exit0, no failure; limit 3,600 seconds |
| Producer proof interval | 242.955 seconds |
| Guest execution logged by SDK | 2.657 seconds, included in the proof interval |
| User / total cycles | **139,763,284 / 149,946,368**, within the 160M profile |
| Segments | **143** |
| Succinct receipt size | **223,930 bytes** |
| Peak sampled summed RSS | 746,266,624 bytes, approximately 711.7 MiB |
| Peak matching-process GPU memory | 13,706 MiB, approximately 13.38 GiB |
| Worker process RSS stop threshold | 12 GiB; no address-space limit; cgroup limits were not exposed |
| B independent CPU plus native verification | 0.700 seconds |
| Service startup measurement | 0.260 seconds; not total container provisioning time |

The recorded CUDA prover SHA256 is
`4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb`, unchanged
from the qualified prover. Hardware and raw matching-process GPU samples are
retained in the archive. Summed virtual memory is not physical RAM. RSS/VRAM are
sampled and may miss peaks or double-count shared pages. Kernel CPU time was
193.749 user + 47.668 system seconds. Initialization and compression are inside
the whole-job timer; separate costs for those phases were not measured. This
single tiny fixture does not establish throughput or wallet latency.

## Independent verification and adversarial controls

The candidate receipt was saved before producer checks and is byte-identical to
the final receipt. B recovered the guard's durable archive, checked size/hash,
then ran the trusted separately built CPU and native executables. Cloud recovered
that archive from B and reran the trusted CPU verifier in a separate process.
Both enforce the independently expected image, join identity, exact 352-byte
journal, successful claim, genuine Succinct type, no unresolved assumptions and
development mode disabled. They do not trust the GPU's success report.

The CPU verifier rejected wrong image, changed seal, wrong control, malformed
control inclusion and mutations at all eleven journal field starts. The local
`TxScriptEngine` accepted the correct new receipt with 1,000,000,000 sompi of
fixture principal. All fifteen negative variants rejected: seal, inclusion,
control/image pins, transaction/batch relation pins, old/new roots and tips,
endpoint, anchor, lane, covenant and reserve diversion. Their actual semantic or
cryptographic errors are in [native-verification.json](evidence/native-verification.json);
no timeout, resource failure or panic was counted as a successful rejection.

See [B verification](evidence/b-verification.json) and the
[Cloud recovery verification](evidence/cloud-recovery-verification.json).

## Rental, backup and cleanup

All provider credentials stayed on B. Cloud used the existing TN10 → B management
route, without additional Cloud domains or secrets. The root-prepared independent
guard on B operated without Cloud, gateway or laptop in its runtime path.
The initial container-boot connection error cleared before the pre-start checks.

| Event | UTC, 2026-10-18 |
|---|---|
| Pod `cqmyyr1ho2jhur` actually created | 17:43:27.331 |
| Immutable maximum rental deadline | 19:43:27.331 (21:43:27 Netherlands) |
| Provider-reported `EXITED` status change | 17:50:01 |
| Controller readback confirmed `EXITED` | 17:50:18.112 |
| Deletion confirmed by GET404 and list absence | 17:51:01.083 |

Provider creation to reported stop was **393.669 seconds**, approximately
6 minutes 34 seconds. The 90 GB container disk and 10 GB local volume were
removed with the Pod; no network volume was created. The attempt's guard unit
was then disabled/inactive. See [stop evidence](evidence/provider-stop.json),
[deletion evidence](evidence/provider-deletion.json) and the
[public B lifecycle records](evidence/b-public.json).

The actual GPU quote was USD1.09/hour. Applying that rate and the planning storage
rates to observed times gives **USD0.1208**, approximately **USD0.12**, including
the short stopped-volume interval. Using the later stop-readback time gives
USD0.1260. These are calculated estimates, **not settled invoice charges**;
storage rates and provider rounding need invoice reconciliation. The original
USD5 planning ceiling and two-hour lease were retained. See the exact
[cost calculation](evidence/cost-estimate.json).

The durable terminal archive is 1,070,537 bytes, SHA256
`492869d6eafca82634786d8ae32203d60724699827f756f964e06cfd8bd03128`.
B and Cloud copies were hash-checked and cryptographically verified before
deletion. B retains the archive and verification results under
`/var/lib/kpi-cuda-guard/private-note-20261018-01`; the trusted public verifiers
remain under `/opt/kpi-remote-cuda/private-note-proof-20261018-01`.

## Retained evidence and reproduction

[manifest.json](evidence/manifest.json) binds the evidence files.
[integrity-checks.json](evidence/integrity-checks.json) records that all eighteen
frozen source bindings and the original 174 PR45 / ten PR46 evidence files still
match, and that the returned guest/input/journal match the original target.
[archive-members.json](evidence/archive-members.json) binds every regular archive
member. The [GPU archive](evidence/gpu-artifacts.tar.gz) contains the candidate
and final receipts, public input/program/journal, telemetry, resources and logs.
It contains no wallet witness, proving parameters, service token or account key.

Restore the trusted public package with the existing
`poc/remote-cuda/private_package.py restore` path; check its original source and
binary bindings. Safely unpack the retained GPU archive into a new directory
using the existing package archive checks, then run, in separate processes:

```text
TRUSTED/bin/kpi-private-note-verifier verify-receipt RETURNED/proof/classifier-receipt.bin NEW_CPU_OUTPUT
TRUSTED/bin/kpi-private-note-native verify-receipt RETURNED/proof/classifier-receipt.bin NEW_NATIVE_OUTPUT
```

These are CPU-only verification commands. They neither rent a Pod nor re-prove
the guest. Output directories must be fresh. Recorded reports are evidence of
the observed execution; archive hashes alone are not a security review.

## Remaining gates and adversarial second pass

The initial pending deposit remains synthetic. The relation-domain slots are
monolithic constants, not separate recursive transaction/batch program images.
The local accessor is not a canonical TN10 chain accessor. Mutation rejection
does not establish a separately proved omitted-operation execution. Bob's exit,
permission creation/consumption, actual amount/destination/single-use payout,
rent/fees/refunds and durable parameter recovery still need implementation and
rehearsal. No full-protocol financial privacy, production safety, anonymity-set
size, permissionless operator availability or mainnet claim follows.

Second-pass assessment: unchanged conservation/nullifier constraints and exact
journal verification add no mint or double-spend path; fixture reserve diversion
rejects, but no actual reserve exit was tested. Stale roots/tips and replay-domain
mismatches reject only within this fixed fixture. A missing prover remains a
liveness failure. B root and the trusted compiler/verifier artifacts remain
operator trust assumptions; image hashes cannot eliminate them. Only public
fixture data reached the GPU, but public timing and a four-leaf experimental
note model do not establish practical anonymity. The experimental wallet setup,
one-input/two-output relation and zero application fees remain unchanged.

The next design target is native deposit lineage and Bob's authorized exit/payout
with complete integer-sompi reserve accounting, followed by a separately released
full TN10 rehearsal. This result does not authorize another GPU rental or a
testnet broadcast.
