# ADR-0015: staged TN10 inputs and one-way covenant initialization

Status: preparation for owner review, 2026-10-19. No funding, broadcast, rental
or new outer proof is authorized by this record.

## Problem and source evidence

The completed PR51 receipts prove four fixed local inputs. Replacing the
deposit outpoint, recipient, covenant or native anchor changes the statement.
Actual TN10 batches must be frozen after the preceding on-chain checkpoint,
with trusted expectations recorded before sending public input to a prover.

There is also a bootstrap self-reference not exercised by the fixtures.
Pinned rusty-kaspa `01b532e8b553523216471682649693af92f0fd16`,
`consensus/core/src/hashing/covenant_id.rs`, hashes the genesis funding outpoint
and authorized outputs' indices, values and versioned scripts. The binding is
excluded, but the initial state script is not. Reviewed `State::hash` includes
the covenant ID. Directly locking that root as the genesis script would require
a hash fixed point; computing an ID from one script and then replacing that
script is invalid. The generic vProgs bootstrap builder does not solve this
application-specific dependency.

## Decision

Keep the reviewed private guest, wallet circuit, parameters, relation and
restricted state/permission scripts unchanged. Use a separate, one-way
initializer for **state rent only**, before any user principal is deposited.
Its fixed script commits the verified active-lane seed, last-touch score,
economic domain, wallet verifier and exact reviewed successor template.

Create its covenant with the normal native genesis-ID calculation. On its only
supported spend, read the actual ID using `OpInputCovenantId`, compute the
existing canonical genesis-state SHA256 and SMT leaf SHA256, reconstruct the
exact lane-restricted successor script and compare its P2SH with output zero.
Require v1/private lane, initializer input zero, two inputs/two outputs, exactly
one covenant output at zero authorized by input zero, unchanged 100M sompi rent,
and an unbound sponsor/change. There is no owner withdrawal key, arbitrary
initializer output, new hash primitive or alternate proof verifier. Anyone can
initialize if they fund the fee; they cannot select a different initial state.

Both creation and initialization use the reviewed lane. Deposit admission is a
later step after native acceptance of initialization. Preserve that entire
lineage, including the zero-liability genesis bytes and original seed endpoint.
Do not fund old unrestricted fixture scripts or migrate an existing pool.

## Staged chain and proof boundaries

Use the existing complete native capture reconstruction, independently pinned
by validator binary SHA256. Its old `export` executes the original 100-score
demo guest, so use `verify` and map the checked native bodies/active inclusion
witnesses directly for the already-reviewed private guest. Preserve merge-set
indices, all lane transactions (including rejected app requests), exact u64
timestamps/scores and actual end-seq commitment. No relaxation to native
reconstruction, lane expiry or endpoint authentication is made.

Freeze each input, program, complete journal and resulting public state locally.
Require checkpoint state/root/tip and next capture start to match. Trusted CPU
receipt verification uses the separately retained target hash, fixed guest/join
and exact journal; GPU metadata cannot redefine them. Native preparation then
executes the fully signed settlement/payout on the pinned TxScriptEngine and
checks measured compute budgets, all mass dimensions and integer-sompi fees.

Refresh selected-chain/UTXO/endpoint eligibility after a proof wait. A fresh
**start** anchor is usable only with the unchanged active tip and last-touch;
otherwise reconstruct from the preceding checkpoint. Never substitute a new
end-seq or header score into a proven journal. The pinned native seqcommit
accessor requires the selected endpoint's score to be strictly within finality
depth of the selected parent. An expired/orphan endpoint is a failed attempt,
not permission to extend the statement or redo proofs automatically.

Keep a single durable four-stage attempt ledger. Start one 3,600-second deadline
at the first proof; conservatively include intervening chain waits. All proofs,
compression and in-container CPU checks share it. Reuse the existing sampler,
external GNU timeout and independent B lease/backup/confirmed-stop guard. A
later stage gets no new hour. Do not claim the old fixed-workload service/image
supports staged input; its separate staged service/image binding must be
qualified before rental. No such deployment is performed in this preparation.

## Alternatives and trust

Removing covenant from the private state hash or adding a special genesis guest
would change the reviewed relation/image and all local receipts. An operator
initialization key would add an unnecessary authority. A native, deterministic
rent-only initializer avoids both, but is **new native code requiring review**;
local tests are not a safety proof or a completed testnet rehearsal.

The trusted controller, native node and independently installed verifier are
still trusted for preparation. Native accepted-chain sequencing/proof checks
remain the eventual settlement enforcement. Separate local 0600 role files do
not isolate Bob from machine root; Bob must control his backup/recipient key
before release. The tiny depth-two note tree, one pending exit and one selected
reserve larger than the exit remain research restrictions. This adds no claim
of production privacy, independent prover implementations or live TN10 success.

Reconsider the initializer if native ID rules/state encoding/template change;
reconsider the staged proof route if real captures exceed the frozen guest input
limit, lose active-lane continuity, or miss the native anchor/proving window.
