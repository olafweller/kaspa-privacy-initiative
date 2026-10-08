# A1 implementation and falsification report

Status: G1–G4 locally qualified; full G5 independent machine/archive evidence
pending on `poc-a1-successor-state`, descending
from merged specification `0193d1847aa53468d6056a925ffb60f2d69e5b23`.
The [first live TN10 attempt](poc-a1-live-attempt-1.md) demonstrated S0 → S1,
then **failed safely at the independent recovery boundary**. B never armed,
A stayed online and recovery did not start. That terminal failed run was not
resumed. Its S1 was later exited by a separate freshly proved, Full-validated,
explicitly authorized transaction. This is not G5 recovery or a full G6 run.
[Live attempt 2](poc-a1-live-attempt-2.md) reached independent C validation,
physical whole-A loss and autonomous B start, then failed at the live checkpoint
decoder before B's lineage scan or proving. **G5 FAILED — autonomous recovery
did not complete during the live run.** A later repaired offline replay and a
separately authorized new-proof terminal exit do not change that result.
**No further live action, mainnet use, G6 execution or merge is authorized.**
**Update 2026-10-08:** the [official trial](poc-a1-official-trial-2026-10-08.md) passed the
scoped S1 scenario: B recovered after physical loss of A and its fresh-proof
terminal payout was accepted on TN10. Full G5/G6 remains open.
The fixture recipient private key is deliberately public **1**: never fund it.

The frozen [ADR](adr/0003-a1-successor-reserve.md),
[matrix](poc-a1-threat-test-matrix.md), [plan](poc-a1-implementation-plan.md)
and [security invariants](../SECURITY-INVARIANTS.md) remain authoritative.
This is a public, fixed-value, single-owner finite reserve experiment, not a
shielded note system. No anonymity, confidential amounts, nullifiers, private
transfers, post-quantum security, audit or production readiness is demonstrated.

## Qualification repair after independent adversarial review

The review of `8d936c1` found two qualification defects. Supplemental output
mutations retained stale IDs: 142 cases rejected in transport decoding before
native validation. The fee checker compared masses but did not bind all SDK
fee/budget/ID/hash fields to the manifest and actual final bodies. These were
evidence/tooling defects, not demonstrated unauthorized-spend paths.

Repair source `9125dc04d4fac49c900e9e56351f27d1b0fac454` restores that portion of G2/G4 qualification.
The [repair receipt](../poc/a1/evidence/qualification-repair-2026-10-04.json)
pins the following newly executed evidence; original receipts remain unchanged:

- [172 supplemental cases](../poc/a1/evidence/extra-native-negatives-repaired-2026-10-04.json)
  use native final ID/storage-mass preparation, strict final-body decoding and
  asserted script/verifier rejection categories. All formerly stale-ID cases
  reach the intended check. Unexpected acceptance or an unrelated error fails
  qualification. Strict `validate-body` never silently repairs stale IDs.
- [SDK v2 receipt](../poc/a1/evidence/sdk-bound-requalification-2026-10-04.json)
  retains exact decoded bodies/input contexts, the manifest hash, per-branch
  measurement and VK/proof/context/redeem hashes. Three positives and nine
  decoded negatives pass. The fee checker rejects mixed/duplicate branch
  records and mismatched fee, budget, ID, full hash, mass or artifact receipts.
- [Bound fee requalification](../poc/a1/evidence/fee-bound-qualification-2026-10-04.json)
  reruns native Full/masses on the decoded bodies. It explicitly replays the
  retained quote at its historical qualification time; it is **not a fresh
  quote or current pre-funding approval**. Actual fees/budgets/amounts are unchanged.
- [Native G3 rerun](../poc/a1/evidence/stateful-requalification-2026-10-04.json)
  requires typed `MissingTxOutpoints`; each replay differs from both competitors.
  [Scanner/accounting coupling](../poc/a1/evidence/reorg-scanner-requalification-2026-10-04.json)
  again agrees with both native conflicting-branch reorgs. No G5 run occurred.

Final repair checks: **20 Rust**, **46 Python**, **13 Node** tests pass; SDK
roundtrips, formatting/syntax, docs and whitespace checks pass. Rust used pinned
1.91.0/locked release builds with the existing native build cache. Existing
historical setup, 966-case generation, 66 context negatives and recovery receipts
were not regenerated or credited as newly executed. New public receipts derive
from retained public fixtures only; the original private claim backup was not
available here, so no new actual-private-value scan or setup ceremony is claimed.

No underlying fund-safety negative was accepted. Historical supplemental coverage
is corrected, not retroactively credited. G1/G3 results remain supported and the
repaired local G2/G4 checks pass; full independent G5 remains open, G6 unexecuted,
and PR #22 stays draft. Fixed-fee liveness and single-party setup trust remain.

## Evidence boundaries and reproduction

The observed setup source is
`91270d35f02b73de9031abf22b25c648ee94dacc`; subsequent qualification tools do not
alter those circuit constants, keys or scripts. The
[setup/G2 fixture index](../poc/a1/evidence/fixture-2026-10-03/public-evidence-index.json)
pins complete literal branch transactions, UTXO contexts, VKs, scripts,
contexts, relation layout maps, traces, malformed-case errors and setup
observation. Manifest SHA256:
`13518264eb4bf142fdcaf222d06725685770b7c6fbb0eee736d570ee48cee6e5`.
The [source limits](../poc/a1/evidence/source-limits.md) pin native v2.1.0,
Rust 1.91.0, SDK files and exact primary sources. A0 evidence is unchanged.
The [aggregate review index](../poc/a1/evidence/evidence-index.json) additionally
pins later stateful, SDK, fee and recovery receipts. It is generated only after
artifacts and never inserted into a circuit/context/manifest; it excludes its
own hash. Neither index is a complete recovery replica.

Git holds review fixtures, **not a complete recovery replica**. Three public
PKs and normalized R1CS exports are externally retained; their exact byte
counts/hashes are in the manifest/index. Retaining only their hashes is not
recovery. The observer retained owner intent before the first setup and compared
separately wired reference matrices before issuing a receipt. This is automated
same-host observation, not a human review or independent-host setup ceremony.
There is no mathematical proof of opaque CRS provenance or trapdoor erasure.
Single-party trusted setup remains an explicit trust assumption. No setup
randomness is retained as recovery material.

Use `scripts/run_poc_a1.sh` with the exact clean upstream checkout and locked
release toolchain. `experiment NEW_DIR` never overwrites a bundle. The CLI has
no wallet, RPC submission, funding or broadcast API. The observer requires clean
committed source, records binary/source/lock pins before invocation and retains
intent independently of final export. A failed candidate has no receipt. The
first candidate stopped at a trace assertion: native `execute()` consumes its
final boolean. The corrected checker requires native execution success and
separately observes `[01]` before consumption, then empty main/alternate stacks
after the final native check. No safety check was weakened.

Qualification source commits are G2 `c20190c`, G3 `5299023` and G4 `7d4dca7`
containing final SDK/mass/fee tools, with final G4 policy requalification
`b7d5456` and chronological local G5 `207e6db`. The original setup/manifest source
pin remains `91270d3`; it is not replaced by a later whole-manifest hash.

## G1 and G2 — model, relation, scripts and real proofs

Checked sompi accounting uses bounded native integers, not field equalities.
The model and strict duplicate-free manifest reject invalid amounts, states,
modes, encodings and inconsistent terms before setup. Fixed G0 context/hash
oracles agree in Rust and independent Python; expected golden values are not
calculated by the production encoder.

The circuit adapts A0's established BN254 Groth16 / SHA256 claim-and-outpoint
authorization relation. It constrains the 32-byte secret, fixed claim digest,
fixed full context, five public scalars and their 128/128/32/128/128-bit ranges.
It does **not** prove variable private monetary arithmetic. Fixed accounting
is independently inspected before setup and actual values/output scripts are
enforced by the redeem script. Mature note/nullifier/transfer systems remain
out of scope; no new cryptographic primitive or vProgs dependency was introduced.

Construction was S1 terms/relation/setup → VK1 → redeem1/SPK1 → S0 continuation
constants/setup, with independent S0 terminal setup → two-key redeem0/SPK0 →
synthetic funding body → dynamic outpoint inputs. No circuit commits to itself,
its own key/script/SPK, a future funding ID or a manifest hash.

All three original real proofs pass standalone Groth16 and native Full
validation on final decoded transactions. ScriptPublicKey version is 0, verifier
tag is raw `20`, and five public inputs are popped as txid-low, txid-high,
index, tag-low, tag-high. Witness bottom first is exactly tag-high32,
tag-low32, proof128, selector1, exact redeem last. Redeem entry has four main
elements and empty alternate stack. S0 continue accepts exactly raw `00`;
S0/S1 terminal exactly raw `01`. Equivalent push opcodes are permitted; empty,
truthy alternatives and noncanonical numeric equivalents are not selectors.

The observed corpus has 966 native cases, including all 256 one-byte selectors
for every branch, multibyte/empty selectors, all missing elements/extra slots/
pair swaps, malformed scalars/proofs, wrong-branch proofs, output/envelope/
metadata/outpoint mutations and equivalent-push positive controls. The repaired supplemental
cases cover scalar lengths 0/16/64, exact Fr modulus, every byte of each output
script, each missing output, forbidden S1→S2 and a different sufficient budget.
Budget+1 is consensus-valid but fails the exact qualified adapter policy; it is
not falsely described as covenant-enforced.

Original-constant context tests independently hash each field mutation while
retaining the original outpoint/relation/VK and secret except explicitly labeled
wrong-secret mutations: the original constraint
system is unsatisfied and the original proof fails verification. They are
separate from executed ephemeral foreign-setup proofs: a same-relation foreign
key has its own positive proof but rejects under the pinned original VK/native
script; a changed-instance foreign relation/key is likewise rejected, without
crediting key mismatch to original-field binding. Actual errors/layers are
retained. No proof is claimed to have been generated for unsatisfied witnesses.

Each successful trace executes matching output count/order/value/full-SPK/
metadata constraints and exactly one matching immutable VK/tag20 verifier.
There is no alternate-verifier or early-success path. The peak combined stack
is nine; pre-final main stack is `[01]`, alternate empty. Counted native ops
include skipped S0 arm instructions and reset per script; active execution
counts are separately labeled.

## Independent parameter inspection

`a1_check.py` does not import the production encoder or script compiler. It
reconstructs contexts, terms, recipient/address and complete scripts from
separately retained owner intent, checks the acyclic SPK dependency, each literal
VK, all artifact descriptors and canonical manifest fields. `a1_reference`
uses separately written circuit wiring/row normalization and validates PK/VK
encodings/mapping. The original normalized matrices match its independently
compiled matrices byte-for-byte. The pinned Arkworks SHA gadget, field and
serialization libraries are shared: this is parameter/compiler consistency,
not a second cryptographic implementation or proof of gadget correctness.
Constant SHA blocks may fold; region maps are not invented per-byte row proofs.
Opaque setup keys are qualified only with the explicit observed-invocation
receipt and its single-party/shared-host limitations. Proof success plus hashes
alone never certifies intended constants or setup provenance.

## G3 — native stateful scope

The harness uses actual upstream TestConsensus, temporary RocksDB, block storage,
acceptance data, virtual UTXOs and native conflict/reorg processing. Genesis is
synthetic and PoW is skipped: **not public TN10 acceptance**. Both S0 choices
are first valid against the same actual fixture UTXO. Continue/continue and
continue/terminal races accept at most one; the losing transaction, exact
replay and a distinct-ID sequence-mutated replay fail for spent input. The
distinct replay is first standalone Full-valid, so its failure is not inferred
from a bad proof. Direct and continued complete paths also have native accepted
body/output/UTXO receipts.

Kaspa DAG rollback must not be modeled as a Bitcoin-only empty-fork rollback:
a known nonconflicting spend can remain in the mergeset. The controlled fork
therefore contains the conflicting alternative and has enough descendants to
change selected chain. Native processing removes old-winner outputs and installs
the alternative's exact outputs. Original S0 remains spent after atomic
replacement. Recovery/accounting must remove the old payout/fee/state pointer
and apply the newly accepted branch together. A mere chain-tip change is not
evidence that the reserve is unspent. Never settle state from proof creation,
submission or an acknowledgement.

## G4 — actual resource measurements and provisional fees

Column order below is direct S0, S0 continuation, S1 terminal. All are measured
from the final native decoded fixture; no A0 metric is reused.

| Measurement | S0 direct | S0 continue | S1 terminal |
| --- | ---: | ---: | ---: |
| Constraints | 119514 | 121124 | 119526 |
| Setup ms | 3437.98 | 3558.13 | 3100.87 |
| Prove ms | 1382.82 | 1089.54 | 1107.40 |
| Standalone verify ms | 6.36 | 5.90 | 6.42 |
| Native Full ms | 7.69 | 7.99 | 7.64 |
| PK bytes | 22923088 | 23178768 | 22925008 |
| VK / proof bytes | 424 / 128 | 424 / 128 | 424 / 128 |
| Redeem / signature bytes | 1289 / 1489 | 1289 / 1490 | 634 / 834 |
| Input full SPK bytes | 37 | 37 | 37 |
| Output raw script bytes | 34 | 35, 34 | 34 |
| Native Borsh bytes | 1679 | 1730 | 1024 |
| Consensus FULL hash-preimage bytes | 1666 | 1721 | 1011 |
| Consensus mass size estimate | 1689 | 1743 | 1034 |
| File transport JSON bytes | 3540 | 3676 | 2229 |
| SDK safe / numeric JSON bytes | 3717 / 3703 | 3853 / 3837 | 2405 / 2391 |
| Actual script units | 15502918 | 15502961 | 15501607 |
| Active instructions / non-push ops | 96 / 54 | 107 / 60 | 90 / 49 |
| Native counted ops: sig / SPK / redeem | 0 / 2 / 93 | 0 / 2 / 93 | 0 / 2 / 47 |
| Peak main+alternate elements | 9 | 9 | 9 |
| Compute / storage / transient mass | 172649 / 27 / 6756 | 173073 / 3128 / 6972 | 171994 / 77 / 4136 |
| Committed compute budget | 1706 | 1706 | 1706 |
| Default relay floor sompi | 17264900 | 17307300 | 17199400 |
| Fixed fee sompi | 30000000 | 30000000 | 30000000 |
| Isolated fresh-proof CLI peak RSS KiB | 199580 | 200884 | 199236 |
| Isolated CLI wall seconds including PK validation/load | 27.73 | 25.23 | 30.77 |

Borsh, hash preimage, transport and the mass-size estimate are different formats;
none is mislabeled as measured P2P/RPC Borsh framing. Native FULL-hash encoding
is independently checked against an exact literal vector/Python calculation.
The successful observed setup/experiment/reference comparisons took 98.17 s,
peak process RSS 324224 KiB; this is a combined run, not isolated prover memory.
Timings are one local sample, not performance guarantees.

The [SDK report](../poc/a1/evidence/fixture-2026-10-03/sdk-roundtrip.json)
executes both SDK byte-string serializers/deserializers, checks exact BigInt
fields and literal witness bytes, compares independent IDs/FULL hashes, and
reruns Full plus fresh native mass calculation on the final decoded bodies.
All three positives and nine decoded proof/budget/metadata negatives pass.
The isolated samples include PK subgroup/canonical parsing and proving/Full
verification in a separate process; they are not a proof-only RSS attribution.
Each generates a different proof than the golden; unchanged txids are expected
because txid excludes the witness. They are not discovery or chain acceptance.
The historical [final SDK requalification](../poc/a1/evidence/sdk-requalification-2026-10-04.json)
repeats all three positives and nine decoded negatives using the v3 native
binary `a2dd5ab1b8431af037d279511467c5b3acbf29712c248f501d4c35e1d8360ae1`
and unchanged independently wired reference binary. Final decoded masses,
IDs, FULL hashes and literal witness bytes agree with the original fixture.

Pinned native limits are stack 244, script/element/counted-op limit 1000000,
signature 250000 bytes/input, output script 10000 bytes, SPK version 0 and u16
budget. TN10 compute/storage/transient ceilings are 500000/500000/1000000.
Measured S0 fits the G0 two-KiB falsification ceiling and every native limit.
One execution pays one 155000-gram Groth16 verifier plus surrounding work; S0
contains two VKs but does not execute two verifiers. No hard protocol blocker
has been found in these measurements.

The fixture uses L0=1000000000, B0=70000000, W=400000000 and
f0=fc=f1=30000000 sompi. Thus R0=1070000000, L1=600000000, B1=40000000,
R1=640000000, P0=1040000000, P1=610000000. Fees consume only explicit owner
fee credit; unused credit is refunded in the terminal payout.

For each branch use overall M=max(native compute mass, native storage mass,
ceil(transient mass/2)) and separately relay N=max(compute, ceil(transient/2)).
Use the exact native relay floor and f>=max(relay, ceil(5*q*M/4)), with q the
conservative maximum of observed bucket rates and source relay rate. The
source-default relay rate is 100
sompi/gram; current external quotes must be rechecked at qualification and be
no older than five minutes before any separately authorized future funding.
At quoted rate 100 the headroom requirements are 21581125/21634125/21499250
sompi; all are below 30000000. B0>=ceil(11*max(f0,fc+f1)/10)=66000000;
70000000 qualifies. These are provisional offline/source-policy and quote
checks, **not remote mempool admission or an attestation of server custom
relay configuration**. Two endpoints do not prove operator independence.
No fee bump, sponsor input, principal haircut or admin rescue exists.
Unfunded fee changes rebuild/reinspect all dependent artifacts; insufficient
fees after funding are liveness failure, not authority to weaken safety.

[G4 quote observations](../poc/a1/evidence/fee-quote-g4.json) were less than
50 seconds old at [qualification](../poc/a1/evidence/fee-qualification.json).
Forced rate 1000, expired quote, B0 below 66000000 and budget 1707 all reject
without changing the original terms. This historical qualification expires;
it is not a reusable pre-funding approval.
The [pre-review quote refresh](../poc/a1/evidence/fee-quote-2026-10-04.json)
and [requalification](../poc/a1/evidence/fee-qualification-2026-10-04.json)
passed at rate 100 with quotes 38.02/37.40 seconds old. All four forced
fee/budget failures still reject without changing terms. Neither observation
certifies target custom relay policy, archive retention or future funding.
Final review corrected a checker-policy omission of storage in the headroom
mass, without changing G0. All three actual fixtures are compute-dominated,
so their numerical fees/resources remain unchanged. A storage-dominant
regression requires 50000000 rather than the relay-only 12625 sompi and rejects
the illustrative 30000000 fee. Native relay zero fallback/cap are tested
separately. Historical receipts predate this correction. The corrected
[final checker qualification](../poc/a1/evidence/fee-qualification-final-2026-10-04.json)
uses a [new quote](../poc/a1/evidence/fee-quote-final-2026-10-04.json) only
19.25/18.92 seconds old, distinguishes M/N explicitly and again passes all three
branches and four forced failures without changing terms. All qualifications
remain historical observations, not approval for subsequent funding.

## G5 — recovery boundaries

[Live attempt 1](poc-a1-live-attempt-1.md) failed to complete C's boundary receipt
before the status deadline because historical validation blocked the shared
status/probe lock. C had the archived material; B correctly stayed unarmed.
Unfunded repair regressions and the later separate owner exit do not close G5.
The historical local rehearsals below retain their original scope.

[Attempt 2](poc-a1-live-attempt-2.md) separately records a live accepted S0 → S1,
C's durable boundary commit 919, qualified physical whole-A loss, and autonomous
B start. B failed after 35.107359 seconds at `c.load_json(checkpoint)`:
fractional `coverage.at` metadata was rejected by the integer-only protocol JSON
parser (`a1_check.Invalid`, a `ValueError` subclass). Artifact and backup/recipient
checks had passed; no B lineage result, fresh proof, SDK terminal receipt or
terminal Full result was produced in the live run. Synthetic `mode='fixture'`,
`checkpoint=None` rehearsals had bypassed this decoder.

The separate narrow metadata/diagnostics repair passed 28 regression tests.
An exact-input offline replay completed in 1229.389 seconds with diagnostic C
memoization unavailable on the deployed B path; it is not live G5 success or
performance qualification. A separately authorized owner exit used a different
new randomized proof and was accepted, with exact 610,000,000-sompi payout and
30,000,000-sompi fee. Its approximately 59.5-second later recheck does not meet
the frozen ≥120-second interval. See the [attempt-2 public ledger](../poc/a1/evidence/live-attempt-2-2026-10-05/public-record.json)
for identities, accounting and retained receipt hashes. Attempt 2 remains
permanently **G5 FAILED**. No protocol source or prior evidence is changed.

Recovery separates terminal spendability A from accepted lineage/accounting B.
The scanner starts from retained exact S0 locator + checkpoint + artifact-index
hash; processes cursor-paginated accepted transaction bodies, recomputes ID/full
hash, validates original inputs and ordered outputs/fees/metadata, authenticates
the funding output, derives S1 index0 and reconciles exact current native UTXOs.
It atomically rolls removed history/accounting/state back before added groups.
Matching an address, UTXO-only discovery or an unchecked accepted-ID claim is
insufficient. Gaps, no-progress, duplicates/reordering, pruning, poisoned bodies,
stale locators and unavailable history fail closed. A public PK cannot be
regenerated under a new setup or recreated from its hash.

The implemented Docker A/B/C rehearsal gives B an allowlisted immutable public
bundle, separately held private claim/recipient backup, old S0 locator and C's
native accepted-path archive. B gets no original filesystem mount, original
prover, prior exit proof or saved S1 pointer; networking is disabled. It checks
artifacts/backups, discovers state and generates a fresh proof. C independently
in its namespace uses native synthetic consensus to validate/accept the exact
payout. Orderly S0, orderly S1 and abrupt loss are separate fixtures.

The [chronological v3 recovery receipts](../poc/a1/evidence/recovery-container-v3-2026-10-04/report.json)
demonstrate the following local namespace results, including artifact inspection,
history discovery and fresh proving in B (startup/build prerequisites separate):

| Case | Whole B recovery seconds | Fresh-proof subprocess seconds | Exact native accepted payout sompi |
| --- | ---: | ---: | ---: |
| Orderly S0 | 103.358 | 46.833 | 1040000000 |
| Orderly S1 | 130.955 | 23.708 | 610000000 |
| Abrupt loss after S1 acceptance | 60.181 | 15.324 | 610000000 |

All whole-B runs finish below the 30-minute local duration threshold; these
are not a physical machine-loss timer qualification. Abrupt A was removed after C acceptance
and before an S1 pointer was recorded. B starts from S0 locator/backup/public
artifacts/C archive; no original bundle or pregenerated exit was supplied.
The archive has one funding page for S0 and two pages for continued S1.
Native C accepted each freshly generated terminal body and exact output.
V3 actually retained C's [native zero-transaction checkpoint](../poc/a1/evidence/recovery-container-v3-2026-10-04/pre-funding-checkpoint.json)
and planned S0 locator **before A created continuation or C accepted funding**.
Every C path matches the retained checkpoint; every B archive compares and
copies the same retained locator bytes, never an accepted-S1-derived locator.
The [program-order timeline](../poc/a1/evidence/recovery-container-v3-2026-10-04/timeline.json)
records abrupt S1 acceptance, A removal before pointer save, then B delivery.
This is executed program order, not hardware timestamp attestation. Original
v3 native C terminal acceptance timings are 0.614/0.254/0.386s, not replays.

The [earlier v2 receipts](../poc/a1/evidence/recovery-container-2026-10-04/report.json)
remain immutable (118.433/115.513/135.713s). A
[post-run locator comparison](../poc/a1/evidence/recovery-container-2026-10-04/old-locator-qualification.json)
established identical old bytes, but is explicitly not evidence that v2
executed v3's chronology guards. V3 supplies that actual local rerun.

44 fast inventory-boundary cases remove/corrupt each of 22 retained dependencies
without changing the original snapshot. Ten separate container negatives reject
missing/corrupt PK, wrong secret, missing/gapped/reordered/duplicate/poisoned
history and missing/wrong recipient key. Eight receipts are explicitly reused
from the SHA-bound v1 run, not falsely described as rerun under v2 or v3 software.
Each later run independently repeats the 44 inventory faults and the two native
recipient-backup negatives. The v3 receipt's inherited reuse-scope string
mentions v2; its recorded v1 hashes remain authoritative, not a v3 rerun claim.
Scanner unit tests additionally exercise pruning/stale locators and actual
native G3 receipts exercise reorg rollback; live pruning integration remains
pending. In v2 a reporting-only defect used the no-float artifact decoder on timing
receipts; the benchmark decoder was separated without weakening artifact
parsing. Persisted B proofs and original native C acceptance are retained.
Extra C timing replays (0.327/0.603/0.454s) are explicitly labeled new replays,
not the original acceptance timings. No G5 live/physical claim follows.

**Docker namespaces share this physical machine. They do not close independent
machine-loss or live/indexed archive G5.** Native-path archive translation is a
scoped fixture, not demonstrated live v2 Full RPC/pagination compatibility or a
complete DAG coinbase archive. The syncing node is neither awaited nor changed.
Its eventual availability does not by itself prove independent retention or
failure-domain isolation. Real independently operated machine/archive evidence
remains a prerequisite before declaring full G5 or recommending G6.

## Original implementation checks (before qualification repair)

Pinned offline locked Rust release tests: **19 passed, 0 failed** in 132.52s;
includes native checkpoint-before-acceptance/reproducible-seed regression.
A1 Python tests: **38 passed, 0 failed**, including overall-storage headroom,
native relay fallback/cap and old-locator/checkpoint chronology rejection.
Runtime real-proof/native-case/SDK/chain/recovery receipts are separate from
these unit tests. Rust formatting, both Node syntax checks, documentation links
and Git whitespace/diff checks pass. Primary-source URLs were checked separately;
automatic relative-link checking does not certify external facts or security.

## Invariant review and residual risks

The [matrix evidence ledger](poc-a1-threat-test-matrix.md#executed-evidence-ledger)
maps all 25 rows to execution scope. The unchanged invariant document is not
reinterpreted as a public one-claim implementation specification.

| Invariant | Result / explicit limit |
| --- | --- |
| I-1 backing | Exact native fixture R=L+B, successor backing and payout/fees reconcile. No treasury backing counted. |
| I-2 conservation | Checked fixed public integer accounting and actual native output constraints; no variable private-accounting claim. |
| I-3 authorization | SHA secret relation + native Groth16, immutable branch key, fixed payout and recovered key checks. Public C alone insufficient. |
| I-4 single spend | Actual native competing-spend/replay tests; public UTXO/linkage means the invariant's private-resource non-revelation goal is not demonstrated. |
| I-5 soundness | Real proof/malformed/context/native tests; no proof of cryptographic soundness or audit. Single-party setup remains trusted. |
| I-6 correct state | Exact context/ranges/current outpoint, branch scripts and authenticated successor; native reorg/accounting replay. Identical copied chain-state limitation remains. |
| I-7 withdrawal | Exact single input/reserve and ordered payout/successor/SPK/metadata/fees; no arbitrary successor or redirected payout. |
| I-8 no confiscation | No admin/upgrade/operator/rescue withdrawal path. Fixed fees/public-artifact loss can still strand liveness. |
| I-9 safety first | Malformed inputs, bad artifacts/history/quotes halt; no fallback weaker script, address-only lookup or principal haircut. |
| I-10 recovery | Clean-container fresh exits and native fixture discovery demonstrated; attempt 2 passed physical whole-A loss/autonomous B start but failed before B lineage/proving. Full independent G5 remains open; later replay/owner exit is separate evidence. |
| I-11 reproduction | Separate Python context/script/accounting and reference R1CS/FULL-hash paths agree; shared cryptographic gadget/field libraries are explicit. |
| I-12 isolation | Owner fee credit, no treasury/sponsor reserve-control input or alternate branch. |
| I-13 upgrades | No upgrade or witness-selected key; source/keys/scripts frozen. Verifier diagnostics cannot change funded artifacts. |
| I-14 spendability | Actual recipient recovery-key derivation checked; no private note exists, so private-note spendability remains deferred. |
| I-15 rejection | Canonical manifest/scalars/witness/context and actual deterministic native negatives; unknown input SPK versions must be rejected by funding/artifact inspection, not assumed native-safe. |
| I-16 scoped privacy | Public values, instance, stage, linkage, recipient, proofs and timing. Local claim witness; a hosted prover would learn it. No anonymity/PQ claim. |

Adversarial second pass found no tested double acceptance, unbacked successor,
redirected payout, selector bypass, witness-selected VK, circular setup or rescue
authority. It preserved important limits: a tip change need not undo a DAG
spend; txid excludes proof/mass; unknown input SPK versions skip VM; an
independently wired compiler shares SHA libraries; hashes cannot certify an
opaque CRS or recreate missing PK/history; containers share hardware; remote
synced/indexed status is not archive retention or operator independence.
These are not removed by passing tests.

The complete local unfunded bundle and observer receipts are retained under
ignored `.local/a1/`, with private files mode 0600 and directories mode 0700.
The public runtime image is also exported there; its image ID is
`sha256:7cac5961174b47c3528c0dc36303c11fff63d9db1f4673f33b7e4279c26bdf25`,
and retained image-tar SHA256 is
`faece4bc81c181376c23a36cc58701cc3a03ee8991fb5898123fdb860756200b`.
This avoids relying solely on transient `/tmp` files but is **not independent
host retention**. Public artifacts/software must be separately replicated and
verified on B before a real machine-loss test. User private backups must remain
separate from publication. Actual random claim bytes/hex/base64 were scanned before
publication; allowlists exclude all private backup files.

Remaining blockers include demonstrated independent whole-A-loss recovery and
live pruning-cycle/history-retention survival. Attempt 1 established live C
capture, but its complete recovery boundary never finished. Attempt 2 established
whole-A loss and autonomous B start but failed at checkpoint parsing; its later
offline replay and owner exit do not close G5. Pre-attempt-3 qualification must
pin repaired tooling, exercise the actual live metadata path and qualify deployed
performance without relying on diagnostic memoization before any new authorization;
full G6 remains blocked by open G5. Future live work requires explicit authority,
fresh quotes/actual target policy and a separately inspected private-owner instance.
**Do not recommend G6 or fund the public fixture.** PR remains draft; the attempt
record authorizes no further funding, broadcast, merge or invariant mutation.
