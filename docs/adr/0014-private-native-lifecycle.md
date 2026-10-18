# ADR-0014: authenticated native private-payment lifecycle preparation

Status: Owner-requested local implementation and execution qualification,
2026-10-18. No GPU rental, funding or TN10 broadcast is included.

## Decision and enforcement boundaries

Preserve PR48's completed receipt and all its source/artifact bindings. Add a
separate lifecycle package reusing its wallet relation/VK, checked accelerated
verifier, canonical v1 transaction hashing, active-lane fold and native
delegate scripts and a deliberately restricted permission policy. No new setup or cryptographic primitive is added.

Start from zero user reserve/liabilities. A deposit is identified by its native
transaction ID and output index, derived from authenticated transaction bytes.
Require the exact covenant-specific, unbound delegate script and positive value.
A deposit reference can be registered and credited only once. Private transfers
and exits retain the wallet's actual proof, current nullifier, anchor and
destination checks. Bob uses his own local backup and available public state/
parameters in a separate wallet process; no witness enters the outer input.

State-covenant principal is invariant and excluded from user backing. Keep
delegate outpoints/values in authenticated private application state. Permission
rent and sponsor fees are separate native accounting domains. An exit moves
private liability into unpaid-exit liability without reducing the reserve.

Observe the later accepted settlement transaction on the same user lane. Bind
its covenant-bound permission output to the pending single-exit amount and
destination, recording its unique outpoint and rent. Native covenant consensus
must authorize that binding; arbitrary output metadata outside accepted L1 data
is insufficient. The subsequent accepted payout must consume that exact
permission and tracked delegate outpoint, pay principal plus permission-rent
refund to the exact destination, and retain exact delegate principal change.
Only then discharge the pending exit and replace the tracked reserve outpoint.
Do not introduce an executor/RPC success boolean. One outstanding permission and
one reserve input are explicit limits of this focused package.

Local fixtures exercise the real permission/delegate scripts and a local UTXO
set for distinct replay attempts. They do not fabricate a new genuine outer
receipt: script authorization of permission issuance still needs the future
lifecycle proof. Accepted-lane fixtures are not canonical chain acceptance.

## Proof batches and idle gaps

Use connected deposit/credit-transfer, exit, and permission/payout reconciliation
batches, retaining invalid operations in lane commitments. Derive state and lane
tip continuity from the previous committed state. Reuse the established recent
unchanged-active-lane anchor technique and canonical `lane_tip_next` fold; do not
reinterpret the old package's `MAX_SPAN=100`. The new relation supports idle gaps
while the native lane remains active; genuine expiry/reset is rejected rather
than guessed. Endpoints still require the real native sequencing accessor at
settlement. Proof delays are outside the old short-interval workload.

Declare a separate local execution profile before measurement: at most 160M
cycles and 900 seconds per new complete batch, four worker threads, at most
3,600 seconds across the positive campaign. This profile does not revise the
old 128M failure, 160M calibration or PR48 proof. Record new guest/image identity
before execution, exact inputs/journals and measured resources. Resource failure
is never attack rejection; no automatic budget increase or proof attempt.

Use segment po2=16 for the small deposit/reconciliation batches and po2=20 for
wallet-verifying batches. This is an execution checkpoint choice, not extra
dummy work or a different statement. Require multiple segments before proposing
the existing fixed `join.zkr` native route: a single-segment Succinct receipt
ends in the official lift program and cannot silently be called a join receipt.
Record segment counts; if the declared configuration does not yield the expected
route, report the incompatibility rather than taking control metadata on trust.

## Alternatives and remaining assumptions

Reducing the state-covenant output for payout violates its continuation rule.
Trusting a host payout callback violates authenticated accounting. Rewriting
the wallet/circuit, native bridge or operator infrastructure is unnecessary.
The chosen composition adapts existing reserve/permission paths and retains the
same experimental setup, public-data availability and tiny-tree limits.

The future TN10 plan must bind actual bootstrap/covenant/deposit identities,
public data recovery, fresh accepted lane captures, genuine receipts, permission
UTXO spentness and native script/fee budgets before broadcast. Local completion
does not mean readiness for a live trial: complete terminal payout and selected
chain confirmation must first succeed in the separately released rehearsal.

## Review correction: enforce the observed native policy

The initial PR49 relation rejected native-valid sponsor top-ups and failed to
observe off-lane payouts. Its second-deposit admission also contradicted its
single-entry payout check. These were blocking errors, not liveness limitations
to accept. See [reproductions and correction](../../poc/private-native/REVIEW-FIX.md).

Choose native restrictions over trying to authenticate every arbitrary payout
lane. Issued permissions bind the private lane, exact selected reserve outpoint,
terminal full consumption, positive change and the supported three-input/output
shape. Upstream cryptographic and principal/rent/change checks remain intact.
Recipient top-ups are correctly accounted as sponsor contributions. Multiple
registered reserves remain tracked; each exit must fit one selected reserve.
The state covenant also enforces the private lane, including permission issuance;
its guard is copied in continuation through the existing suffix construction.
Pinned vendor files/PR48 bindings are preserved. The new state hash domain is v2.

A fatal guard prevents committing an unreconciled native spend as an ordinary
economic rejection. Actual native exclusion of unsupported forms, not that fatal
guard alone, supplies the bounded liveness argument. Real-engine regression
comparisons and 21 actual guest executions qualify the revised local relation.
The real sponsor builder also accepts the matching public restricted redeem
bytes, with an actual-script integration test. New receipts, actual funded
construction and a terminal rehearsal remain unperformed.

## Fixed four-batch GPU preparation

After merge of PR49, package the unchanged reviewed guest/targets and executable
for four sequential proof jobs, with separate CPU verifications and genuine exit
receipt native checks. Use one externally supervised process group for the entire
3,600-second proving/compression/check allowance, not one hour per batch. Retain
partial candidates and the existing independent B lease/back-up/stop mechanism.
See [fixed package](../../poc/private-native-proof/README.md) and its adversarial
review. Image publication and CPU startup qualification are software preparation;
rental/proof execution and actual chain acceptance require separate release.

## Released local four-receipt result — 2026-10-18

The [corrected runtime rehearsal](../../poc/private-native-proof/gpu-2026-10-18-02/README.md)
completed all four genuine receipts, independent trusted B/Cloud CPU verification,
the new exit receipt's actual local native permission issuance/restricted payout,
and per-batch CUDA observation in 379.676 seconds. The first released attempt's
missing-parent-directory failure remains preserved; the owner separately released
the small runner fix and one fresh attempt after a real-subprocess regression and
new immutable-image qualification. Neither the guest nor native relation changed.
Both Pods were independently stop-confirmed and deleted after external preservation.
The earlier pending-receipt statements are superseded for local fixtures only.
Funded construction, canonical TN10 acceptance/anchors, actual payout confirmation
and full transaction budgets remain separately released work.
