# Future TN10 publication and canonical interval capture

No live publication was authorized. This runbook contains no executable broadcast
command. Fixture outpoints, bodies, amounts and block labels are synthetic and
must never be submitted. A dedicated real trial requires fresh identities and an
explicit authorization before funding or submitting anything.

## Supported source-level publication route

Use an ordinary version-1 Kaspa transaction on a user lane, not a settlement
covenant spend for each operation. For this experiment the namespace is the four
literal bytes `4b50494c` (`KPIL`), followed by 16 zero bytes. Hex subnetwork ID:
`4b50494c00000000000000000000000000000000`. This encoding satisfies KIP-21:
at least one namespace byte in positions 1–3 is nonzero. Namespace uniqueness is
not permissioned or guaranteed: other users can publish here too. For a live
trial choose a fresh namespace and define all unrelated/malformed lane payloads
as no-ops while including them in every activity commitment.

Payload is `4b50492d4c414e452d7631 || u32_le(operation_number)` for numbers 1–10.
Normal fee-paying inputs and change outputs are required. User lanes support gas;
zero gas is supported by the current reference activity builder for this trivial
app. Gas is not a privacy fee or authorization mechanism. The payload has 15 bytes.

Reuse [`ActivityTx`/`activity_transaction`][ACT] and [`FeePolicy`][FEES]. The builder
uses the specified lane and version, signs ordinary inputs, prices the final mass
and commits storage mass. Pass current TN10 consensus parameters; do not reuse
the fixture's synthetic inputs or assume its amounts are spendable. An isolated
offline builder is not a mempool acceptance test. Verify node version, network,
Toccata activation, lane shape, current fees and relay policy before any authorized
publication. Record actual funding/operation/settlement transactions and receipts.

## Canonical order and witnesses

1. Retain the deployed covenant outpoint, actual covenant ID, exact guest image,
   old state, lane key/tip, last-touch score and a verified start block/seqcommit.
   A real covenant ID must come from the bootstrap transaction; the fixture uses
   a dummy ID. Initialize a fresh lane with authenticated non-inclusion at the
   start, or establish its active start tip before the measured interval. The
   current guest supports only an already-active lane; add and review first-touch
   initialization before a fresh live deployment. Do not use a development redeem.
2. Use [`getVirtualChainFromBlockV2`][RPC] at `Full` verbosity, as in the reference
   [bridge][BRIDGE]. It provides ordered accepted bodies and chain headers. Its
   full accepted stream includes selected-parent coinbase. Enumerate **before**
   lane filtering; the resulting index is `merge_idx`. Use the supplied selected
   chain ordering, not sorting payload numbers, transaction IDs or arrival times.
3. Obtain `GetSeqCommitLaneProof(end_block, lane_key)` and start inclusion from
   a synchronized, independently operated node. Authenticate its SMT decomposition
   against the header's `accepted_id_merkle_root`. Verify selected-parent visibility
   and access depth from the settlement's validation point of view. A JSON document
   or executor-provided root is not a canonical L1 anchor.
4. Feed the public transaction payloads/rest preimages and context into the guest.
   Process `(start,end]`: selected-parent timestamp, accepting-block DAA and blue
   score, strictly ascending block-local mergeset indices. Every accepted lane
   transaction participates, including application no-ops.
5. Retain removed-chain notifications. Roll back and discard orphaned proof
   candidates before settlement; obtain new witnesses. This PoC does not implement
   a live reorg-aware collector. It rejects unknown/orphan anchors at the script
   boundary in the offline harness.
6. Build the production settlement with `block_prove_to=end_block`, correct
   covenant ID/outpoint, old state/tip and new state/tip, and a real receipt. Native
   script reconstructs the journal using `OpChainblockSeqCommit(end_block)`.
   Add independently fee-funded inputs; the successor must preserve the covenant
   value. Size the budget by actual verification and check all three mass limits.
   Obtain explicit funding/broadcast authorization for the concrete trial.
7. Repeat omission of 3/6/9 over exactly that accepted interval. Keep rejection
   errors, bodies, witnesses and node acceptance evidence. A successful full
   executor alone does not establish completeness or censorship resistance.

## Gates still open

Live node availability, canonical header validation, activation/relay policy,
first-touch bootstrap, reorg capture, namespace contamination, witness availability,
pruning/archival retention, expiry/reactivation, fee funding and actual settlement
confirmation remain untested. The short continuous-lane guest intentionally does
not reset its tip after expiry: unsupported intervals fail or cannot match the
canonical endpoint. It cannot validate long-silent/reactivated intervals without
inactivity/non-inclusion proofs. General scheduling and cross-app vProgs machinery
are unnecessary for this application, but this test does not settle whether a
future private pool requires them.

[ACT]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/l1/wallet/src/build/activity.rs
[FEES]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/l1/wallet/src/build/pricing.rs
[RPC]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/rpc/service/src/service.rs
[BRIDGE]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/l1/bridge/src/worker.rs
