# Proposed first shielded TN10 cycle — review required

Status: a concrete conditional proposal, **not ready for funding**. This local
work package performs no new TN10 transaction and selects no production protocol.
See [RFC-0002](../../docs/rfc/0002-shielded-payment.md), [visibility](VISIBILITY.md)
and [results](RESULTS.md).

## One experiment

Use a fresh pool/identity, native test-KAS only, with separate Alice and Bob wallet
roles and a fee payer outside user backing. Bootstrap reviewed immutable program/
verifier pins. Alice's authenticated ten-test-KAS deposit creates a private note.
Alice locally proves a payment of four to Bob and change of six to herself. Bob
independently discovers and validates the encrypted receipt from accepted public
data, rebuilds his witness and locally proves a four-test-KAS withdrawal. Proved
canonical processing creates the pending claim; the native permission path pays
Bob the exact principal plus any separately backed rent refund. Alice retains six
in private claims backed by six native test-KAS. Fee/rent funding is measured and
reported separately; the example principal values exclude those charges.

Use an initial fixed native-KAS pool and one explicitly supported statement
version. Preserve the same native verification path as the public rehearsal
where applicable; no older funded outputs, privileged rescue or migration path.
Each broadcast has a write-once intent and retained raw response. Failed trials
use new identities. The normal node is not stopped.

## Decisions required before implementation/funding

1. **Complete private relation and data formats:** review membership, authority,
   nullifier derivation, bounded values, output/change/delivery binding and exact
   canonical public intent. The small measured preimage/sum relation is not this
   circuit. Resolve code rights; no RAILGUN circuit source is imported.
2. **Invalid-operation handling:** demonstrate an enforced valid/invalid outcome
   with no arbitrary host rejection, unresolved assumptions or whole-batch-only
   halt. The measured composition syscall alone does not supply this capability.
   Prove that valid-bad-valid lane processing preserves both valid operations and
   commits the rejected one without economic side effects.
3. **Real lane payload and budgets:** design the noncircular intent/proof envelope,
   bind the actual native ID/context outside the wallet proof, provide verifiable
   proof/data availability, and measure full serialized/transient/storage/compute
   mass. An archived succinct receipt's byte length is not the selected wire size.
4. **Deposit credit/recovery and native exits:** implement/prove every supported
   funded deposit's pending-credit or owner-recovery path without double credit/
   refund. Bind actual reserve/permission outputs, liabilities, fees and refunds.
   The model refund method is not an already available native covenant feature.
5. **Review and full rehearsal:** review the above design and new security-critical
   implementation before a fresh funded TN10 run. A complete real terminal payout
   is required before calling the funded trial successful or ready for repetition.

The local experiment can support a candidate recommendation but does not close
these decisions. If no practical invalid-proof path or payload budget is found,
report a blocker or revise the candidate; do not weaken completeness or safety.

## Declared acceptance criteria for that experiment

| Criterion | Required observation |
| --- | --- |
| Actual private lifecycle | Real wallet proofs, real ordered lane inputs, correct shielded transitions and confirmed native payout; no development receipts. |
| Witness privacy boundary | Only wallet processes receive private notes/keys/selected witnesses. Executor/outer prover inputs, public journals and logs contain the specified public fields only. |
| Bob's receipt | Bob discovers/decrypts, validates commitment/ownership and creates his own next spend using his secrets and public protocol data, without Alice/executor private state. |
| Conservation/backing | Exact native IDs/output amounts, private input/output/fee equations, six remaining principal and pending exits/rent reconcile at every stage. |
| Double-spend/current state | Two individually valid wallet proofs sharing an old anchor cannot both consume the same economic note, within or across batches. |
| Invalid processing | Valid-bad-valid sequence has forced canonical outcomes; invalid proof, unauthorized spend, wrong root, range/inflation, changed output/fee/payout and replay are rejected at their actual enforcing layer without partial updates. |
| Native settlement binding | Correct claim accepted; omitted same-endpoint operation and underpaid/diverted native payout rejected by the node, not only by preparation. |
| Version boundary | Other pool/network/version statements rejected; no alternate accepted version route can consume an already spent claim. No migration support is claimed. |
| Performance/data report | Measure wallet/outer proving separately, proof/wire sizes, actual fees, retained data and discovery/witness costs on declared hardware. |

## Claims expressly not established by Alice/Bob

This is one shielded payment cycle under explicit assumptions, not effective
anonymity, a production architecture or the N-user shutdown test. A unique public
10 deposit and 4 exit can correlate strongly. General reorg/expiry/pruning
recovery, independent operators, migration, sustained throughput, mobile wallet
performance, permissionless fee liveness and independent security review remain
separate gates. These limitations cannot be removed by an otherwise successful
proof or payout.
