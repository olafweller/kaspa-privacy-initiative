# Second pass — actual-chain adapter and local user custody

- No new monetary relation: the guest/common relation, wallet VK/circuit and
  native restrictions remain pinned. The bootstrap's recovery-state tag and
  covenant-dependent root must exactly reconstruct the restricted state script;
  native tests reject wrong root/lane/rent/authorizing input/output shape.
- Principal vs rent: the new signed payout builder emits reserve change only
  when positive. Bob and Alice native receipt-based tests execute all scripts,
  preserve proof compute budgets and reject underpayment/destination/lane attacks.
  Only the proof-authorized ledger destination is used; no operator recipient
  override/admin release exists. Full drain removes the selected reserve and
  keeps state rent separate. Historical PR54 funds cannot be upgraded by this code.
- User secrets: init imports only the exact receiving schema/domain and distinct
  public keys. The operator creates only its own unfunded sponsor key. Credit,
  transfer and exits run locally against an independently supplied state root;
  wallet backups/native keys are not sent to Cloud/B/GPU or committed to Git.
  Same-owner role administration remains trusted, not independent-human custody.
- Public destination privacy: receive records have no native payout key. The
  user's local native key appears publicly only in its EXIT payload, already bound
  by its wallet proof/current-nullifier checks. No hidden witness is exported.
- Untrusted prover: the trusted B target hash precedes upload; full journal,
  guest/control, input and program identities are validated. The service accepts
  no executable uploads. Separate B verification uses its trusted binary and
  target copies; candidate verification does not equal six final receipt success.
- Replay/order: all six stages and 16/20 profiles are fixed. Roots/tips/protocol
  fields must continue; each accepted checkpoint requires exact transactions in
  a complete native-validated interval. Proof waits and prior settlements are
  included. A submit success flag cannot manufacture accepted native context.
- Process loss/cost: one durable shared hour counts interstage waits. The external
  process-group timeout survives controller loss. Restart cannot replay a consumed
  stage or lease; duplicates return the existing job. B's independent guard still
  handles absolute rental stop and durable backup/confirmed provider stop. No
  provider, rental or existing-service mutation occurred during this preparation.
- Private run binding: the public image contains only generic code/binary/guest.
  An allowlisted public trial is validated before persistence, bound once on the
  volume and reused byte-for-byte. B independently derives the same policy hash;
  JSON normalization cannot silently produce a different GPU binding. Wallet-secret
  fields are refused and no actual receive/configuration values are in this PR.
- Reorg/unavailability: local receipt/transaction tests use synthetic contexts;
  they do not establish current native UTXO state, checkpoint freshness or TN10
  payout. The runbook requires real original-controller unavailability and cold
  recovery from backups/public history. Merely stopping an unrelated service is
  insufficient. Native node/gateway/B guard/prover availability stays explicit.
  Reorg/stale/spent anchors abort rather than relabel a receipt or extend a lease.

Remaining execution gates are explicit: Mint installation/public parameters,
concrete original-controller process/cache isolation, trusted fresh chain captures,
B installation/lease qualification and the separately released live rehearsal.
The offline wallet cycle and preserved local receipts are not independent public
archive availability, a completed shutdown test or a production privacy audit.
