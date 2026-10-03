# A1 threat and test matrix

**Status:** Proposed design; every A1 test below is **planned, not executed**.
[ADR-0003](adr/0003-a1-successor-reserve.md) defines the finite S0/S1 graph,
encoding and accounting. The [implementation plan](poc-a1-implementation-plan.md)
assigns execution gates. No invariant is changed.

Use all three valid real-proof branches as positive controls. For negative
variants, recompute transaction IDs/mass as needed so an unrelated malformed
transaction does not masquerade as proof/covenant rejection. Record the rejecting
layer and error. Fixed monetary terms are checked before setup and enforced by
actual output checks; this is not a variable private-accounting circuit.

Context-binding tests must distinguish circuit constraints from key mismatch.
Keep the original circuit/constants, secret and outpoint fixed. Independently
encode each one-field-mutated context and calculate its reference tag `T`; the
original constraint system must reject that tag, while the original-context
positive control succeeds. Exercise the same public tag through the original
proof/key path as applicable, recording whether constraint generation or actual
verification rejects it. Do not claim a proof was produced if proving refuses
an unsatisfied witness. Independent native/circuit golden vectors must agree
on the complete original encoding.

Separately attempt foreign-context proofs against the original pinned VK and
funded script, and test script/key substitution. Rejection across randomized
setups can occur solely because their keys differ; it does not establish that
every intended context field participates in the relation. Failing only a P2SH
mismatch also does not establish circuit context binding.

## Planned attacks and oracles

| ID / invariants | Attack or failure | Required assertion / test oracle |
| --- | --- | --- |
| A1-01 / I-1, I-2, I-7 | Underback successor; reduce liability without payout; omit recipient output | Positive partial settlement records exact old/new R,L,B,E,W,fc. Check R=E and E0=E1+W+fc. Mutate each amount independently; proof or covenant rejects. Actual accepted outputs must satisfy every equality. Entitlement E decreases only by accepted payout plus the exact owner-authorized fee; submission alone changes nothing. |
| A1-02 / I-1, I-2, I-15 | u64 overflow/underflow, field wrap, negative/script integer ambiguity, amount beyond native maximum | Boundary corpus 0,1, native MAX_SOMPI, MAX+1, u64::MAX; L+B and R1+W+fc carry cases; W=0, W=L0, W>L0; f>B; B1<0. Reject values not allowed by selected branch. Constructor/manifest checks use bounded wide intermediates and exact equality before setup; public circuit limbs remain range-constrained. The fixed-term authorization circuit must not be described as proving variable monetary arithmetic. |
| A1-03 / I-1, I-2, I-12 | Fees charged from principal; treasury subsidy mislabeled as backing; surplus silently confiscated | Mutate f while holding successor and payout fixed; no reduction of principal L except W; refundable B remains in total entitlement E until paid as rebate or authorized fee. Document designated B provider and consent. Terminal payout is exact L+(B-f); mutate the rebate separately to reject omitted or redirected surplus. Treasury keys absent from reserve control; no sponsor input branch. |
| A1-04 / I-3, I-5, I-7 | Wrong/absent secret, public commitment used as authority, proof copied and redirected | Wrong witness with recomputed authorization tag fails; public C alone insufficient. Copying a valid proof cannot alter recipient, amount, old/new state or mode. Correct secret plus wrong commitment/state fails. |
| A1-05 / I-5, I-13, I-15 | Chosen VK/program, invalid identity proof, trailing proof/key bytes, malformed Fr, wrong arity | Pin exact redeem scripts and branch VKs. Reject all substitutions and malformed encodings through real verifier. Unknown protocol/VK/branch identifiers fail closed; no maintainer override or dev verifier. |
| A1-06 / I-6, I-11, I-13, I-15 | Successor script/VK substitution; branch confusion; circular setup dependency | Construct S1 first and S0 second without knowledge of their future outpoints; validate both immediate exit and continuation with real proofs. Mutate actual successor SPK/version/value and reject. Apply original-circuit reference-tag negatives to fixed successor/context fields; separately test VK substitution and foreign-key proofs. Wrong branch selector, absent/extra branch arguments, cross-branch proof and unknown selector reject. No witness-selected key/script; measure stack/element/script/compute use. |
| A1-07 / I-6, I-7 | Proof claims a safe successor while transaction creates different output, missing continuation, duplicate successor or covenant metadata | Fix continue output indices/count and terminal output count. Mutate output SPK/version/value/covenant metadata independently. Extra inputs, extra outputs, swaps, missing outputs and duplicated successor reject after recomputed mass. KIP-20 lineage alone never counts as continuation validation. |
| A1-08 / I-4, I-6 | Competing continue-vs-continue or continue-vs-terminal spend, proof replay against replacement outpoint | Both legitimate competitors must first pass standalone validation against the same supplied original UTXO. In actual stateful consensus at most one consumes it; loser cannot create second successor/payout. Exact replay may return already accepted; distinct-ID replay must remain proof-valid locally before actual missing-input rejection. Test different txid and index separately. |
| A1-09 / I-4, I-6, I-11 | Stale S0 proof at S1; cross-instance/domain/state proof; stage reset or S1->S2 | Mutate instance, network/version, old state/stage and mode in independent reference tags while retaining original circuit constants; require unsatisfied constraints with positive controls. Separately test foreign-setup replay, actual outpoint txid/index mutation and S0 proof at S1. S1 only terminal. Copied identical chain state is explicitly outside genesis-label replay claims. |
| A1-10 / I-6, I-9, I-11 | Rollback after partial settlement; UI treats submitted/proved as settled; accepting body differs from candidate | Deterministic branch/reorg fixture rolls back accepted UTXO/state pointer and credits together. Never debit or credit twice; return to the actual selected-chain unspent state, revalidate outpoint and regenerate proof when needed. Reorg test is distinct from a TN10 confirmation wait. Unknown/mismatched readback halts; saved ID supports reconciliation. |
| A1-11 / I-8, I-9, I-10 | Default operator/prover disappears, or material retained only on original host | Shut down original process and remove access to original storage/RPC. On a clean machine use declared independently retained public artifacts + user secret/backups + independent software/infrastructure to discover current accepted UTXO, recreate proof and exit both S0 and S1 in separate cases. Also interrupt immediately after continuation acceptance but before the original host archives S1 or updates its pointer: recovery from the retained S0 locator must discover accepted S1 independently and freshly exit. No pre-generated exit proof or original operator help. Report elapsed time and exact payout. |
| A1-12 / I-10, I-11, I-15 | Pruned history, missing/poisoned PK or redeem/state file, wrong backup, stale locator | Inventory bytes needed for discovery, validation, proof, and receipt; hash/authenticate each public artifact against funded script/accepted state. Delete or corrupt each required item individually. Correct independent replica restores operation; absence fails explicitly, never creates a substitute state or new setup. Chain root/UTXO hash alone cannot recreate PK or secret. Distinguish independently retained data from chain-reconstructable data. |
| A1-13 / I-8, I-9, I-10 | Rising fees or resource costs strand successor; auto-resize takes principal | Before funding measure all three branches, committed finite budgets and current-policy fee needs; require the fixed f0, fc and f1 to fit the initial B0 and measured relay policy. Force unsupported/too-high fee conditions and insufficient budget: halt with no altered payout, bypass, extra input or secret upload. Record this bounded liveness assumption; do not claim guaranteed exit under arbitrary future fees. |
| A1-14 / I-3, I-14 | Payout key not owned; authorization secret or recovery key absent; unintended recipient handoff | User independently proves possession of the fixed recipient wallet and claim secret before funding; verify recovered keys produce fixed recipient/commitment. Continuation cannot rotate C/recipient in A1. No private note is created, so full note recipient spendability remains untested/deferred rather than claimed satisfied. |
| A1-15 / I-5, I-8, I-13 | Malicious setup or hidden upgrade/administrator; lost key leads to bypass | Public VK/PK/redeem manifest pinned before funding; known single-party setup/toxic-waste trust remains explicit. No recovery/upgrade key can replace proof or redirect funds. Recovery never includes toxic-waste randomness. PQ unresolved under issue #19, not a claim addressed by A1. |
| A1-16 / I-9, I-11, I-15 | SDK cached ID, missing v1 compute budget, integer loss, misleading/malicious RPC | Native serialization roundtrip preserves all authenticated fields, BigInt boundaries, covenant=null semantics, computed ID/storage mass and fees; full validator runs on final decoded transaction. Divergent RPC observations fail closed. Endpoint URL count is not proof of independent trust or locally validated UTXO consensus. |
| A1-17 / I-16 | Public values/linkage/network metadata marketed as privacy | Evidence explicitly enumerates public amount, claimant linkage, fixed destination, instance/stage, proof and timing. Document witness stays local; hosted prover would learn it. No anonymity, confidential accounting, sender/receiver unlinkability or post-quantum claim. I-4's private-resource non-revelation goal is not demonstrated by this public one-claim UTXO fixture. |

## Invariant coverage and limits

| Invariant | Principal rows / scope |
| --- | --- |
| I-1 backing | 01–03; total entitlement E includes refundable B |
| I-2 conservation | 01–03; fixed public single-claim accounting only |
| I-3 authorization | 04, 14; same owner across both states |
| I-4 single spend | 08–09; native UTXO uniqueness; private-resource unlinkability not demonstrated |
| I-5 soundness | 04–05, 15; tests do not prove cryptographic soundness |
| I-6 correct state | 06–10; exact script/branch/outpoint binding |
| I-7 withdrawal | 01, 04, 07; exact actual payouts and successor |
| I-8 no confiscation | 11, 13, 15; no privileged escape; fixed fees can still limit liveness |
| I-9 safety first | 10–13, 16; unavailable/corrupt inputs halt |
| I-10 recovery | 11–13; one-owner experiment, not N-user gate |
| I-11 reproduction | 06, 09–12, 16; independently derived state and artifact checks |
| I-12 isolation | 03; owner funds principal and fee credit, no treasury control |
| I-13 upgrades | 05–06, 15; no upgrade path |
| I-14 spendability | 14; native recipient control tested; no new private note exists |
| I-15 deterministic rejection | 02, 05–06, 12, 16; canonical bytes and malformed cases |
| I-16 scoped privacy | 17; public/linkable lifecycle, no anonymity claim |

## Recovery inventory and measurable pass criteria

Private backups: claim secret, recipient spending key/seed, and any backup
unlocking key. Public artifacts: all three full proving keys/VKs, exact S0/S1
redeem scripts/SPKs, contexts and manifest, pinned source/toolchain/SDK,
initial funding locator, accepted transition history/current outpoint, and
reconstruction/build instructions. List byte counts and hashes. Authenticate
these against actual funded scripts and accepted bodies, not self-reported hashes
alone. Toxic waste must never be a recovery dependency.

Before the experiment, declare a clean second machine, independently retained
artifacts and independent chain infrastructure. After build/sync prerequisites,
allow at most 30 minutes from disabling original services/access to a freshly
proved and fully locally validated terminal transaction for each state. Report
build/sync duration separately; timeout is a failed gate, not a silent extension.
A later authorized live test must additionally observe exact accepted payout
within a predeclared 10-minute submission window and recheck at least 120 seconds
later under the selected confirmation policy. These are experiment thresholds,
not expected timings, throughput guarantees or finality claims.

At G5, run separate synthetic/native-consensus fixtures for direct S0 exit and
continued S1 exit. Separately funded TN10 instances belong only to authorized G6.
The abrupt-loss case must succeed using the old S0 locator and independently
available accepted-chain body/history, without a final export from the original
host. Locate the accepted spending transaction, check its complete continuation
outputs against the pinned S0/S1 manifest, and verify the resulting S1 outpoint
is current and unspent. A matching address alone is insufficient. If pruning
removes that history and no independent replica exists, record failed recovery;
do not silently add original-host access or claim that a safe halt passes I-10.
No saved
exit proof, original host filesystem, original prover/RPC service or freshly
regenerated setup may be used. Delete/corrupt each required artifact in negative
recovery fixtures and record explicit failure or restoration from an independent
replica. Report every required item as recovered, replicated or missing: 99%
recovery with one missing exit dependency fails.

Deterministic reorg and competing-spend tests need an actual stateful native
consensus integration harness; a model alone or two stateless Full validations
cannot establish those properties. Live observation is a separate gate, and
bounded confirmation waits cannot substitute for a controlled rollback test.

## Stop criteria

Any unexplained acceptance of a forbidden transition, unbacked entitlement,
redirected/missing payout, arbitrary successor or second accepted spend blocks
progress. Missing recovery material, unaffordable fixed fee, failed branch
resource limit, ambiguous chain state or inability to exit either reachable
state blocks funding or further progression. Fix the design and repeat affected
gates; do not relax the verifier, output constraints or invariant scope.
