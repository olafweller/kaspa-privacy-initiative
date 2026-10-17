# Adversarial second pass

AI self-review, not independent human review or cryptographic audit. Security
invariants are unchanged. No native funds, outputs, signing keys or services
were accessed. The full sequence has an execution profile, **not** an outer
proof; this limitation is part of the research conclusion.

| Question | Tested boundary | Remaining limitation |
| --- | --- | --- |
| Mint or release reserve? | Checked wallet sum and bounded proxy balance subtraction; rejected middle operation preserves balance. | No implemented note/ownership/membership/nullifier relation, native reserve or payout. The proxy counter is not a KAS ledger. |
| Replay twice? | Repeating one genuinely valid intent gets outcome 4; all native IDs remain in sequence. | Seen-intent set is finite-batch only, not current cross-batch/version nullifier state. |
| Executor invents invalidity? | No verdict field or optional assumption; actual receipt bytes are checked. Missing/replaced/reordered bytes fail fixed endpoint authentication. | Endpoint is an independently checked local fixture, not actual TN10 accepted-lane authentication. |
| Fake/unresolved receipt accepted? | Only canonical succinct encoding; disabled dev mode; trusted wallet image and SDK verifier context; SDK checks successful fully resolved claim. | No outer classification receipt was generated, so actual cryptographic enforcement of that program remains unqualified. |
| Malformed SDK data crashes? | Byte/count/exponent bounds, fixed codec, eight bounded/reduced control siblings, reduced seal words; directed guest controls and real-seal host mutations. | Tests are not a totality proof over all permitted encodings; the exact SDK/profile needs deeper review before deployment. |
| Bad operation consumes resources? | Receipt/operation/input bounds limit decoded data. Main run and same-size fast-rejection baseline measured. | 870.8 million cycles for three late-verification operations and 89.7% block transient footprint each. No economic denial-of-service policy is implemented. |
| Change recipient/domain/fee? | Intent binds every byte including output commitments and delivery records; journal mismatch or wrong fixed domain rejects. | Opaque synthetic delivery bytes do not establish actual encryption, recipient spendability or privacy. |
| Witness leakage? | Classifier input contains only public intents, receipts and native preimages; wallet arithmetic/preimage witnesses remain in wallet inputs. | Wallet inputs are deliberately public synthetic fixtures archived for reproduction, not production secret handling or client isolation. |
| Hash circularity? | Intent excludes receipt bytes; native v1 ID binds complete final operation. | Future vProgs/resource metadata, complete private fields and accepted-lane integration must preserve that structure. |
| Dependency failure/reorg? | Missing fixture bytes never become a false invalid-proof verdict. | No archive/DA guarantee, reorg recovery, independent N-user recovery, migration or legacy access is implemented. |

The native dimension fixture uses an explicit v1 compute budget and dummy
nonexistent UTXOs. Passing its dimension calculation does not imply valid
signatures, relay acceptance, a sufficient actual fee or a funded trial.
Do not infer production cryptographic correctness from green CI or SDK tests.
