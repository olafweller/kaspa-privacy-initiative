# Concrete TN10 recovery run procedure — no execution release

1. **Prepare before rental.** Record immutable image/host/guest/control/source
   identities. Run the trusted native/receipt tests and pulled-image CPU smoke.
   Keep the owner's public receive files and unfunded trial out of Git/image.
   Install the trusted host on TN10/B and Mint without transferring user secrets.
   Deliver and hash-check the existing public parameters on Mint. Owner confirms
   a fresh working restore path and backups; both logical users remain owner-run.
2. **Freeze the outage contract.** Inventory actual run-scoped original controller
   PIDs/unit/working-directory/data paths. Identify the public history captured
   before shutdown, replacement B access and a restart plan. Establish that cold
   recovery cannot read the original controller cache. Do not stop native TN10,
   Cloud gateway, B guard, unrelated history/observer services or the prover.
   No unavailable-service claim is valid without recorded process/access checks.
3. **Fresh native initialization after a separate funding release.** Use only a
   new trial and the recovery lane-restricted bootstrap. On TN10 run the trusted
   native capture validator (`seed`), build/sign bootstrap → initialize → deposit,
   and confirm actual accepted transactions/UTXOs. Keep 10 KAS principal, 1 KAS
   state rent, two sponsored 0.5 KAS permission rents and fees separately booked.
   Preserve the prior PR54 pool; do not reinterpret its guest or remaining funds.
4. **Lease after a separate GPU release.** Check B NTP/storage, one L40S/storage
   quote within USD5 planning, fixed image and a fresh trial-bound runtime package.
   Supply the exact public trial JSON as base64 via B; the account key stays on B.
   Bind lease to actual creation, at most 7200 seconds, activate the independent
   B guard and require its fresh heartbeat. Require >3960 seconds at first proof.
   Start promptly: 3600 seconds jointly includes all six proof stages **and chain,
   local-wallet and management waits**. No retry, reset, extension or budget raise.
5. **Freeze/prove/settle each stage.** Run `freeze VALIDATOR VALIDATOR_SHA PROGRAM
   STAGE COMPLETE_CAPTURE PRIOR_CHECKPOINT NEW_TARGET_DIR` on trusted data. B
   retains its target hash, program, public input and complete expected journal
   before approving/uploading that one stage. Deposit/reconciliations use 2^16;
   payment/exits use 2^20, each at most 160M cycles. Run independent CPU verification
   before signing settlement; recheck current state UTXO, native anchor eligibility,
   signed layout/budgets/mass/fee and actual chain acceptance. `checkpoint` validates
   the accepted interval and successor. Capture from the prior proven endpoint;
   never skip proof waits or substitute a newer anchor for a frozen receipt.
6. **Owner-local payment.** After accepted deposit, give Mint the public state,
   trusted trial, parameters and independently accepted root. On Mint only:
   `kpi-recovery-tn10 wallet TRIAL STATE EXPECTED_ROOT OWN_ALICE_BACKUP PARAMETERS
   credit-transfer NEW_PUBLIC_OUTPUT`. Verify public operation envelopes and
   publish credit/payment with distinct native funding. Retain the existing
   invalid-operation control if included; invalid native publications still spend
   their funding. Complete the accepted credit-transfer proof/settlement.
7. **Actual interruption and cold recovery.** Stop the contracted original
   controller, confirm unavailability, retain public history externally. On Mint
   restore each own backup into a fresh private directory. Rebuild using the new
   relation wallet tool from ordered public inputs and independently checked
   start/end roots. B starts the replacement controller from public evidence;
   it must not fetch the original wallet/operator cache or user keys.
8. **Sequential exits.** Mint prepares `wallet ... bob-exit ...`; only its public
   operation and payout public key leave Mint. Freeze/prove Bob's exit; use the
   real receipt to issue permission, sign/accept payout, then freeze/prove/settle
   bob-reconcile. Obtain the new accepted root before Mint prepares `alice-exit`.
   Use its new receipt for full permission consumption and final payout: three
   inputs/two outputs, no zero reserve output. Prove/settle alice-reconcile.
9. **Success checks.** Independently verify six **final** receipts with mutation
   controls and genuine native issuance/payout checks. Require matching-process
   CUDA for each stage. Confirm both native payouts and spent permissions/reserves
   on TN10. Final user principal/liabilities/pending deposits/exits must be zero;
   1 KAS state rent remains separate. Reorg/spent/stale anchors abort safely and
   preserve evidence; they do not authorize an automatic new proving attempt.
10. **Preserve/stop/delete.** B's corrected bounded extractor and trusted verifier
    check returned bytes against independently stored targets; candidates/partial
    sets stay labelled. Preserve all accepted captures, signed layouts, stage and
    CUDA logs and exact cold-recovery/outage evidence on B. Confirm provider EXITED
    on every outcome; verify external copies before deleting Pod/local storage and
    confirming 404/list absence. Restore only originally active contracted services.
    Report actual rate/time/storage estimates separately from an itemized invoice.

This document and preparation runmanifest authorize none of funding, broadcasting,
rental, new outer proving or stopping existing services. The next live release
must refer to its concrete qualified image, native trial and outage contract.
