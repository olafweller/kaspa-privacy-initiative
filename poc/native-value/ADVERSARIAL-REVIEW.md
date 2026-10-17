# Adversarial second-pass review

Date: 2026-10-17 UTC. Experimental code, not independent audit or security proof.
All [security invariants](../../SECURITY-INVARIANTS.md) remain unchanged. Temporary
public accounts test bridge behavior, not the final private-state requirements.

## Theft, inflation and authorization

A deposit names an output of the **same accepted L1 transaction**. Its v1 ID
commits payload, output SPK and amount; the native lane commitment authenticates
that ID. Upstream Deposit binds the user resource to its lock and the output to
the configured delegate address. The wrapper additionally rejects covenant-bound
funding outputs, records `(txid,index)` and commits the complete previous user
map. Repeated outputs within one transaction and repeated credit across states
must fail without persisting partial effects. Fake output values can be processed
in a hypothetical computation, but cannot retain the authentic L1 ID/end anchor.
No host assertion about a payment is accepted as proof of its existence.

Withdraw uses upstream checked subtraction and owner-lock authorization. The
trial's prev-tx witness proves the carrying accepted L1 transaction spends the
user's P2PK output; L1 verifies its signature and payload binding. An executor
cannot simply substitute the recipient while retaining that signature. A
sponsor's correctly signed command targeting somebody else's user is accepted
by L1 but fails app authorization and remains committed as a no-op. No config
Init/Update, unlocked admin withdrawal, treasury allocation or rescue path is
enabled. The reference genesis scalar is not used by the actual trial wallet.

The guest commits the exact emitted permission hash and deposit hash into the
352-byte journal. The covenant pins guest image, domains, lane, current state,
next state, old/new tip, actual input covenant and the end commitment read by
`OpChainblockSeqCommit`; it preserves state-covenant value and fixes sponsored
permission rent. Allowed control root, official fixed lift-20 identity and empty
assumptions remain. Host-only budget sizing is not consensus verification.

## Native reserve and claims

The state-covenant UTXO and fee wallet are **not** user backing. The actual native
deposit pays the upstream delegate-entry P2SH. Permission payout must consume that
reserve input, authenticate the committed recipient/amount, return exact delegate
change, and consume/continue the claim tree. Its final claim also refunds the
sponsor-funded rent to the recipient. No payment from the sponsor wallet can be
counted as the 4-test-KAS reserve principal payout.

The permission rent refund is also a user entitlement once the claim output is
created. Count its 0.5 test-KAS liability against that already-locked 0.5 output,
separately from the 10-test-KAS principal ledger; it is no longer free treasury
value. Total unpaid-stage entitlement is 10.5 against 10.5 reserved. State rent
and uncommitted sponsor fees remain excluded.

App debit does not mean payment: before claim spend, balance 6 plus unpaid claim
4 is still a liability of 10 against reserve 10. Only confirmed claim consumption
and actual recipient/reserve UTXOs establish 6+0<=6. Balanced mutations send the
freed one sompi to ordinary change, isolating script enforcement from value
imbalance. A distinct post-payout transaction attempting the spent claim must
fail native UTXO validation, separate from the app's request replay rejection.

All balances, deltas and fees use exact integer sompi and checked Rust arithmetic.
Node 22 source-token parsing preserves u64 nonces/amounts; unsafe Number values
cannot silently serialize. Repaired historical derivatives cite their original
raw source and prior hashes; original RPC strings and binary proof artifacts
remain byte-identical. Existing failed-trial archives are historical; their raw
records, not a rounded derived header, remain authoritative.

## Completeness, stale state and operator choices

The guest processes every supplied lane transaction in order, even if its app
execution returns an error. The proof journal binds the resulting tip/seqcommit;
L1 compares against a real selected-chain end anchor. Omitting a valid withdrawal
while retaining the same real endpoint produces a valid *partial computation*
receipt that cannot settle at that endpoint. Proving failure alone would not
establish a native node rejection.

The current covenant fixes the old state/tip. The start witness is checked against
the supplied start seqcommit in the guest and against the selected-chain source
by the capture software; **the ABI does not separately carry the start block hash
for L1 to re-read**. End-anchor verification and old-tip continuity are the
cryptographic safety bindings of this scoped continuously active-lane experiment.
Do not advertise a separately consensus-enforced start-checkpoint policy.

A legitimate shorter prefix is allowed; no inspected protocol rule forces the
latest endpoint. Scheduler progress, third-party inclusion/censorship resistance
and maximum waiting time are not proven. The original interval's proof-shape
mismatch is retained. Before any proof/settlement, resegmentation moved the pivot
without changing the combined interval, dropping any command, changing the guest
or changing the funded verifier. Actual-input profiling is execution only.

## Material liveness/recovery limits

The reused PR31 relation deliberately supports a short continuously active lane:
`MAX_SPAN=100` blue-score units relative to the old last-touch score. It does not
implement upstream's general inactivity/long-span machinery. Both trial intervals
are captured before lengthy proving and remain eligible for the recent-header
accessor. **This does not demonstrate processing a newly published operation
after a long idle gap with the current fixed guest.** Remaining account value is
backed, but continued/independent withdrawal after such a gap is not established.
Do not call the remaining 6 test-KAS independently recoverable or production
spendable based on this experiment. The smallest generalization is reuse of the
upstream per-batch/aggregate relation and compatible recursive proving path,
validated in a fresh instance; no upgrade/rescue authority exists in this one.

The old state/root cannot reconstruct public resource bytes or pruned activity.
A successor executor needs authenticated retained state/bodies/witnesses, exact
artifacts and fees. This trial uses one owner-operated validating node; no
independent node/operator, shutdown takeover, archive loss or automatic reorg
rollback was tested. Pre-submit canonicality/UTXO checks and native re-evaluation
limit stale-state acceptance, but do not establish full reorg recovery. Failure
of witness/prover availability safely halts rather than authorizes theft.

## Privacy and supply chain

Public keys, accounts, amounts, commands, rejection timing and recipients are
visible. The hosted prover sees public witnesses; no privacy claim exists. Keys
remain only on the VPS outside packaged public trial directories. Dependencies,
images, native artifacts and source hashes must be retained. The deployed node
is identified by version and binary hash; a reproducible source-to-node build is
not claimed. Passing local/CI/native tests does not establish cryptographic
correctness or review of all imported runtime paths.
