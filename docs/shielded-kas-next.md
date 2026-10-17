# Next focus: shielded native KAS and financial privacy

Owner-directed priority, 2026-10-17, after the scoped
[Based App feasibility milestone](based-app-feasibility-2026-10-17.md).
The next deliverable is a reviewable private-payment specification and executable
model, followed by a minimal TN10 privacy experiment. No production architecture
or proof system is selected here; [RFC-0001](rfc/0001-state-architecture.md) remains
Open. Native KAS is the sole backing asset; there is no new privacy token.

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
