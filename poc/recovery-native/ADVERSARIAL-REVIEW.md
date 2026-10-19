# Adversarial second pass — integrated guest

- Inflation/backing: only accepted canonical delegate output IDs register
  principal; existing real credit/transfer/exit proofs enforce conservation and
  current nullifiers. Native principal remains reserved through exit/permission.
  Both reconciliations deduct only authorized principal, not sponsor top-ups or
  either rent domain. Full drain removes exactly its selected reserve; the
  second-deposit regression preserves unrelated backing and pending credit.
- Unauthorized exit/double spend: same configured wallet VK/proof and current
  spentness checks, one pending exit, exact native recipient/outpoint and final
  permission consumption. Replay, underpayment, destination substitution, extra
  inputs/outputs, wrong lane/reserve and partial permission forms are rejected at
  their actual semantic layer. Zero/overflowing exit-plus-rent amounts cannot wrap.
- Native/application mismatch: both permitted payout forms reconcile, including
  top-ups, versioned sponsor outputs and tagless third-party payment. Native
  restrictions exclude unsupported shapes. A contradictory accepted tracked
  spend aborts the guest; it cannot become a successful stale-backing no-op.
  Paid exits are skipped during later permission detection because their old
  reserves are gone. Six successive batches regress that specific integration bug.
- State binding: fixed lane/covenant/old root/tip/inclusion/last-touch, ID-derived
  native bodies, six complete journals and state/tip/template-outpoint continuity.
  New state/resource and guest identities prevent relabelling old state/proofs.
  Old real and fake receipts cannot satisfy the compiled verifier. Local anchors
  are not an accepted Kaspa chain; actual selected-chain/UTXO checks remain needed.
- Prover assertions: current CPU outputs are not receipts. A new real outer
  receipt and native issuance script acceptance are still required. The prepared
  issuer validates genuine receipt bytes first, then exact frozen transaction ID,
  actual native scripts and reconciliation. No host success flag is added to the
  guest. Positive issuer execution remains untested until new receipts exist.
- Dependency loss/reorg: public scan state, ciphertexts, parameters, accepted
  history and current anchors must be independently available. The new wallet
  adapter requires the new independently expected root and refuses old roots.
  Local reconstruction is not canonical freshness, archive availability or a
  shutdown trial. Expiry/reorg reset is not invented; old data cannot be relabelled.
- Privacy/operator role: only public PR55 proof fixtures are reused. User proofs
  stay local; shared receiving data contains no native key. Native destinations
  appear at exit. Same-host/root access and timing/amount/network correlation are
  not solved by this guest. Independent user administration remains a live gate.
- Upgrade/custody: no admin key, migration path, confiscation capability or change
  to the old funded instance. A new policy requires a fresh bootstrap/covenant;
  this qualification cannot rescue or drain PR54's old remaining reserve.

The first local preparation exposed paid-exit script reconstruction from a retired
reserve; skipping paid/already-issued exits fixes it without deleting history.
A separate preparation serialization error required native v1 ComputeBudget
inputs in non-broadcastable templates. Both were corrected before the frozen
CPU campaign. Guest intermediate builds and local logs remain under `.local`;
only the final image/input set is qualified. No limits were raised and no funded
or proving attempt occurred.

## Review correction: one native input spend across the complete fixture history

Astra's review of `8922c193` found two fixture-only native conflicts: the invalid
and valid transfers shared funding, and the two payouts shared sponsor funding.
The new host check reproduces exactly both conflicts from the preserved binaries;
the previous per-transaction script checks did not enforce cross-transaction
spentness. This is a test-history error, not evidence of a native consensus bypass.

Each publication now uses distinct funding, and payout sponsor IDs are derived
deterministically from the exit ID with an explicit fixture domain. Whole-history
input uniqueness is mandatory during preparation and checking saved inputs.
Thirteen captured transactions spend 22 distinct inputs; templates and alternative
attack histories are not appended a second time. The regression reintroduces
both bugs separately and requires rejection. Invalid app operations still consume
their native publication funding. No guest assumption or cryptographic check is
weakened, and no native UTXO ledger is added to the guest.

Dependent public inputs, native IDs, state roots, tips, exact journals and host
pins were regenerated. All fifteen actual guest CPU cases passed under the same
limits using the identical guest program; all nine Rust tests passed. The original
corpus, measurements and manifest remain explicitly superseded evidence, not proof
targets. The correction does not establish signed chain-valid funding, canonical
UTXO availability, new outer receipts or independent recovery after shutdown.
