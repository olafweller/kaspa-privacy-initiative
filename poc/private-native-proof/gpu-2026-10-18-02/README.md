# Four real local lifecycle receipts after the directory correction

**The fixed local four-batch rehearsal succeeded.** All four actual Succinct
receipts were independently verified on B and again in Cloud against the frozen
program, join identity and complete journals. The genuine new exit receipt passed
native permission issuance and restricted payout checks. Each proof batch has
matching-process CUDA evidence. This is local proof/script validation, not a
TN10 broadcast or a production privacy claim.

The first [failed attempt](../gpu-2026-10-18/README.md) is retained separately.
After its stop and deletion, the owner explicitly authorized the small directory
fix and **one fresh attempt**, conditional on regression and image qualification.
The runner now creates both common output parents before invoking unchanged Rust
children. The new real-subprocess regression exercises all nine filesystem stages;
all 29 credential-free orchestration controls pass. The wallet circuit/setup,
guest, VK, wallet proof bytes, public inputs, expected journals, native policy,
compiled proof executable and proof/lease limits did not change.

## Immutable workload and measured execution

- Image: `ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:7f32b3692d174b55c5feb1b7355b087076df4c1107e228c9cd08d621ef4530f0`.
- Image source: `80605a38c06c837afc2c0a9a432032a13b2b069d`.
- Program: `794cfff4cfa509799ec1f6750678d3fe4bc8623522aa647cc65e6b53955c4bc9`.
- Join control: `7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e`.
- Public archive: `f28dfcea27c8c357cece022b7036f013895d907a48b151c4e45d9700f3c2e5a0`.
- Workload: `f723def3f8da9fc63bb2bc08afadbb40745f2a7a3685885793b50b584ecf66fa`.

| Batch | Producer process seconds | User cycles | Segments | CPU verification / CUDA |
| --- | ---: | ---: | ---: | --- |
| Deposit | 27.795 | 551,028 | 34 | Passed / observed |
| Credit-transfer | 194.732 | 93,105,559 | 95 | Passed / observed |
| Exit | 91.679 | 43,964,526 | 45 | Passed / observed |
| Reconciliation | 62.600 | 1,486,804 | 79 | Passed / observed |

The shared process group, including compression, CPU and native checks, completed
in **378.536 seconds**. The worker's full elapsed time including startup and
completion work was **379.676 seconds**, within the unchanged 3,600-second budget.
The nine recorded stages all exited successfully. The native exit stage took
0.081 seconds inside that group; B's entire independent recheck took 1.704 seconds.
Total measured user cycles were 139,107,917 across 253 segments; each frozen
batch retained its 160M execution limit.

The Pod had one L40S reporting 46,068 MiB VRAM, driver 595.91.07, 16 provider
vCPUs and 188 GB provider RAM. Proof processes retained affinity `[0,1,2,3]` and
four compute threads, with the existing 12 GiB sampled-RSS stop boundary.
Sampled peak summed process RSS was **759,599,104 bytes**, about 724.4 MiB;
sampled peak matching-process VRAM was **13,706 MiB**, about 13.38 GiB. These
samples may miss peaks and are not a phone-wallet or production throughput test.
Per-batch process/VRAM samples and the observed container limits are retained.

| Receipt | SHA256 |
| --- | --- |
| Deposit | `cf34430183d4a5c25ae8ddcf57c83a4f587172db1f88aeb8ed998bce7bd199b1` |
| Credit-transfer | `fa79270168d950c6e374a3603983fcc34951701b7df6681ac2f57ffc56f1d2eb` |
| Exit | `3ee87294ce187676557ec3cfc03fa5e7af7ee0969e864443774cb4a05a98a32a` |
| Reconciliation | `ae56737e256191a55845620a17e0a813ce6eaa1130a6ee4cde371336070096b5` |

## Independent cryptographic and native outcomes

B and Cloud each used the trusted, byte-pinned CPU package, never an executable
from downloaded GPU results. Every receipt verifies its exact expected 352-byte
journal, expected program and join control with development mode disabled and
no unresolved assumptions. Expected consecutive state roots and lane tips agree.
For each receipt the existing verifier rejects the wrong image, all 11 journal
field mutations, corrupt seal, corrupt control inclusion and a wrong expected
control through actual cryptographic verification. Independence means separate
processes/hosts using the same reviewed implementation, not two independent
cryptographic implementations.

The genuine exit receipt was passed into the local native permission issuance
and the restricted payout path. The parent native report records
`permissionIssuanceReceiptVerified=true` and confirms that issuance matches the
frozen reconciliation input. Permission transaction ID:
`ef9bfd4093e15da8e831d6bd7dcb874d85930e60e4ca311f438d30fda272c9a1`.
Its input script-unit measurements were `[25006820,0]`.

The payout scripts accept Bob's 400M sompi principal plus 50M permission-rent
refund, leaving 600M reserve change. State-covenant rent of 100M remains separate;
the fixture sponsor pays the 100,000-sompi fee. Underpayment, reserve diversion
and wrong recipient are rejected by the actual script engine. The distinct
payout replay is rejected by the local spent-UTXO fixture, not live consensus.
The frozen reconciliation receipt proves the expected remaining private value
and reserve with Bob's paid exit cleared.

The nested `payout` helper retains its old standalone synthetic-issuance label
and `permissionIssuanceReceiptVerified=false`: that helper does not repeat receipt
verification. The **parent** native invocation verifies the genuine new receipt
and actual receipt-bearing issuance before invoking the payout checks. The two
fields must not be combined into a claim that the helper independently verified
another issuance. Full reports are preserved without editing their labels.

## Preservation, stop, deletion and costs

Pod `2kh9nm61nffwwf` was created at **21:15:50.779 UTC**, with a lease ending at
23:15:50.779 UTC and B's proactive stop boundary at 23:14:50.779 UTC. It started
promptly, with 7,143 seconds remaining and the stricter transfer-margin check.

The unchanged independent guard initially recorded a 10-second download timeout
for the final archive, then recovered through its own retry. It durably saved the
2,465,830-byte archive with SHA256
`056058ffdbc808ca8a77b4442495f3db6bb266dea3f710736a4bc9f693a97b6e`.
No manual backup, manual stop, guard-code modification or lease extension was
needed. It requested and confirmed provider `EXITED` after its terminal-backup
grace, around **21:25:11 UTC**. B and Cloud revalidated the external copies and
all proofs before deletion.

Deletion of the Pod, 90 GB container disk and 10 GB local volume was confirmed
at **21:26:10.221 UTC** by API 404 and absence from a successful list response.
No separate network volume existed; the account then had zero Pods. The second
guard is disabled/inactive and both attempts' B state/evidence remain preserved.
The administrative gateway was not a runtime dependency of B's guard.

At the actual USD1.09/hour quote, provider creation/exit text implies about
560.22 seconds compute and **USD0.1696** compute cost. A conservative estimate
using the later EXITED observation plus storage through deletion is **USD0.1755**.
Including the earlier separately released failed attempt gives approximately
**USD0.2206** combined. These are rate/timestamp estimates; no itemized invoice
was available. The USD5 allowance was a planning limit, not a provider invoice cap.

## Reproduction and limits

Run the hash, exact-journal, genuine receipt, native and cleanup evidence audit:

```bash
python3 poc/private-native-proof/gpu-2026-10-18-02/check_evidence.py
```

This uses the restored trusted package for **CPU verification only**; it does not
start a proof, GPU, provider request or TN10 transaction. The archive, individual
receipts and B/Cloud reports are retained under [evidence](evidence/result.json).

This completes the scoped **local** proof/native-script lifecycle rehearsal.
Canonical TN10 anchoring, full transaction consensus/size/mass/fee acceptance,
funded permission issuance and actual chain payout still require a separately
released experiment. The fixture supports one pending exit, one sufficient
selected reserve with positive change, and the restricted transaction shape.
No general multi-exit reserve selection, anonymity/security claim, wallet-device
benchmark, production fee model, mainnet use or new circuit/setup follows from it.
