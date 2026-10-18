# Proposed complete TN10 lifecycle — not released

This is the concrete transaction/proof sequence for a future rehearsal. No funds,
broadcast or rental are authorized by this preparation. Local fixtures cannot
be sent as real TN10 transactions. Review the [local results](RESULTS.md) first.

## Identities and release inputs

[targets.json](evidence/targets.json) records the new guest image, exact public
fixture inputs/journals, unchanged wallet VK and fixed join identity. The two
journal relation slots remain monolithic domain constants, not separate recursive
guest IDs. Reuse the existing TN10 economic domain for its still-unfunded first
trial; another pool/domain would require corresponding wallet proof artifacts.

Before funding, create one fresh unfunded trial directory/identity in one command
using the established trial tooling. Bind the actual bootstrap funding outpoint,
covenant ID, seed lane tip and genesis empty-state root. Record the actual fee
wallet/public keys and sponsor intent without publishing secrets. Derive the
state covenant with the new image, relation pins, lane key, official join control
and 50M-sompi permission rent, using the lane-restricted `native::state_redeem`
adapter from bootstrap onward. The generic unwrapped contract is incompatible
with this policy. Its principal is 100M sompi throughout.

Use fresh actual native recipient keys controlled by Bob; the local fixture's
scalar-one destination is publicly spendable and must never receive a funded
trial. Supply its actual public key to the separate `bob-exit` command.

The existing CUDA prover binary and B stop/backup guard are reusable. The new
producer and verifier binaries have their own recorded identities. Publish and
CPU-smoke-check a fixed immutable image/package for these new batches before a
paid attempt; do not deploy the old PR47 fixed job as if it were this workload.
The owner must separately release the actual quote and native rehearsal.

## Transactions and proof batches

1. Bootstrap the state covenant with zero user reserve/liabilities and seed the
   fixed user lane. State rent is sponsor-owned and not user backing.
2. Alice deposits 1,000,000,000 sompi to the covenant-specific unbound delegate.
   Put the deposit descriptor in the carrying transaction, before signing.
   Retain its complete canonical v1 transaction bytes and accepted selected-chain
   context. Compute the unique `(txid,index)` reference from those actual bytes.
   Alice generates the credit proof for that exact reference with the existing
   relation/parameters. Reusing the old fixture credit proof would be invalid.
3. **Batch A — deposit:** reconstruct all accepted lane transactions from the
   bootstrap tip to the native endpoint, register the deposit once, prove and
   independently verify. Settle using the unchanged 100M state-covenant value.
   The resulting user ledger is reserve10/pending10/private0/unpaid0 KAS.
4. Publish credit then Alice's real private payment to Bob4/change6. Retain all
   payloads/ciphertexts. **Batch B — credit/payment:** extend the settled root/tip,
   include every intervening lane transaction (including prior settlements and
   irrelevant/failed operations), prove, independently verify and settle. State
   is reserve10/private10/pending0/unpaid0. Bob independently reconstructs public
   state and discovers/validates his note with his own backup and hash-checked
   public parameters.
5. Bob publishes his real exit proof binding principal400M and exact recipient.
   **Batch C — exit:** extend the committed state/tip, prove and independently
   verify, then settle with separately sponsored permission rent and native fee.
   Native scripts must accept the genuine new receipt and create the expected
   covenant-bound permission UTXO. Record its actual outpoint and value. State
   is reserve10/private6/unpaid4; no liability is discharged yet.
6. Supply the real sponsor builder with the restricted public `permissionRedeem`
   bytes and pinned reserve. Its `privateExitId` flag selects the lane; the redeem
   bytes must also match the actual restricted permission UTXO script hash.
   Keep fee measurement and signing after selecting the exact lane/payload.
   Spend that permission and the selected actual deposit delegate once.
   Native outputs must be **at least 450M to Bob (400M principal + 50M rent refund)**,
   **600M delegate principal change**, and separate sponsor change. Re-read the
   actual native acceptance/UTXO data; do not take executor/RPC success as an
   application accounting instruction.
7. **Batch D — reconciliation:** include the accepted permission-creating
   settlement and native payout in complete lane order, with their actual bytes.
   The guest recognizes covenant output and consumed outpoints, validates all
   native amounts/scripts and marks the exit paid exactly once. Prove and verify
   this state, then settle the final continuation. Require reserve6/private6/
   pending0/unpaid0 and actual permission spentness/recipient output on the
   selected chain. Keep the state-covenant 100M unchanged.

The local fixture's input positions are fixed: permission0/reserve1/sponsor2;
payout0/delegate-change1/sponsor-change2. The settlement's two covenant outputs
remain continuation0/permission1, as required by the existing script. Sponsor
change is an unbound sibling. No operator withdrawal key is introduced.

## Ordering and waiting for proofs

After each proof wait, obtain a recent selected-chain anchor authenticating the
unchanged prior active lane leaf (same tip and last-touch score). Reconstruct all
accepted activity since that tip. Use the real latest native context and endpoint
SMT proof; never replace the old last-touch score with the recent block's score.
The new active-lane fold has no artificial 100-score span limit. An expired lane
cannot be treated as unchanged/active: halt and report it. The local gaps of
4,989 / 5,000 / 5,000 scores are fixture tests, not measured TN10 waiting periods.

At each settlement, independently verify the guest image and exact journal;
require the native seqcommit accessor's selected-chain/finality window and
recheck accepted ancestry before the next step. A reorg requires reconstructing
from the last still-accepted checkpoint; a host boolean cannot repair it.

## Explicit proposed budgets

| Resource/domain | Proposed boundary / accounting |
|---|---|
| New guest execution | <=160M user cycles and <=900s per batch, four threads |
| Small / wallet segmentation | po2=16 for A/D, po2=20 for B/C; require multi-segment join |
| Future GPU diagnostics | One separately released L40S; <=3,600s aggregate complete proof process group, including all selected batches/compression/checks |
| Rental | Fresh B lease/guard, <=7,200s from actual creation; no automatic retry or extension |
| Money | USD5 planning ceiling, including actual GPU/storage quote; not a guaranteed provider invoice cap |
| User principal | 1,000M sompi in; 400M out; 600M retained |
| State rent | 100M sompi, excluded from user principal throughout |
| Permission rent | 50M sponsored; returned to Bob on terminal consumption, separate from his 400M principal |
| Native fee planning | Up to 500M test-sompi sponsor allocation, separate from rent/principal; actual fee/mass quotes required for complete final transactions before release |

Local restricted payout measured 3,322/181/100,001 script units for the permission/delegate/
public-key fixture sponsor. Its sponsor signature is genuine; actual funding
inputs, selected UTXOs and a real outer-receipt settlement need their own sizing. Use the existing native engine and checked compute-budget
conversion, native mass rules and final fee estimation; measure all actual
inputs. The fixture's 100k-sompi fee is not a network acceptance quote. Local
execution times do not predict CUDA proving time or production throughput.

## Required negative controls and final evidence

Before a live release, rehearse the complete terminal path locally with genuine
new receipts, including native issuance and full payout. Once released, require
actual TN10 rejection at its enforcement layer for balanced underpayment,
recipient substitution and reserve diversion. After the valid payout, make a
distinct transaction attempting to reuse its permission/delegate and confirm
missing-spent-input rejection. Keep this separate from proof-verifier rejection.

Retain fabricated/duplicate deposit, stale/double-spent note, current nullifier,
wrong predecessor/anchor/domain, missing/foreign permission and accounting replay
checks. Include all invalid operations in lane commitments. An omitted payout
must change the native endpoint; claiming a genuinely proved omitted execution
would require its own separately released proof, not mutation of a receipt.

Deliver exact sompi inputs/outputs, principal/rent/refund/fee reconciliation,
actual receipt verification, native script outcomes, selected-chain acceptance,
permission/reserve spentness, Bob's recipient UTXO and final state/delegate UTXOs.
For any future GPU lease preserve verified evidence on B before confirmed stop
and deletion. No full financial-privacy or production-safety claim follows from
one small testnet lifecycle.

Before funding, confirm the [restricted policy](REVIEW-FIX.md) is used by every
bootstrap/continuation/permission path, including real UTXO selection and signed
payout witnesses. A builder choosing the lane is insufficient native enforcement.
A second registered deposit must survive the first payout; exits cannot aggregate
several reserves in this bounded version. No old unrestricted permission or pool
is silently migrated by these local changes.
