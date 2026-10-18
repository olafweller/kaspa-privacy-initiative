# Next focus: shielded native KAS and financial privacy

## Current checkpoint — 2026-10-18

PR42 and PR43 are merged. The [complete classifier receipt](../poc/remote-cuda/FULL-RESULTS.md)
closes the outer-receipt blocker for the existing compact-wallet test model:
117,473,222 user cycles, one real succinct receipt, independent CPU verification
and actual wrong-image/journal/seal rejection. The complete GPU worker took
256 seconds; the provider stop was confirmed. Both GPU archives were subsequently
restored from B and verified again before the two stopped Pods/local volumes
were deleted. Evidence and source pins remain preserved.

The owner has resumed the local private-payment work. Concrete experimental
choices are recorded in [ADR-0011](adr/0011-local-private-note-wallet.md): hidden
note membership/authority/conservation, economic nullifiers across batches,
recipient validation and an atomic application kernel. The small new wallet
circuit is separate from the completed PR43 classifier. The
[local result](../poc/private-note-wallet/RESULTS.md) contains five real wallet
proofs, nine passing tests and separate pinned-key verification; full outer/native
integration remains a subsequent gate. No new GPU rental, native funding or
TN10 transaction is part of this local implementation.

Owner-directed priority, 2026-10-17, after the scoped
[Based App feasibility milestone](based-app-feasibility-2026-10-17.md).
The next deliverable is a reviewable private-payment specification and executable
model, followed by a minimal TN10 privacy experiment. No production architecture
or proof system is selected here; [RFC-0001](rfc/0001-state-architecture.md) remains
Open. Native KAS is the sole backing asset; there is no new privacy token.

## Historical local work-package checkpoints, 2026-10-17

The following sequence is preserved as dated research. Pending outer-receipt
statements below are superseded by the completed GPU result above.

The first [local package](../poc/shielded-design/README.md) now supplies
[RFC-0002](rfc/0002-shielded-payment.md), a visibility contract, executable model,
adversarial tests, source/reuse review and real bounded wallet-to-batch proof
composition. No funded privacy trial was run. The current recursive syscall does
not prove an invalid-operation no-op; that classifier, complete private relation,
noncircular proof-carrying payload and authenticated deposit recovery require
review before the [conditional TN10 proposal](../poc/shielded-design/TN10-PROPOSAL.md).
The model/proxy proof do not establish financial privacy or close the issues below.

The [classification follow-up](../poc/proof-classification/RESULTS.md) executes
the correct valid-invalid-valid sequence using ordinary verification of real
wallet proof bytes. It costs 870,829,938 user cycles / 880 segments; no outer
classification proof was produced. A complete proxy native operation already
uses 89.7% of the pinned block transient capacity. Compare the previously named
specialized proof route before building the full private relation around this
path. Keep real accepted-lane integration, private economics and funding gated.

The [Groth16 follow-up](../poc/groth16-comparison/RESULTS.md) produces actual
specialized 128-byte wallet proofs with the same small predicate, but the outer
classifier exceeds its 32-million-cycle budget. Next resolve the maintained
BN254 backend/budget question and produce one complete outer receipt before
expanding to the private note circuit. No new funded TN10 experiment is ready.

The [bounded accelerated backend](../poc/accelerated-bn254/RESULTS.md) now completes
the real-proof sequence at 117.47M cycles (121 segments) in its separate calibration.
It is compatible with the existing pinned VM but does not meet the 32M practical
cap; no outer proof ran. The next concrete budget decision is a declared 128M
practical experiment, retaining full adversarial controls and the one-hour proof
limit, before connecting private notes or actual native settlement.

The [approved 128M proof attempt](../poc/outer-proof-128m/RESULTS.md) completes all
24 required execution cases, then reaches the one-hour proof-job stop without a
receipt. No budget is automatically increased. Next profile actual segment
proving/recursive compression and memory behavior; the compact wallet candidate
and execution qualification remain useful, while the real outer-receipt gate
and the full private-note/native-integration gates remain open.

## First work package: define the private payment statement

Work through existing issues rather than inventing a second backlog:

| Priority | Existing issues | Concrete deliverable and completion condition |
| --- | --- | --- |
| 1: privacy and spendable notes | [P04/#4](https://github.com/olafweller/kaspa-privacy-initiative/issues/4), [P13/#13](https://github.com/olafweller/kaspa-privacy-initiative/issues/13) | Specify which values/owners/links are hidden from chain observers, executors, provers and RPC providers. Compare established note/ownership/encryption designs, recipient spendability and delivery requirements. Include an explicit public/private data table and linkability risks at entry/exit. |
| 2: conservation and spentness | [P05/#5](https://github.com/olafweller/kaspa-privacy-initiative/issues/5), [P06/#6](https://github.com/olafweller/kaspa-privacy-initiative/issues/6) | State exact integer-sompi ranges, deposits, hidden transfers, nullifiers, pending exits, completed payouts, rent and fees. Bind proof version/domain, accepted note anchors, current spentness and actual native reserve/payout. Executable adversarial vectors must reject inflation, overflow, wrong ownership, duplicate spends within/across batches and replay across domains. |
| 3: native entry and exits | [P07/#7](https://github.com/olafweller/kaspa-privacy-initiative/issues/7), [P08/#8](https://github.com/olafweller/kaspa-privacy-initiative/issues/8), [#23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23) | Map a native deposit to one private claim and an authorized spent claim to an exactly bound native payout. Keep unpaid liabilities counted. Specify user-accessible fee handling and exit data; no operator withdrawal signature or privileged rescue path. |
| 4: witness privacy, delivery and retained data | [P10/#10](https://github.com/olafweller/kaspa-privacy-initiative/issues/10), [P11/#11](https://github.com/olafweller/kaspa-privacy-initiative/issues/11), [P12/#12](https://github.com/olafweller/kaspa-privacy-initiative/issues/12), [P09/#9](https://github.com/olafweller/kaspa-privacy-initiative/issues/9) | Define how private proofs are generated without exposing another user's secrets to an executor or hosted prover. Inventory commitments, spentness, ciphertexts, accepted updates, witnesses and user backups. Specify complete discovery and safe handling of missing/corrupt data; identify a falsifiable later independent recovery test. |

These are coupled requirements, not four isolated implementations. Public-account
balances cannot be made into a private payment protocol merely by encrypting a
JSON file or putting their existing execution inside a ZK VM. Public payloads,
resource identifiers, fee inputs, timing and note retrieval can still reveal the
payment graph. A service that receives plaintext witnesses is within the privacy
threat model even if the resulting on-chain proof reveals less.

## Reuse and comparison before implementation

The [Phase 1 comparison](../research/phase1-source-review-2026-10-08.md) and its
[Orchard](../research/zcash-orchard.md), [Aztec](../research/aztec.md),
[RAILGUN](../research/railgun.md), [Monero](../research/monero.md) and
[MWEB](../research/litecoin-mweb.md) notes are the starting point. Refresh exact
upstream state and the [existing Kaspa privacy inventory](../research/existing-kaspa-privacy.md)
before selecting constructions; the prior source reviews are dated evidence.
Record reused components, required adaptations, rejected alternatives, license
constraints and assumptions. Do not invent new cryptographic primitives.

Use the tested Based App ordering, recursive proof and native bridge path as a
candidate backend. Keep Candidate A as a comparison for cost, native bindings
and witness/recovery needs. A single logical privacy domain is the initial
comparison workload; add sharding, a full runtime or operator network only when
measurements or an explicit requirement justify it. A note/nullifier or settlement
design decision requires RFC review and an ADR before substantial cryptographic
implementation, with [all invariants](../SECURITY-INVARIANTS.md) preserved.

## Next experiment's falsifiable target

After reviewing that statement/model, the minimal experiment should demonstrate:

```text
native test-KAS deposit
-> recipient-spendable private claim
-> private value-conserving transfer to another user
-> deterministic duplicate-spend rejection
-> authorized exit claim with backing preserved
-> confirmed native test-KAS payout
```

It must use real proofs with pinned identities and disabled development mode.
Report the exact number of users/notes, public observations, hidden witnesses,
proof time/memory/fees and every unpaid liability. Include unauthorized spend,
wrong-root, overflow/inflation, same-note duplicate, cross-domain replay,
recipient substitution, malformed proof and underpaid/diverted payout controls.
Neither encrypted transport nor a hidden amount alone establishes payment
unlinkability; report residual timing/amount/network/service correlations.

This work package does not require building an independent operator network now.
It does require specifying the data and user secrets needed to replace services.
The [N-user shutdown and exit gate](ROADMAP.md#early-exit-and-recovery-gate) stays
mandatory before treating an architecture as credible. Same-node replay does
not satisfy it, and private transfers do not excuse an unavailable exit.

## What counts as progress now

The immediate artifact is the reviewed statement, threat/data table, reuse map
and adversarial model linked to P04/P05/P06/P07/P08/P10/P12/P13. Only then build
the smallest testnet private lifecycle that can falsify those requirements.
Further public-account runtime expansion is secondary to a demonstrated private
protocol requirement. Existing issues remain open until their own acceptance
criteria are met; completing the Based App milestone closes none by implication.
