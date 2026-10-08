# A1 live attempt 1 — failed independent recovery boundary

Date: **2026-10-04**. TN10 test KAS only. [PR #22](https://github.com/olafweller/kaspa-privacy-initiative/pull/22)
remains draft. **FAILED — recovery boundary did not complete.**

## Goal

Attempt 1 funded the finite, public, single-owner A1 reserve to obtain the
missing independent G5 evidence: after accepted S0 → S1, independent archive C
would authenticate a durable boundary receipt, recovery machine B would arm,
and original machine A would disappear before B discovered S1 from old S0 plus
pre-positioned material and C, freshly proved, and Full-validated a terminal exit.
A was the owner's ThinkPad. Neither an orderly owner exit nor synthetic repair
tests satisfy this whole-A-loss recovery goal.

## Live result summary

| Step | Result |
| --- | --- |
| S0 funding | PASS |
| S0 → S1 | PASS |
| C independent capture | PASS |
| Boundary receipt | FAIL |
| B armed | NO |
| A powered off | NO |
| Independent recovery | NOT RUN |
| Fail-closed behavior | PASS |
| S1 fund safety | PASS |
| Separate terminal exit | PASS |
| Overall G5 attempt | **FAILED** |

PASS describes the bounded observations below, not production security or finality.

## Exact live TN10 evidence

- Funding txid: `c0968d6206fe0f2f5c9f96bae6d13a9d4a4ae8078a50c9401cba56bc50f323bb`.
  S0 was output **0**, funded with **10.7 test KAS**. Funding fee:
  **0.007047 test KAS**; total wallet debit: **10.707047 test KAS**.
- Accepted continuation txid:
  `5027a249234a139807657454055578f2c84ed31be85d027a0e2f4254f341d294`.
  It was submitted **exactly once**. Output **0** was the exact **6.4 test-KAS S1**;
  output **1** paid **4 test KAS** to the frozen owner recipient; fee **0.3 test KAS**.
  Accounting: `10.7 = 6.4 + 4 + 0.3`.
- C independently retained the accepted continuation body/acceptance,
  funding body, historical S0 input context and required chain/history data.
  S0 was spent; exact S1 was unspent and backed during the halted run.
- Terminal txid:
  `c3e155010dacbdc5a367db183170a96df0ddf80efa34d1c73cbad4e08d2b8483`.
  Full hash: `482e62cbae89f4b650205be5aef7f7478486bd50717784b8a96ecb7329463b9f`.
  Its sole input was the continuation's output **0**; sole payout was
  **6.1 test KAS**, terminal fee **0.3 test KAS**.

Exact outpoints, SPKs, absent covenant metadata, source/runtime/artifact/checklist
hashes and observation times are in the [sanitized public record](../poc/a1/evidence/live-attempt-1-2026-10-04/public-record.json).
The [terminal native validation request](../poc/a1/evidence/live-attempt-1-2026-10-04/terminal-exit.validate.json)
contains the exact decoded public transaction and historical S1 input entry.

## Failure

C validated historical acceptance data synchronously while holding the same
lock needed by status/probe responses. Repeatedly replaying the accumulated
prefix of **77 pages** required **1,049,867 native hash-checker invocations** under
the frozen algorithm. That work count is reconstructed from source and archive,
not a retained trace of completed invocations. Status responses timed out at the
**150-second client deadline**, while the separate capture service continued
advancing: **19 commits and no capture errors** during B's wait.

C already had the required archived bodies, acceptance data and S0 historical
context, but did not finish validation and produce the complete authenticated
boundary receipt. B did not fail to consume an existing valid receipt. Frozen
source, durable logs/data, positive authentication evidence and isolated
reproduction support control-plane lock contention; no circular deadlock was
demonstrated. The original stack trace and precise B exception were not retained,
so the diagnosis does not claim instruction-level reconstruction of that stall.

No unauthorized spend or underbacked S1 was observed, and no proof, covenant or
accounting failure was demonstrated. This does not exclude all possible bugs.
**G5 nevertheless failed because independent recovery never began.**

## Fail-closed behavior

B correctly refused to arm without C's complete independently authenticated
receipt. Its durable result remained a terminal failure; no recovery worker or
G5 terminal proof ran. A stayed online and was never powered off. No recovery
proceeded on incomplete evidence; S1 remained unspent until the separate exit.
The failed run was declared terminal and **was not resumed**. Original failure
records and fault journals remain preserved; later classification is additive.

## Remediation

Separate recovery-infrastructure work moved expensive validation into bounded
workers, added bounded native-result caching, deadline checks, read-only status
retry/reconnect, exclusive one-shot arming and more useful durable error records.
Protocol rules, proof logic, accounting and acceptance criteria were unchanged.

Separate **unfunded** qualification passed **12 B tests** and **22 C tests**
(with overlapping cases): delayed responses, timeout, actual process restart,
stale/wrong/replayed receipts, arrival just before/at/after deadlines, bounded
retry/reconnect, lost/late arm responses, no duplicate arming, synthetic
independence from A, and native receipt equality/missing-evidence rejection.
The live S1 was not used as a repair test target. Versioned repair source was
staged and exercised separately; original live controller configuration/pins
were not replaced. These tests **do not retroactively make attempt 1 pass G5**.

## Separate terminal exit

With A online, an independently reverified exact live S1 was reconciled against
C's archive/current TN10 state, reviewed source and frozen manifest. A fresh
terminal proof was generated for that outpoint; no pregenerated recovery,
rehearsal or synthetic proof was reused. The **10.63-second** subprocess included
PK loading, proving, standalone verification and native Full; it was not a
pure proving-only benchmark. Peak RSS was **187.15 MiB**.

The exact final decoded transaction passed SDK roundtrip and independent native
Full on A/B/C, including fresh prebroadcast Full at C's current chain context.
Fresh fee/policy checks passed. Compute budget was **1706**; native
compute/storage/transient mass was **171994 / 77 / 4136**. The one fixed-recipient
output returned all **6 test-KAS principal** plus **0.1 test KAS** refunded fee
credit: `6.4 = 6.1 + 0.3`. No extra output or principal haircut occurred.

A separate authorization bound the exact txid/full hash before its **single**
broadcast. C independently observed the exact prepared body accepted, S1
consumed, the exact 6.1-test-KAS payout UTXO unspent, and no conflicting accepted
spend or submission/reorg ambiguity. No retry occurred. A later observation
**98.685 seconds** after the first retained the same accepting block, with
blue-score distance **1802** (policy: greater than 20); it was **181.939 seconds**
after the submission claim. These are historical observations, not permanent
finality or current UTXO assertions. The approximately 99-second interval does
not establish the [matrix's](poc-a1-threat-test-matrix.md#recovery-inventory-and-measurable-pass-criteria)
separate ≥120-second later-observation interval. This owner exit is **not G5 recovery**
and does not close G6.

## Evidence boundary / remaining claims

- Attempt 1 is **FAILED**; independent G5 recovery remains **open**.
- A live A1 S0 → S1 transition and a separate live terminal S1 exit were demonstrated.
- Independent whole-A-loss recovery is still unproved; live pruning-cycle survival
  is still unobserved. Local G1–G4 qualification retains its documented limits.
- [Fixed-fee liveness issue #23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23)
  remains open. Full G6 has not run; PR #22 remains draft.
- No production architecture, security, anonymity, audit or PQ claim follows.
  Single-party setup and C node/archive observation trust remain explicit.

The public record is an allowlist extraction, not a dump of private receipts.
Original investigation, preparation, broadcast, failure and classification
receipts remain retained outside Git with SHA256 references. B/C copies of the
exit/observation/classification receipts were independently re-read and matched
A before publication; B's original failure hash and C's original fault journal
were also checked. Actual live claim-secret, recipient-key and unlock-value
scans passed before publication; the exported public request also passed a new
**offline** pinned native Full check. Hashes alone are neither a recovery replica
nor independent proof of chain acceptance. Private keys/seeds/claim secrets, backup/unlock
material, SSH credentials, addresses of infrastructure, environment, setup
randomness and unrelated wallet history are withheld.

This record is ready for review of a **separate** attempt 2, not authorization or
qualification to execute it. A new frozen run configuration/checklist must bind
the repaired tooling and fresh performance, topology, artifact, checkpoint,
chain and fee/policy qualifications. Attempt 1 must remain terminal; attempt 2
requires separate authorization. This documentation task starts no live work.
