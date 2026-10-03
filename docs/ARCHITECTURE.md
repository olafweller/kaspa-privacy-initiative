# Candidate Architecture

**Status:** exploratory. No architecture has been selected.

The proposed comparison is in [ADR-0001](adr/0001-state-architecture.md). It remains unaccepted pending review.

The [A0 feasibility experiment](poc-a0.md) investigates direct Groth16 proof
authorization and native payout constraints for one terminal claim. Its local
consensus-code evidence must be distinguished from funded TN10 acceptance and
the broader private-state/recovery requirements. This experiment does not select
Candidate A or accept ADR-0001. A0.5 now records a terminal TN10 release and
spent-input replay rejection through a retained-key/native-RPC test adapter
under [ADR-0002](adr/0002-a0-reserve-release-experiment.md), with no change to
the terminal proof statement or the candidate architecture.

The purpose of this document is to compare candidate ways to create optional privacy for native KAS without prematurely locking the project into one implementation.

## Initial asset scope

**Initial scope: native KAS only.** KCC20/private token transfers and trading are explicitly out of scope for the initial protocol and PoCs.

Where reasonably possible, the architecture should avoid design decisions that would unnecessarily prevent future support for KCC20 or other Kaspa-native assets. This is a future extensibility consideration, not a requirement for the initial protocol. It must not outweigh security, simplicity, native-KAS privacy, or other primary design requirements.

This is a reversible early-stage scope/design constraint, not a commitment to a long-term protocol feature or a selection of any candidate architecture. Future KCC20 or other asset support would require separate research and an explicit later design decision recorded in an ADR.

## 1. Common economic model

Regardless of implementation, the intended model is:

```text
native KAS enters
      |
      v
protocol-controlled reserve
      |
      +---- public commitments / state roots
      |
      v
private claims / notes
      |
private transfers change claim ownership
      |
      v
valid exit proof
      |
      v
native KAS leaves
```

A private note is best understood as a cryptographic claim on backing, not as a separate cryptocurrency.

The proof-statement specification must define separate integer accounting equations for deposits, private transfers, withdrawal requests, pending exits, completed payouts, and explicit fees. An unpaid exit remains a user liability after its private note is consumed. Reserve rent and externally sponsored fees must be distinguished from spendable user backing. Every actual reserve output and payout must be bound to the verified transition. See [proposal P06](INITIAL-ISSUES.md#p06--define-value-conservation-proof-statement) and [I-1, I-2, I-7, and I-12](../SECURITY-INVARIANTS.md).

If a user shields 10,000 KAS and privately pays 5,000 KAS, the public Kaspa ledger does **not** necessarily need to show a 5,000 KAS UTXO moving. The reserve can remain locked while private state changes which keys can later prove claims on that reserve.

## 2. Common private-state building blocks

A note-based design would likely need concepts such as:

### Notes

Private records containing at least some combination of:

- value;
- recipient/owner information;
- randomness;
- protocol/domain identifiers;
- metadata required for secure nullification and encryption.

Exact construction is undecided.

### Commitments

Public cryptographic commitments to private notes. Observers can verify inclusion without seeing note contents.

### Nullifiers

Public one-time values proving that a private resource has been consumed without necessarily revealing which commitment was spent.

Nullifier design is security-critical and should draw from mature systems rather than being improvised.

### Commitment/state tree

An append-only or otherwise verifiable structure tracking public commitments/state.

### Proofs

A spender proves the required facts without exposing private note contents, for example:

- valid ownership/authorization;
- input existence;
- authenticated spent-state checks and updates;
- value conservation;
- valid output commitments;
- correct prior state binding.

Note inclusion alone does not establish that an input is unspent. The design must specify how proof-verified spent-state updates and settlement duplicate-nullifier checks work together. A historical note inclusion anchor, if explicitly permitted, must not allow stale settlement/nullifier-state replay.

### Encrypted note delivery / discovery

Recipients must learn enough private data to recognize and later spend notes without revealing ownership to untrusted infrastructure.

## 3. Publicly observable boundaries

A likely shielded system cannot hide everything on the public L1.

Depending on design, observers may still see:

- native KAS entering the reserve;
- native KAS leaving the reserve;
- public commitments/nullifiers/state roots;
- Kaspa fees;
- timing;
- network-level behavior.

The privacy claim must therefore be scoped carefully.

Proof confidentiality against public observers does not automatically hide private witnesses from the prover. Specify local proving or disclose what a hosted prover learns. A based app must also explain confidential execution and what its public payloads and resource-access patterns reveal.

## 4. Candidate A: Minimal L1 covenant + ZK pool

### Sketch

```text
Deposit KAS
   |
   v
Covenant-controlled reserve/state UTXO
   |
private transition proof
   |
   v
Updated covenant/state UTXO
```

### Why it is attractive

- smallest candidate scope for a testnet settlement experiment;
- uses current Kaspa primitives directly;
- direct relationship between state progression and settlement;
- may demonstrate ZK verification and value conservation without a full application runtime, subject to verifier, budget, and recovery validation.

### Main concern: contention

If one state-carrying UTXO must be spent for every update, concurrent users may compete to consume the same state object.

This may be acceptable for a PoC but unattractive for a large privacy system.

### Research questions

- Can commitments/nullifiers be split across multiple UTXOs safely?
- Can batching reduce contention?
- Can state be sharded without fragmenting privacy or complicating exits?

## 5. Candidate B: Sharded/native covenant UTXO architecture

Instead of one state object, state could be partitioned across multiple covenant-controlled UTXOs or resources.

### Potential benefits

- greater concurrency using native UTXO parallelism;
- less dependence on an external shared-state runtime.

### Potential costs

- harder cross-shard/private-note semantics;
- more complex wallet behavior;
- fragmented state may reduce anonymity or complicate note selection;
- exit and rebalance paths may become difficult;
- proving across multiple state objects may be expensive.

This route should be evaluated rather than assumed to be superior merely because Kaspa is a UTXO system.

## 6. Candidate C: Based app / vProgs shared state

Kaspa's based-app model uses L1 for ordering/commitment while application execution and proving can happen in an application runtime, followed by proof-based settlement to an L1 covenant.

Simplified flow:

```text
Kaspa L1 lane activity
        |
        v
execute private app transactions
        |
        v
update shielded application state
        |
        v
prove receipts / batches / aggregate
        |
        v
settle proof to L1 covenant
        |
        v
new accepted application state
```

This pattern may amortize settlement across many operations. Whether that makes it suitable for a large shared shielded state requires benchmarks and a reviewed privacy/recovery model. Executed, proved, settled, and withdrawable states are distinct; asynchronous execution does not make an unproved exit withdrawable.

### Potential benefits

- batching may reduce L1 updates per user operation; settlement UTXOs still serialize updates;
- asynchronous proving/aggregation;
- potential throughput improvement that remains to be measured;
- application-level execution and storage tooling.

### Current limitation

The `kaspanet/vprogs` repository describes itself as early development / prototype. Kaspa's builder documentation describes full vProgs as the future direction for composition between independent apps, with the runtime still evolving rather than a stable external API or production dependency.

Therefore:

> Investigate which based-app/vProgs components, if any, this application needs. Neither vProgs nor sharding is preselected as the scaling path.

## 7. Safety and liveness separation

The architecture must explicitly distinguish:

### Safety

Can funds be stolen, inflated, or spent without authorization?

### Liveness

Can valid users make progress promptly?

A preferred design allows infrastructure to fail or be replaced without compromising safety.

A state root authenticates data; it does not supply commitment history, nullifiers, encrypted note delivery, or Merkle witnesses. Specify which data comes from retained Kaspa history, replicated archives, user backups, and independent software. Pruning and reorg handling must be explicit. Safely halting under I-9 does not satisfy recoverability under I-10 by itself.

For example, if prover A disappears, the desirable failure mode is:

```text
transactions temporarily stop
-> prover B reconstructs state
-> proving resumes
```

not:

```text
prover A disappears
-> user funds cannot ever be recovered
```

## 8. Exit architecture

A viable architecture must explain how a user can recover native KAS without cooperation from a privileged operator. A candidate must pass the [early exit and recovery gate](ROADMAP.md#early-exit-and-recovery-gate) before it is treated as credible.

Each candidate must specify:

- the exact proof or protocol condition authorizing native KAS to leave the reserve;
- the component that verifies that condition;
- the L1 covenant/script/state transition that releases the KAS;
- the public inputs bound to the proof and how they bind authorization to the corresponding native KAS payout;
- the required user-held material, including keys/secrets, note data, or backups;
- the required public or independently reconstructable state and history;
- whether an independent prover can reproduce the required exit artifact;
- the recovery and exit behavior when all default operators, provers, and executors disappear.

Open questions also include whether an emergency/escape path is needed and how exits remain safe during upgrades.

## 9. Candidate proof technology

No proof system has been selected.

Toccata provides native L1 ZK verification through `OpZkPrecompile`, including Groth16 and RISC Zero Succinct verification paths; see the [pinned verifier sources](../research/kaspa-toccata-vprogs.md#exact-verifier-surface). This capability does not require full vProgs. Other privacy systems provide lessons from Halo 2 and specialized circuits.

Selection should follow architecture and benchmarking, not branding.

### Proving topology

The architecture should evaluate both local and delegated proving. No proving topology has been selected.

Local proving has privacy and trust-minimization advantages because witnesses do not need to be exposed to external infrastructure. However, proving latency, RAM usage, and hardware requirements may make it impractical on some devices, especially mobile. The protocol should not assume that every user device can efficiently generate proofs locally.

If delegated proving is needed, the preferred direction is permissionless and provider-replaceable. A prover should provide computation, not custody or authorization over user funds. Failure or disappearance of a prover may affect liveness; it must not compromise fund safety.

Architecture comparisons should benchmark:

- proving latency;
- peak memory;
- hardware requirements;
- proof size;
- L1 verification cost;
- opportunities for batching or aggregation.

## 10. Architecture decision process

The next step is not to choose based on intuition.

Review the proposed [ADR-0001](adr/0001-state-architecture.md), which compares:

1. minimal L1 covenant pool;
2. sharded/native covenant state;
3. based-app/vProgs shared state.

Evaluate each against:

- security invariants;
- exit safety;
- current Kaspa capability;
- implementation complexity;
- throughput/concurrency;
- state availability;
- wallet complexity;
- privacy/anonymity implications;
- proving cost;
- upgrade risk.

## Primary sources

- [Kaspa builder overview](https://kaspa.org/build)
- [Kaspa based-app documentation](https://github.com/kaspanet/docs/blob/main/content/docs/toccata/based-apps.mdx)
- [vProgs repository](https://github.com/kaspanet/vprogs)
