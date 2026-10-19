# Adversarial second pass — 2026-10-19

| Question | Enforcing check and result / remaining dependency |
|---|---|
| Mint value by changing snapshot, missing history or spentness? | Independently expected roots, canonical bytes and exact inter-batch prior state; CLI rejects omitted/reordered/duplicate history and altered/root-substituted state. A root obtained from the same untrusted provider is insufficient. |
| Restore someone else's wallet or redirect exit? | Trial-decryption + note/owner/commitment validation, fixed VK, real EXIT proof, current nullifier, recipient derived from user's native key. Unrelated wallet cannot exit; destination mutation is cryptographically rejected. |
| Spend a nullified claim twice? | Ledger checks current nullifier; re-admitting the saved exit against final state fails. Native replay requires exact permission/reserve UTXOs and eventual consensus spentness. No new TN10 replay claim is made. |
| Drain more reserve or consume permission partially? | Terminal native prefix pins exact reserve/outpoint/amount, 3 inputs / 2 outputs, lane, sponsor separation and no covenant/delegate outputs; upstream permission verifier enforces principal/refund, recipient and terminal Merkle consumption. Thirteen correctly re-signed mutations fail with specific semantic script errors, not resource/build failures. |
| Wrongly book a native-valid sponsor top-up? | Native acceptance and local reconciliation both accept it; only authorized principal is subtracted. Exact-reserve removal leaves zero liabilities, with state rent excluded. |
| Lose original services? | Local subprocesses replay from public inputs and user backup without network services; parameters, history and fresh native checkpoints must remain independently available. Physical shutdown/independent administration are untested. |
| Stale or reorganized chain? | Offline root equality does not select latest canonical state. A future spend requires fresh native lineage/UTXO/selected-chain checks and new proofs; no automatic rollback, stale-root relabeling or reset is implemented. |
| Leak secret witnesses? | Only receive address and public wallet operation/payload leave user process. Fresh public fixture publication is allowlisted; no historical live backup/key is used. Local balance output is private to the wallet user. Same-host root/operator still controls the host. |
| Introduce privileged withdrawal / hidden upgrade? | No rescue key or alternate signature authority. Old guest/scripts remain byte-unchanged and still reject the exact-reserve exit. New host-only policy is not a live contract, migration or proof-backed permission issuance. |
| Treat fixture acceptance as consensus acceptance? | Explicit synthetic permission UTXO/native context and host-only tagged claim. Actual outer proof, authenticated issuance, replacement-service TN10 execution and every-user payouts remain open. The fixture cannot satisfy I-5/I-10 alone. |

The terminal native change does not require implementing any curve, pairing,
subgroup, encryption or new hash primitive. Upstream cryptographic/script bodies
are reused. Archive readers are not added; the historical `final_backup.py` and
all PR54 evidence remain unchanged, and future archive consumers must reuse the
existing bounded reader rather than that historical one-shot helper.


PR55 targeted review correction: shared receive data now has a four-field
allowlist with no native payout key. Bob's native destination is obtained only
from his later public EXIT result and checked against its proof-bound payload,
operation ID and prior root. Historical code-workflow bytes/hash checks are
preserved, with CLI coverage moved to a separate workflow. No crypto, native
policy, guest, setup or statement is changed. Address reuse during future exits
and network/amount/timing correlation remain unsolved privacy considerations.
