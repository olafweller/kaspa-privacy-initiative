# Long-gap public-account takeover experiment

Status: completed fresh rehearsal on 2026-10-17, including native payout.
See [measured results and limits](LIVE-REHEARSAL.md). This plan records the
intended scope; further trials require a fresh identity.

Question: can an executor reconstructed from public data process a new authorized
withdrawal after more than the old adapter's 100-blue-score bound, using real
recursive proofs and the existing native bridge? This is not lane-expiry,
permissionless data availability, privacy or independent-node validation.

Reuse vProgs `f9b84a863a7c7c20586a9cf947550475e894f72e` per-batch verifier,
aggregate verifier, recursive `env::verify`/assumption resolution, permission
tree/scripts and official resolve-pinned covenant. Keep compatible Kaspa
`01b532e8b553523216471682649693af92f0fd16`, RISC Zero 3.0.3 and v1compat 2.2.2.
Current vProgs HEAD was checked again and is unchanged.

First qualify real batch-to-aggregate proof composition without funds. Then use
the retained public native-account action relation as one coarse resource in
the reference SMT journal format. The small per-transaction adapter must bind
the actual v1 ID, lane, context, entire previous account state and next state;
invalid commands remain authenticated no-ops. This serial public resource is
deliberately not a scalable resource scheduler or privacy design.

The batch wrapper calls the reference verifier and rejects `lane_expired`.
The former 100-score adapter bound is not Kaspa's inactivity threshold. Test a
real gap greater than 100 while the lane remains natively active. True expiry
requires a separate authenticated inactivity/reset design and is not silently
enabled by trusting the bridge's host flag.

The reference aggregator already binds state/tip/image/lane/covenant continuity
and final lane inclusion; do not implement another lane accumulator. Check the
real resolve control identity and empty assumptions before funding. No relaxed
verifier pins, privileged rescue, genesis credit or mainnet execution.

Takeover means a separate clean execution directory/process with no original
executor database, replaying retained public inputs and checking the current
state UTXO. It does not mean another independent human operator, physical node,
unavailable archives, pruning recovery or loss of user signing keys. Use a
separate fee wallet if native submission needs a signer; user authorization
remains separate. All keys stay on the VPS.

Valid case: fresh zero-balance app, deposit, confirmed credit, original executor
stops, real idle gap, clean reconstruction, new authorized withdrawal, real
recursive settlement and native payout. Negative case: same actual endpoint
with omitted input; additionally reject wrong continuity/expired-lane metadata
and missing/wrong inner receipts at their actual enforcing layer.

Retain exact sources, artifacts, failed attempts, elapsed blue scores, real proof
costs, raw RPC, native transaction IDs, backing and fee reconciliation. All
execution uses Cloud and the existing VPS terminal/localhost RPC. Do not modify
the old funded instances or rebroadcast an old trial.
