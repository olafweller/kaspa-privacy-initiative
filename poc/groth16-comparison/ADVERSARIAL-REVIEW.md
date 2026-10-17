# Adversarial second pass

AI self-review, not independent human audit. All security invariants are unchanged.
The classifier did not complete its valid-invalid-valid execution budget; no
outer receipt or native privacy payment is claimed.

| Risk | Enforcing/checking boundary | Remaining gap |
| --- | --- | --- |
| Weaken statement to get speed | Same SHA-256 preimage/value/full-intent hashes and 96-byte journal; genuine R1CS/proof tests | Small predicate is not ownership/membership/nullifier/native backing. |
| Field-wrap inflation | Four 64-bit values, positive input, sum in Fr below its modulus; max/overflow tests | Exact wallet predicate only, no complete economic ledger. |
| Change public fields/delivery | Complete intent SHA-256 and original journal constrained; actual altered-statement proofs reject | Opaque records do not establish actual encryption or spendability. |
| Accept wrong-subgroup proof | Standard checked canonical decoding, actual outside-subgroup G2 test in guest | No independent formal totality or cryptographic audit. |
| Malicious prepared parameters | Public recomputation from checked VK; both static and compressed bytes compared; compiled program image pins them | Setup/program selection remains a trust boundary; not a production ceremony. |
| Skip static point checks unsafely | Only immutable prechecked constants load without repeated validation; untrusted operation points remain fully checked | Caller must verify the exact expected program and parameter identity. |
| Executor invents rejection | No host verdict/optional assumption; root binds actual operation/proof bytes; five expected guest authentication controls | Local fixture, not accepted TN10 ordering; full valid sequence exceeds budget. |
| Replay or partial mutation | Counter updates only after code 0 and current intent/balance checks | Full valid/replay/continuation guest runs are not qualified; finite intent set is not economic nullifiers. |
| Hide resource failure | Exact expected assertion matching; cycle error remains unexpected/budget failure; watchdog exercised | No outer proof, full cycle/segment/proving-time measurement unavailable. |
| Witness leak | Only public intent/proof/preimage enters classifier; wallet fixtures are explicitly public test data | No independent client isolation, scanning, archive or recovery experiment. |
| Dependency/setup loss | Verification artifacts need VK/proofs/program, not the 90.3 MiB proving parameters | Future proof generation needs retained parameters; real protocol distribution/legacy/recovery is open. |

No wrong proof was converted to an accepted one to obtain a benchmark. No new
native broadcast, reserve path, administrator key, production primitive or
operator network is introduced. Monetary costs and effective anonymity remain
unmeasured. Budget exceedance is not evidence that all Groth16 implementations
or larger explicitly reviewed research runs are infeasible.
