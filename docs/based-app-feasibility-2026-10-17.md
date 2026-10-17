# Based App feasibility conclusion — 2026-10-17

**Conclusion: the scoped public-account Based App PoC works on Kaspa TN10.**
Real accepted lane activity was reconstructed, executed, cryptographically proved
and settled. The node accepted the correct result and rejected an omitted-input
result claiming the same endpoint. Native deposit and payout were confirmed.
This completes this investigation's five acceptance criteria. It does not select
a production architecture or establish shielded KAS, independent recovery,
general data availability, guaranteed progress or production security.

This is a review of the published experiments in PRs
[#31](https://github.com/olafweller/kaspa-privacy-initiative/pull/31),
[#32](https://github.com/olafweller/kaspa-privacy-initiative/pull/32) and
[#33](https://github.com/olafweller/kaspa-privacy-initiative/pull/33).
Kaspa supplies ordering and the settlement verification boundary; application
execution/proving runs outside L1. “End-to-end” does not mean running the whole
application inside Kaspa consensus.

## Acceptance criteria and evidence

| Criterion | Explicit acceptance condition | Observed evidence | Outcome and scope |
| --- | --- | --- | --- |
| BA-1: real L1 ordering | Actual signed lane transactions are accepted on TN10; reconstruct IDs, merge positions, contexts and lane commitments from accepted-chain data rather than submission order. | PR31: three real lane operations in 33 selected-chain blocks; native and Python reconstruction. PR32: deposit, unauthorized request, withdrawal and copied request. PR33: fresh deposit and withdrawal, each bound to its recorded accepted interval. | Satisfied for the recorded intervals. Same-block order mutation is exercised by a separate native capture, not claimed for a KPI interval lacking a same-block pair. |
| BA-2: correct execution | Apply every accepted lane input in canonical order, including deterministic app rejections; bind old state, new state, owner authorization, principal and claims. | PR32 commits unauthorized/replayed app commands as no-ops. Its 10/4/6 principal accounting is independently audited. PR33 reuses that relation as one serial SMT resource, checks recursive continuity, and reconstructs the checkpoint from empty public state. | Satisfied for this public Deposit/Withdraw app. Not a general scheduler, private transfer or complete vProgs runtime. |
| BA-3: cryptographic proof | Generate real receipts with development mode disabled; verify actual program identities, committed journals and recursively resolved assumptions. | PR31/32 use real monolithic receipts. PR33 produces nine real receipts on retained historical inputs, then eight fresh receipts for the live rehearsal. All eight live receipts were SDK-reverified during final review; changed journals and wrong program identities were rejected. | Satisfied with pinned RISC Zero/program/control identities. An execution profile, host assertion or receipt callback alone does not count. |
| BA-4: accepted settlement | Broadcast the correct settlement; observe selected-chain acceptance and actual successor state UTXO. Confirm native payout separately. | PR31 confirms continuation. PR32 and PR33 confirm both settlements and actual payouts. PR33 final settlement `38262de73d7e86022f0be8c308e5fc6d37e98c87c6bb92b668ca18ca1cc28408`; payout `d0d4122e3b1166878aa47f4077ceff955f5a0c444272862425cb0490ca1f5910`. | Satisfied as a recorded observation by one validating node, beyond mempool admission or local script acceptance. |
| BA-5: incomplete processing rejected | Omit an actual accepted operation, retain the same real endpoint and old state/tip, generate the partial computation proof and submit it. Require an actual native verification rejection. | PR32 and PR33 each do this. PR33 omission transaction `2445cc12ae32b241e9ace2471667c0846e0715f0c3cbc17b0332e70537f385bf` is rejected with `ZK Integrity: Verification failed`; the valid final settlement is accepted. The final-review audit confirms identical endpoint and prior covenant input for both variants. | Satisfied for omission within the claimed interval. A shorter honest prefix remains permitted; this does not force the latest endpoint or bound censorship time. |

The number of operations is not used as a proof shortcut. An earlier planning
note proposed ten toy operations; PR31 instead records three ordinary signed
lane inputs, including app no-ops, and PR32/33 add meaningful deposit/withdrawal
execution. The current five acceptance criteria concern the authenticated
input/execution/settlement chain, not reproducing that historical ten-operation
workload or establishing throughput. No ten-operation or benchmark completion
claim is made.

## Actual asset path and stop/reconstruction boundary

In PR33, a fresh user deposited 1,000,000,000 sompi (10 test-KAS), which was
credited through recursive settlement. A clean Cloud directory reconstructed
that checkpoint from retained public input without importing the original
account-state file. A new authorized withdrawal followed **175 blue scores after
the node tip observed at stopping**, or 212 from the stable stop anchor. The
native lane remained active; actual expiry/reset was not tested.

A confirmed payout consumed the real deposit reserve and permission. The user
received 400,000,000 sompi principal plus 50,000,000 sponsored permission-rent
refund. The remaining native reserve and account balance both equal 600,000,000;
no unpaid permission claims remain. State rent is separate. All nine accepted
transactions and their 193,850,800 sompi in fees reconcile. The first read-only
accounting script's response-shape failure and its successful correction remain
in the evidence. No financial stage was rebroadcast for that correction.

This establishes clean public replay on the same owner/node infrastructure,
using retained history. It does not establish independent restoration after all
operators/archives disappear, pruning recovery or recovery without user keys.
The normal Kaspa node was not stopped. Earlier funded instances were untouched.

## Review and reproducibility

The [PR33 final review](../poc/takeover/FINAL-REVIEW.md) records the inspected
source and enforcing layers. The [machine-readable review](../poc/takeover/evidence/final-review.json)
retains the additional verification results and tool hashes. No blocking defect
was found for this isolated public-account experiment. This is an AI-assisted
second pass over AI-assisted work, not independent human security review.

Additional verification performed for this conclusion:

- Independently reconstruct the real PR31 capture's three ordered lane IDs.
- Re-run PR32's public accounting/journal audit over all 120 original files.
- Verify PR33's outer archive inventory and all 89 public VPS files; reconstruct
  lane IDs, merge positions, block contexts and fixed commitments with the Python
  implementation; bind public state roots, journals and clean reconstruction.
- Recalculate actual input/output fees and backing, match accepted transactions
  and accepting headers to the recorded final read-only RPC checks, and check the
  same-endpoint omission evidence. Native compressed and expanded parent-level
  encodings are normalized before comparing complete headers.
- SDK-reverify all eight live receipts against archived program bytes, require
  succinct receipts and matching journals, reject changed journals and wrong
  programs, and re-run the seven Rust adapter tests.

The new review utilities only read public artifacts. They create no proof,
funding, transaction or current-chain observation and do not change any guest or
funded verifier. SDK re-verification reuses the pinned cryptographic verifier;
the Python lane/accounting implementation is separate from the Rust executor,
not an independent node or human operator.

No additional TN10 broadcast was needed: each acceptance criterion already has
a real positive path and its required recorded enforcing-layer evidence.
Reorg recovery, true expiry and independent takeover are separate unproven
properties, not gaps silently treated as passed. A future test targeting one of
those properties needs an explicit falsifiable criterion and a fresh identity.

## Remaining limitations

- **Privacy:** balances, owners, amounts, operations and recipients are public.
  A ZK execution proof does not by itself make this application private.
- **Data/recovery:** roots authenticate but cannot recreate missing bodies,
  witnesses or ciphertexts. Same-node retained replay is narrower than I-10.
- **Progress:** interval completeness does not guarantee fresh endpoint choice,
  processing of every future operation, censorship resistance or timely exit.
- **Expiry/reorgs:** lane expiry is explicitly unsupported. Reorg detection
  halts these runners; general rollback/recovery was not demonstrated.
- **Scale/cost:** one coarse public resource deliberately serializes state.
  Eight tiny live receipts took 18.24 minutes combined at about 4.60 GiB peak
  individual-process RSS. This is feasibility evidence, not payment throughput
  or a usable wallet latency measurement.
- **Trust/maturity:** one owner-operated validating node, experimental upstream
  code, pinned proof-system/toolchain assumptions and no independent security
  audit. Source/build provenance does not prove cryptographic correctness.
- **Architecture:** native-KAS backing works for these public instances; a
  scalable shielded reserve, private ownership/spentness, fee access and the
  common N-user shutdown/exit gate remain unresolved. RFC-0001 stays Open.

## Development focus from this checkpoint

The narrow Based App sequencing/execution/settlement feasibility milestone is
complete. The development focus now moves to **shielded native KAS and financial
privacy**, with existing Based App components available as a tested candidate
backend. This is not automatic acceptance of Candidate C or an instruction to
build an operator network before specifying the private protocol.

The [shielded-KAS work plan](shielded-kas-next.md) starts with a reviewable private
payment statement, note/nullifier/delivery and data requirements, then a minimal
private-value lifecycle experiment. Its privacy, conservation, exit and recovery
requirements remain simultaneous constraints. General runtime/network expansion
is driven by a demonstrated requirement, not by this milestone alone.

## Community summary

KPI has demonstrated a public-account Based App proof of concept on Kaspa TN10:
real lane transactions were reconstructed and executed, real cryptographic proofs
settled, and the node rejected processing that omitted an accepted operation
while claiming the same endpoint. Native test-KAS deposits and withdrawals also
completed, including clean public-state reconstruction after an idle gap. This
answers the scoped sequencing-to-settlement feasibility question. It does not
establish a working privacy protocol or production readiness. KPI's next focus
is shielded native KAS: confidential payments with correct backing, spend
protection, usable exits and an explicit recovery model.
