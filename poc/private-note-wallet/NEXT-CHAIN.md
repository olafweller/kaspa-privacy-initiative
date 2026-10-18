# Bounded next chain and fresh TN10 plan (proposal, not executed)

This package implements a real local wallet relation and real-proof application
kernel. The native facts are fixtures; an application kernel is not an outer
state proof or a confirmed native payout. Do not reuse the old public delegate
funding script as if it implemented private credit/recovery.

1. Freeze the measured circuit, canonical 410-byte statement and 14 public Fr
   limbs, actual VK hash, accepted ciphertext encoding and state serialization.
   Port the real-proof state kernel into the new transaction/classifier guest,
   with the qualified ordinary BN254 verifier and strict encoding/curve/subgroup
   checks. Qualify the new VK and all 14 full-width packed field inputs against
   the native Arkworks reference and existing adversarial proofs; the old four-packed-field-input
   backend measurement does not qualify this new configuration by itself.
   Independently pin the new classifier image before execution. Keep the
   24-case/PR43 receipts as historical baselines, not this new guest's identity.
2. Replace authenticated native-fact fixtures with actual accepted native input,
   pool script/value/deposit descriptor and permission-consumption/output facts.
   The transaction journal must bind old/new note/nullifier/deposit/exit states,
   deterministic verdict and complete native lane ID/context. Fold every lane
   input, including rejected proof payloads, through batch/aggregate. Require
   current nullifiers across two batches/competing proofs at an old allowed root,
   atomic malformed/invalid-then-valid rejection and credit/refund/payout replay.
3. Use the existing 352-byte aggregate/native ABI and RISC Zero Succinct route.
   There is no assumed extra Groth16 conversion of the outer receipt. Check a
   genuine new aggregate locally with the native script engine, then omission
   with the same endpoint and underpaid/diverted/reused payout failures at their
   actual enforcement layer. Record every new program/VK/control identity.
4. Execution-only calibration proposal: at most 128M cycles/900s for each selected
   complete sequence on four compute threads; actual failures do not count as
   successful rejection. Stop and report if that profile is insufficient.
   Only after measured suitability propose one complete receipt on one L40S,
   3600s whole proof job, RSS policy without RLIMIT_AS, new independent B lease
   <=2h from creation, actual quote/storage plan <=USD5, no automatic retry.
   This document does not allocate a GPU or silently lift previous budgets.
5. Verify the whole new receipt on independent CPU against independently expected
   image and exact journals, no unresolved assumptions/development mode. Repeat
   wrong-image, journal/claim and seal mutation controls; retain evidence and
   confirm provider stop. Remote proof inputs contain no wallet witness material.
6. Before a fresh unfunded/testnet rehearsal, define actual deposit descriptors,
   current-state owner recovery and unpaid liabilities, native fees/rent/refunds,
   public accepted ciphertext/commitment retention and Bob's independent scan/path
   reconstruction. Then execute one fresh TN10 identity: actual 10 deposit ->
   proof-authorized credit -> Bob4/change6 -> Bob's own proved exit4 -> actual
   accepted native payout4. The 10/4 native values are public and correlate; the
   rehearsal is not an anonymity or N-user shutdown claim. No mainnet/funds.

New tree capacity, nonzero private fees, migration and a production setup need
separate decisions. One local four-leaf demonstration cannot close those gates.


Checkpoint 2026-10-18: the [next calibration](../private-note-chain/RESULTS.md)
fixes the target TN10 domain and new identities, integrates native preimage and
current-state checks, and passes 21 selected executions. The complete three-proof
sequence reaches 128M incomplete. No budget increase, native acceptance or rental
is implied. Actual recursive/native bindings are tracked separately.
