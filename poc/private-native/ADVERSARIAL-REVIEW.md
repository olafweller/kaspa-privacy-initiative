# Adversarial second pass

- **Mint/backing:** only ID-derived delegate outputs register deposits; exact
  outpoint deduplication and the existing constrained credit relation prevent
  second credits. Reserve outpoints are summed independently against ledger
  principal. Payout is detected by tracked native input consumption before
  interpreting deposit payloads, preventing a reserve change disguised as a
  fresh deposit. Acceptance of those native bytes still requires genuine L1
  endpoint authentication; the local fixture cannot establish it.
- **Double spending/replay:** current nullifiers remain in committed state even
  for historical note anchors. Permission outpoint, paid exit and native payout
  output history prevent reconciliation replay. Native UTXO consensus prevents
  a second real permission/delegate spend. The local spentness set tests the
  condition, not full consensus or reorg recovery.
- **Reserve release:** state-covenant value never funds payout. Existing native
  permission/delegate scripts enforce recipient, principal/refund and exact
  reserve change. A genuine new exit receipt must authorize issuance through the
  lane-restricted continuation covenant; this positive outer-proof/native step remains
  unexecuted during preparation. Merely serializing a covenant ID is insufficient
  without accepted native covenant authorization.
- **Public tags/availability:** permission/payout recognition uses covenant
  outputs and tracked outpoints, including empty/unrelated payloads. Withholding
  data, proofs or a supported active-lane endpoint must halt settlement. The
  single-reserve-input/one-permission shape is enforced natively; multiple
  registered deposits are retained. It limits exit aggregation outside this experiment;
  this is not a general multi-deposit production wallet.
- **Stale state/reorg:** old root/tip/last-touch are committed and checked. Recent
  anchors preserve the old active leaf; they cannot reset the score or cross true
  expiry. Final selected-chain membership/window is supplied by native consensus,
  not this CPU fixture. A future reorg needs replay from the last valid checkpoint.
- **Privacy/recovery:** Bob's backup stays local and whole parameter hash is
  enforced before load. Only public ciphertexts/proofs/state enter outer inputs.
  Deposit/exit amounts, destination, timing and sponsor activity remain public.
  A tiny tree and a restored wallet do not establish practical anonymity or durable
  public-data availability. No secret scanning material is sent to a server.
- **Trust/identities:** wallet setup trust, trusted compiler/verifier binaries,
  pinned SDK/curve adapter and retained public data remain. The new image is
  distinct from PR48; its actual receipt cannot substitute for the new claim.
  Fixed join control is appropriate only for the declared multi-segment profiles.
  Operator/B-root infrastructure cannot create a valid claim by a success report.
- **Fees:** principal, state rent, permission-rent refund and sponsor fees are
  separate integer-sompi values. The sponsor builder chooses lane/payload before
  signature/fee computation. Fixture fee and public test-only sponsor key are not a deployable
  funding input or network quote. Actual signing, mass and accepted payout must
  be established in the released rehearsal.

No security invariant is changed. Passing local tests are implementation evidence,
not proof of cryptographic correctness or production security.

The blocking Astra counterexamples and native-permitted forms are now covered
in [REVIEW-FIX.md](REVIEW-FIX.md). A native spend cannot be silently folded as a
rejected wallet no-op. Default-lane issuance is also excluded by the copied
state-script guard, qualified with PR48’s genuine archived receipt. No new
lifecycle receipt or accepted TN10 effect is claimed.
