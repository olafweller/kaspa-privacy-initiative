# Public native-value cycle — 2026-10-17 UTC

**Completed from Codex Cloud and the existing VPS: actual native deposit,
proof-backed credit/withdrawal, two TN10 settlements and confirmed native payout.**
This is temporary **public** test state. It establishes the tested backing,
authorization and interval-completeness properties, not privacy or a production
based app. [PR31](https://github.com/olafweller/kaspa-privacy-initiative/pull/31)
remains the earlier integration milestone at `6810058`; this is its separate
stacked [draft PR32](https://github.com/olafweller/kaspa-privacy-initiative/pull/32).
Neither PR was merged.

## Executed configuration

Sources and enforcement are in [MAPPING](MAPPING.md); commands and execution
locations are in [README](README.md). Guest/host-v1 source: `11906ef`;
host-v2/driver source: `c8562c5f4d956ccadf23034114483bcb405f78f1`;
public verification/audit tools: `d274b75`, completed accounting/finish source:
`a39fbb9`, full rent-entitlement audit `8ea98c2`. Full hashes, exact source-file hashes, upstream revisions and native
binary identities are in [runtime.json](evidence/runtime.json) and
[source manifest](evidence/source-sha256.json). The overall delivered version is
the draft's Git head; evidence commits do not change the executed guest.

- Guest image: `52c214c2a4789cb882ac7f4c25996bcba3e0693dec1c8c0c1c093f262dcc6cf0`.
- Official fixed lift-20 verifier; no development mode, receipt or redeem.
- vProgs `f9b84a863a7c7c20586a9cf947550475e894f72e`; compatible Kaspa dependency
  `01b532e8b553523216471682649693af92f0fd16`; current upstream master
  `f7d7877363fb97c2ec6871be0e8cbc351d44df10` was separately checked.
- Existing VPS node 2.1.0, `testnet-10`, synced, UTXO index, PID 43275 throughout.
  Existing root admin WSS terminal invokes localhost JSON RPC. No node restart,
  public listener, VPN or network infrastructure was introduced.
- Real CPU proofs ran in Cloud (four cores, 16 GiB); keys/signing/capture and
  finite detached systemd jobs ran on the VPS. No laptop execution dependency.
- Trial: `trial-2026-10-17T00-14-55-563Z-47c6d76b` under
  `/opt/kpi-pr31-cloud-20261017/native-value`.
- Lane: `6b2756b200000000000000000000000000000000`;
  lane key: `b7a69959c0c7389984390a6273dd50892b9ed697eb096faef0e08fe1f45cac30`.
- Covenant: `15596ff6d40ac3b83be9787b622db05d649d19d36c1ddee648e9e362f38bbe15`.

## Actual native transaction flow

The fresh user's app balance was zero; there was no seeded user claim. Its
transparent wallet was funded with 12 test-KAS: 10 for the deposit and separate
funds for native action fees. User and sponsor used different random keys; both
remain only on the VPS, outside the public trial archive.

| Confirmed transition | TN10 transaction ID |
| --- | --- |
| Fund user's native wallet | `07a63ceb71b52b7dc663f65394a129d1a48b9abd7c603b2e8d372b8297844fe8` |
| Activate lane (outside measured interval) | `e437249eedc646466a7ee16c2bb56dddf561ef55c853da54ef9a251152041597` |
| Bootstrap empty app state | `c914f4dfc89e0c20ecec009833ac7befc876bcf63f9b4bbca70828a6d2bd84e7` |
| Actual 10-test-KAS deposit to delegate reserve | `2ff3fac19ab657293aea9885e6efe28b474bd2db50e426a3579c439174885afb` |
| L1-accepted, app-unauthorized command | `40060b1b1921a8d7a1877b74a2c7e43d21927428c341a9c604c748c876833bdb` |
| Authorized 4-test-KAS withdrawal request | `63f273fede2629e4e26ebc8e287cd2023a5b4a5dc686a28625a51a7dca208c6f` |
| L1-accepted copied command, rejected by app | `9dfeb601a2f945bd48371552f306de0ca5c8d88f40880260a534f4d532ac2190` |
| Real prefix settlement: credit 10, reject unauthorized command | `5025d386522a734b5c780baca1725455b93267d0c2507cf6b4d7d94b7be0461b` |
| Real final settlement: debit 4, create exit permission | `1585391d16c3a0de7dd82c3f79621300b8116a5425c082c03200c81daba2b454` |
| Actual native payout and reserve change | `772897261ef2b6500a475b616b9636395c901e75ae09150d9403d12caa23239b` |

The native payout consumes **deposit transaction output 0**, not a sponsor
substitute. It pays output 0 to the authorized user's P2PK and returns output 1
to the same protocol delegate script. The spent permission had the actual
covenant ID. Payout was observed with ten selected-chain confirmations, followed
by recipient/reserve/claim queries. A final read-only check found both settlement
accepting blocks and the payout accepting block still selected-chain blocks.

Payout accepting block:
`264695195dcf8922ed437e15498612a92800001e76bb09b32b8f33d2be256fdf`.
The continuation remains 100,000,000 sompi under the same covenant ID and final
state hash `11e0060285b73a72ea132fb79f8e620c9ae586462b723f5d6db0800b90ca3cb8`.
The prior covenant inputs and paid permission are spent. These are actual node
observations, not merely successful local script execution or mempool admission.
They remain observations from one owner-operated validating node, without
independent node/operator corroboration.

## Exact backing and fees

All quantities below are integer sompi. The Python [audit](audit.py) independently
checks user-key/resource binding and balances from the resource bytes, hashes
both complete public states and all journal fields, reconstructs native IDs,
recomputes fees from funding entries and reconciles all four ending fund domains.
Its [executed result](evidence/audit.json) passes for all 120 original public files.

| Protocol stage | Spendable user balance | Valid unpaid claims | Native reserve | Check |
| --- | ---: | ---: | ---: | --- |
| Before deposit | 0 | 0 | 0 | 0 <= 0 |
| Deposit accepted, not credited | 0 | 0 | 1,000,000,000 | 0 <= 1,000,000,000 |
| Deposit credited by prefix settlement | 1,000,000,000 | 0 | 1,000,000,000 | equality |
| Withdrawal settled, not yet paid | 600,000,000 | 400,000,000 | 1,000,000,000 | equality |
| Native payout confirmed | 600,000,000 | 0 | 600,000,000 | equality |

The table tracks principal. Once the permission output exists, the recipient also
has an enforceable 50,000,000-sompi rent-refund entitlement. Including **all**
user entitlements, the unpaid stage is 600,000,000 spendable + 400,000,000 principal
claim + 50,000,000 rent claim = 1,050,000,000, backed by 1,000,000,000 delegate
value + the already-locked 50,000,000 permission output. After payout it is
600,000,000 against 600,000,000. The audit checks both ledgers; no uncommitted
sponsor/treasury funds are counted as backing.

The payout output is **450,000,000 sompi**: 400,000,000 principal (4 test-KAS)
plus the upstream permission mechanism's separately sponsored 50,000,000 rent
refund (0.5). It does not remove 4.5 from user backing. The remaining delegate
output is exactly 600,000,000. State-covenant rent of 100,000,000, sponsor funds,
and native fee change are excluded from user backing.

Ten confirmed transactions paid **194,256,000 sompi = 1.94256 test-KAS**:
prefix settlement 95,160,600; final settlement 95,252,000; payout 1,042,000;
other seven transactions 2,801,400. All six rejected native transactions paid
zero fees. Full per-transaction fee entries are in the audit and original requests.

The sponsor started with 999,432,038,000 sompi. Ending domains are sponsor
997,888,618,200; user native wallet 649,163,800; state rent 100,000,000; user
reserve 600,000,000. Their sum plus 194,256,000 fees equals the exact starting
amount. Legacy PR31 covenants are outside this new-cycle accounting.

## Lane bounds, completeness and progress

Legitimate checkpoints:

- Start: `5bfd34096be2a333adf1d95b55b65d4147ddfe787ac61d320906077940995301`.
- Prefix end / next start: `94b86adae86e5d2fc94dab1761e026efd4bae0ad9650b140ad74bfb6bce78972`.
- Final end: `7535227bf481646dd6ebf472d596feaa1e2586b78e4f2d7c5e3757a8dc78aa6c`.

The shorter prefix really settled while the accepted withdrawal/replay were
waiting. No inspected L1/covenant rule mandates the latest endpoint. That is an
allowed interval choice, not evidence of mandatory progress. The two final
intervals contain all four commands; failed app commands are provable no-ops,
not filtered out of lane commitments. Independent Python reconstruction agrees
on ordered IDs, lane tips and authentic seqcommits. Its legacy SHA-fold operation
count is zero because these are runtime payloads; it is used here for L1/lane
authentication, not as an independent monetary execution engine.

The omission input removes **the valid withdrawal**, retaining exactly the same
legitimate old state/tip, start/end witnesses and end block as the valid final
input. The remaining replay keeps the final last-touch score unchanged. There
is no mandatory count-to-two rule in the guest. A real succinct partial receipt
was generated and SDK-verified; its derived seqcommit differs from the real end.

Signed omission settlement
`18d10a5447bd3d5a1b67c2802bc8c070a7ccded30733d0a65054cba44545d0af`
was actually rejected by TN10 with:

> failed to verify the signature script: ZK Integrity: Verification failed

The same real node then accepted the full-input settlement. This closes the
scoped live cryptographic omission test missing from PR31. The builder's
counterfactual accessor is used only to measure the partial receipt's budget;
the node reads the real selected-chain seqcommit. This is neither a host count
check nor a failed proof-generation run presented as a node rejection.

## Negative test boundaries

| Case | Actual rejection layer / evidence |
| --- | --- |
| Wrong/missing native deposit SPK, foreign covenant, wrong user/lock | Application execution, reused runtime plus wrapper; Rust test. No native acceptance claim for these synthetic cases. |
| Same deposit credited twice, same output twice within one tx | Application execution; persistent `(txid,index)` and upstream consumed-output checks. Invalid state effects are not committed. |
| Withdrawal above balance; u64 overflow | Application execution, upstream checked-sub/checked-add; Rust boundary tests. |
| Sponsor command targeting user's balance | **Real proof-backed deterministic app rejection** of an L1-accepted command (`withdraw: lock not satisfied`), retained in prefix lane digest. |
| Copied withdrawal command | **Real proof-backed deterministic app rejection** of an L1-accepted replay (`prev_tx witness does not match outpoint`); same-ID replay also rejected by app state test. |
| Alter recipient while keeping owner signature | Native script verification; actual TN10 `e73225879b80c754e64d9b2c1462d991b423cca5d951c95f4e95a6d9a9628062` rejected with false stack entry. |
| Omit accepted valid withdrawal at unchanged real endpoints | Real partial proof **succeeds**; actual native ZK verification rejects the settlement as above. |
| Underpay principal/rent by 1 sompi, divert 1 sompi of reserve change, change payout recipient | Native permission-script verification; three distinct balanced TN10 variants rejected with `script ran, but verification failed`. Local native-engine counterparts also pass. |
| Spend paid claim/deposit again | Actual native UTXO validation rejects distinct transaction `0a4df8a0067d901466fafa2495b828fc629543441602599e5bd236efaf83be4a` as orphan where orphans are disallowed. Spent permission and exact successor reserve independently queried. |

All original rejection responses and signed transaction bodies/requests are in
[evidence](evidence/). No proving failure is counted as a native rejection.

## Genuine proof costs and retained operational failures

| Real receipt | Proof seconds | Maximum individual-process RSS (KiB) | Receipt / journal bytes |
| --- | ---: | ---: | ---: |
| Prefix | 452.894 | 9,580,192 | 223,930 / 352 |
| Final withdrawal | 450.216 | 9,587,516 | 223,930 / 352 |
| Omitted withdrawal | 440.451 | 9,576,956 | 223,930 / 352 |

All have one 1,048,576-cycle segment and the same fixed lift-20 control identity.
RSS is Linux RUSAGE_CHILDREN's maximum individual process, not summed simultaneous
memory. Profiles created no receipts. Each real receipt was verified in generation
and again with the public-only verification executable; all journal bytes also
match the independent audit. [Proof artifacts](evidence/proofs/) retain exact stats.

The original final batch profiled `[20,17]`, incompatible with the already funded
fixed lift-20 covenant. Before proving/settling, the operator moved the batch
pivot to the unauthorized-command checkpoint. Original inputs/metadata/captures
remain; both valid intervals and the omission now profile `[20]`. All commands
and the overall start/end remain. No verifier/guest check or funded identity was
changed and no transaction was rebroadcast.

An initial Cloud download raced that read-only resegmentation and obtained old
inputs. A missing shell `set -e` allowed an old-prefix proof to start after the
profile guard failed. Its own process tree was terminated before completion;
no receipt or transaction resulted. Original inputs/profiles and cancellation
reason are retained in [cancelled attempt](evidence/stale-copy-cancelled-proof.tar.gz).
Subsequent completed-marker/hash checks and fail-fast execution avoided repeating
it. This partial run is not a completed proof-cost measurement or protocol defect.

## Limits and smallest next step

**Backing:** demonstrated for one public 10/4/6 cycle, including unpaid claims.
**Authorization:** demonstrated through the tested runtime/owner signature and
native permission conditions. **Completeness:** demonstrated for these fixed,
authentic intervals with an actual native omission rejection. **Payout:** actual
protocol reserve input spent and native recipient/change UTXOs confirmed.

**Progress/recovery remain open.** The retained guest has `MAX_SPAN=100` relative
to old lane last touch, lacks general expiry/long-span processing, and has a
fixed image/control form. Both intervals were captured before proving. Remaining
six test-KAS are backed, but their continued/independent withdrawal after a long
idle gap is **not established** by this artifact. There is no admin rescue or
upgrade path. Do not report that balance as independently recoverable or this
experiment as production spendability. This is a limitation of our bounded
adapter, not an established missing Kaspa guarantee.

Next reuse the existing upstream per-batch/aggregation and compatible recursive
proof trajectory for long spans and executor takeover, in a fresh instance.
Then test reconstruction and continuing/withdrawing without the original executor.
Do not rebuild general lane infrastructure. Also unproven: multiple independent
users/provers, automatic reorg rollback, pruning/archive-loss recovery and privacy.
All accounts/amounts remain public. See [adversarial review](ADVERSARIAL-REVIEW.md).

## Evidence corrections and validation

PR31's rounded acceptance nonces were re-extracted losslessly from the original
RPC strings, including six derived public-archive members. Raw RPC members and
all binary proof artifacts are byte-identical; full provenance, prior hashes and
regression checks are retained. No original PR31 experiment was repeated.

Three new Rust tests cover account rejection cases, native permission mutations
and owner-signature binding. Exact nonce/u64/sompi regressions, independent lane
reconstruction, SDK re-verification, actual TN10 negative/positive execution and
independent monetary/journal/file audit pass. Code/Documentation CI passed at
`c8562c5` and `d274b75`; subsequent head checks are reported on PR32. CI never funds or broadcasts.
