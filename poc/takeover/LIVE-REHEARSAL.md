# Confirmed recursive TN10 rehearsal

The fresh public-account rehearsal completed on 2026-10-17, including confirmed
native payout. The owner authorized proceeding after local review `35b84c1`.
Only test-KAS was used. Older funded experiments and the normal node service
were not changed. This is one owner's node and retained public archive, with no
privacy, independent-operator, true-expiry or production-security claim.

See the [verified result](evidence/tn10-rehearsal.json) and
[public evidence archive](evidence/tn10-rehearsal-artifacts.tar.gz).

## Confirmed result

| Observation | Result |
| --- | --- |
| Native deposit and recursive credit | 1,000,000,000 sompi (10 test-KAS) |
| Empty-state reconstruction | Matched checkpoint root, tip and real state UTXO |
| Withdrawal after original executor exit | 400,000,000 sompi (4 test-KAS) |
| Gap from observed stop sink | **175 blue scores**, exceeding 100 |
| Gap from stable stop anchor | 212 blue scores |
| Gap since preceding lane activity | 4,579 blue scores; native lane still active |
| Confirmed native recipient output | 450,000,000 sompi: 4 principal + 0.5 permission-rent refund |
| Remaining native reserve and app balance | Both 600,000,000 sompi (6 test-KAS) |
| Remaining unpaid permission claims | Zero; payout permission spent |
| State-covenant rent, excluded from backing | 100,000,000 sompi (1 test-KAS) |
| Actual fees across nine accepted transactions | 193,850,800 sompi (1.938508 test-KAS) |

The observed sink score was 587339859 when the stop operation first read a block;
the stable anchor was 587339822. Withdrawal acceptance was at 587340034. Using
the actual observed sink prevents the anchor's confirmation lag from inflating
the reported idle gap. Raw stop RPC and the arithmetic are retained.

The final read-only audit rechecked the selected-chain accepting blocks of all
nine transactions and exact sponsor, fee-wallet and user balances. They were
995,388,210,600, 957,393,000 and 649,163,800 sompi respectively. Accounting separates
principal, reserve, state rent, refunded permission rent and sponsor fees.

## Native transactions

Trial: `trial-2026-10-17T08-35-17-858Z-20ebc367`.
Covenant: `4a441ad493e4553a2db328eedf5b06198d1931e3733fcec0407266f3d7515e20`.

| Stage | Confirmed transaction ID |
| --- | --- |
| Fund fee wallet | `abb14f3630d67d9357ab4f805353d583cef7db7febe8e66b8302244a5cbda6ac` |
| Fund user | `57d42a9b352f2061ff99844a159b1ec20eef62c30648f1f1b9188b72df7382a5` |
| Seed lane | `b2bc6646a5af40db15f498d55fe512c5682baa1e1aca5307056d5ff2cc2672c9` |
| Bootstrap | `c54b01db9b1f6dc6c2d8a309e12a01bb1e0254d34ab1a40deda0e61c9eb0b0c5` |
| Deposit | `99841e1d44764deb8ab7411df629391f67bd2e3a0f785b0c267d2405aeb8b632` |
| Recursive deposit checkpoint | `b8298b47eef586965dcc23883c835f9f67add0803f1e461b2b26614b16eda489` |
| Authorized withdrawal request | `2e803f6fffbb30ebb4d5d85531212cd85742a084b14d530311ed0fbc0b4226b3` |
| Recursive final settlement | `38262de73d7e86022f0be8c308e5fc6d37e98c87c6bb92b668ca18ca1cc28408` |
| Native payout | `d0d4122e3b1166878aa47f4077ceff955f5a0c444272862425cb0490ca1f5910` |

## Reconstruction and enforcement

The finite preparation/checkpoint processes exited. A separate clean Cloud
directory replayed public prefix capture from empty state, importing no original
account-state file. It matched the live checkpoint UTXO, covenant, script, state
root `40143c69fd9614953fa83da551e2578fe3e900afa58b017864f3fb36467befd6`
and lane tip `8bf07b6fdf514587e4273df48ea981d0706ef4c5485313a6579f1077da71b6f0`
before the new withdrawal was published.

The recent stop anchor's authenticated unchanged lane entry bridges the idle
period without fetching thousands of unrelated blocks accumulated during prefix
proving. Immediately before withdrawal publication, the observed lane tip and
last-touch score still matched that stop record. The complete catch-up interval
and an interval omitting the withdrawal used the same actual final endpoint.
This is retained-public-data replay on the same infrastructure, not recovery
from missing history, independent verification or a stopped Kaspa node.

The live node rejected five deliberately invalid submissions:

- Omitted withdrawal settlement: native **ZK Integrity: Verification failed**.
- Underpayment, reserve diversion and recipient substitution: native signature
  script verification failed for each balanced variant.
- Distinct payout replay: orphan/missing-spent-input rejection after the valid
  payout consumed the permission. This is an input-liveness rejection, not a
  second proof-verifier result.

The valid settlement and payout then matched the native UTXOs and committed
journals. Local proof execution also retained wrong-anchor, missing/wrong inner
receipt and expired-lane rejection checks at their actual enforcing layers.
Native expiry remains rejected by the guest; this trial never crossed expiry.

## Proofs, sources and operational observations

Eight real succinct receipts were generated without development mode: three for
the deposit checkpoint, two for the omitted-input control and three for the final
withdrawal. The measured jobs took 382.26, 181.37 and 530.57 seconds respectively,
18.24 minutes combined, with peak individual-process RSS 4,820,948 KiB (4.60 GiB).
All jobs exited zero. Aggregate receipts resolve their assumptions and retain the
pinned official resolve control ID. The source manifest records exact host,
builder, prover, program and source hashes. Guest programs are unchanged from
the verified local build; the transaction/batch/aggregate implementation remains
based on pinned vProgs `f9b84a8`, Kaspa `01b532e`, RISC Zero 3.0.3 and kernel
v1compat 2.2.2.

The omission leaves an empty batch. A host-only applicability fix runs the
wrong-transaction-receipt control on nonempty batches, which have transaction
assumptions. No guest relation, verifier pin or funded covenant was weakened.
Seven Rust adapter tests passed. Fast checks passed 81 Python cases (two skips),
13 Node tests, exact-u64 RPC checks, source syntax and documentation checks.

The first final read-only accounting script incorrectly treated the RPC UTXO
response object as an array and stopped before assertions. Its raw responses and
failure log are retained. Version two sums the response's `entries` array and
completed all reconciliation assertions. No financial stage or broadcast was
repeated to fix this audit script. Both source hashes are retained.

All broadcasts have a write-once intent and raw RPC record. Transport errors
cannot count as rejection; no automatic mutation retries are performed. The
node remained synchronized on testnet-10 v2.1.0 with UTXO index. Keys were created
and used only on the VPS, outside the public trial directory. Evidence collection
verified all 89 public VPS files by size and SHA-256 and matched each deployed
aggregate receipt to its Cloud proof output. The archive contains no wallet keys.
Host `complete.json` reports describe local proof verification and therefore say
`actualTN10Settlement: false`; the subsequent confirmed native submissions and
read-only reconciliation establish the separate live result.

## What this establishes and what remains

This instance completed the repository's full rehearsal path: native deposit,
recursive credit, executor exit, idle gap beyond the old 100-score adapter bound,
empty-state public replay, newly authorized withdrawal, real recursive settlement
and confirmed native payout. The final native reserve equals the remaining
public account balance, with no unpaid claims or privileged rescue path.

Adversarial review keeps the boundaries explicit: old state/inner receipts and
fixed-endpoint omission must fail verification; permissions and consumed inputs
prevent the tested duplicate payout; public amounts/owners remain visible;
missing history or prover can halt progress; chain reorganization causes a halt,
not an implicit retry. This same-node rehearsal is a canonical-chain observation,
not a general reorg recovery test. The separate fee signer funds liveness but
has no new privileged reserve withdrawal path.

True lane expiry/reset, unavailable/pruned archives, an independent operator and
node, confidential state, scalable scheduling and mandatory progress remain open.
The six-test-KAS reserve is still in this test instance. No further trial is
running and this used identity must not be rebroadcast. These results do not
select a production architecture or close RFC-0001.
