# Local native/private lifecycle result — 2026-10-18

The local package completes zero liabilities → native deposit registration →
private credit/payment → Bob's independently proved exit → permission consumption
and native payout reconciliation. The real existing wallet proofs and actual
native payout scripts are used. **Accepted lane/UTXO fixtures remain synthetic;
no new outer receipt, canonical TN10 acceptance, funding or GPU rental occurred.**
Native permission issuance from a genuine new lifecycle receipt is prepared in
code but has not been positively executed. PR48 remains the completed older
private execution proof; it cannot be substituted for this new program.

## Exact principal accounting

All values are integer sompi. State rent 100M, permission rent 50M and sponsor fees
are outside user principal. The native state-covenant continuation is never
reduced to pay Bob.

| Stage | Delegate principal | Private liabilities | Pending deposits | Unpaid exits |
|---|---:|---:|---:|---:|
| Genesis | 0 | 0 | 0 | 0 |
| Deposit output registered | 1,000,000,000 | 0 | 1,000,000,000 | 0 |
| Alice credited | 1,000,000,000 | 1,000,000,000 | 0 | 0 |
| Bob4 / Alice6 payment | 1,000,000,000 | 1,000,000,000 | 0 | 0 |
| Bob exit authorized | 1,000,000,000 | 600,000,000 | 0 | 400,000,000 |
| Permission output observed | 1,000,000,000 | 600,000,000 | 0 | 400,000,000 |
| Payout consumed/reconciled | 600,000,000 | 600,000,000 | 0 | 0 |

The actual local payout output is **450M = 400M principal + 50M permission-rent
refund**. Delegate change is 600M. The OP_TRUE fixture sponsor supplies 200M,
receives 199.9M change and pays 100k fee. State rent stays 100M. Those fixture fees
are not a network quote. See [lifecycle.json](evidence/lifecycle.json) and
[native-payout.json](evidence/native-payout.json).

## New identity and measured execution

The program was built and identified before guest execution:
`090b7317005efecd18425f56fbdbd7598da451cb5e29f30c2b7df295edab8adc`.
The wallet VK remains
`d3c179aae5c2c6c013b1de1da5ad4412e4b2c8bae7288c0b9d85e0c986b5a3ec`.
Independent journals and complete inputs are fixed in
[targets.json](evidence/targets.json). Each journal is 352 bytes; transaction/batch
slots are monolithic relation-domain constants, not recursive guest identities.

| Batch | User cycles | Segments | Segment po2 | SDK execution seconds |
|---|---:|---:|---:|---:|
| Deposit | 551,055 | 34 | 16 | 0.234 |
| Credit/payment | 93,104,947 | 95 | 20 | 2.171 |
| Bob exit | 43,877,348 | 45 | 20 | 1.156 |
| Permission/payout reconciliation | 1,382,110 | 74 | 16 | 0.256 |

All four matched their complete independent expected journals, under the
declared 160M/900s per-case limits. Together with nine economic rejection cases
and four exact authentication-abort cases, **17/17 zkVM executions passed** in
11.269 seconds whole campaign wall time. No timeout/resource failure was counted
as rejection. Four CPU threads were used; peak sampled group RSS was below80MiB
and wait4-reported max RSS approximately114.6MiB. See the raw
[campaign](evidence/execution/campaign.json) and per-case reports/logs.

Small-batch checkpointing was explicitly declared before measurement to retain
the existing join-control native route. It adds no dummy operations. All positive
profiles have multiple segments; a one-segment lift control is not silently
accepted as join. More segments can increase future proving cost; none of these
execution times is a measured outer-proof duration or price prediction.

The final reconciliation fixture uses the actual next state-covenant script,
not an OP_TRUE continuation. Its unsigned issuance transaction ID is bound into
the permission/payout input. The prepared genuine-receipt native entrypoint
requires the witness-bearing settlement to reproduce that same native ID.
Its positive invocation remains pending a separately authorized new receipt.

## Bob and enforcement tests

Bob's separate local process restored only his own owner-only backup, checked the
whole public-parameter file against independently recorded SHA256
`812b3bda0ec5f9b0c17fc1d530e49fc21defc9dcc5ea9c70a133ca62fec31e99`,
discovered/validated his 400M note and generated a fresh exit proof accepted by
the current state. Only the new public operation/report were retained here.
The report's 11.976s is the proof/verification interval; total parameter loading
and wallet startup were not separately timed. See
[Bob recovery](evidence/bob-recovery.json). No parameters/setup or secrets were
created for an outer prover.

Seven host tests exercise real-proof accounting, canonical native parsing/all
truncations, native payout mutations/UTXO replay, recipient/permission binding,
gap/predecessor authentication, payload-independent reconciliation and capture
conversion. One additional fixed-proof-target test rejects Fake receipts for
all four compiled targets. The old native host's three tests pass after adding
private-lane mode; its native payout test covers both modes, genuine sponsor
signature acceptance and post-signing payload mutation rejection.

The nine complete negative guest executions cover duplicate/fabricated deposit,
old-root competing spend, transfer replay, wrong exit recipient, underpayment,
reserve diversion, wrong payout recipient and repeated payout reconciliation.
Four actual guest aborts require exact expected predecessor-state/tip,
start-inclusion or last-touch assertion failures. Host- and guest-resource errors
cannot stand in for these expected failures.

The actual local `TxScriptEngine` accepts the permission/delegate payout and
rejects three balanced native mutations: underpayment, reserve diversion and
recipient substitution. Distinct native replay is rejected in the explicit local
UTXO set; this is not a live node's missing-input response. Endpoint comparison
shows omitted payout activity changes the commitment; it is not a newly proved
omission result. Fake receipts and actual PR48 receipt substitution are rejected
by the prepared trusted verifier. See
[PR48 substitution](evidence/pr48-substitution-rejected.json).

## Evidence and remaining release gates

[manifest.json](evidence/manifest.json) binds the retained evidence;
[source-bindings.json](evidence/source-bindings.json) records source and binary
identities. Original PR48 artifacts/source bindings and the prior private-note
evidence are preserved. No guards, leases, keys or remote services were changed.

Before another paid attempt, package these new binaries/public targets in a new
fixed immutable image and qualify its startup/lease binding. Before TN10 funding,
complete the [transaction/proof plan](TN10-PLAN.md) with actual native outpoints,
accepted lane captures and independently verified new receipts. The new
`genesis`/`prepare-capture` commands prepare public state/inputs using the existing
capture format without funding or replacing endpoint authentication with a flag.
Freeze actual captured targets separately; these local fixtures are not evidence
of native chain acceptance. Full terminal rehearsal/confirmation remains a gate
before describing the path as ready for a live trial.

The experimental four-leaf, one-input/two-output wallet, single-party setup,
whole-note exits and zero application fees remain. This package handles one
reserve input and one outstanding permission at a time. No mainnet, production
safety, practical anonymity, permissionless availability or full privacy-protocol
claim follows.
