# A1 S0 trials 2026-10-08 — recovery, direct exit and competing spends

Live runs: **2026-10-08**, testnet-10 (TN10), native test KAS only.

**Result: PASS for the three scoped S0 scenarios.** A complete A-direct rehearsal paid out before the official trials. B then recovered from S0 while the whole original machine A was physically off; A exited directly in a separate identity; and two valid S0-terminal candidates competed for one reserve. B was accepted and the later A candidate was rejected.

These results add S0 coverage to the earlier [S1 recovery trial](poc-a1-official-trial-2026-10-08.md). They do **not** close the full G5/G6 matrix. The competing attempts were ordered about **1.4 seconds apart**, not simultaneous network arrivals.

## What happened, in plain terms

1. Each identity was new. A funded one S0 reserve with 32.1 test KAS; there was no S0 → S1 continuation in these trials.
2. In the successful rehearsal, A made a fresh proof, passed native Full validation and SDK readback, submitted once, and received the exact 22.1 test-KAS payout. Only then did the official trials start.
3. For official trial 1, B already held its own public artifacts and the user’s recovery material. The operator physically powered A off. A delayed worker on B started independently, read C’s complete accepted history from its retained pre-funding checkpoint, discovered S0, proved the terminal spend freshly, and paid out through its own connection to C. B did not need A’s files, wallet or running processes.
4. In official trial 2, A performed the same direct S0 exit in a new identity.
5. In official trial 3, A and B each prepared a distinct, independently valid terminal transaction for the same S0 input and fixed payout. Both submitted once. The node accepted B and rejected A. Both programs reconciled the actual accepted history and native payout; A wrote a normal loser result and exited successfully.

Every successful payout was checked again at least 120 seconds after its first successful observation. Native Full and the SDK checked the exact candidate body before submission; accepted-body hashing, recipient, amounts, fee and spent reserve were checked after submission. No used identity was resubmitted.

## Transactions and failed attempts

All funded rows deposited **3,210,000,000 sompi (32.1 test KAS)** at output 0. Every accepted terminal paid **2,210,000,000 sompi (22.1 test KAS)** at output 0 and charged **1,000,000,000 sompi (10 test KAS)**. Funding fees are separate and recorded per identity in the [public record](../poc/a1/evidence/s0-trials-2026-10-08/public-record.json).

| Case | Funding txid | Accepted payout txid | Outcome / cause |
| --- | --- | --- | --- |
| Rehearsal 1 | `ee6e5cca082a5f2d67da8cd1e1203e9564e0ba01a871834d11120c2bce0aca04` | — | The SDK's JSON conversion dropped a covenant field whose value was undefined. The scanner rejected the incomplete history before a terminal attempt. |
| Rehearsal 2 | — | — | A standalone transport connection ended with broken pipe. No funding or terminal submission. |
| Rehearsal 3 | `ccd36b8ff22fa9b808abb0828b62dd7902fca642aca2c9c9fb9ae477cf74d372` | — | History fetch reported a reorg and halted before a terminal attempt. The failing removed-suffix response was not retained; a later query found the checkpoint still selected. The precise chain change is unproved. |
| Successful rehearsal | `998c35856aaf4dd39317c4db642cf4bc3141a8079349aff9ea77b9159c2435f8` | `f9e9eb1f42550599ecbbfe09ebdfc50565f95873bc2e9e5a24dce814f2cf7235` | PASS |
| Official 1: B recovery, A off | `94545234e7075736181d08496dfa54c5140fb7ff1d3e795c8e73d527ace4c572` | `292e6af065d065b7d1ce0580a8086a9ac8925a855fca03ea23c0fc084684efa6` | PASS |
| Official 2: A direct exit | `ae64bec7d7038c5c4551f4fd6313bfa80fa762090e8d618ad17e99dea3400b77` | `246d59964470674872610400a066f70d9af5311cf76ce66045625384e5cc9a47` | PASS |
| Competing spend, first attempt | `0f91a6cf070d056fcb6d6bbae6cca82fb01f49146e4e881c44526b9e5b1f92f4` | — | Executor command quoting produced a Python SyntaxError before B started. A only prepared a candidate. Neither terminal was submitted. |
| Official 3: competing spend, fresh identity | `4ff7bf88309ed35ef82966f5954b09780aaefc28875a69e43de8b7ed446589de` | `4b478659fa9e52fd094195c39c3dce70dba1d75585d7afdbff513a1b897aa91e` | PASS; B accepted, A rejected |

The three failed funded identities stopped before any terminal submission. Their S0 reserves were still unspent at the final operator check: **96.3 test KAS** in total. The failed transport rehearsal was unfunded. Recovery material and original evidence remain retained locally; each retry used a new identity.

The reported reorg failure does not establish that the pre-funding checkpoint was removed. A later read-only query found it still selected, and the failing removed-suffix response was not retained. A changing snapshot/page suffix was a hypothesis, not a demonstrated cause.

## Physical A loss and observation times

The operator reported powering off the whole A machine, rather than merely closing its routes. Locally retained C heartbeats stopped before B started; A had a different boot ID after return. B finished before A’s estimated new boot. These observations corroborate the operator action; they are not hardware power telemetry or a forensic proof of host isolation.

| Event / case | Time or interval |
| --- | --- |
| B independent worker start | 2026-10-08T16:15:30.313774Z |
| B recovery worker finished | 2026-10-08T16:39:11.192624Z |
| Successful rehearsal: successful payout recheck interval | 153.51 s |
| Official 1: B recovery, A off: successful payout recheck interval | 324.73 s |
| Official 2: A direct exit: successful payout recheck interval | 141.84 s |
| Official 3: competing spend, fresh identity: successful payout recheck interval | 334.23 s |
| A loser: successful outcome recheck interval | 323.32 s |

The intervals are between successful checks, not a claim of uninterrupted sampling. In each case, fixed amounts, recipient, accepted body and reserve spentness had to agree.

## The competing-spend result, without overstating the timing

Both programs targeted **2026-10-08T17:28:00.000000Z**. They still checked checkpoint and snapshot survival after that barrier, before making their one submission. B recorded its submission intent at **2026-10-08T17:28:16.228478Z**; A recorded its intent at **2026-10-08T17:28:17.654180Z**, **1.425702 seconds later**. These are durable times immediately before RPC, not exact network-arrival timestamps.

B’s accepted candidate was `4b478659fa9e52fd094195c39c3dce70dba1d75585d7afdbff513a1b897aa91e`. A’s rejected candidate was `804f7d169da6855362766e538638a4f4e20f134bbf33be86eb09f195059cf78a`. The node reported A as an orphan with orphan admission disabled. The RPC error was retained locally, but the result was determined from accepted history, not inferred from an error alone.

Both candidates had already passed native Full and SDK checks against the same S0 context. They used different lock-disabled sequences to distinguish their IDs. Both committed to the same output, recipient, amount and fee. This was **S0 terminal versus S0 terminal**; it did not test a continuation-versus-terminal race or arrival while both transactions were still unconfirmed.

Each final accepted-history scan covered five pages. B’s candidate occurred once in each accepted history; A’s candidate occurred zero times. There was exactly one spender of the S0 outpoint, the payout UTXO had the fixed value, and the reserve was gone. Both scans agreed on the winning Full-body hash:

`28c1184ecb6e737ef3bcec48338fa1fb78c8340d3af08861ef8c65f52a59797c`

A wrote a normal `lost` result, with its own txid and the winner’s txid, and exited with code 0. A’s later check interval was 323.32 seconds; B’s was 334.23 seconds. The case demonstrates one accepted reserve spend and rejection of the later competing candidate; it does not demonstrate perfectly simultaneous submission.

## Accounting

- Seven funded identities deposited **224.7 test KAS**.
- Four accepted terminal payouts returned **88.4 test KAS**.
- Their fixed terminal fees totalled **40 test KAS**.
- Three failed identities retained **96.3 test KAS** in unspent S0 reserves at the final check.
- Additional funding fees totalled **0.050447 test KAS**.

`224.7 = 88.4 payouts + 40 terminal fees + 96.3 unspent reserves`.

All stored monetary amounts are integer sompi. The large fixed terminal fees are experimental admission terms, not an estimate of practical exit cost. These trials do not resolve [fixed-fee exit liveness](poc-a1-implementation-plan.md).

## Runtime provenance and local checks

The four successful cases used runner source commit `c541dd51a8672241f885b1af4bf30b539297dda5`, the pinned Kaspa v2.1.0 SDK and validating TN10 node, and the existing A1 native validator/reference binaries. The public record includes per-identity source/artifact hashes and the successful native Full/SDK software hashes. No new cryptography or protocol rule was introduced. See the [runner design](poc-a1-trial-runner.md).

Rehearsal failures led to these operational repairs before fresh trials:

- Preserve an SDK field that exists with JavaScript `undefined` as JSON null; genuinely absent Full fields still fail.
- Retain checkpoints and snapshot horizons below the moving tip by walking 64 selected-parent links. Removed prefixes, incomplete pages and mismatched contexts still halt; this depth is not a finality guarantee.
- Reuse native ID/hash checks only for unchanged, unrelated bodies. Relevant reserve spends still receive fresh native Full validation.
- Replace a broken standalone connection with a reconnecting transport, and correct the executor’s command quoting before a new identity.

Thirty offline runner cases passed, including two native integrations. They include corrupted/missing/reordered history, wrong checkpoint/cross-instance state, reorg, loser reconciliation, private diagnostics/redaction, and the configurable 30-minute wait limit. These are implementation tests, not live fault-injection coverage or a cryptographic soundness proof.

## Scope: what this does and does not show

Demonstrated in the scoped TN10 runs:

- S0 recovery and a real native payout through independently running B while A was physically off;
- a direct S0 payout through A, in a separate identity;
- two actually submitted, locally valid terminal candidates, one accepted spend, and a normal result proving the later candidate was absent from accepted history;
- exact payout, recipient, fee, Full-body hash and reserve spentness, checked again after at least 120 seconds.

Not demonstrated:

- the complete G5/G6 set: live archive/artifact-loss, malicious or divergent provider behavior, controlled reorg/rollback, all competing-branch variants, and future fee/resource liveness remain open;
- independence from C. Its validating-node history, UTXOs and chain assertions remain trusted; this is not a light-client proof or an attestation of C’s executable;
- trust-free setup. Single-party Groth16 setup and host integrity remain assumptions;
- anonymity, hidden amounts or private transfers. A1 is a finite same-owner covenant; amounts, scripts, recipients, outpoints and timing remain public;
- cryptographic correctness, an audit, production safety, mainnet readiness, permanent finality or post-quantum security.

## Public evidence and limits

The [evidence directory](../poc/a1/evidence/s0-trials-2026-10-08/) contains a newly constructed public summary and checksums. It includes selected transaction IDs, integer-sompi amounts, UTC times, software/artifact/body hashes and scoped outcomes. It includes no operator configuration, credentials, infrastructure bindings, wallet files, recovery material or private JSON exports.

Raw accepted histories and validation records remain retained locally. Hashes bind identifiers and bytes; the public summary is not a self-contained replay package or independent chain-acceptance proof. This report adds evidence without changing an invariant, ADR, protocol rule, or the outcome of any earlier failed attempt.
