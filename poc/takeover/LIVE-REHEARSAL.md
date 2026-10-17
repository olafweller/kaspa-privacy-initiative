# Fresh recursive TN10 rehearsal

Owner authorized proceeding on 2026-10-17 after local review commit `35b84c1`.
Test-KAS only, a fresh public-account instance, no old funded output changes.
No mainnet, private-state or independent-operator claim is made.

Status: fresh rehearsal preparation. Node observed synchronized on testnet-10,
version 2.1.0 with UTXO index. Existing root terminal and localhost native wRPC
are reused. Separate new user and fee keys are created on the VPS only; the
existing test sponsor funds the fresh fee wallet. No key contents leave the VPS.

## Route and enforcement

1. `remote/run.mjs init` creates a fresh unfunded identity in one command.
2. `prepare` funds the new fee/user wallets, seeds a random user lane, bootstraps
   the fixed reviewed program images, confirms a ten-test-KAS native deposit and
   retains a public prefix capture. The Cloud prover credits it with a real
   transaction/batch/aggregate chain; the VPS submits and confirms that settlement.
3. The original finite executor exits. A stop record checks the current state
   UTXO and records a recent selected-chain anchor whose authenticated lane tip
   still equals the confirmed checkpoint tip. After more than 100 additional
   blue scores, a new authorized four-test-KAS withdrawal is published.
4. Public captures are replayed in a separate clean Cloud directory from zero
   state, with no original executor database or saved account state. The replay
   must match the real checkpoint state/tip and the new prior-state binding.
   Catch-up starts at the recent stop anchor: its authenticated unchanged lane
   entry bridges the idle period without downloading thousands of unrelated
   blocks that accumulated during prefix proving. This uses the same node and
   owner, not an independent operator or unavailable-archive recovery.
5. Prove the withdrawal and a separate omitted-input control against the same
   actual endpoint. The node must reject the omitted settlement for native ZK
   integrity and accept the full settlement. Then exercise the native permission
   payout and its balanced negative controls; confirm payout, reserve change,
   consumed permission and final backing/fee reconciliation.

Every broadcast has a write-once submission intent. Transport errors are not
classified as native rejection; inspect actual outcomes before any next action.
There are no automatic mutation retries. A failed trial uses a fresh identity.
The normal node is not stopped or restarted.

The omission control leaves an empty batch. The bundle host now tests wrong
transaction receipts only on nonempty batches: an empty batch has no such
assumption. This corrects the test runner's applicability check without changing
any guest, state relation, verifier pin or funded covenant. The seven native
adapter tests pass after this host-only adjustment. Node-script syntax is included
in fast CI checks.

Actual transaction IDs, resources, elapsed scores, node outcomes and final
qualification will be recorded here after execution. The complete confirmed
native payout is required before calling this rehearsal successful.
