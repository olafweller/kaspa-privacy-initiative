# A0: upstream integration evidence

**Reviewed:** 2026-10-03. **Status:** source-grounded integration findings; see [A0 experiment results](poc-a0.md) for the checks actually executed. This document does not establish acceptance by a live TN10 node. Candidate A remains experimental and ADR-0001 remains proposed.

## Source snapshots

The checked-out default-branch heads still match the repository's October 2 research snapshot:

| Repository | Exact revision | Relevant source |
| --- | --- | --- |
| Rusty Kaspa | `01b532e8b553523216471682649693af92f0fd16` | [v2.1.0 manifest][manifest], [TN10 parameters][params], [script engine][engine] |
| Kaspa docs | `0ac77d043a802fc8196abfd5812ac2afbd97a2b9` | [Inline ZK][inline] |
| KIPs | `e4ae2332117b5cb68bd6188e065ef885b6d17939` | [KIP-16][kip16], [KIP-17][kip17], [KIP-20][kip20] |

Rusty Kaspa requires Rust >=1.91.0 and edition 2024. Its manifest pins the Arkworks BN254/Groth16/relations/serialization family to 0.6.0. The RISC Zero verifier dependencies include `risc0-binfmt`/`risc0-zkp` 3.0.4, `risc0-core` 3.0.1, and recursion 4.0.4. Experiment-specific dependency resolution belongs in its Cargo.lock.

The node code is [ISC licensed][license]. It is used as an external pinned dependency; this research document does not copy or relicense its implementation. Original KPI documentation/code remains Apache-2.0. Dependency and transitive licenses retain their own terms, as explained in [LICENSING.md](../LICENSING.md).

## What actually authorizes release

The relevant [virtual processor][utxo] first looks up every input's previous outpoint in the current UTXO view. A missing or already spent outpoint produces `MissingTxOutpoints`. The script does not establish that a UTXO exists.

The [transaction validator][validator], with `TxValidationFlags::Full`, then checks coinbase maturity, checked input-value accumulation, output total <= input total, storage-mass commitment, sequence locks, and covenant bindings. Isolation validation separately checks transaction version, input/output limits, duplicate input outpoints, output-value ranges, and native-subnetwork fields.

`check_scripts` constructs the actual `TxScriptEngine` for each input with that input's committed script-unit limit and calls `execute()`. For a P2SH reserve, the engine verifies the supplied redeem script against the stored script hash before executing its conditions. These conditions must identify the intended proof statement and constrain the actual payment transaction.

[`OpZkPrecompile` (`0xa6`)][opcodes] parses the proof-system tag, charges its resource cost, calls the real selected verifier, and pushes true only when verification returns no error. A malformed or invalid proof aborts script execution. Successful verification is not an external oracle response or a reusable authorization token. It is one condition in that input's executing redeem script. All other covenant checks must succeed and the engine must finish with a clean true stack.

Only successful transaction acceptance consumes the reserve's native KAS UTXO and creates native KAS outputs. The application must therefore bind the fixed verifying key/program, authenticated old state, domain/context, recipient, amount, and any successor state to the verified public inputs and actual transaction. A valid proof alone does not constrain outputs.

```text
unspent native-KAS UTXO
  -> P2SH redeem-script identity
  -> fixed verifier + transaction/state/context bindings
  -> real OpZkPrecompile verification AND all covenant conditions
  -> transaction validation and acceptance
  -> old UTXO consumed, specified native-KAS outputs created
```

The [Inline ZK guide][inline] describes this same division: the proof establishes a transition and the covenant checks that the transaction installs its result. Neither a custom token nor vProgs is required for this narrow native-UTXO authorization mechanism. This says nothing by itself about a complete private accounting system, data availability, or permissionless recovery.

## Covenant IDs and replay boundaries

[KIP-17][kip17] introspection can restrict a standard P2SH spend even when `covenant_id=None`. The optional [KIP-20][kip20] identifier provides non-forgeable lineage and efficient membership/context inspection. [`CovenantsContext::from_tx`][covenants] validates genesis or continuation bindings; it does **not** automatically require continuation, constrain payout values, or enforce outstanding user liabilities. Those are covenant/proof responsibilities.

For a terminal single-claim withdrawal, the reserve outpoint's consumption prevents its second spend. A proof can remain mathematically valid afterward; consensus rejects the unavailable input. A continuing reserve would additionally need authenticated successor state and note/nullifier/accounting rules beyond this terminal experiment.

A harness supplied with a `PopulatedTransaction` already has caller-provided UTXO entries. Even the real public transaction validator then does not test live UTXO existence, spentness, block inclusion, chain selection, or reorg behavior. A manually maintained local UTXO map is not TN10 replay evidence. Distinguish rejection of a proof against another state/outpoint from rejection of a second spend by an actual UTXO view.

## Verification surfaces

| Tag | Real verifier | Binding and encoding requirements |
| --- | --- | --- |
| `0x20` | [Groth16 over BN254][groth16] | Compressed VK and 128-byte compressed proof; public-input arity; one canonical 32-byte Fr encoding per input; no trailing key/proof bytes. Covenant pins VK and meaning of inputs. |
| `0x21` | [RISC Zero Succinct receipt][risc0] | Claim, control proof/index, seal, journal digest, image ID, control ID, hash-function ID; Poseidon2 only; control proof depth <=8. Covenant pins expected image ID and constrains journal meaning. |

Groth16's stack before dispatch has, from top downward, compressed VK, compressed proof, script-i32 public-input count, and the public inputs. The tag is consumed first by `OpZkPrecompile`. Inputs are popped in circuit order, so serializers push them in reverse. The [SDK][sdk] provides encoding/building helpers. The [scalar decoder][fields] accepts exactly 32 canonical bytes; arbitrary input must not be reduced modulo the field by application code to evade this requirement. `gamma_abc_g1.len()` must equal the public-input count plus one. Curve validity checks and verification run inside the precompile.

Groth16 requires a circuit-specific trusted setup. Locally generated test setup, especially any deterministic fixture, is not a production ceremony. BN254/Groth16 is not post-quantum. An implemented verifier is not an audit of the circuit, setup, or application bindings.

RISC Zero verifies receipt integrity and binds the resulting claim to the supplied image ID and journal digest. The implemented tag is a Succinct STARK receipt, not a generic arbitrary RISC Zero receipt or a development receipt. The separate vProgs TN10 development path previously noted in [research](../research/kaspa-toccata-vprogs.md) cannot satisfy A0's real-proof requirement. A0 can use Groth16 without adding the full runtime or zkVM proving toolchain.

## Current source rules, budgets, and relay policy

The v2.1.0 [TN10 configuration][params] is `NetworkId(Testnet, 10)`, 10 blocks per second. This current source has no Toccata activation parameter and runs its Toccata transaction/script rules unconditionally. A test explicitly rejects a `toccata_activation` override. The remaining Crescendo DAA activation value, 88,657,000, is not a Toccata gate. This source inspection does not confirm the software, DAA score, or activation state of an unqueried remote node. Historical preactivation prose in the [node setup guide][guide] must not be mistaken for a switch in this current code.

| Constraint | Current pinned value or behavior |
| --- | --- |
| Transaction | Version 1; native subnetwork; gas 0; per-input `ComputeCommit::ComputeBudget` |
| Block mass limits | Compute 500,000; storage 500,000; transient 1,000,000 |
| Input/output count | At most 1,000 each |
| Signature script | At most 250,000 bytes |
| Output script-public-key | At most 10,000 bytes; current supported SPK version 0 |
| Script engine | Stack depth 244; script/element limit 1,000,000 bytes; mass and transaction bounds can bind first |
| Values | No zero-valued output; checked sums and maximum native-money bound |
| Budget | u16 units; 1 unit = 100 compute grams = 10,000 script units; 9,999 free script units per input |
| Groth16 base | 140,000 grams = 14,000,000 script units |
| Groth16 VK addition | 250,000 script units = 2,500 grams per `gamma_abc_g1` element, including the constant element |
| RISC Zero base | 250,000 grams = 25,000,000 script units |
| Minimum relay fee | 100,000 sompi/kg = 100 sompi/gram, applied to max(compute, normalized transient) |

Costs come from [precompile tags][tags], [Groth16 metering][groth16], [mass units][units], [engine limits][engine], and [mempool fee configuration][fee]. Pushes, hashing, other opcodes, transaction bytes, output scripts, storage mass, and transient mass still matter. These are protocol accounting values, not wall-clock benchmarks or a throughput guarantee.

[`ComputeBudget::checked_covering_script_units`][units] calculates a minimal covering input budget. Do not set an unlimited engine budget and present that as a valid transaction. Do not use the validator's `new_for_tests` constructor for mass evidence: it intentionally supplies a zero-valued mass calculator.

[Mempool standardness][standard] accepts conventional output classes such as P2PK and P2SH. A reserve should therefore be standard P2SH, not a bare custom script; the recipient must also use a standard class for relay evidence. The <=15 classical signature-operation limit in P2SH policy does not count a Groth16 verifier as 140 classical signature operations.

For illustration, a 150,000-gram withdrawal requires at least 15,000,000 sompi (0.15 KAS) under the default minimum fee before market premium. A fee of 1,000 sompi is not plausible live-relay evidence for this proof. Fee funding must remain distinct from user backing: paying a legitimate liability must not silently charge another user's reserve. The invariant remains `outstanding user liabilities <= native KAS reserved for users`.

## TN10 execution and current blocker

Upstream documents running `kaspad --utxoindex --testnet` for TN10; current RPC must preserve transaction version, input compute budget, storage mass, and output covenant fields. A meaningful run also needs a synchronized endpoint, native **test** KAS funding, actual UTXO queries, correctly computed storage mass/fee, transaction submission, and acceptance observation. No mainnet funds or node should be used.

The inspected cloud configuration on 2026-10-03 reports current, enforced restricted HTTP policy with package-manager/source-host destinations; no permitted TN10 RPC/P2P/faucet destination; no TCP grants; no VPN; and no configured secret/runtime-variable/outbound-identity bindings. GitHub/raw/codeload source retrieval is available. No authorized reachable TN10 endpoint or funded test UTXO was provided. This is a concrete execution-environment blocker, not evidence that the consensus primitive is missing. No denied destination was probed and no proxy restriction was bypassed.

The remaining live evidence requires supported network access and test funding, then an unmodified current node accepting the valid withdrawal and rejecting invalid variants. Source inspection and local consensus-code execution must stay labeled separately from this missing network result.

[manifest]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/Cargo.toml
[license]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/LICENSE
[params]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/params.rs
[engine]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/lib.rs
[utxo]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/src/pipeline/virtual_processor/utxo_validation.rs
[validator]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/src/processes/transaction_validator/tx_validation_in_utxo_context.rs
[opcodes]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/opcodes/mod.rs
[covenants]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/covenants.rs
[groth16]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/groth16/mod.rs
[fields]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/fields/mod.rs
[risc0]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/risc0/mod.rs
[sdk]: https://github.com/kaspanet/rusty-kaspa/tree/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/zk-sdk
[tags]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/tags.rs
[units]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/units.rs
[fee]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/config.rs
[standard]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/check_transaction_standard.rs
[guide]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/docs/toccata-guide.md
[inline]: https://github.com/kaspanet/docs/blob/0ac77d043a802fc8196abfd5812ac2afbd97a2b9/content/docs/toccata/inline-zk.mdx
[kip16]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0016.md
[kip17]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0017.md
[kip20]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0020.md
