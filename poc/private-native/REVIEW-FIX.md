# PR49 native/accounting alignment

The review at `0d3a8e88d8bb9430ec498c3dd66c38fb32296d76` found three real
mismatches. They were reproduced locally before changing the application relation:
[record](evidence/review-reproduced.json). The sponsor for both payout examples
was genuinely signed; all input scripts ran in the pinned `TxScriptEngine`.
These are synthetic UTXO/ordering fixtures, not node or TN10 acceptance.

| Reviewed counterexample | Before correction | Corrected rule and result |
| --- | --- | --- |
| Bob receives 450,000,001; sponsor change decreases by one | Native accepts, app rejects | Native accepts; app discharges exactly 400M principal and 50M rent, advances the reserve to 600M; sponsor top-up creates no private credit |
| Otherwise correct payout on the default lane | Native accepts, fixed-lane app cannot observe it | Issued permission rejects other lanes through `OpTxSubnetId` before funds move |
| A second unique 1,000M deposit before payout | App admits it but then rejects the first payout | Exit pins one sufficient reserve; payout replaces only that outpoint, preserving the other deposit and its 1,000M pending liability |
| Partial permission consumption, with three or four outputs | Upstream scripts allow continuation | Issued permission requires every output unbound; partial/continuation is rejected natively |
| Additional sponsor input or output | Upstream scripts allow the tested forms | Issued permission requires exactly three inputs/outputs; rejected natively |
| Sponsor output has the delegate’s raw bytes but script version1 | Native allows this unrelated sponsor output; the app compared only raw bytes | Compare the complete versioned SPK; native acceptance now produces correct authenticated accounting |
| Substitute an untracked delegate outpoint | Upstream permission accepts equivalent funding | Issued permission pins the admitted reserve's txid/index; rejected natively |

See [native/application regression results](evidence/review-regressions.json).
The existing underpayment, recipient substitution and reserve diversion controls
still fail in the actual script engine. Empty/unrelated payloads remain allowed:
recognition uses consumed outpoints, not an honest executor's tags.

## Enforcement composition

`common/src/restricted.rs` prepends stack-neutral introspection checks to the
unchanged pinned upstream single-leaf permission verifier. The guest commits the
**hash of these restricted permission bytes**, not the generic accumulator's
script hash. Existing curve, Merkle and amount logic is reused. No custom
cryptography or new wallet setup is introduced.

The permission binds v1, the private subnetwork, permission input0, the exact
reserve at input1, an unbound non-delegate sponsor input2, three outputs, unbound
outputs, positive reserve change and a non-delegate sponsor output2. Upstream
verification binds the recipient, full principal, rent refund and exact delegate
change. Because continuation outputs are forbidden, its partial-consumption
branch cannot succeed. Its terminal domain suffix remains unchanged, retaining
the pinned delegate authorization checks.

An exit is admitted only if a tracked reserve strictly exceeds its principal;
its chosen outpoint is committed in `exit_reserves`. One pending exit is retained.
Multiple deposits/reserves are allowed, but combining several reserves into one
exit, partial consumption and concurrent permissions are deliberately unsupported.
An unsupported wallet exit is rejected atomically before permission issuance;
no nullifier or private liability is consumed. Later deposits cannot change the
reserve already chosen for an outstanding exit. Zero-change full-reserve exits
are also outside this bounded route and cannot pass its positive-change guard.

The state covenant must enforce the lane as well: otherwise permission issuance
could be invisible. `host/src/native.rs::state_redeem` inserts the same lane check
**after** the upstream 99-byte prefix and includes it in the self-referential
script length. The copied suffix therefore retains the check in every successor.
Both fixture issuance and the prepared genuine-receipt settlement entrypoint use
this adapter. The pinned vendor files and all PR48 evidence remain untouched.

A genuine archived PR48 receipt qualifies this additive state-script adapter:
private-lane execution succeeds; default-lane execution and removing the guard
from the continuation fail in the real engine. See
[state guard evidence](evidence/state-guard.json). This is explicitly **not** a
new lifecycle receipt or proof of new permission issuance.

## Accepted native effects versus invalid wallet requests

Invalid wallet requests remain deterministic rejected operations in the lane
fold. If an allegedly accepted transaction consumes a tracked permission or
reserve but cannot be reconciled, the guest aborts with
`unreconciled accepted native consumption`; it produces no successful journal
containing a stale economic no-op. This is a defensive consistency check, not
the solution to liveness: the actual restrictions above exclude the unsupported
native forms before they can spend funds. Their native rejection is tested
separately from the guest aborts. Resource failures never count as rejection.

## Requalification and boundary

The corrected state uses a v2 hash domain and a new fixed guest identity, exact
inputs and 352-byte journals. [Execution declaration](evidence/execution-declaration.json)
records the unchanged 160M-cycle/900s-per-case, four-thread, 3,600s campaign
limits before execution. The 21-case campaign includes the four lifecycle batches,
four native-accepted positive regressions (top-up, second deposit,
versioned sponsor output and tagless payout),
six ordinary economic rejections, three mandatory native-consumption aborts and
four authentication aborts. It is execution only; no new outer proving was run.

This is a new, unfunded contract policy, not a migration of an existing pool.
The sponsor builder’s `privateExitId` option only selects a lane. Its additional
`permissionRedeem` public field now accepts the exact restricted bytes, checks
their unchanged verifier body and actual UTXO script hash, measures native script
cost and signs the chosen transaction. The integration test executes all three
input scripts using this package’s frozen public policy, and rejects a missing or
substituted redeem script. Before funding, rehearsal tooling must use these exact
restricted state/permission scripts,
measure/sign the real inputs, produce genuine new receipts, and complete the
terminal TN10 rehearsal. No image publication, GPU rental, provider action,
funding or TN10 broadcast is part of this correction. PR49 remains open for the
owner's renewed review.

An additional final-review regression reproduced the versioned-sponsor mismatch
on the initial correction: [failure log](evidence/version-reproduction.log).
A script is identified by version and bytes together. A v1 output is not the
tracked v0 delegate; it spends sponsor money only and must not strand a completed
exit. The corrected predicate and actual native/guest positive regression cover
this case. The new native policy itself is unchanged by that accounting fix.
