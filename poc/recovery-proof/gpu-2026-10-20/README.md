# Six real recovery lifecycle receipts and both native withdrawals

**The bounded local rehearsal completed.** Six final Succinct receipts verify
against the frozen new guest, Join control and exact journals. B and Cloud each
repeated trusted CPU verification, including all 90 cryptographic mutation checks
and both proof-authorized native permission/payout paths with 17 semantic
rejection variants. Matching-process CUDA activity is present for every batch.
This completes this local proof milestone; it is not a new TN10 transaction or
independent-user shutdown/recovery demonstration.

PR57 was merged as `c4dc4d8126c5497447760828ffc10382609d49a4` after checking the approved
`f9a4ec0` head and thirteen successful checks. The owner released one L40S attempt
under the existing limits. The extractor correction remained B-side; this run
used the already published immutable image without rebuilding it. Historical
preparation evidence, inputs, journals, wallet relation/VK and guest are unchanged.

## Frozen workload and measured results

- Image: `ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:442bc15d6d4cece6e0cd28b30862a0a9c15c64c67a637275fd45ea648600a628`.
- Image source: `5e9a5c3c47c00dcf3d483cce7eaa1a2471e6a300`.
- Guest image: `095a2fb2f58c350ccd2688ae7f72748c915bd973c60fd4abaa8d87b282ad68b5`.
- Join control: `7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e`.
- Public package: `42aae900499190386464c36208c0aa2a4b3e6c102e443ff99a714ef8469656c4`.
- Producer/verifier binary: `b90c13fea98b941a661e2d13ba8ddc96dc79418f2366c25ff4e53747f603ab9d`.

| Batch | Producer process seconds | User cycles | Segments | CPU verification / CUDA |
| --- | ---: | ---: | ---: | --- |
| deposit | 28.087 | 552,697 | 34 | Passed / observed |
| credit-transfer | 316.625 | 139,741,397 | 143 | Passed / observed |
| bob-exit | 98.924 | 43,994,671 | 46 | Passed / observed |
| bob-reconcile | 65.392 | 1,496,280 | 79 | Passed / observed |
| alice-exit | 99.656 | 44,189,850 | 46 | Passed / observed |
| alice-reconcile | 70.534 | 1,623,712 | 85 | Passed / observed |

The full worker completed in **683.024 seconds**;
the shared proof/check process group took 681.657
seconds. All fourteen stages exited successfully within one 3,600-second timer.
Deposit and both reconciliations used segment limit 2^16; credit-transfer and
both exits used 2^20. Every batch stayed below 160M user cycles. There was one
start and no automatic retry, fresh setup, guest change or statement expansion.

The GPU reported 46,068 MiB VRAM, driver
595.91.07 and compute capability 8.9.
Provider allocation was 188 GB RAM and 16 vCPUs; the proof group used four CPU
threads and the recorded CPU affinity. The existing sampled-RSS stop boundary
was 12 GiB. Peak sampled summed process RSS was
791,191,552 bytes (754.5 MiB);
peak matching-process GPU memory was 13,706 MiB.
These samples can miss peaks and double-count shared host memory. Raw samples,
stage times, process IDs, GPU identity and limits are retained.

| Receipt | SHA256 |
| --- | --- |
| deposit | `3a4c76ab02f878a7b1feef9b41b4733f251ed7e89a7c864e0e6f7fe261629228` |
| credit-transfer | `1f8582bb081685db41c63b480a82f07dff11e9c335a7aaf8a662ae8ad1b43c1a` |
| bob-exit | `f8e99ba7a78cd0976616583617b16e4f5ab712e1475e063067f8f47c432ee4c3` |
| bob-reconcile | `9dc92760e729e30712ee29b4ab706873de3a1919b1a2a4bc8e66876813ad9b42` |
| alice-exit | `11b5abd135045f392ec32013b8f3cf52837ced34f31622b27102b9b8cc239789` |
| alice-reconcile | `bced678527a331f4f7b2162b6d796648964c5ef1e8a876b5296b2909a1ab2fcb` |

## Proof and native accounting checks

B used its prequalified package; Cloud independently restored the same pinned
package. Neither executed a downloaded GPU binary or accepted GPU metadata as
verification expectations. Every receipt binds the independently expected new
program, exact 352-byte journal and Join control, with development mode disabled
and no unresolved assumptions. Consecutive state roots/lane tips retain the
reviewed continuity. Each verifier rejects eleven journal-field mutations, a
wrong program, corrupt seal, corrupt control inclusion and wrong expected control.
Independence here means separate hosts/processes using the same reviewed
implementation, not separately developed verifiers.

Both genuine exit receipts authorize their native permission issuance in the
actual pinned TxScriptEngine. The resulting issuance and signed payout IDs match
the subsequent frozen reconciliation input:

| Exit | Permission transaction ID | Payout transaction ID |
| --- | --- | --- |
| bob-exit | `484ef8c8ea48083a8b7c4713387c90a1a9d61a493180344722dd828cd6455e84` | `4795347a068ee17f7410893f6299ee42cceabc55994f622f4e93d31c9422aa87` |
| alice-exit | `846f4ede996f7caa910179d29ddca9e0d4b47cd88d0a4e31f5bbcfdc52b651bb` | `5f8116631f1487a724722455032678d666c227cf1341df19e30f97a7a2f1696e` |

Bob receives 400M sompi principal plus 50M permission-rent refund, leaving 600M
reserve. Alice then receives 600M principal plus her separately sponsored 50M
permission-rent refund, consuming the last selected reserve with no zero-valued
reserve output. Final reserve principal, private liability, pending deposits,
unpaid exits and outstanding permission rent are all zero; **100M sompi state
rent remains separate**. Sponsor fees and rent do not become private principal.

Eight semantic native attacks per exit reject underpayment, wrong recipient,
default lane, foreign reserve, extra sponsor input/output and partial permission
forms. Alice's ninth attack adds a forbidden zero-reserve output. These are
specific script rejections, not resource failures. This native fixture still
uses synthetic UTXOs and a fixed chain accessor; its acceptance is not live
consensus, canonical funding or actual payout confirmation.

## Independent preservation and cleanup

Pod `lwg8z2huy343fa` was created at **2026-10-20T07:55:12.118+00:00**. Its
absolute lease ended at 2026-10-20T09:55:12.118+00:00; B's proactive stop boundary was
60 seconds earlier. Start preflight read back the actual immutable image, exact
`FIXED_RECOVERY_SIX_SUCCINCT_RECEIPTS` scope, fresh idle attempt, actual creation
binding, resources and guard heartbeat, with more than 3,960 seconds remaining.

B's independent guard preserved the final 3,386,420-byte
archive (`46f0c06aa7f465753b8f13bb1b06dc001eb532793dd3e4132d937286b9b77b9f`). B and Cloud revalidated its hash/size
and independently verified all six final receipts and both native exits before
deletion. The guard confirmed provider `EXITED`; the provider reported
`Exited by user: Tue Oct 20 2026 08:08:40 GMT+0000 (Coordinated Universal Time)`. No manual stop or lease extension was
needed. A boot-time HTTP error before the service became ready is retained;
the guard recovered and supplied fresh heartbeats before proof start.

Deletion was confirmed at **2026-10-20T08:09:35.735+00:00** by GET 404 and absence
from a successful Pod list. The 90 GB container disk and 10 GB local volume were
removed; no network volume was created. The account then had
0 Pods. This attempt's guard is disabled/inactive;
B retains its archive, results and trusted package. Cloud, gateway and laptop
were management paths, not runtime dependencies of the B guard.

The actual quote was USD1.09/hour. Provider creation/exit
text implies approximately 807.88
seconds of compute and USD0.2446 compute cost. Using the
later confirmed-stop observation and storage through deletion gives a conservative
**USD0.2622 rate/timestamp estimate**.
This is not an itemized invoice; taxes/billing adjustments are unknown. USD5 was
a planning allowance, not a provider-enforced billing cap.

## Reproduce and next boundary

```bash
python3 poc/recovery-proof/gpu-2026-10-20/check_evidence.py
```

This checks the retained manifest, safely extracts the bounded archive, restores
trusted binaries and repeats real CPU receipt/native verification. It performs
no proving, provider requests, funding or broadcast. The new CI job runs this
same check. [Result](evidence/result.json), [B audit](evidence/results/b-verification.json)
and [cost estimate](evidence/cost-estimate.json) retain machine-readable details.
[Historical operator sources](operator/README.md) document this one authorized run.

The next remaining live gate is a **fresh TN10 instance** with actual accepted
captures, new proofs for those inputs and independent user recovery/withdrawal
through the final drain after the original service is unavailable. The old PR54
instance and its reserve are untouched. No permissionless data-availability,
independent custody, anonymity, production security/throughput or mainnet claim
follows from this fixed public-fixture rehearsal. No further rental or TN10 work
is released by this result.
