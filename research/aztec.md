# Aztec — Research Notes

## Why study it

Aztec provides a modern example of private application state built from notes, commitments, nullifiers, private execution, note discovery, and public/private state interaction.

It is especially useful for thinking beyond a one-shot mixer toward a persistent private economy/wallet experience.

## Relevant concepts

### Private state as notes

Aztec documents private state as UTXO-like notes whose commitments live in an append-only note hash tree.

### Nullifier tree

Consuming a private note creates a nullifier rather than deleting the original commitment. This prevents double spending while reducing direct linkage between creation and spend.

### Note discovery

The user needs an efficient way to identify encrypted notes intended for them without asking an untrusted server, "which notes are mine?"

### Private execution environment

Aztec treats private state and public state as different execution concerns, with wallet/client-side private execution playing a major role.

## Lessons for KPI

- private state is not only a settlement problem; it is also a wallet state-management problem;
- note discovery must be designed early;
- append-only commitments + nullifiers are a strong pattern to evaluate;
- user-owned local private state databases may be required;
- privacy-preserving state access can be as important as the proof circuit.

## Questions before reuse

- Which parts depend on Aztec's rollup architecture?
- Can Kaspa provide enough public/reconstructable data for similar note discovery?
- Should KPI wallets maintain local encrypted note databases?
- How are backup and recovery handled without trusted servers?

## Primary sources

- https://docs.aztec.network/developers/docs/foundational-topics
- https://docs.aztec.network/developers/docs/foundational-topics/state_management
- https://docs.aztec.network/developers/docs/aztec-nr/framework-description/state_variables
