# Adversarial second pass — local private-note experiment

This is an implementation self-review, not an independent cryptographic audit.
The scope separates real R1CS/Groth16 constraints, recipient checks and a local
unproved state kernel. No failure of a resource limit counts as a valid rejection.

| Attack | Enforcing layer and exercised evidence |
|---|---|
| Create value / wrap a sum | Circuit uses bounded UInt64 limbs and field equality below Fr; altered conservation/output commitment and repaired-binding overflow fail. Valid 2/u64::MAX cases pass. Kernel reserve/batch overflow is checked. |
| Spend without authority or membership | Real constraint-system ownership, secret, path, domain and nullifier mutations fail; actual valid spend proofs pass. Viewing keys alone do not meet the spend-secret relation. |
| Spend twice with distinct valid proofs | Competing proof has different outputs but the same note-derived NF. Kernel accepts the first, rejects the competing proof/replay at an allowed old root after a batch boundary, and preserves state. |
| Replace verifier or reduce a hash modulo Fr | Separate process pins canonical VK SHA256; state pins the same verifier; wrong expected identity fails. Statement bytes pack in <=248-bit limbs, injectively, with constrained bytes. |
| Smuggle malformed or false proof | Actual decoder rejects wrong subgroup, identity point, unknown/trailing operation data. A canonical subgroup-valid false pairing is rejected by real Groth16 verification, then the next valid proof still applies. |
| Change payload/intent | Eight proof/statement/payload mutations fail; ciphertext digests are recomputed from actual payload bytes. Canonical binary round trips cover every archived operation. Review controls change Bob’s nonzero exit destination and recompute a modified ciphertext digest; both fail the actual Groth16 equation. |
| Credit and recover the same deposit | Both real proofs can independently be valid; the shared current pending record permits only one. Credit-then-recovery and recovery-then-credit reject atomically. |
| Release reserve before or to wrong payout | Pending exit remains a liability. Exact amount/destination and unique nonzero native-output reference are required by the fixture API; diverted/underpaid/duplicate/reused output facts fail without changing state. **Native authentication itself is unimplemented.** |
| Partial commit after tree capacity/duplicate error | Candidate-state clone commits only after proof, NF, append, lifecycle and backing checks. Duplicate/capacity/rejection controls compare the full state hash. |
| Give Bob bad or someone else's encrypted note | Recipient checks decryption, exact encoding/domain/owner/incoming key, positive amount, rebuilt commitment, accepted leaf and current spentness. Corrupt and other-recipient ciphertexts fail. Encryption correctness is not circuit-proved; a sender may burn their own output. |

## Privacy, liveness and remaining assumptions

- Spending and incoming keys, note openings and Merkle witnesses stay in the local
  wallet process. Persisted evidence is whitelisted public statements, ciphertexts,
  proofs, public VK and measurements; no witness is sent to a remote prover.
  This experiment does not test secret-memory zeroization, side channels, a
  compromised wallet/administrator or independent-machine backup recovery.
- Incoming/owner addresses must be authenticated outside this prototype. A
  malicious address replacement can divert a payment. The concrete SHA/HMAC
  composition needs independent review; no mature protocol's security theorem
  transfers simply because its engineering lessons were followed.
- One setup participant can retain toxic waste. The local setup is not a
  production ceremony, and no funds may rely on it. Public proving-parameter
  distribution and retention are also untested.
- Public data contains output commitments, roots, nullifiers, ciphertexts and
  deposit/exit boundaries. A tiny four-leaf workload and public 10/4 on/off-ramp
  amounts correlate users. No effective anonymity, metadata protection or
  receiver unlinkability result is claimed.
- Current nullifiers survive a logical batch boundary. A production state loader,
  crash persistence, canonical-chain reorg handling, anchor expiry and verifier
  migration are not implemented. Losing history or mixing domains is not an
  acceptable recovery path; the future adapter must authenticate complete state.
- Losing ciphertext/commitment history prevents recipient discovery and recovery.
  The local public fixtures are available for replay but no independent DA or
  recovery service has been qualified. Failure must halt, not authorize a payout.
- The executor still supplies test native facts. Replacing this interface with
  accepted native inputs and exact permission/output facts is a required next
  gate, followed by a genuine new outer receipt and real TN10 payout rehearsal.
  PR43's older receipt cannot certify these state transitions.
- No privileged administrator withdrawal, new token, mainnet endpoint, paid GPU
  attempt or native signing path is introduced. Exit/refund authority remains
  the actual proof relation; the fixture API must never be exposed as an oracle.
