# RAILGUN

**Reviewed: 2026-10-08.** Selected public V2 contracts, circuits and SDK files were read at independent pins. This is not a claim that every current deployment uses these revisions. No contract, circuit or wallet was run.

## Source facts: commitments, nullifiers and conservation

The SDK's [TransactNote][R1] derives a note public key from the master public key and randomness, and commits to note public key, token hash and value. The [join-split circuit][R2] binds the master key to spending-public-key coordinates and a nullifying key. Its signature covers root, bound parameters, nullifiers and commitments. Input membership, output value ranges and same-token balance equality are separate constraints.

The [nullifier circuit][R3] derives `Poseidon(nullifyingKey, leafIndex)`. The contract's [commitment storage][R4] indexes spent markers by **tree number and nullifier**. Thus copying only the hash formula without its tree/domain context would change replay semantics. Trees have depth 16 and roll over; known-root storage supports historical roots, while current nullifier checks still reject spent inputs.

The [logic][R5], [verifier][R6] and [smart wallet][R7] together bind chain ID, root, transaction parameters and unshield preimages before transferring assets. A membership proof alone would not establish withdrawal authorization or conservation. V2 token-specific integer limits are not automatically suitable for native KAS sompi.

## Discovery and recovery: P12 / P10

The [wallet scanner][R8] decrypts shield/transact data and checks reconstructed note hashes against accepted commitments. [V2 event decoding][R9] supplies Shield, Transact and Nullified data with tree positions; [UTXO-tree logic][R10] reconstructs membership and spentness.

**Interpretation:** recovery needs seed-derived keys, retained event ciphertexts, ordered commitments/nullifiers, chain authentication and circuit artifacts. A root plus current contract storage cannot replace old encrypted events. EVM receipt availability is an external history assumption; a Kaspa adaptation needs an explicit authenticated archive or independently retained equivalent after pruning. Viewing keys and scanned private data are sensitive even when they cannot authorize a withdrawal.

## Exits, fees and service policy

Unshielding releases publicly visible assets to a recipient bound by the proof and contract. Treasury shield/unshield fees in [smart-wallet code][R7] are distinct from broadcaster compensation. Official [broadcaster documentation][R11] describes paying the relay from shielded balances while the relay pays public gas. That can avoid exposing the user's public fee wallet; timing, relay contact and funding can still correlate activity. Self-broadcast exposes its gas-paying account.

Official [PPOI documentation][R12] describes list proofs and broadcaster acceptance policy. This is a dependency to investigate separately from smart-contract consensus validity, not evidence that exits remain permissionless when list/proof services disappear. The same documentation describes immediate unshielding back to the original shielding wallet through self-broadcast when PPOI is incomplete. That escape route has a public-address privacy boundary and was not exercised here. The SDK has a separate [POI layer][R13].

The inspected [proxy administrator][R14] has privileged upgrade authority. Study the accounting mechanics without importing that governance assumption into KPI or adding a privileged withdrawal path.

## Anonymity, batching and failure lessons

**Interpretation:** trees, assets, public adapters, input/output counts, withdrawals and traffic patterns delimit effective anonymity. Rollover does not imply a single unlimited set, and sharding may fragment it further. Join-splits amortize proofs over multiple inputs/outputs, but shared tree updates and nullifier conflicts remain. Permissionless proof generation must be distinguished from availability of keys/artifacts, RPC history and accepting relays.

Source tests include [join-split cases][R15] and a [cross-tree nullifier collision regression][R16]; they were inspected, not executed or treated as soundness proofs. The enduring risks are missed token/recipient/chain bindings, incorrect per-tree spentness, unavailable history and service filtering. No new current vulnerability is alleged by this review.

The [circuit license][R17] explicitly provides no license to other parties. Conceptual study is possible; importing this circuit code requires resolving rights. The Groth16/curve-based construction is classical and has setup assumptions; a Kaspa tag accepting Groth16 does not certify a particular RAILGUN circuit, key or deployment.

## Component assessment — provisional

| Building block | Potentially reusable | Adaptation needed | Risks | Still to prove for KPI |
| --- | --- | --- | --- | --- |
| Note / join-split relations [R1][R2] | Hidden balances with explicit authorized conservation | Native KAS, ranges, keys and circuit rights | Wrong asset; field wraparound; underconstraints | Integer-sompi conservation across private and public boundaries |
| Per-tree nullifiers [R3][R4] | Precise spentness and root handling | Pool/lane/version replay domains | Cross-tree collision or replay | Concurrent duplicate spends rejected in all domains |
| Encrypted event scanning [R8][R9] | Client decryption checked against commitments | Pruning-resistant authenticated Kaspa logs | Censorship; seed cannot recover missing history | Independent restore after all preferred indexers vanish |
| Merkle accumulation [R4][R10] | Append and rollover/witness mechanisms | Shared anonymity across state partitions | Fragmented anonymity; stale witness | Witness freshness and throughput without unsafe root shortcuts |
| Unshield and output binding [R5][R7] | Separate proof validity and asset release | Exact native reserve/fee/output constraints | Redirected funds; over-release | Permissionless native exit with no privileged bypass |
| Private relay fees [R11] | Relay funded from hidden balance | Native KAS quote/proof/fee lifecycle | Relay outage; public wallet or network linkage | Independent proving and fee payment under changing relay costs |
| PPOI service policy [R12][R13] | Lesson in separating policy and consensus | KPI's permissionless-exit requirements | Lists or services veto practical exits | Exit without default relay/list operators |
| Upgrade and setup boundaries [R6][R14][R17] | Explicit trust and code-rights accounting | Invariant-preserving migration and usable implementation rights | Privileged upgrades; compromised setup | No admin withdrawal; reviewed keys and safe version transition |

**Open hypothesis:** shielded fee transfers and event-based scanning may be useful patterns. Neither the V2 asset model, relay policy nor upgrade authority is selected for KPI.

[R1]: https://github.com/Railgun-Community/engine/blob/6e2614d53a106dd62abad91e7ce03ee4a3956138/src/note/transact-note.ts
[R2]: https://github.com/Railgun-Privacy/circuits-v2/blob/0aa2d13763a9fcfbb7b7ea9c02e004e71f1394bb/src/library/joinsplit.circom
[R3]: https://github.com/Railgun-Privacy/circuits-v2/blob/0aa2d13763a9fcfbb7b7ea9c02e004e71f1394bb/src/library/nullifier-check.circom
[R4]: https://github.com/Railgun-Privacy/contract/blob/36bcf5ed7cf94bfafb6e1a303e1832c769c16780/contracts/logic/Commitments.sol
[R5]: https://github.com/Railgun-Privacy/contract/blob/36bcf5ed7cf94bfafb6e1a303e1832c769c16780/contracts/logic/RailgunLogic.sol
[R6]: https://github.com/Railgun-Privacy/contract/blob/36bcf5ed7cf94bfafb6e1a303e1832c769c16780/contracts/logic/Verifier.sol
[R7]: https://github.com/Railgun-Privacy/contract/blob/36bcf5ed7cf94bfafb6e1a303e1832c769c16780/contracts/logic/RailgunSmartWallet.sol
[R8]: https://github.com/Railgun-Community/engine/blob/6e2614d53a106dd62abad91e7ce03ee4a3956138/src/wallet/abstract-wallet.ts
[R9]: https://github.com/Railgun-Community/engine/blob/6e2614d53a106dd62abad91e7ce03ee4a3956138/src/contracts/railgun-smart-wallet/V2/V2-events.ts
[R10]: https://github.com/Railgun-Community/engine/blob/6e2614d53a106dd62abad91e7ce03ee4a3956138/src/merkletree/utxo-merkletree.ts
[R11]: https://docs.railgun.org/developer-guide/wallet/broadcasters
[R12]: https://docs.railgun.org/wiki/assurance/private-proofs-of-innocence
[R13]: https://github.com/Railgun-Community/engine/blob/6e2614d53a106dd62abad91e7ce03ee4a3956138/src/poi/poi.ts
[R14]: https://github.com/Railgun-Privacy/contract/blob/36bcf5ed7cf94bfafb6e1a303e1832c769c16780/contracts/proxy/ProxyAdmin.sol
[R15]: https://github.com/Railgun-Privacy/circuits-v2/blob/0aa2d13763a9fcfbb7b7ea9c02e004e71f1394bb/test/joinsplit.test.js
[R16]: https://github.com/Railgun-Community/engine/blob/6e2614d53a106dd62abad91e7ce03ee4a3956138/src/merkletree/__tests__/utxo-merkletree-nullifier-collision.test.ts
[R17]: https://github.com/Railgun-Privacy/circuits-v2/blob/0aa2d13763a9fcfbb7b7ea9c02e004e71f1394bb/License.md
