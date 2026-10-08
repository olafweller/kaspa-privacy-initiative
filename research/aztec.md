# Aztec

**Reviewed: 2026-10-08.** The pinned reference is Aztec v5.2.0 (`49a5921`), matching the inspected developer documentation. The moving `next` head (`a36ddcc`) was also resolved, but has a different tree layout; its behavior is not substituted for release code. No Aztec application or prover was run.

## Source facts: private application state

Aztec's [state model][A1] combines append-only note hashes with nullifiers. A note is application-defined private state; it is not automatically a value-conserving payment note. The [note interface][A2] handles note hashes, ownership and nullification, with kernel-level contract siloing and note uniqueness. Its unconstrained helpers are not substitutes for constraints. The [UintNote implementation][A4] is a concrete value-note example, not a proof that arbitrary apps conserve assets.

The [indexed Merkle-tree description][A3] stores ordered nullifier values with next-value/index links. A predecessor non-membership proof can avoid a field-width sparse tree, and batches can amortize insertion. Correct predecessor bounds, duplicate rejection, current roots and linkage remain necessary; a faster tree is not a weaker spentness rule.

## Discovery and data availability: P12 / P10

The pinned [note-discovery guide][A5] describes shared-secret tags and contract siloing. Four setup approaches have different recovery/privacy costs: arbitrary secrets exchanged off chain; address-derived secrets with known senders; non-interactive on-chain handshakes; and interactive delivery requiring recipient participation. The non-interactive handshake reveals its recipient. The PXE fetches tagged private logs, decrypts them and checks the reconstructed note against transaction effects. Its tag-query API can reveal linkable interest to a server; proposed private retrieval is not a present guarantee.

The [delivery guide][A6] also permits off-chain encrypted delivery. Consequently, a seed alone may not restore every app's notes: sender relationships, shared secrets/counters, handshakes, contract artifacts and delivery history can matter.

The official [blob-storage operator guide][A7] explains finite Ethereum blob retention and the use of independent archives for old synchronization. **Interpretation:** DA at publication and long-term recoverability are different properties. KPI needs retained ciphertexts, ordered note hashes/nullifiers, accepted state and necessary discovery metadata after Kaspa pruning. PXE availability does not itself establish P10.

## Exits and fee privacy

The [Outbox contract][A8] consumes authenticated messages from proven rollup state. Its comments identify assumptions about stable leaf identifiers across partial-epoch roots; those are responsibilities of the larger protocol. An L2 exit intent, an accepted proof, an L1 message claim and a native payout are distinct events. The official [bridging guide][A9] does not by itself establish a universally available exit during sequencer/prover failure.

FeeJuice payment has a public funding boundary. The pinned [private FeeJuice guide][A10] describes a community FPC pattern with privately held notes and nullifiers over claims. It is an application pattern to examine, not an audited fee-privacy guarantee or a proposal to create a KPI token. A fee sponsor can hide the user's direct gas payer while introducing funding, service and timing links.

## Anonymity, scaling and failure lessons

The [privacy considerations][A11] warn that public interactions can fingerprint an otherwise private operation. Contract-siloed state, tagging, handshakes and application behavior affect the effective anonymity set. Private local execution can hide a witness from the sequencer; outsourcing that witness changes the assumption. Parallel private proving and batched insertion do not remove shared-root consistency or final settlement bottlenecks.

**Known boundaries, not an alleged current exploit:** off-chain note loss, tag-query leakage, public-call fingerprints and incomplete L1/L2 bindings are explicit things to investigate. Indexed trees do not solve censorship or archive loss. Grumpkin/Barretenberg-based machinery is classical and is not automatically compatible with either Kaspa verifier tag or post-quantum migration.

## Component assessment — provisional

| Building block | Potentially reusable | Adaptation needed | Risks | Still to prove for KPI |
| --- | --- | --- | --- | --- |
| Notes / local PXE [A1][A2][A4] | Client-side private execution and typed notes | Explicit native KAS conservation and spending rules | App underconstraints; witness outsourcing | Amount ranges, ownership and outputs enforced by real proofs |
| Siloed hashes/nullifiers [A2] | Contract/version replay separation | Pool/lane domains and accepted root rules | Wrong-domain spend; duplicate transient notes | Cross-pool and cross-version replay rejection |
| Indexed spent tree [A3] | Short non-membership proofs and batched insertion | Kaspa state transitions and reorg rollback | Bad predecessor bounds; stale-root insertion | Duplicate-safe concurrent processing and measured contention |
| Tagged discovery [A5][A6] | Less trial decryption; multiple delivery models | Recovery metadata and private query transport | Recipient handshake or server interest leakage | Sender-independent restore and privacy with little activity |
| DA / archives [A7] | Separation of inclusion, availability and retention | Persistent encrypted Kaspa history | Seed-only recovery fails; archives disappear | Recovery from authenticated data after default operators vanish |
| Outbox / portal [A8][A9] | Consumed-message accounting | Native covenant reserve and exact payout bindings | Replay across roots; stalled proving/settlement | Independent permissionless exit with stable liabilities |
| Private fee pattern [A10] | Fee payment from private state | Native KAS fee accounting and permissionless services | Sponsor dependence; public funding correlation | Fee volatility and sponsor failure without user linkage |
| Parallel proving / batching [A1][A3] | Independent witness computation | Shared anonymous state with ordered conflict resolution | Sharding privacy loss; root bottleneck | Throughput, witness updates and anonymity under realistic workloads |

**Open hypothesis:** tagged discovery and indexed spent-state techniques may be useful independently of adopting Aztec's runtime. Their security, license, circuit/backend compatibility and long-term recovery costs must be established before selection.

[A1]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/docs/docs-developers/docs/foundational-topics/state_management.md
[A2]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/noir-projects/aztec-nr/aztec/src/note/note_interface.nr
[A3]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/docs/docs-developers/docs/foundational-topics/advanced/storage/indexed_merkle_tree.mdx
[A4]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/noir-projects/aztec-nr/uint-note/src/uint_note.nr
[A5]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/docs/docs-developers/docs/foundational-topics/advanced/storage/note_discovery.md
[A6]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/docs/docs-developers/docs/aztec-nr/framework-description/note_delivery.md
[A7]: https://docs.aztec.network/operate/operators/setup/blob_storage
[A8]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/l1-contracts/src/core/messagebridge/Outbox.sol
[A9]: https://docs.aztec.network/participate/basics/bridging
[A10]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/docs/docs-developers/docs/aztec-js/how_to_use_private_fee_juice.md
[A11]: https://github.com/AztecProtocol/aztec-packages/blob/49a592109ec4f18d79212b43d621891aaf36f7b6/docs/docs-developers/docs/resources/considerations/privacy_considerations.md
