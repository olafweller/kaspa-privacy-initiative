# Concrete next task: one complete private-state receipt and local native checks

Status: proposed software/proof work after the completed 160M CPU calibration.
No GPU rental or proof job is started/authorized by that CPU-only instruction.
No new cryptography, wallet setup, opcode, infrastructure design or TN10 broadcast.

## Exact proof target

Use [calibration-160m/next-proof-target.json](calibration-160m/next-proof-target.json)
as the machine-readable manifest. Freeze before any proof job:

- Aggregate/monolithic program image:
  `20d8431e18f42c6e337ab726f166914516e3ebcd70577e67d49e687737901f8b`.
- Wallet VK:
  `d3c179aae5c2c6c013b1de1da5ad4412e4b2c8bae7288c0b9d85e0c986b5a3ec`.
- Original public input/proofs and 352-byte expected journal SHA256:
  `88ba872f3aca413a41b83e91ba40c4eb0b27eb9db31150b7af3d133bb6ccf22e`.
- Transaction relation slot:
  `8879a9eca31d685b5f93fa534c612bd5e8eae4990e9c0994b8209a06c9f69e38`.
- Batch relation slot:
  `ec9dcba9919849d591c009a81c790d343748d034d4f9507d4b471dcef4d7d5b1`.

Those last two values are monolithic relation-domain constants, **not** compiled
recursive transaction/batch images. There are no separate new recursive program
identities or receipts to infer from this target. Reuse the existing RISC Zero
Succinct route directly; no extra outer Groth16 wrapper is necessary.

The actual claim is a private state transition from an already registered
synthetic pending deposit, through credit -> invalid transfer -> valid transfer.
Permission and deposit journal slots are both zero. It proves neither original
native deposit acceptance nor Bob's exit/payout. All old/new state/tip, covenant,
seqcommit and lane-key bytes are independently fixed in the target manifest.

## Local preparation before requesting paid deployment

1. Add fixed `prove` and separate `verify-receipt` entry points for this target.
   Reuse the receipt handling in `poc/outer-proof-128m/host.rs`: request
   `ProverOpts::succinct()`, require `InnerReceipt::Succinct`, successful expected
   image, `VerifierContext.with_dev_mode(false)`, no unresolved assumptions and
   byte-exact expected journal. Never accept a fake/composite substitute or host
   success flag. Pin the new producer and independently built CPU verifier.
2. Extend the existing fixed remote workload/service/package for this program,
   exact public input and journal. The old `full_worker.py` invokes the proxy
   classifier-specific host and cannot run/verify this new 352-byte target as-is.
   Reuse its authenticated fixed-job interface, one-attempt marker, telemetry,
   backups and independent B guard; do not build another infrastructure system.
3. Reuse the qualified RISC Zero 3.0.3 CUDA prover. The prior full image is
   `ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:fb6af438a2f4735b878d07ea5ddfd709c4bd7ecf4b4327df4314286076eb51a6`.
   Its prover SHA is `4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb`.
   A new package/host requires its own immutable image digest and CPU startup/
   fixed-token/identity smoke checks; the old image digest does not qualify the
   new producer. Wallet keys/openings/paths/149MiB wallet PK never enter the GPU.
4. Prepare a local native fixture verifier using the existing `Settlement::build`
   / `TxScriptEngine` path in `poc/takeover/host/src/main.rs`, with actual new
   program identity and the exact relation slots, roots, covenant and lane key.
   Replace that helper's hardcoded reference batch-image derivation for this
   explicitly monolithic target. The native fixture reserve must back the full 1,000,000,000 sompi pending/private principal; do
   not reuse the old helper’s 100,000,000-sompi fixture value. Keep state rent
   and sponsored native costs separate. It must not pretend to authenticate
   the initial synthetic deposit. Do not use development mode or fabricate a
   receipt to pass.

## One bounded future GPU proposal

After reviewed software preparation and separate owner release: one L40S 48GB,
one attempt, explicit 160M execution profile, <=3600s entire process group
including Succinct compression/resolution, <=7200s rental from provider creation.
Fresh independent B lease/guard; no reset/restart of old deleted Pods. Use only
B's existing credentials and the Cloud -> TN10 -> B management route.

Obtain current actual GPU/storage quote; plan <=USD5 and <=2h total runtime.
No guaranteed provider-invoice cap is implied. The old 121-segment proxy receipt
cost/time is historical; this target has 143 segments, but that ratio is not a
measured GPU duration/cost forecast. Preserve immediate receipts/results, copy to
B, independently CPU-verify, and require a confirmed provider stop. Resource
failure stops the attempt without automatic retry or budget increase.

## Required checks with the returned genuine receipt

| Check | What a passing result closes | What remains open |
|---|---|---|
| Independent CPU image/journal/seal verification; wrong image, tampered journal and seal reject | Actual proof of this exact monolithic private-state execution | Separate recursive transaction/batch/aggregate proofs are absent. |
| Existing native script engine accepts correct fixture settlement with the genuine seal/control proof | This new image's 352-byte ABI/control/seal and state/endpoint coupling under the fixture accessor | Synthetic block/seqcommit accessor is not canonical TN10 acceptance. |
| Wrong predecessor root/tip, endpoint, covenant or program pins fail at actual native enforcement with the unchanged genuine receipt | Rejects reuse of this claim against a mismatching native fixture | A genuinely proved omitted-operation run needs its own separately approved proof; mere receipt mutation does not close omission. |

No exit permission or payout is in the proof target. Actual deposit lineage,
stable owner recovery for unusable verifier versions, exit permission creation/
consumption, exact payout amount/destination/single use, native fees/rent/refunds
and durable public parameter/data recovery remain explicit later gates.
A fresh deposit -> credit -> Bob4/change6 -> Bob exit4 -> actual payout4 TN10
rehearsal requires their complete implementation/rehearsal and separate release.
