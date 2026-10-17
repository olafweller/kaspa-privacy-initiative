# Local review of the recursive public-account adapter

Date: 2026-10-17. Owner-authorized local development/review resumed after the
historical pause. New TN10 transactions remain outside this review.

Status: local review passed, including the full real recursive proof chain and
fixed-captured-anchor native script verification. No new TN10 trial was run.

## Corrections

- Preparation decoded `smtProof` as a hex string. The retained native JSON RPC
  responses contain byte arrays. It now uses the upstream typed RPC response.
  The first actual preparation run exposed this; a successful host build had
  not tested that path.
- Preparation now retains the authentic captured endpoint commitment. The
  bundle runner checks the native script against that fixed commitment as well
  as the derived one and a deliberately wrong one. A synthetic accessor returning
  only the prover-derived commitment cannot demonstrate omission resistance.
- The native builder rejects a withdrawal previous-output index outside u32
  instead of truncating it. Coinbase-maturity addition and fee multiplication
  use checked integer arithmetic. These are builder hardening changes, not
  claims of a demonstrated node/consensus vulnerability.
- Real execution rejection details are retained for missing inner receipts,
  wrong images and unsupported expiry. These are execution-layer controls,
  separate from native script rejection and actual node acceptance.
- A proof-free command reverifies the imported gate's receipts with the SDK and
  native engine and rejects a changed journal in both checks. Host wrapping,
  guest rebuild and offline retained-capture reproduction are documented.
- The Rust CI matrix includes this workspace; fast checks parse its Python code.

## Native tests and historical inputs

Seven adapter/builder Rust tests pass. They cover native ID/lane/preimage,
previous-state binding, deposit credit and replay, malformed/foreign/overflow
no-ops, authorized withdrawal and exact claims, overspend/bad witness/replay,
context/order/image/receipt callback contracts, aggregate state/tip/score/lane/
covenant/image continuity, permission payout mutations and native signature
binding. Receipt callbacks are explicit test doubles, not proof verification.

The unchanged native-value regression suite's three tests also pass. Fast checks
exercise 81 Python cases (two existing skips), 13 Node cases, lossless JSON/u64
handling and exact reconstruction of prior RPC derivatives.

The prepare executable and retained native validator replay the original
`prefix2` and `final2` public captures. The resulting application state equals
the retained PR32 state exactly as structured data: initially zero, then
1,000,000,000 sompi spendable, then 600,000,000 sompi spendable plus the
400,000,000 sompi exit claim. State/tip continuity between intervals matches.
Omitting an accepted transaction changes the derived commitment against the
same endpoint. Altering a payload while preserving its claimed native ID fails
native capture validation. The repeatable harness is [check_retained.py](check_retained.py).
Omission is checked during preparation. The real proof run uses the complete
interval; its wrong-anchor script control is separate from generating a new
omitted-input proof. A newly proved omission bundle is not part of this review.

The combined interval is a documented derivative of those two contiguous
historical captures, not a newly fetched node response. It has 55 selected-chain
blocks, four lane transactions and four active batches. Original compressed
captures remain unchanged on main. No privacy or independent-node claim follows.
The historical withdrawal was already paid in PR32; replay here creates no new
native entitlement or payout.

## Real recursive proof result

The full combined interval completed with exit code 0: four transaction proofs,
four batch proofs and one aggregate proof, all real succinct receipts. Every
receipt passed SDK image/journal verification; every guest journal matched its
prepared bytes. Development mode was absent. The aggregate resolved four batch
assumptions and used the official resolve control ID
`53a7b23d07f99e5d5685e85874f5181e8486aa267a0ae607ffe9ba47c8bdda4a`.

The local native Kaspa script engine accepted the aggregate with the fixed
commitment from the captured endpoint and rejected a deliberately wrong one.
It consumed 25,006,924 script units. Eleven separately recorded execution
rejections cover missing transaction receipts (four), expired-lane flags (four),
missing batch receipts, a wrong batch-image assumption and a wrong transaction-
image assumption. These have actual execution error details, not inferred
protocol rejection from a failed build/start.

Whole run: 1,635.358 seconds (27.26 minutes), maximum individual-process RSS
4,820,868 KiB (about 4.60 GiB). Aggregate proof: 271.645 seconds, one 262,144-cycle
segment, 352-byte journal. This remains local script/proof evidence with a local
accessor; no full node economic validation, current chain observation, actual
settlement or new payout was performed. The 201-score gap test is synthetic;
the real historical interval has 55 blocks and is not the planned long-gap trial.

The [machine-readable result](evidence/local-review.json) and
[artifact archive](evidence/local-review-artifacts.tar.gz) retain prepared inputs,
rebuilt programs, receipts, journals, source/prover hashes, profiles, failure
records and selected logs. The final capture harness produced byte-identical
proof inputs to the ones actually executed. See [evidence notes](evidence/README.md).

## Source and artifact reconciliation

The uploaded archive's 79 inventory entries matched their sizes and SHA-256
hashes. The original work is committed separately at `b4cb2bb`; ignored original
logs/programs and the exact executed old gate binary remain preserved locally.
The imported real empty-batch gate receipts reverify successfully and use the
official resolve identity. This gate still has zero user transactions and no
actual TN10 settlement.

All three guests were rebuilt from the current sources with the hash-checked
PR31 official toolchain (guest Rust 1.97.0-dev, host Rust 1.91.0). Batch and
aggregate programs reproduce byte-for-byte. The transaction program differs in
exactly two bytes, the panic-source line entries for the assertions now at
`common/src/lib.rs:43` and `:78` (previously 30 and 49). The import therefore did
not contain the exact formatting used by that earlier transaction build.
The new transaction program/image is used for the new proof path; the old bytes
remain intact. No old funded covenant is repinned.

New transaction image:
`50e554e2ec71fa74ac6753a55ebc467d110259b805e10ccad75da2422052d290`.
Batch image:
`fac3707f1e6bf1c5363a2b968545bc5c361934a48a376b8083d4c14247a61f70`.
Aggregate image:
`14bedaace438fe568000405a947909bcdd7df82e8458bc3a87e6d85bdfdab166`.

The new execution snapshot records 50 relevant source/lock/manifest hashes,
host-binary and r0vm hashes, compiler versions and all program hashes. This is
local build provenance, not an independent reproducible-build audit.

## Adversarial second pass

| Concern | Enforcing layer / evidence | Remaining boundary |
| --- | --- | --- |
| Fabricated/repeated credit, overflow | Reused native deposit relation; new adapter no-op/replay/overflow tests | Public coarse state only; no private-note model |
| Unauthorized or repeated withdrawal | Reused witness/action relation; exact claim/replay tests; native signature test | Owner keys and native accepted-input validation remain essential |
| Wrong prior state | Whole-state hash in the one resource; reference SMT batch verification; negative test | Host state JSON alone is not authenticated until tied to covenant UTXO |
| Wrong batch continuity | Reference aggregate checks state/tip/score/lane/covenant/image; negative tests | No new independent aggregator audit |
| Missing/wrong proof | Native test callback contracts; real guest execution controls in bundle run | Passing callbacks alone establish no cryptographic property |
| Omitted accepted activity | Native reconstruction and fixed endpoint; bundle native script fixed-anchor check | A new live long-gap omission/payout trial remains unexecuted |
| Reserve diversion | Reused permission/delegate scripts; balanced underpay/reserve/recipient rejection tests | Actual fresh settlement and payout still need a complete TN10 rehearsal |
| Expiry, reorg, missing dependencies | Expiry guard in batch guest; fail on unavailable/invalid witnesses | True expiry/reset, pruning recovery and independent operators remain unsupported |
| Privacy leakage | All balances, keys, commands and claims are public | No privacy, anonymity or confidential-state claim |

## Next boundary

Local checks do not satisfy the repository's complete-rehearsal requirement.
A fresh TN10 rehearsal must still bind the new program images to the actual
bootstrap/UTXO, confirm deposit, stop the original executor, measure a gap greater
than 100 blue scores below native expiry, replay public data in a clean process,
settle the real recursive proof and confirm native payout. The old funded
instances and PR32's six-test-KAS balance are untouched. No project VPS job,
wallet, funding, broadcast or node restart was performed by this local review.
Only native v1 transaction preimages are supported. An unsupported native version
halts this experiment; it is not treated as a supported application no-op.
