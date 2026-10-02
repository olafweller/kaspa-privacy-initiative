# Terminology

## Native KAS

KAS recorded and transferred under Kaspa's base-layer rules.

## Shield

Move native KAS from transparent ownership into protocol-controlled backing while creating a corresponding private claim.

## Unshield

Consume a valid private claim and release the corresponding native KAS to a transparent Kaspa output/address.

## Shielded domain

The private state/system in which ownership and transfers are represented cryptographically rather than as directly visible KAS payment amounts on the public ledger.

## Private KAS

Informal UX phrase for KAS value represented by valid private claims inside the shielded domain. It is **not** a separate token.

## Note

A private record that may encode value, owner/recipient information, randomness, and other metadata needed by the privacy protocol.

## Note commitment

A public cryptographic commitment to a private note. It allows the system to commit to note existence without revealing note contents.

## Nullifier

A public one-time value used to show that a private resource has been consumed without necessarily identifying the original note commitment. Duplicate nullifiers can prevent double spending.

## Commitment tree / note tree

A verifiable data structure containing note commitments or state commitments.

## State root

A compact cryptographic commitment to a larger state structure.

## Witness

Data needed to prove a statement such as note inclusion in a commitment tree.

## Zero-knowledge proof (ZK proof)

A proof that a statement is true without exposing all private inputs used to prove it.

## Prover

Software/infrastructure that generates a ZK proof.

## Verifier

The logic that checks a proof. For protocol safety, the verifier must enforce the exact intended statement.

## Covenant

Kaspa programmability that constrains how an output may be spent based on protocol-defined conditions and transaction context.

## Toccata

Kaspa's programmability upgrade, including covenants, transaction introspection, ZK verification, and sequencing support for based apps.

## Based app

An application model where Kaspa L1 provides ordering/commitment while application execution and proving occur in an application runtime and settle back to L1 under verifiable rules.

## vProgs

Kaspa's evolving reference framework/runtime for based computation, including transaction scheduling, execution runtime, state management, and proving components. As of October 2026 it remains early/prototype infrastructure.

## Executor

A component that interprets ordered application transactions and computes state transitions.

## Sequencing / sequence commitment

Mechanisms binding application activity to the relevant ordered Kaspa L1 activity so proofs settle the intended sequence/state.

## Anonymity set

The set of plausible users/notes/actions that an observer cannot reliably distinguish from one another.

A large pool balance alone does not guarantee a large effective anonymity set.

## Timing correlation

Inferring a relationship between public events because they occur close together in time.

## Amount correlation

Inferring a relationship because public deposit/withdrawal values are unusually similar or unique.

## Safety

The property that invalid actions cannot cause theft, inflation, double spending, or unauthorized state changes.

## Liveness

The property that valid users can continue making progress.

## Custody

A situation where another party has discretionary ability to control, move, or withhold a user's assets.

## Project steward

A coordination role for research, contributors, documentation, and project execution. It should not imply protocol ownership or privileged control of user funds.
