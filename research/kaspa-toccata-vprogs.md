# Kaspa Toccata and vProgs Research Notes

**Reviewed: 2026-10-08.** Heads, trees and selected files were refreshed from upstream; downloaded source blobs were checked against Git tree hashes. This review read sources only: no node, prover or testnet query was run. Historical execution evidence remains in [A0](../docs/poc-a0.md), [A1 S1](../docs/poc-a1-official-trial-2026-10-08.md) and [A1 S0](../docs/poc-a1-s0-trials-2026-10-08.md); none establishes a multi-user private pool.

## Source snapshots

| Repository | Branch | Exact reviewed commit |
| --- | --- | --- |
| [kaspanet/kips](https://github.com/kaspanet/kips/tree/e4ae2332117b5cb68bd6188e065ef885b6d17939) | `master` | `e4ae2332117b5cb68bd6188e065ef885b6d17939` |
| [kaspanet/rusty-kaspa](https://github.com/kaspanet/rusty-kaspa/tree/01b532e8b553523216471682649693af92f0fd16) | `master` | `01b532e8b553523216471682649693af92f0fd16` |
| [kaspanet/docs](https://github.com/kaspanet/docs/tree/0ac77d043a802fc8196abfd5812ac2afbd97a2b9) | `main` | `0ac77d043a802fc8196abfd5812ac2afbd97a2b9` |
| [kaspanet/vprogs](https://github.com/kaspanet/vprogs/tree/f9b84a863a7c7c20586a9cf947550475e894f72e) | `master` | `f9b84a863a7c7c20586a9cf947550475e894f72e` |
| [kaspanet/research](https://github.com/kaspanet/research/tree/c923faca11a49148fa7d912d27ce00197a5c5a4a) | `main` | `c923faca11a49148fa7d912d27ce00197a5c5a4a` |

The Kaspa heads still match the earlier review, now rechecked. Rusty Kaspa's [v2.1.0 release](https://github.com/kaspanet/rusty-kaspa/releases/tag/v2.1.0) is dated 2026-09-22. Live network configuration and current third-party builds were not inspected.

## Implemented primitive map

| Primary specification | Implemented surface / meaning | What it does not supply |
| --- | --- | --- |
| [KIP-10][K10] | Transaction/UTXO introspection in [opcodes][N1] | Note ownership, confidentiality or conservation rules |
| [KIP-16][K16] | Generic ZK opcode with tagged dispatch [N1][N2] | An automatically safe circuit or withdrawal |
| [KIP-17][K17] | Covenant/script extensions for checking spending structure [N1] | A chosen private state architecture |
| [KIP-20][K20] | Covenant IDs and covenant-bound output access [N1] | Correct liabilities unless the application checks them |
| [KIP-21][K21] | Sequencing commitments and lane resources | Private data retention or automatic anonymous sharding |

## Exact verifier surface

`OpZkPrecompile` is opcode `0xa6`; [dispatch][N2] accepts only tags `0x20` and `0x21` at this pin. Unknown tags fail. There is no native Orchard/Halo2, CLSAG or Bulletproof tag in that dispatch.

| Tag | Source facts | Binding still required by the application |
| --- | --- | --- |
| `0x20`, Groth16 [N3] | BN254; compressed validated points; public-input/key arity checks; trailing key/proof bytes rejected. Base charge 140,000 grams, plus 250,000 script units per `gamma_abc_g1` element. | Fix authorized key/circuit, pool/version, roots, nullifiers, amount ranges, outputs and fees. Circuit-specific setup assumptions remain. |
| `0x21`, RISC0 succinct [N4] | Poseidon2 only at this pin; receipt integrity, allowed control-root inclusion and image/journal claim binding. Base charge 250,000 grams [N2]. | Fix the permitted guest image and intended journal semantics; prevent substituting another valid program or state. |

[Mass units][N15] define 100 script units per gram; [transaction mass calculation][N9] applies the resource accounting. Base verification alone therefore consumes substantial compute mass; it is not the total transaction cost. A STARK verification path also does not make surrounding keys, commitments or encrypted note delivery post-quantum.

## Consensus limits, relay policy and fee cost

| Layer | Reviewed limit / rule | Consequence |
| --- | --- | --- |
| Script VM [N5] | Stack 244; script size, element size and opcode count each bounded by 1,000,000; script-public-key version 0 | These are VM ceilings, not admissible transaction sizes. |
| Transaction consensus [N6][N14] | TN10 parameters: at most 1,000 inputs / outputs; signature script 250,000 bytes; output script 10,000 bytes | Other mass and structural limits can reject smaller transactions. |
| Block resources [N6][N16] | TN10 compute 500,000, storage 500,000, transient 1,000,000; four transient mass units per serialized byte cap the block's accounted footprint at 250,000 bytes | Proving more work off chain does not remove L1 verification or data limits. |
| Standard relay [N7] | Standard script forms/version; P2SH classic signature operations at most 15 | The 15-signature rule is not a 15-equivalent-ZK-operations budget; compute mass meters ZK. |
| Minimum relay fee [N7][N8] | Default 100,000 sompi/kg; floor scales with maximum of compute mass and normalized transient mass | This is configurable policy, not a fixed fee guarantee or a quote from a live node. Storage mass and miner inclusion are separate. |

**Interpretation:** quantify public ciphertext bytes, witnesses, key/proof size and verification charges together. Ignoring storage/transient cost or presenting a base verifier capacity as private-transfer TPS would be misleading. Fee funding from a public wallet can defeat unlinkability even if the note circuit is sound; [issue #23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23) remains a protocol question.

## Pruning and node recovery surface: P10 / P12

The [pruning constants][N10] define 108,000 seconds (30 hours) as the pruning-duration parameter. Actual retained history is governed by DAG/retention processing and configuration, including archival mode and [retention settings][N13]; this is not a guaranteed 30-hour ciphertext service.

The [processor][N11] advances and checks the pruning-point UTXO commitment, then deletes old block bodies, acceptance data, UTXO diffs and other stores as permitted. Some retained proof/header blocks become header-only. Consensus bootstrap data and live UTXOs are not an archive of every accepted application transition.

The [RPC service][N12] exposes blocks, virtual-chain acceptance information and current UTXOs. Block-body retrieval depends on retained bodies; address UTXO queries require the relevant index and expose the current set. They cannot by themselves recover spent outputs, deleted ciphertexts or an application's old note/nullifier sequence.

**Interpretation:** a publicly spendable state commitment proves a state exists; it does not recover its preimages or recipient ciphertexts. KPI must identify retained authenticated data, append order, reorg handling, discovery metadata and independent providers/self-backups. An archival node is one possible data source, not proof of permissionless recovery after that operator disappears.

## vProgs components — provisional assessment

The [README][V1] explicitly calls the framework early/prototype. Scheduler/state/storage documents describe resource-based parallel batches, versioned state, rollback and persistence; they do not establish private notes or indefinitely available state. The [withdrawal action][V4] and [permission script][V3] are concrete accounting references. The latter binds payout destination/value, continuation and delegate change; [issue #77](https://github.com/kaspanet/vprogs/issues/77) is closed as of 2026-07-09, not an alleged current vulnerability.

| Building block | Potentially reusable | Adaptation needed | Risks | Still to prove for KPI |
| --- | --- | --- | --- | --- |
| Scheduler / versioned state [V6][V7] | Dependency tracking, batches and rollback | Shielded roots, nullifiers and reorg semantics | Shared-root contention; anonymous state split into identifying shards | Measured throughput without stale-state or privacy shortcuts |
| Storage / bridge catch-up [V8][V9] | Replay and persistence interfaces | Authenticated encrypted history after pruning | Local database mistaken for publicly recoverable DA | Fresh independent recovery with preferred operators gone |
| Proof settlement [V5] | Bind proven execution to reserve continuation | Private conservation and correct verifier/program pins | Valid proof of wrong program; old-state settlement | Sound current-root transitions and cross-pool replay rejection |
| Withdrawal permissions [V3][V4] | Explicit payout/liability constraints | Native private claims, fees and permissionless holders | Correct destination but wrong amount; stranded liabilities | Full independent payout path, not just an exit event |
| Guest/runbook examples [V2][V10] | Encoding, transport and integration scaffolding | Actual note authorization and real proofs | Synthetic exits; development-mode acceptance | A complete private lifecycle under the real verifier |

The runbook defaults to `RISC0_DEV_MODE=1`; inspected guests exercise demonstrations, not KPI's shielded note lifecycle. The [workspace manifest][V11] tracks Rusty Kaspa master; today's pins do not prove build compatibility. The [full-vProgs draft][R1] studies cross-program composition and dependency metering; it is a separate research layer from a single based app.

## Interpretations, hypotheses and open gates

Direct inline-ZK covenants and based-app batching both merit comparison. Neither is selected or excluded. Separate parallel proving, conflict-free state execution and serialized L1 settlement; adding shards may improve throughput while reducing anonymity.

Remaining work: choose and specify note/conservation relations; authenticate spentness and recovery data; establish local discovery and permissionless fee/prover paths; measure witness updates, contention and low-activity privacy; define safe verifier/key migration. Historical A0/A1 proofs answer their stated reserve questions, not these multi-user gates. RFC comparison and any architecture decision are outside this step.

[K10]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0010.md
[K16]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0016.md
[K17]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0017.md
[K20]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0020.md
[K21]: https://github.com/kaspanet/kips/blob/e4ae2332117b5cb68bd6188e065ef885b6d17939/kip-0021.md
[N1]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/opcodes/mod.rs
[N2]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/tags.rs
[N3]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/groth16/mod.rs
[N4]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/risc0/mod.rs
[N5]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/lib.rs
[N6]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/params.rs
[N7]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/check_transaction_standard.rs
[N8]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/config.rs
[N9]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/mod.rs
[N10]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/constants.rs
[N11]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/src/pipeline/pruning_processor/processor.rs
[N12]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/rpc/service/src/service.rs
[N13]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/src/config.rs
[N14]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/src/processes/transaction_validator/tx_validation_in_isolation.rs
[N15]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/units.rs
[N16]: https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/constants.rs
[V1]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/README.md
[V2]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/examples/tn10-flow/scripts/README.md
[V3]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/api/src/permission_script.rs
[V4]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/runtime-processor/src/action/withdraw.rs
[V5]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/covenant/src/settlement.rs
[V6]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/scheduling/README.md
[V7]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/state/README.md
[V8]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/storage/README.md
[V9]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/l1/bridge/src/bridge.rs
[V10]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/zk/backend/risc0/transaction-processor-with-exits/src/main.rs
[V11]: https://github.com/kaspanet/vprogs/blob/f9b84a863a7c7c20586a9cf947550475e894f72e/Cargo.toml
[R1]: https://github.com/kaspanet/research/blob/c923faca11a49148fa7d912d27ce00197a5c5a4a/vProgs/main.tex
