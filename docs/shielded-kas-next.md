# Next focus: shielded native KAS and financial privacy

## Current checkpoint — 2026-10-19

The [actual TN10 private/native lifecycle](../poc/tn10-live/README.md) completed
with four new actual-input outer receipts, independent B/Cloud CPU verification,
matching-process CUDA evidence and four accepted native settlements. Bob received
4 test-KAS principal plus 0.5 test-KAS rent refund; the remaining 6 test-KAS reserve
matches 6 test-KAS private liability with no unpaid exit. TN10 rejected the three
signed payout attacks and a distinct spent-input replay. The single bounded L40S
attempt stayed within its original limits; provider stop and Pod/storage deletion
were confirmed after external preservation. The estimated GPU/storage cost is
USD0.6654, pending the final provider invoice.

This closes the single-trial actual-chain integration gap. The existing operator
controlled logical Bob's wallet/recipient during this test. Independent user
custody, the N-user operator-shutdown/recovery gate, production privacy and scale
remain unproven; no production protocol is accepted by this result. The complete
[results and limitations](../poc/tn10-live/evidence/result.json) are retained for
review. No further rental or funded trial follows automatically.

## Historical checkpoints — 2026-10-18

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

PR44 is now merged with the equation-level intent-binding review controls.
The [private-state integration calibration](../poc/private-note-chain/RESULTS.md)
uses a new explicitly selected unfunded TN10 domain, real wallet VK and guest.
Twenty-one selected guest cases pass, including linked previous-state/current-NF
and native deposit-output controls; the full valid-invalid-valid sequence hits
128M before its third pairing completes. No budget is raised, receipt produced
or GPU rented. Separate-process Bob recovery/public-parameter reload now work
locally; native acceptance/payout and durable independent availability remain
open. See the [binding map](../poc/private-note-chain/BINDINGS.md) and
[CPU-before-GPU proposal](../poc/private-note-chain/GPU-PROPOSAL.md).

The owner-approved [single 160M follow-up](../poc/private-note-chain/calibration-160m/RESULTS.md)
now completes that same sequence at 139,763,284 cycles / 143 segments, exactly
matching its 352-byte reference journal. The 128M failure remains unchanged.
The [next precise task](../poc/private-note-chain/NEXT-PROOF.md) is one genuine
Succinct receipt plus independent CPU/native fixture verification after local
producer/package preparation and separate GPU release. This measured scenario
has no Bob exit, actual native deposit acceptance or payout.

That task is now completed by the separately owner-released
[single private-note GPU result](../poc/private-note-proof/gpu-2026-10-18/RESULTS.md):
243.088 seconds, exact genuine receipt, independent CPU verification and local
native positive/fifteen-negative checks. Provider stop/deletion followed verified
external preservation. The next substantive gap is actual native deposit lineage
and Bob's authorized exit/payout with complete reserve accounting, before a
separately released full TN10 rehearsal. No additional rental follows automatically.

The subsequent [local native/private lifecycle package](../poc/private-native/RESULTS.md)
now implements and execution-tests that accounting path with actual wallet
proofs, Bob's separate recovery/proof process and native payout scripts. Four
positive batches and seventeen additional positive/rejection/abort cases pass. Accepted native
events remain fixtures; no new outer receipt or TN10 transaction was made.
Review [ADR-0014](adr/0014-private-native-lifecycle.md) and the
[concrete transaction/proof plan](../poc/private-native/TN10-PLAN.md) before
releasing new proof packaging/rental or the terminal native rehearsal.

The [four-batch GPU rehearsal](../poc/private-native-proof/gpu-2026-10-18-02/README.md)
has now produced and independently verified the four new local lifecycle receipts,
including genuine exit-receipt native permission issuance and restricted payout.
All four proofs have CUDA evidence; the aggregate run took 379.676 seconds.
The source-pinned output-directory fix/regression and the earlier failed attempt
are retained. Independent B preservation/stop and external-copy verification
preceded confirmed Pod/storage deletion. The next substantive gate is the
canonical TN10 rehearsal, with actual deposit/permission lineage, native
transaction resource/fee acceptance and terminal payout confirmation. No live
funding, broadcast or additional rental is authorized by this result.

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

### TN10 lifecycle preparation after the local four-receipt milestone

PR51 completed the fixed local proof/native-script rehearsal. The next scoped
artifact is the [staged actual-chain adapter and run manifest](../poc/private-native-tn10/README.md).
Its [initializer decision](adr/0015-tn10-private-native-preparation.md) preserves
the reviewed guest while breaking the native genesis-ID/state-root circularity.
Review this new native code and the per-stage data/verification boundary first.
Actual funding/broadcasts, a separately qualified staged GPU service/image and
one bounded live rehearsal remain separate release gates. There is no new
GPU lease or TN10 funding in this preparation.

### Pre-release native preflight — 2026-10-19 (historical)

PR53 is merged. The [concrete TN10 preflight](../poc/tn10-preflight/README.md)
records installation/CPU verification on B, current synchronized native node,
verified inactive-lane capture, available test funding and read-only rental quote.
The owner confirmed trusted-operator custody of Bob for this test; one complete
live release remains pending. Independent user custody is not demonstrated. The staged image and
private/native relation are unchanged; no funding, broadcast, GPU rental or new
proof was performed. Next execution begins with fresh funding/activation and
chain checkpoints before the four actual-input receipts.

The subsequent explicit owner release and completed execution are recorded in
[the actual TN10 result](../poc/tn10-live/README.md), superseding the pending-release
status above without changing the historical preflight evidence.

### Local user recovery / last-user exit package — 2026-10-19

PR54's actual lifecycle evidence is preserved after merge. The next
[local package](../poc/user-recovery/README.md) prepares user-held backup/discovery,
public-history reconstruction and the missing exact-reserve native terminal
path. No new GPU rental, outer proof, funding or broadcast is included. The
host-only terminal policy still requires a new guest/issuance proof. Independent
user custody and the N-user service-shutdown gate remain open; local process
separation is not an independently administered user machine.

### Integrated recovery guest execution — 2026-10-19

PR55 is merged. The [separate new guest](../poc/recovery-native/README.md) supports
both payout forms in six continuous local batches, with new-root user tooling,
native regressions and a bounded CPU measurement. New outer receipts and genuine
proof-authorized permission issuance remain next; this does not change the old
funded instance. Prepare a six-job bounded proof package after review, retaining
the existing aggregate proof/lease limits. Rental/funding/broadcast and the
independent N-user shutdown test remain separately scoped work.

After the focused PR56 correction/review and merge, the next concrete artifact
is the [six-receipt software package](../poc/recovery-proof/README.md). It retains
the corrected inputs, exact journals and per-case segment limits. Its target is
six real independently verified receipts and both receipt-authorized local
permission/payout paths. Package/image preparation grants no rental, proof,
funding or broadcast release; a fresh canonical TN10 instance remains next.
