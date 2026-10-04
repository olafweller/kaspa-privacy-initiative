# A1 threat and test matrix

**Status:** G0 merged; unfunded A1 execution results are recorded in the
[implementation report](poc-a1-proof-report.md) and evidence ledger below.
The ADR's independently calculated G0 context vectors remain separate from
actual G2 real-proof/native-script tests. Full G5 independent machine/archive
recovery is pending; G6 is unauthorized/unexecuted. No funding or broadcast.
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

## Frozen attacks and oracles

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
| A1-18 / I-5, I-6, I-7, I-15 | OP_IF truthiness bypass, numeric-equivalent/negative-zero selector, raw mode confused with selector | S0 accepts only raw `00` continue and `01` terminal; S1 only `01`. Use ADR's exact OP_EQUAL dispatch. Exhaust all 256 one-byte selectors and the multi-byte corpus; each successful trace must execute matching count/order/value/SPK/metadata checks and exactly one matching immutable VK/tag20 verifier. Empty, `80`, `02`, `81`, `ff`, `0000`, `0100`, `0080`, `0180`, `0001` reject. Same raw bytes via equivalent push opcodes pass subject to native resource bounds. No signature-script minimal-push policy may be misreported as consensus safety. |
| A1-19 / I-5, I-11, I-15 | Witness ambiguity, hidden alt-stack values, supplied count/VK/outpoint, wrong public limb order | Exactly five pushed elements: high tag32, low tag32, proof128, selector1, exact redeem. Depth=4 at redeem entry; alt empty. Derive txid/index on script; verifier order low txid/high txid/index/low tag/high tag. Remove each item, insert extra at every slot, swap every pair, try scalar sizes 0/16/31/33/64, >=Fr modulus and nonzero upper bits, proof 127/129/trailing bytes. Reject at recorded layer with unequal-limb positive controls. Inspect alternate stack before VM boundary clearing; no leftover items. Store three literal real-proof golden transactions at G2; encoding-only OP_TRUE scaffold must never count as a positive script. |
| A1-20 / I-5, I-7, I-13, I-15 | Unknown-version SPK bypass; wrong verifier/key accepted through adapter-only restriction | Funding reserve, exact S1 and recipient all version 0. Input unknown-version native acceptance is a diagnostic of upstream semantics, not a valid A1 success. Change successor/payout version and reject via full SPK equality; substitution of funded SPK/redeem must fail artifact/funding inspection/P2SH. Check embedded VK_0c/VK_0t/VK_1t with six gamma_abc terms, 424 bytes; tag raw20, five scalars, proof128. No alternate tag/VK witness. |
| A1-21 / I-2, I-5, I-6, I-11, I-13 | Self-consistent malicious manifest/compiler/setup, wrong R/L/B/recipient/state/branch, hashes mistaken for relation provenance | Second reviewer independently reconstructs terms/contexts, compares normalized R1CS from reviewed exact source, inspects constant-byte/range/public allocation and both SHA relations, disassembles/reconstructs scripts and acyclic dependency graph. Mutate each field/branch/key and regenerate hashes/proof under malicious artifacts: independent owner-intent/checker must reject. Final setup needs witnessed exact R1CS -> PK/VK hash receipt; unwitnessed opaque keys fail qualification. Proof success/PK-VK equality/hash alone cannot certify setup relation. Single-party toxic-waste assumption remains. |
| A1-22 / I-6, I-10, I-11 | S1 address match mistaken for legitimate successor; incomplete history, wrong accepting block, txid mistaken for whole-body checksum | From independently retained S0 locator/checkpoint scan accepted mergeset bodies with native v2 Full or v1 ID/body join. Exact accepted input spends S0; outputs/count/order/values/SPKs/None/fee/branch verified; derive S1 txid/index0 and current UTXO. Unrelated S1-address deposit is not lineage. Check full body hash/signature/budget/storage separately because txid excludes signature/mass commitments. Distinguish terminal spendability A from accepted lineage/accounting B; missing B history fails B even if A can still exit. |
| A1-23 / I-6, I-9, I-10, I-11 | Pagination gaps/duplicates, pruning, reorg at page/horizon boundary; original host lost before pointer save | Test >one server page, inclusive-v1 lowHash, missing acceptance/body, repeated/no-progress cursor, removed hashes at/before horizon, stale S0/S1 UTXOs, conflicting provider assertions. Only advance after complete groups; undo removed acceptance/accounting before added groups; independently retained archive restores missing history. Abrupt loss uses only old S0 locator and independent C archive; no final export, saved S1 pointer or original node/filesystem. Loss of required history without a replica fails recovery, not a silent address fallback. |
| A1-24 / I-1, I-2, I-8, I-9, I-10 | Wrong relay floor, fixed fees lack headroom, setup terms changed after funding | Apply ADR's exact rational fee rules: branch 25% rate headroom, B0 >= max(f0,fc+f1) + 10% refundable credit headroom; default relay r=100000 sompi/kg, use actual config/standardness and <=5-minute quotes. Recompute fee-dependent scripts/keys before funding. Any funded insufficiency is liveness failure; no sponsor, bump, principal haircut/admin rescue. Different budget may be consensus-valid but adapter refuses unqualified exact budget; do not conflate that policy with script enforcement. |
| A1-25 / I-5, I-9, I-11, I-15 | Source estimate mistaken for measured capacity; verifier count doubled or alternate body skips checks | First G2 falsifier records all branch bytes, peak main+alt stack/count, executed ops, VK/tag/verifier count and U_j; G4 records final committed budgets, native compute/storage/transient masses and relay results. S0 has two embedded VKs but executes one. Assert exact envelope version1/native/gas0/payload0/lock0 via script, and distinguish unconstrained sequence/budget from adapter defaults. Actual hard limit/semantic blocker stops work; estimate miss requires reviewed revision, never safety relaxation. |

## Executed evidence ledger

The [setup/G2 fixture index](../poc/a1/evidence/fixture-2026-10-03/public-evidence-index.json)
contains G2's literal positives, 966 cases and native traces.
[Supplemental native cases](../poc/a1/evidence/extra-native-negatives-repaired-2026-10-04.json),
[66 original-context tests](../poc/a1/evidence/context-negatives.json),
[foreign setups](../poc/a1/evidence/foreign-setups.json) and
[native verifier diagnostics](../poc/a1/evidence/verifier-diagnostics.json)
have separately classified layers. The original supplemental receipt had 142
stale-ID decoder rejections and does not establish those native checks. Its
replacement recomputes ID/mass and asserts the intended layer. Bound SDK/fee
receipts reject mixed transactions/artifacts; fee replay uses a historical quote
and is not fresh funding approval. See the report's qualification-repair section. A fabricated diagnostic SPK is not an A1
accepted path; unknown input-version acceptance is an upstream diagnostic that
A1 funding/artifact inspection must reject.
The [post-artifact aggregate index](../poc/a1/evidence/evidence-index.json)
additionally pins G3/G4/G5 receipts and is never inserted into setup/constants.
The [v3 recovery receipt](../poc/a1/evidence/recovery-container-v3-2026-10-04/report.json)
and timeline record actual native checkpoint/S0-locator retention before
funding/continuation, then reuse of those exact old bytes after abrupt A loss.
This is local program-order evidence, not physical-machine or live-archive G5.

| Rows | Executed scope / evidence | Still outside demonstrated scope |
| --- | --- | --- |
| 01–03 | Checked integer Rust/Python model boundaries and golden accounting; actual native output/fee mutations; accepted direct/continued payouts in synthetic consensus | Variable private accounting, treasury or multi-user reserve |
| 04 | Claim/secret and outpoint circuit tests, original-context wrong-secret test, copied-proof output/recipient mutations | Cryptographic soundness proof or audit |
| 05 | Literal pinned keys, malformed proof/scalar/range corpus; native arity/tag/trailing-key diagnostics | Production-safe setup/gadget assurance |
| 06–07 | Acyclic real setup order; every output script byte/value/version/count/order/metadata mutations; wrong branches and fresh foreign setup proofs | Unbounded successor graph or arbitrary recipients |
| 08 | [Actual native race/replay receipts](../poc/a1/evidence/stateful-requalification-2026-10-04.json): two first-valid competing spends, exact and distinct-ID replay rejection | Public TN10 races/settlement |
| 09 | Original-key instance/domain/stage/mode/range/outpoint tests; S1→S2 rejection; separate foreign-context/key tests | Copied identical-chain-state replay excluded by ADR |
| 10 | [Native reorg + scanner accounting](../poc/a1/evidence/reorg-scanner-requalification-2026-10-04.json): actual removed/added chain groups, old outputs absent, final UTXOs exact; rollback/replay pointer/credits agree | Imported S0 checkpoint is not funding-lineage G5; no Bitcoin-only global-unspent claim |
| 11–12 | Recovery scanner unit negatives and clean network-disabled Docker B fresh proof/direct/S1/abrupt fixtures; immutable inventory/artifact checks | Independent physical machine loss and live/indexed archive compatibility remain G5 pending |
| 13 | Measured finite budgets; inadequate decoded budget rejects; [exact fee rules/forced failures](../poc/a1/evidence/fee-bound-qualification-2026-10-04.json) halt without changing terms | Guaranteed exit at arbitrary future rates |
| 14 | Native fixed recipient derivation and actual backup-key/claim checks in clean B | Private note recipient spendability does not exist in A1 |
| 15 | Observed circuit-specific setup, public VK/redeem pins, no bypass, no retained trapdoor material | Single-party setup trust, erasure/provenance proof, PQ unresolved |
| 16 | [Pinned SDK roundtrips](../poc/a1/evidence/fixture-2026-10-03/sdk-roundtrip.json), BigInt u64 max, independent ID/FULL hash and fresh native masses, nine decoded native negatives | Live malicious/divergent-provider observation and complete RPC archive integration |
| 17 | Report lists public amounts/linkage/recipient/stage/timing and local witness exposure | No anonymity/confidential amount/unlinkability/PQ claim |
| 18–20 | All 256 selectors each branch, multibyte/empty/equivalent pushes, every witness pair/slot, exact key/tag/ABI, output version and unknown-input diagnostic | Unknown input SPK versions are inadmissible, not magically script-enforced |
| 21 | Independent intent/codec/scripts/R1CS reconstruction, actual key validation and observed receipt; schema/matrix/hash/intent mutation unit tests | Same-host automated observation is not an independent-human ceremony; opaque CRS/shared gadget trust remains |
| 22–23 | Paginated native accepted-path discovery, current exact UTXOs, body hashes, scanner gap/duplicate/reorder/pruning/reorg tests; actual native reorg receipts separately coupled | Full independently retained TN10 DAG-body archive and actual machine-loss G5 pending |
| 24 | Historical quotes/replay, bound final-body receipts, rational 25-percent rate / 10-percent B0 headroom and 10-percent execution budget; forced high/stale quote/low credit/wrong budget negatives | Remote custom relay configuration/admission, later quotes and post-funding liveness |
| 25 | Actual three-branch byte/resource/trace measurements, fresh native SDK-decoded masses; every measured path fits pinned limits | Live G6 measurements/admission/inclusion |

After qualification repair, 20 Rust tests, 46 A1 Python tests and 13 Node tests pass. Runtime proof/case/SDK/native-chain
results above are separate from unit tests; none is proof of cryptographic
correctness. Full G5 is not closed, and G6 remains unauthorized.

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
initial funding locator and pre-funding independent scan checkpoint,
accepted transition history/current outpoint, reviewer setup/inspection receipt,
normalized constraint exports, artifact schema/index hashes, and
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
Use the ADR's A/B distinction: A is terminal spendability of an authenticated
current S1 UTXO; B is discovery plus accepted lineage/accounting from the exact
S0 outpoint. Both must pass the experiment. The recovery key controls the fixed
payout; the claim secret, PK_1t and public terms authorize the reserve proof.
Declare original, clean recovery and independent indexed chain/archive machines
on separate failure domains as specified in the ADR. A fully synced local pinned
node is preferred when available independently of the original host; G0 does
not wait for the currently syncing process.

The abrupt-loss case must succeed from the old S0 locator and a gap-free
pre-funding-checkpoint-to-horizon independent acceptance/body archive, without
a final export from the original host. Scan native v2 Full acceptance groups
with cursor pagination; if only v1 accepted IDs are available, join exact
archived bodies across DAG mergesets. Check the accepted S0-spending transaction
against branch constraints, derive S1 index0 and check current unspentness.
A matching address alone is insufficient. Include >one page,
pruning/independent restore, original disappearance before local pointer save,
reorg rollback and stale-horizon cases (A1-22/23). History loss without an
independent replica fails B even if a separately authenticated current S1 can
satisfy A. Do not silently add original-host access or claim that safe halting
passes I-10. No saved
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
