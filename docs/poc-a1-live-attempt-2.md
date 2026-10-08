# A1 live attempt 2 — failed autonomous recovery after whole-A loss

Live run: **2026-10-05**; separate owner exit: **2026-10-06**. TN10 test KAS only.
[PR #22](https://github.com/olafweller/kaspa-privacy-initiative/pull/22) remains draft.

**G5 FAILED — autonomous recovery did not complete during the live run.**

Run ID: `attempt-2-checkpoint-clean-c121a95184e24b6293d82338bf8e52b5-live-6f8404fde5dd`.
[Attempt 1](poc-a1-live-attempt-1.md) remains separate, unchanged historical evidence.

## Goal and live result

Attempt 2 intended to demonstrate that after accepted S0 → S1 and physical loss
of original machine A, independent machine B could start autonomously, discover
S1 from old S0 plus pre-positioned artifacts/backups and C's retained history,
reconcile accounting, generate a fresh terminal proof, and native Full-validate
the SDK-decoded terminal transaction. Independent archive C's successful
lineage validation alone does not establish B's recovery.

| Step | Result |
| --- | --- |
| S0 funding | PASS |
| S0 → S1 | PASS |
| C independent capture | PASS |
| Whole-A-loss gate | PASS |
| B autonomous start | PASS |
| Independent lineage recovery | FAIL |
| Fresh proof during G5 | NOT REACHED |
| Terminal Full during G5 | NOT REACHED |
| Fail-closed behavior | PASS |
| S1 fund safety | PASS |
| Separate terminal exit | PASS |
| Overall G5 attempt | **FAILED** |

PASS describes bounded historical observations, not production safety or finality.
The fail-closed result means the failed worker produced no recovery exit or
terminal submission; it does not establish that every failure mode is safe.

## Exact live sequence

- Funding/S0: `8f92f958803d02eea2feb2e97886ba4e2aa6b5430990ba018322705fe7afddcc:0`.
- Continuation txid: `b540852ed61407e56d5ca7e715b70eb59d1a700baa21b3aaa84667b311cf94dc`.
  Full hash: `70746d43cc23de184862af94fc67e619f781453b80a30bbbd1350cea85178d07`.
  Accepted exactly once; S1 was its output **0**, amount **640,000,000 sompi**.
- Accounting: `1,070,000,000 = 640,000,000 S1 + 400,000,000 payout + 30,000,000 fee`.
- C independently retained and validated the continuation and S1. Its durable
  boundary was commit **919**, digest
  `3c9e627d920956339fdb620711e63f98321236731ba7f3278dd9c7e2d945a737`.
- Physical whole-A shutdown followed. C qualified the loss gate using unavailable
  machine and KPI availability endpoints, an unavailable independently challenged
  SSH lease, and **ten consecutive absence samples**. B started only after that
  gate: qualified loss at **20:08:19.680831 UTC**, B start at **20:08:22.661465 UTC**.
- B stopped after **35.107359 seconds**. No independent B lineage result, fresh
  terminal proof, SDK terminal receipt, or terminal Full result was produced
  during this live G5 run. The failed attempt remains terminal.

## Exact failure and synthetic-test gap

The original durable failure reported stage `fresh-proof-and-Full` and exception
`ValueError`. Subsequent diagnosis located the failure in
`original/B/software/recover_exit.py`, function `recover()`, at
`c.load_json(checkpoint)`. The live C checkpoint contained fractional metadata
timestamps, including `coverage.at`. The strict protocol JSON reader rejected
these with:

```text
a1_check.Invalid: float/NaN JSON values forbidden
```

`Invalid` inherits from `ValueError`. This was an orchestration/glue parsing
failure, **before B's lineage scan or proving started**, despite the wrapper's
broad stage label. Artifact verification and backup/recipient verification had
already passed. This failure does not demonstrate a failed proof or covenant.

Synthetic rehearsals used `mode='fixture'` and `checkpoint=None`, bypassing the
real live checkpoint decoder. Passing those fixtures missed this live-schema
boundary. The original failure receipts are preserved; the diagnosis adds detail
without rewriting their result.

## Separate repair and offline diagnostic replay

The separately retained repair introduces a bounded, duplicate-rejecting metadata
reader. Fractional values are allowed only for eight explicitly named timestamp
paths: `coverage.at`, `coverage.current.at`, `pre_seal_coverage.at`,
`pre_seal_coverage.current.at`, `page_committed_at`, `sealed_at`,
`pre_seal_observation.at`, and `selected_observation.at`. Protocol/accounting,
amount, index, and hash parsing remains strict. Lineage, artifact, proof, output,
and accounting checks are preserved. Durable sanitized child stdout, stderr,
exception, and stacktrace reporting was added. **28 regression tests passed**,
including reproduction of the exact live checkpoint failure.

A subsequent exact-input **offline diagnostic replay** completed:

```text
old S0 → C retained history → independent S1 discovery
→ accounting reconciliation → fresh proof → SDK serialize/decode → native Full
```

It took **1229.389 seconds / 20m29s** and used C native-result memoization after
the failed live run. The deployed B path did not have that memoization, so this
is not live performance qualification. It produced no broadcast and is not a
resume or retry of the live G5 run. It **cannot retroactively make attempt 2 pass**.
This publication records the repair; it changes no protocol or tooling source.

## Separately authorized owner terminal exit

The existing live S1 remained unspent after failure. A separate owner-recovery
procedure generated a **new randomized proof**, distinct from the diagnostic
replay proof. The separately authorized accepted transaction was:

- Txid: `16285ec837fba58db9a6782bcfc584f034c618975fd1e8358ddece9ad55fd228`.
- Full hash: `6b39e7a7ea925a1d76be13d8182e14f4a1aad5a1a345f39d1696777b2f094603`.
- Sole input: `b540852ed61407e56d5ca7e715b70eb59d1a700baa21b3aaa84667b311cf94dc:0`.
- Sole payout: **610,000,000 sompi**; fee: **30,000,000 sompi**.
  Accounting: `640,000,000 = 610,000,000 + 30,000,000`.
- Compute budget: **1706**; compute/storage/transient mass: **171994 / 77 / 4136**.
- Payout UTXO: `16285ec837fba58db9a6782bcfc584f034c618975fd1e8358ddece9ad55fd228:0`.
- Accepting block: `41d66f60e9cac255e99de7883a7e815aa8fd7f7b54bdb4d0784a01782349bdf4`.

C independently confirmed the exact prepared body accepted, S1 spent, the payout
UTXO present/unspent, and no conflicting spend, retry, or reorg ambiguity. The
later recheck passed **59.483394 seconds** after initial confirmation. This does
not establish the [matrix's frozen ≥120-second later-observation interval](poc-a1-threat-test-matrix.md#recovery-inventory-and-measurable-pass-criteria),
permanent finality, or current UTXO status at publication. This was separately
authorized owner recovery, **not autonomous G5 recovery or a completed full G6**.

## Public evidence and limits

The [sanitized public record](../poc/a1/evidence/live-attempt-2-2026-10-05/public-record.json)
contains the status table, accounting, public identifiers, C boundary, selected
observations, repair source hashes, and SHA256 references to retained original
failure/diagnosis/exit receipts. The [terminal validation request](../poc/a1/evidence/live-attempt-2-2026-10-05/terminal-exit.validate.json)
contains only the exact decoded public transaction and historical S1 input entry.
Original B/C failure copies match. Hashes bind retained records; they are not
independent proof of acceptance, data availability, or recovery replicas.

The [publication checks](../poc/a1/evidence/live-attempt-2-2026-10-05/publication-checks.json)
record passing documentation/heading links, fast CI (46 Python / 13 Node tests),
the separately retained 28-test repair rerun, an offline native Full check with
the exact retained validator binary, and private-value/preservation checks.
These checks do not rerun the live attempt or qualify attempt 3.

Attempt 2 demonstrates live TN10 S0 → S1, independent C lineage evidence,
physical whole-A loss, autonomous B recovery start, fail-closed behavior in this
failure, and a later safe terminal exit under the observed conditions.

It does **not** demonstrate successful autonomous G5 recovery, a live autonomous
terminal proof after A loss, production readiness, pruning survival, indefinite
historical recovery, or security/audit/anonymity/PQ guarantees. Full G5 remains
open; full G6 is incomplete. Single-party setup and C node/archive observation
trust remain explicit. [Issue #23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23)
and [RFC-0001](rfc/0001-state-architecture.md) remain open.

Claim secrets, recipient private keys, backup/unlock material, SSH credentials,
raw infrastructure secrets/configuration/logs, setup toxic waste, and unrelated
wallet history are withheld. No private receipt or backup is copied into Git.
Attempt 1 evidence remains unchanged.

The repository is ready for review/planning of **pre-attempt-3 qualification**,
not qualified execution. That review must pin repaired tooling, exercise the
real checkpoint decoder end to end, qualify the deployed uncached performance
and durable failure diagnostics, and recheck topology, artifacts, archive/chain
context, fee policy, and all frozen criteria. A future attempt requires separate
authorization. This publication starts no attempt 3, funding, broadcast, merge,
mainnet use, or protocol/invariant change.
