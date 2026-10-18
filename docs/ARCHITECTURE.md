# Candidate Architecture

**Status:** exploratory. No architecture has been selected.

The open comparison is in [RFC-0001](rfc/0001-state-architecture.md), pending review.

The [A0 feasibility experiment](poc-a0.md) investigates direct Groth16 proof
authorization and native payout constraints for one terminal claim. Its local
consensus-code evidence must be distinguished from funded TN10 acceptance and
the broader private-state/recovery requirements. This experiment does not select
Candidate A or accept RFC-0001. A0.5 now records a terminal TN10 release and
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

Candidate A is the current experimental baseline: the smallest falsifiable use of current L1 primitives. It is not the accepted production architecture. [RFC-0001](rfc/0001-state-architecture.md) remains open. A0/A1 evidence informs its comparison; notes, nullifiers and private transfers may require major redesign or a different candidate.

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

**Open production blocker: fixed-fee exit liveness.** A1 precommits branch fees. Headroom helps only under bounded future conditions; higher relay/inclusion costs can prevent practical exits. Extraordinary miner cooperation is not an acceptable production exit design. A reviewed sponsorship or other mechanism must preserve reserve, accounting, authorization and output invariants. [Issue #23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23) tracks this question; no mechanism is selected here.

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

No production proof system has been selected. A0/A1 use BN254/Groth16 because the current verifier makes it useful for the experiment. It is not post-quantum. A1's per-instance/fixed-context setups are not the intended scalable private-pool architecture; single-party setup provenance remains trusted.

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

Review the proposed [RFC-0001](rfc/0001-state-architecture.md), which compares:

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

## Public based-app native-value integration experiment

[ADR-0004](adr/0004-public-based-app-native-value.md) scopes the authorized
[public native-value PoC](../poc/native-value/MAPPING.md) following PR31. It combines
existing vProgs account Deposit/Withdraw actions and delegate/permission scripts
with the demonstrated monolithic lane proof. Public balances are temporary test
state, not private notes or a new asset. User backing excludes state-covenant
rent and sponsor fees; an unpaid permission claim remains a liability until L1
consumes it into a payout. Full runtime composition, privacy, mandatory processing
progress and independent recovery remain open. RFC-0001 remains Open.

## Recursive public-account research follow-up

[ADR-0005](adr/0005-long-gap-recursive-takeover.md) and the
[recursive adapter](../poc/takeover/README.md) replace the monolithic proof route
for an isolated experiment: the complete public account state is one SMT
resource, transaction journals feed reference batch verification and batch
receipts feed reference aggregation. This deliberately serial state model is not
a production scheduler or privacy design. The source-pinned local review checks
historical public inputs. A separate [fresh TN10 rehearsal](../poc/takeover/LIVE-REHEARSAL.md)
now confirms a deposit, clean public reconstruction after a 175-blue-score stop
gap, recursive settlement and native payout, with reserve matching the remaining
account balance. This used the same owner/node and retained public archive.
Native expiry is rejected inside the batch guest; unavailable public history
can halt recovery. No privileged withdrawal path is introduced.

## Feasibility checkpoint and private-protocol focus

The [five-criterion assessment](based-app-feasibility-2026-10-17.md) concludes the
public Based App integration milestone from PRs #31–#33. Ordering completeness
within a claimed interval, correct public execution and native settlement are
established for those experiments; privacy, mandatory progress and independent
recovery are not. The next [shielded-KAS work package](shielded-kas-next.md) must
specify confidential ownership/value, spentness, retained data and exact native
backing before implementation. A/B/C remain comparison candidates, not accepted
production designs. No new primitive or admin path is selected by this checkpoint.

## Protocol evolution and privacy-preserving migration

**Status: design requirement and open research, not a selected upgrade mechanism.** See [principle 25](../PRINCIPLES.md#25-privacy-preserving-protocol-evolution), [RFC-0001](rfc/0001-state-architecture.md#privacy-preserving-version-migration-research), and existing [issue #19](https://github.com/olafweller/kaspa-privacy-initiative/issues/19) on cryptographic/PQ migration.

Before defining the first production shielded pool, evaluate how future versions could be deployed without giving an administrator the power to rewrite existing verification rules or seize reserve assets. Favor independently verifiable version identities and voluntary user authorization; immutable parallel versions are a candidate, not an accepted decision.

A user should not be forced to make a transparent withdrawal and fresh deposit merely to adopt improved privacy rules. Investigate a proof-authorized, value-conserving shielded-to-shielded migration path with authenticated old/new pool identities, spentness across versions, exact reserve/exit accounting, and no privileged bypass. A direct mechanism may require additional covenant capabilities and does not automatically conceal timing, amounts, origin/destination links, fees, or network metadata.

A user who never upgrades must not be silently stranded by project policy or a discontinued website. Specify how valid legacy claims remain independently spendable or recoverable when executors, provers and maintainers disappear, which old verifier/programs and public histories must remain accessible, and what user-held notes/witnesses/backups are required. Unchangeable contracts alone cannot guarantee availability if data, consensus support, fee access, or cryptographic security are lost.

Any proposed migration mechanism must be tested for unauthorized movement, reserve conservation, double claims across versions, replay/downgrades, partially completed migration and unpaid exits. Compare privacy leakage under low activity and long dormant periods, and include old-version users in the multi-user recovery/shutdown test. Do not implement or approve a migration path solely on these requirements; select it only after a separate reviewed RFC/ADR and scoped test evidence.

## Proposed private-payment statement and local compatibility

[RFC-0002](rfc/0002-shielded-payment.md) proposes the hidden ownership/value,
current nullifier, delivery, deposit recovery and unpaid-exit interfaces. The
[local work package](../poc/shielded-design/README.md) exercises an ideal economic
model and real representative wallet -> transaction -> reference batch/aggregate
composition with local native script verification. It selects no production
note/encryption construction or funded deployment. Missing/wrong recursive
assumptions abort; a cryptographically enforced invalid-operation no-op remains
unimplemented. Intent must exclude proof bytes to avoid a circular native-ID
binding. PR34's shared economic single-consumption and voluntary migration/legacy
requirements remain open. [ADR-0006](adr/0006-shielded-design-local-work-package.md)
records the bounded local research decision only.

The [local classification follow-up](../poc/proof-classification/RESULTS.md),
under [ADR-0007](adr/0007-local-proof-classification.md), executes ordinary
receipt verification on canonical proof bytes and obtains valid-invalid-valid
outcomes. Its full run requires 870,829,938 user cycles and 880 proof segments;
no outer receipt was generated. The native-ID sequence is a fixed local fixture,
not an accepted TN10 endpoint. Affordable proved classification and real-lane
integration remain blockers; this result does not qualify the privacy circuit.

The [specialized Groth16 comparison](../poc/groth16-comparison/RESULTS.md), under
[ADR-0008](adr/0008-specialized-groth16-comparison.md), retains the same small
SHA-256/u64 statement and reduces complete proxy operations to 702 bytes.
Its ordinary in-guest verifier does not finish the agreed 32-million-cycle run,
so no outer receipt is produced. Circuit-specific setup and immutable prepared
parameter pins are explicit new assumptions. Compact wallet proofs are promising
for publication, but affordable proved classification and actual private/native
integration remain open.

The [accelerated BN254 qualification](../poc/accelerated-bn254/RESULTS.md), under
[ADR-0009](adr/0009-accelerated-bn254-qualification.md), reuses those exact proofs
and finishes the full correct sequence in a separately bounded calibration:
117,473,222 cycles, 121 segments. Actual pinned-VM/precompile compatibility is
demonstrated. This still fails the predeclared 32M practical cap; no outer proof
is attempted. A new classifier identity is pinned before execution. An explicit
larger practical-budget decision and full-sequence adversarial qualification
must precede any one-hour outer-proof attempt or private-note expansion.

The owner-approved [128M proof experiment](../poc/outer-proof-128m/RESULTS.md),
under [ADR-0010](adr/0010-approved-128m-outer-proof.md), completes all 24 full/narrow
adversarial execution cases with the same classifier image. Its one real
succinct-proof attempt is stopped at the one-hour whole-job limit without a
receipt, using four logical CPUs and 9.19 GiB peak sampled summed RSS. This closes
the missing replay/continuation execution checks, not the outer-receipt milestone.
Profiling actual proof production/compression remains necessary before expanding
to private notes; no new setup, accepted L1 endpoint or native funding is added.

The [bounded phase diagnostics](../poc/proof-phase-diagnostics/RESULTS.md) retain
two segment proofs, two lifts and an actual adjacent join, all independently
reverified. Segment proving dominates the measured costs; the original guest,
wallet relation and proving architecture are unchanged. These middle-segment
receipts are not a complete classifier proof. The next proposed qualification
is the official pinned CUDA proving path on the same retained assets.

## Local private-note experiment checkpoint — 2026-10-18

The [complete classifier receipt](../poc/remote-cuda/FULL-RESULTS.md) closes the
older test-model outer-proof blocker. [ADR-0011](adr/0011-local-private-note-wallet.md)
records a new experimental wallet circuit and local application kernel: hidden
SHA256 Merkle membership, rightful HMAC economic nullifiers, bounded conservation,
version/domain/verifier and output/delivery binding, independent recipient
validation, current spentness and deposit/exit liabilities. The first tree has
four slots and zero app fees, chosen only for the Alice/Bob research lifecycle.
This is not selection of a production commitment/encryption construction.

The new kernel's native inputs/payout confirmations are explicitly test fixtures;
its transitions are not yet proved in an outer guest. The next chain must bind
new transaction/batch/aggregate program identities to the existing native
Succinct verification ABI. A wallet receipt or the old 167-byte classifier
journal cannot substitute for that native aggregate statement. User witnesses
remain local; external executors/provers receive only public operations/state.


## Private-state integration calibration — 2026-10-18

[ADR-0012](adr/0012-private-note-state-integration.md) fixes a distinct unfunded
TN10 economic domain before a new wallet setup/image. The monolithic
[calibration guest](../poc/private-note-chain/README.md) binds a previous private
resource/config, actual v1 preimage IDs and computed native lane endpoints,
checks deposit value/script/owner references, verifies ordinary wallet proofs
and emits the existing 352-byte aggregate ABI plus permission commitments.
Reference per-transaction journals are decoded but no separate recursive
transaction/batch/aggregate proof is produced. Completed journals match the
independent native reference; the full three-proof execution hits 128M.

The new [binding map](../poc/private-note-chain/BINDINGS.md) distinguishes these
checks from canonical native acceptance, actual permission consumption/payout,
fee/rent handling and independent recovery. A permission commitment does not
confirm a payout or release reserve. No host fixture may bypass these gates.


The [separately approved 160M calibration](../poc/private-note-chain/calibration-160m/RESULTS.md)
completes that identical monolithic execution at 139,763,284 user cycles and 143
segments. Its exact 352-byte journal preserves the same program/VK identities;
only host/runner selection changed. It still starts after synthetic deposit
registration and contains no exit/payout. The
[next proof manifest](../poc/private-note-chain/calibration-160m/next-proof-target.json)
records exact program, state, lane and journal identities, explicitly distinguishing
relation-domain slots from absent recursive transaction/batch image identities.

The [fixed proof package](../poc/private-note-proof/README.md), recorded in
[ADR-0013](adr/0013-private-note-proof-package.md), now prepares that unchanged
claim for a genuine Succinct receipt. Its native variant explicitly pins
`join.zkr`; earlier assumption-composing fixtures retain `resolve.zkr`. Producer,
independent CPU verification and actual native fixture checks share independently
compiled image/control/journal expectations. Archived PR43 verification qualifies
only join/precompile compatibility. The new private receipt/native positive is
subsequently completed by the owner-reviewed and released
[single L40S run](../poc/private-note-proof/gpu-2026-10-18/RESULTS.md): a genuine
139,763,284-user-cycle Succinct receipt in 243.088 seconds, independent CPU
verification and local native positive/fifteen-negative checks. The correct
352-byte journal and 1,000,000,000-sompi fixture backing are enforced. Provider
stop and deletion were confirmed after external preservation. No runtime,
privacy relation or backing rule changed; canonical deposit lineage, Bob's exit
and actual native payout remain open.

## Local private/native lifecycle preparation — 2026-10-18

[ADR-0014](adr/0014-private-native-lifecycle.md) and the
[local package](../poc/private-native/README.md) connect zero-liability deposit
registration, real private credit/payment, Bob's independent exit proof and
native permission/delegate payout reconciliation. State-covenant rent 100M is
separate from the user delegate reserve 1,000M and sponsored permission rent 50M;
Bob's 400M exit remains an unpaid liability until the accepted native permission/
reserve spend and at least 450M recipient output (including 50M rent refund) justify
discharge. The remaining delegate principal/private liability is 600M.

The separate guest carries full state, reserve/permission outpoints and active
lane continuity beyond the old short fixture's 100-score cap. Four connected
batches and 17 additional cases ran in the zkVM; actual local native payout scripts
accepted/rejected their targeted variants. The sponsor builder supports the
private lane before signing. These are synthetic accepted-lane/UTXO fixtures,
not native chain acceptance. Genuine new lifecycle receipts, native permission
issuance and terminal TN10 confirmation remain future gates under the
[proposed rehearsal plan](../poc/private-native/TN10-PLAN.md). No new GPU rental,
funding, broadcast or general architecture selection follows from preparation.

The [PR49 review correction](../poc/private-native/REVIEW-FIX.md) enforces the
private lane in both the state covenant and issued permission, preserves these
restrictions in continuation, and pins a sufficient reserve per admitted exit.
Other registered deposits remain tracked. Partial consumption and additional
sponsor inputs/outputs are excluded by native rules; recipient top-ups are
accounted correctly. The builder checks the supplied restricted permission bytes against the actual
UTXO hash; live construction still must use the restricted state adapter.

The [fixed four-batch GPU package](../poc/private-native-proof/README.md) reuses
these reviewed identities without changing the guest or native relation. A single
externally watched process group covers all four proofs, compression and local
CPU/native checks. B independently re-verifies returned data using trusted local
executables. A new immutable image identifies this workload separately from PR47.
Software preparation does not establish new receipt or TN10 acceptance evidence.
