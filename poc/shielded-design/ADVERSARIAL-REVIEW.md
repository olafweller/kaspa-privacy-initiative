# Adversarial second pass — local design package

AI-assisted source/model review, not independent human or cryptographic audit.
All security invariants remain unchanged. The complete private circuit and funded
native integration are deliberately unimplemented, not implicitly qualified.

| Risk | Check / result | Remaining boundary |
| --- | --- | --- |
| Mint/inflate/overflow | Input/output/fee equation, strict integer/range and aggregate overflow checks; seeded value vectors | Ideal proof oracle, not a real shielded circuit. |
| Spend twice | Membership under an old root is allowed, current nullifiers reject a second spend within/across batches and within one operation | Stable economic identity must survive all future accepted encodings/versions; no migration implemented. |
| Duplicate outputs | A valid model statement trying to append the same commitment twice is rejected before spending inputs | Final circuit/commitment uniqueness rules require review. |
| Owner/view key confusion | Separate incoming/spending keys; view-only holder cannot authorize; receiving encryption-key substitution fails address signature | Model address authentication is not the final wallet/key design. |
| Redirect output or fee | Public statement mutation breaks model proof binding; fee recipient/amount/replay checked | Real wallet proof must constrain the complete intent/ciphertext/exit/fee relation. |
| Debit mistaken for paid exit | Principal liability retained until exact payout; rent is separately funded/locked/refunded; payout amount/recipient/change/replay tests | Native private relation/payout not implemented. |
| Create permission rent from nowhere | Explicit external rent funding required; unfunded exit rejects atomically, with a conserved rent ledger | Model external funding stands for actual native validated inputs in the later trial. |
| Funded invalid deposit loses owner claim | Pending liability retained; authorized retry or refund consumes it once; bad authority/refund-credit races rejected | This is a model requirement, not a feature of the older funded delegate script. |
| Executor silently skips | Host verdict ignored by model; actual compatibility adapter rejects a host skip request; every model rejection remains recorded | Actual recursive missing/wrong proof aborts, not a proven invalid no-op. This is an explicit blocker. |
| Fake inner receipt / missing assumption | Real local missing/wrong-journal controls abort; changed wallet journal fails SDK; successful aggregate resolves the wallet through all layers | Profiles alone are not cryptographic verification; ordinary invalidity-verifier path not implemented. |
| Self-referential native ID | RFC separates intent hash from receipt serialization and derives final native ID outside wallet proof | The measured old native ID fixture does not implement a new proof-carrying lane payload. |
| Leak selected note/values | Model public transfer has no input commitment, owner, randomness or path/index; fixed-size encrypted note encoding | No ZK/anonymity/side-channel claim; test harness knows synthetic witnesses. |
| Bob cannot recover delivery | Local authenticated-data scan and commitment/owner checks succeed; corrupt/missing records never create a spendable balance | Retention, query privacy and independent shutdown recovery are open; a root cannot reconstruct missing history. |
| Dependency/reorg disappearance | Design requires explicit retained artifacts/data and canonical state; no admin fallback | Model has no general rollback, arbitrary expiry, archives or network failover. |

The local compatibility guest adds a valid preimage/value assumption to the old
public deposit relation. It does not bind an implemented private note transition
to public backing. The result is evidence of composition/pinning compatibility,
not permission to advertise an end-to-end shielded payment or fund the proposal.

Review decisions are the complete private statement/formats, enforced invalidity
outcomes and cost, proof/intent availability and native payload budgets, and the
authenticated deposit credit/recovery path. No private-payment issue is closed
merely because these model tests and four local proofs pass.
