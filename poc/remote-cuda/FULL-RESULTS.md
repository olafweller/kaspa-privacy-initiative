# Complete compact-wallet classifier receipt — 2026-10-18

**One real succinct receipt for the complete existing valid–invalid–valid
classifier execution was produced on the qualified L40S/CUDA route and verified
independently on CPU.** The independent B guard stopped the new Pod; separate
provider read-back confirmed EXITED. There was one attempt and no lease extension.

This closes the missing outer-receipt milestone from PR39 for the existing small
test relation. It does not add the full private-note circuit, a private payment,
a new TN10 transaction or native settlement for that privacy relation.

## Preserved statement and qualification

The classifier image remains
`397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.
The original wallet circuit/VK/proofs/operation fixtures and full expected journal
are unchanged. The hash-bound PR39 archive supplies 116 required public input,
expectation and qualification files. Its 24 qualified execution cases were reused;
a separate CPU check and the existing proof host gate validate their exact
program/input/journal/resource bindings. No 24 extra proof jobs were run.

The complete 167-byte journal binds the ordered root, initial balance, all three
native IDs, outcomes and balances. The root is
`ba3987f8b58cf47dc711923064710e42aa52258039c4d52a645937519f9cc2f0`.
The outcomes are **[0, 3, 0]** and proxy balances
**[600,000,000, 600,000,000, 500,000,000]** sompi, starting from 1,000,000,000.
See [the independently expected statement](evidence/full-classifier-2026-10-18/expected-statement.json).
The invalid middle operation is rejected and the later valid operation proceeds.

## Actual proof and resources

| Measurement | Observed result |
|---|---:|
| Succinct prove API, including its receipt checks/saving | 248.256 seconds |
| Supervised proof process, including pre-proof execution | 252.711 seconds |
| Whole GPU worker, including startup/snapshots | 256.076 seconds |
| User cycles | 117,473,222 |
| Total cycles, including paging/reserved | 125,960,192 |
| Execution segments represented by the completed receipt | 121 |
| Serialized complete classifier receipt | 223,560 bytes |
| Peak sampled summed process RSS | 748,212,224 bytes (0.697 GiB) |
| Peak sampled matching-process GPU VRAM | 13,706 MiB (13.385 GiB) |
| GPU activity for the actual prover process | Observed |
| Compute affinity / thread settings | CPUs 0–3 / four compute threads |
| Kernel wait user / system CPU | 194.898 / 54.849 seconds |

These are measurements for this three-operation fixture, not throughput or
private-payment cost measurements. Summed RSS/VRAM are sampled and can miss
peaks; RSS can double-count shared pages. Helper OS threads are separate from
four compute-thread settings and four-CPU affinity. CUDA reserves over 100 GiB
of virtual address space; the qualified GPU wrapper has no RLIMIT_AS and retains
the 12 GiB sampled summed-RSS stop policy. The one-hour whole-job timer included
all execution, proving, succinct compression/resolution and host receipt work.

The prior CPU run stopped at 3,600 seconds without a receipt. That is not a
completed CPU proving time, and the memory policies differ; no full-proof
CPU/GPU speedup ratio is established by dividing those two measurements.

The exact qualified RISC Zero 3.0.3 CUDA binary is unchanged:
`4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb`.
The new derived image is
`ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:fb6af438a2f4735b878d07ea5ddfd709c4bd7ecf4b4327df4314286076eb51a6`.
It keeps the original GPU-qualified base image and proof-host binary, adding only
the separate static job/package. The independent CPU verifier is separately built
and pinned to SHA256
`90be6101639335feee8ccb1c75d2188750e0293d37c8c8d9e2471c71d2996eaa`.

## Independent cryptographic acceptance

The GPU's host saves the returned candidate receipt immediately and writes the
completed classifier receipt after its checks. B backs up the complete archive
with verified size/hash and durable atomic storage. Cloud then retrieves the
archive through the existing TN10 → B management route and checks every returned
public input against the locally trusted package before separate CPU verification.
No additional Cloud secret/domain was needed; provider/service tokens stayed on B.

The trusted CPU verifier accepted a genuine succinct receipt against the fixed
expected image, successful program exit, empty assumptions and exact full journal,
with development mode disabled. Actual receipt verification also rejected:

- A wrong expected program image.
- Five journal mutations: ordered root, initial balance, native ID, outcome and
  final balance (offsets 0, 32, 44, 76 and 166).
- A corrupted succinct seal.

See [independent verification](evidence/full-classifier-2026-10-18/independent-verification.json).
The receipt SHA256 is
`9e68cda38325f673d00734433a1bd7b127fab20ac88f16aad948f2bec1492186`.
The original 899,488-byte archive SHA256 is
`6bfb8b8851d6188ac7822ebc08fa309886c13da73f175bb70c8a27f275677969`.

## Lease, stop and costs

New Pod `wzozsg2nej95tb` was created at **11:43:01.410Z** with one L40S,
125 GiB host RAM, 32 available vCPUs, 90 GB container disk and 10 GB `/workspace`.
Actual quote/read-back: **USD 1.09/hour**. Its separate immutable lease deadline
was **13:43:01.410Z**, with guard stop/retry beginning one minute earlier.

After the completed archive was backed up, B stopped the Pod following its
60-second terminal grace. Separate provider GET confirmed **EXITED at 11:49:24Z
(13:49:24 Europe/Amsterdam)**; the guard unit exited normally. The observed
creation-to-confirmation window is 383.25 seconds, corresponding to approximately
**USD 0.116 of GPU compute** at that quote. This is an observed-window estimate,
not an invoice or guarantee of billing boundaries. Actual settled charges are not
available from the used Pod read-back. Storage planning rates remain the rounded
owner references, not independently returned final storage quotes.

Results and the independent CPU report remain on B at
`/var/lib/kpi-cuda-guard/full-20261018-01/results`; the original archive is retained
under its hash in the sibling `artifacts` directory. The completed prior PR42 Pod
`qaxhwjd6e1b4bg` and its evidence were preserved. Both stopped Pods' 10 GB volumes
remain; no volume/Pod was deleted. Retention/storage cleanup and invoice
reconciliation remain separate. No proof retry, budget increase, new wallet
setup, private witness upload or new TN10 transaction occurred.

## Research conclusion and remaining work

The existing compact wallet proofs can now be processed as a complete, ordered
valid–invalid–valid batch inside the unchanged classifier and represented by one
independently verified succinct outer receipt within the declared GPU budget.
This is the complete test-model proof milestone, not a completed privacy protocol.
The full private-note relation, witness protection and eventual native settlement
integration remain subsequent work. Larger batches, mobile wallet performance,
real fee economics and production operation are not measured by this attempt.

[The evidence directory](evidence/full-classifier-2026-10-18/README.md) contains
receipt, original archive, manifests, expected statement, resources and stop read-back.
