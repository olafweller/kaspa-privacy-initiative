# ADR-0004: Public native-value based-app integration experiment

**Status:** Experimental decision for this authorized TN10 PoC only; RFC-0001
remains Open and no production architecture is selected. Date: 2026-10-17 UTC.

## Problem and scope

PR31 binds a public fold to native lane input, but has no user liabilities or
bridge. Test one zero-user-balance native deposit, partial withdrawal, remaining
backing and confirmed payout, with real proofs. All balances are temporary public
test state. Keep PR31 intact and publish a stacked draft follow-up.

## Source review and alternatives

At vProgs `f9b84a863a7c7c20586a9cf947550475e894f72e`, runtime-processor
`action/deposit.rs`, `action/withdraw.rs`, `deposit_policy.rs` and the API
`permission_script.rs` implement compatible account/bridge mechanisms. Its
`tn10-runtime` driver defaults to development mode; it is not real-proof evidence.
The bridge collecting L1 data is distinct from delegate-entry reserve control.
The existing Orchard/Aztec/RAILGUN/Monero/MWEB assessments and
`research/existing-kaspa-privacy.md` remain comparison inputs: no private notes,
new crypto, nullifiers or their security claims are imported in this public test.

Prefer the upstream action executor and permission script, enclosed by the
existing PR31 monolithic lane relation and real RISC Zero proving route. This
avoids implementing a general scheduler or recursive runtime merely to test a
small bridge. Compare with the full recursive runner: it supplies scalable
composition but needs separately compatible guest artifacts/proving control pins.
A custom reserve-spending signature would be smaller but violates the intended
proof-authorized withdrawal model and is rejected.

## Experiment-specific glue and obligations

The guest commits a canonical complete map of public user-resource bytes, feeds
actual lane transaction preimages to upstream actions, derives an immutable
minimum-withdrawal/covenant configuration from its own proven parameters, and
permits only Deposit and Withdraw actions. There is no genesis balance, admin
configuration action or reserve key. Invalid application commands are recorded as
failed/no-op while their L1 IDs remain in the lane commitment. The wrapper must
commit effects only on success, enforce declared access, deduplicate credit and
bind native outputs to spendable delegate entries of the actual covenant.

The upstream delegate/permission pair controls reserve funds. Settlement emits
an exact permission commitment for authorized exits; payout consumes its claim
and delegate funds, sends exact remaining reserve back, with fees paid separately.
A claim remains a liability until L1 pays it. Public app balances plus unspent
permission claims must remain covered by protocol-controlled delegate value;
state-covenant rent and fee-wallet funds are not backing.

Execution-only profiling must precede funding and establish the real guest,
journal, prover and fixed official proof-control identity match. A fixed control
pin is a limitation, not a general runtime. Do not weaken image, journal,
assumptions, chain anchor, authorization or accounting checks.

## Batch bounds and limits

Operators choose intervals; the inspected protocol does not prescribe one latest
mandatory endpoint. Correct prefixes may settle while later accepted commands
wait. Continuity and completeness of a claimed interval are safety obligations;
latest-endpoint selection and proof scheduling are liveness choices. A live
same-anchor omission attack must reach real verification, not just a host count.
First-touch, general expiry, reorg recovery, pruning, independent takeover and
privacy remain separate gates. No privileged recovery/exit or mainnet use.
