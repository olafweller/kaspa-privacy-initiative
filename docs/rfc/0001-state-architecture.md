# RFC-0001: State architecture for the first native-KAS privacy PoC

**Status:** Open

**Date:** 2026-10-02

**Review owner:** project review; no architecture accepted by this draft.

## Context

We need to determine the smallest architecture that can demonstrate:

```text
test KAS deposit -> private claim -> private value-conserving transfer
-> double-spend prevention -> authorized exit -> native test KAS withdrawal
```

The three candidates in [ARCHITECTURE.md](../ARCHITECTURE.md) share native-KAS backing but place state updates and ordering differently. Current Toccata specifications/code support investigating direct covenant proof verification. The based-app runtime remains a prototype; full cross-program vProgs composition is a separate research design. Exact reviewed commits, interfaces, and limitations are recorded in the [upstream evidence map](../../research/kaspa-toccata-vprogs.md).

This RFC compares candidates and proposes an investigation order. It does not select production cryptography, establish feasibility, or authorize deployment.

## Constraints

- Preserve all [I-1 through I-16](../../SECURITY-INVARIANTS.md). No invariant change is proposed.
- Native KAS is the backing asset; no separate privacy token, real funds, mainnet experiment, or privileged reserve withdrawal.
- Proofs must constrain integer ranges, authorization, authenticated state, conservation, and actual settlement outputs. A proof of an unrelated computation is insufficient.
- Use established constructions after the existing-work review; protocol reuse and licensing remain separate gates.
- Users must have an independently executable recovery/exit path. A safely halted but permanently inaccessible reserve is not a final solution.
- Pin network, genesis/pool identity, program/key identity, state encoding, dependencies, and resource limits. Test compatibility on the actual TN10 configuration.
- Separate cryptographic confidentiality from public boundaries and metadata. Outsourced proving must not silently disclose note secrets.

## Options considered

### A. Minimal L1 covenant + ZK pool

A covenant-controlled reserve/state UTXO commits to authenticated note and spent-resource state. A deposit, private transition, or withdrawal spends it and installs the successor state under the same protocol rules. A proof validates the hidden operation; the covenant validates the transaction's actual outputs and reserve accounting.

**Pros**

- Fewest execution/ordering components to investigate.
- L1 UTXO consumption supplies one serialized settlement history.
- Direct relationship between state progression and reserve release.
- No lane runtime or cross-app composition is assumed necessary.

**Cons / risks**

- Updates compete for the current state UTXO; losing transactions may require new witnesses/proofs.
- Wallet discovery, authenticated nullifier updates, historical data, and recovery still need a specification.
- A root alone cannot reconstruct a tree or encrypted note history.
- A proof binding the successor root does not automatically bind successor script, amount, fees, or exit recipient.

### B. Sharded/native covenant UTXO state

Partition reserve/state across covenant resources. Independent shards can progress concurrently; cross-shard transfers and reserve movement require atomic settlement or another reviewed coordination mechanism.

**Pros**

- Potential native concurrency without adopting a shared runtime.
- Can benchmark a localized contention bottleneck.
- May reuse direct covenant settlement ideas from A.

**Cons / risks**

- Duplicate spending across shards unless note assignment/nullification is globally coherent.
- Cross-shard migration can duplicate claims or leave claims without backing.
- A globally serialized nullifier root may erase the expected concurrency gain.
- Shard selection, rebalance, and cross-shard access add wallet complexity and observable structure.
- Per-shard solvency and aggregate solvency need separate proof obligations.

### C. Based app / vProgs shared state

L1 lane activity provides ordering commitments. An off-chain application validates shielded operations, constructs batches, and proves updates; a covenant settles the proven state and exits against the correct L1 sequence. Evaluate one based app first; do not assume full cross-app composition is required.

**Pros**

- Batching may amortize L1 verification across many operations.
- Runtime components may provide scheduling, storage, rollback, and proving coordination.
- A single logical commitment/nullifier domain may avoid shard-specific spend semantics.

**Cons / risks**

- More components and prototype APIs; pin a compatible dependency set.
- Accepted execution, proved state, settled state, and withdrawable state must be distinguished.
- Settlement still advances covenant UTXOs; batching does not remove all serialization.
- Lane proofs must establish the intended sequence and handling of failed/invalid operations.
- Payload access patterns and proving witnesses can leak ownership or amounts. A general-purpose executor is not automatically a private executor.
- Recovery needs published/retained data and reproducible proving, not just a state-service API.

### Comparative assessment

These are design expectations, not measured results.

| Criterion | A: one state UTXO | B: sharded covenant state | C: based app/shared state |
| --- | --- | --- | --- |
| Current capability | Direct inline-ZK primitives; pool unvalidated | Primitives present; shard semantics unvalidated | Lanes/verifiers present; runtime prototype |
| Implementation complexity | Lowest relative scope; custom pool rules remain | High coordination complexity | High integration and operational complexity |
| Concurrency | Serialized updates; batching possible | Parallel only where dependencies permit | Batched execution/proving; serialized settlement remains |
| Exit safety | Direct atomic reserve debit + claim consumption | Must bind shard reserve and unique claim | Must bind settled state, sequence, exit commitment, and payout |
| State availability | Retain commitments/nullifiers/ciphertexts | Same, plus shard/migration history | Same, plus lane/settlement replay data |
| Wallet complexity | Inclusion witnesses and retries | Multi-shard witnesses/routing | Pending vs settled state and runtime interfaces |
| Privacy/anonymity | One logical pool; operation timing visible | Possible fragmentation and routing leakage | Shared pool possible; payload/resource access can leak |
| Proving cost | Per update; no benchmark | Multiple roots/coordination may add work | Recursion/batching may amortize cost; no benchmark |
| Upgrade risk | Covenant/verifier identity | Coordinated shard versions | Runtime/guest/ABI/covenant compatibility |
| Additional assumptions | Witness/history availability | Atomic cross-shard consistency | Lane replay, runtime determinism, proving/settlement availability |

## Security analysis

All candidates must satisfy the same obligations. None receives a waiver for being a testnet experiment.

| Invariants | Required check | Candidate-specific concern |
| --- | --- | --- |
| I-1, I-2, I-12 | Range-constrained claims and explicit deposits, exits, fees, and isolated reserves | A: all outputs; B: migration/solvency; C: pending exits and settlement accounting |
| I-3, I-14 | Spend authorization and recipient-verifiable spendability | A/B/C: reuse a reviewed note/key model; do not mistake inclusion for ownership |
| I-4, I-15 | Authenticated spent-state update and deterministic rejection | A: current nullifier root; B: cross-shard duplicates; C: batch duplicates and replay |
| I-5, I-6 | Pin verifier/program and bind current settlement state and domain | A: state UTXO/pool; B: complete shard input set; C: lane, sequence interval, and guest images |
| I-7, I-8, I-13 | Bind payout destination/value, reserve continuation, and explicit upgrade authority | No operator signature or upgrade mechanism may bypass withdrawal rules |
| I-9, I-10, I-11 | Reject unverifiable updates; independently reconstruct state and generate exits | State roots alone do not provide witnesses; C also needs deterministic lane replay |
| I-16 | State privacy limits and measured leakage | A: event timing; B: shard metadata; C: public payloads and outsourced witnesses |

For every deposit, claim creation must bind to new native backing and must not replay a deposit. For every withdrawal, claim consumption, any pending-exit entitlement, reserve debit, payout, change, and explicit fees must account for the same value atomically or through a proven intermediate state. Burning a private claim into an unpaid public exit does not eliminate the liability.

L1 input/output conservation alone does not prove private supply conservation or correct payout: an attacker can redirect value into another transaction output. A covenant must enforce the complete intended output layout.

A note inclusion anchor may be historical if the protocol explicitly permits it; that must not permit stale settlement-state or spent-state replay. Define this distinction before choosing root policies.

## Privacy analysis

Deposits, withdrawals, public amounts at those boundaries, fees, roots, operation timing, and network activity may remain observable. Nullifiers must prevent duplicate consumption without linking spends to note commitments under the selected construction. Sharding can expose routing and restrict effective anonymity; batching can obscure individual timing but does not guarantee anonymity.

For C, publish ciphertexts/proofs and sufficient public transition data without publishing private witnesses. Specify how an executor validates a confidential operation. For every candidate, sending plaintext notes/spend material to a hosted prover introduces a confidentiality assumption that must be disclosed or avoided through local/private proving.

## Proposed direction / outcome

**Not decided.** Proposed investigation order: test A's settlement feasibility first, retain B and C as alternatives, and reconsider after measured results. A is the smallest falsifiable baseline, not an accepted production architecture. No throughput or permissionless-exit claim has been demonstrated.

Before implementation, reviewers must assess this RFC and the existing-work map. Then define the proof statement, recovery data, and covenant output constraints. A later explicit review records acceptance or rejection; this draft changes no architectural commitment.

## Objections / unresolved questions

- Can A's full proof and output layout fit TN10 script, transaction, and relay budgets?
- Which established note/nullifier/key construction fits the supported verifier path and setup assumptions?
- What exact published/archived data lets an independent participant rebuild witnesses after pruning?
- Can a user exit despite infrastructure censorship, and with what confirmation/reorg policy?
- Does B actually parallelize nullification and cross-shard reserve movement?
- Can C process confidential operations without giving an executor private spend material?
- What are real-proof costs and delays, including retries and settlement contention?

## Evidence

- [Pinned upstream map](../../research/kaspa-toccata-vprogs.md): active KIPs, verifier source, prototype runtime, draft full-vProgs specification, and inspected exits.
- [Existing Kaspa work](../../research/existing-kaspa-privacy.md): prior proposal and boundaries of source inspection.
- Mature-protocol research leads: [Orchard](../../research/zcash-orchard.md), [Aztec](../../research/aztec.md), [RAILGUN](../../research/railgun.md), [Monero](../../research/monero.md), [MWEB](../../research/litecoin-mweb.md). These notes are study inputs, not completed component reuse/security reviews.
- [A0](../poc-a0.md) now supplies local real-proof consensus-code measurements and a limited circuit/covenant review for one terminal claim. No real-proof TN10 round trip or recovery experiment exists yet. This preliminary evidence does not accept this RFC; upstream development-mode demos do not substitute for the remaining gates.

## Revisit if

- A fails a verifier/budget/recovery gate or contention makes the intended experiment impractical.
- B demonstrates independent safe nullification and atomic cross-shard accounting.
- C supplies a reproducible real-proof lifecycle and recovery path for confidential operations.
- Upstream verifier, lane, runtime, or upgrade semantics change.
- Independent review finds an invariant violation or an undisclosed trust assumption.
