use kaspa_consensus_core::{
    config::params::TESTNET_PARAMS,
    hashing::{sighash::SigHashReusedValuesUnsync, tx::transaction_v1_rest_preimage},
    mass::{transaction_estimated_serialized_size, units::ComputeBudget, MassCalculator},
    subnets::SubnetworkId,
    tx::{
        PopulatedTransaction, ScriptPublicKey, Transaction, TransactionInput, TransactionOutpoint,
        TransactionOutput, UtxoEntry,
    },
};
use kaspa_hashes::{Hash, SeqCommitActiveNode};
use kaspa_seq_commit::{hashing::*, types::*};
use kaspa_smt::{proof::ProofTerminal, tree::SparseMerkleTree};
use kaspa_txscript::{
    caches::Cache, covenants::CovenantsContext, engine_context::EngineContext,
    seq_commit_accessor::SeqCommitAccessor, standard::pay_to_script_hash_script, EngineFlags,
    TxScriptEngine,
};
use kpi_lane_common::*;
use risc0_zkvm::{
    compute_image_id, default_prover, sha::Digestible, ExecutorEnv, ProverOpts, Receipt,
};
use serde_json::{json, Value};
use std::{collections::BTreeMap, fs, path::Path, time::Instant};
use vprogs_zk_backend_risc0_covenant::{
    script::{CommonPins, RedeemPins, SuccinctPins},
    Settlement, SettlementInput, SettlementWitness, SuccinctWitness,
};

type Smt = SparseMerkleTree<SeqCommitActiveNode>;
fn save(dir: &Path, name: &str, value: &Value) {
    fs::write(dir.join(name), serde_json::to_vec_pretty(value).unwrap()).unwrap();
}
fn tx(lane: [u8; 20], n: u32, payload: Vec<u8>) -> Transaction {
    Transaction::new(
        1,
        vec![TransactionInput::new(
            TransactionOutpoint::new(h([n as u8; 32]), n),
            vec![],
            0,
            1,
        )],
        vec![TransactionOutput::new(
            1_000_000,
            ScriptPublicKey::new(0, vec![0x51].into()),
        )],
        0,
        SubnetworkId::from_bytes(lane),
        0,
        payload,
    )
}
fn anchor(
    smt: &Smt,
    key: Hash,
    tip: Hash,
    score: u64,
    parent: Hash,
    ctx: Hash,
    miner_root: Hash,
) -> (Anchor, Hash) {
    let proof = smt.prove(&key).unwrap();
    let depth = match proof.terminal {
        ProofTerminal::Collapsed { depth } => depth,
        _ => panic!("fixture terminal"),
    };
    let a = Anchor {
        parent_seq: bytes(parent),
        payload_ctx: bytes(payload_and_context_digest(&ctx, &miner_root)),
        shortcut: [0; 32],
        blue_score: score,
        bitmap: proof.bitmap,
        depth,
        siblings: proof.siblings.iter().copied().map(bytes).collect(),
    };
    let seq = a.seq(key, tip);
    let activity = activity_root_hash(&h(a.shortcut), &smt.root());
    let state_root = seq_state_root(&SeqState {
        activity_root: &activity,
        payload_and_ctx_digest: &h(a.payload_ctx),
    });
    assert_eq!(
        seq,
        seq_commit(&SeqCommitInput {
            parent_seq_commit: &parent,
            state_root: &state_root
        }),
        "fixture must match full active-lane tree"
    );
    (a, seq)
}
fn fixture(dir: &Path) -> Input {
    let mut lane = [0; 20];
    lane[..4].copy_from_slice(b"KPIL");
    let key = lane_key(&lane);
    let mut smt = Smt::new();
    let mut tips = BTreeMap::new();
    let mut coinbase = [0; 20];
    coinbase[0] = 1;
    let native = [0; 20];
    let seed = h([0x19; 32]);
    let score = 100;
    let context = mergeset_context_hash(&MergesetContext {
        timestamp: 1_800_000_000_000,
        daa_score: 1000,
        blue_score: score,
    });
    for (i, id) in [lane, coinbase, native].into_iter().enumerate() {
        let key = lane_key(&id);
        let seed_tx = tx(id, 100 + i as u32, b"fixture-start-noop".to_vec());
        let activity =
            activity_digest_lane(core::iter::once(activity_leaf(&seed_tx.id(), 1, i as u32)));
        let tip = lane_tip_next(&LaneTipInput {
            parent_ref: &seed,
            lane_key: &key,
            activity_digest: &activity,
            context_hash: &context,
        });
        tips.insert(id, tip);
        smt.insert(
            key,
            smt_leaf_hash(&SmtLeafInput {
                lane_tip: &tip,
                blue_score: score,
            }),
        );
    }
    let initial_lanes: Vec<Value> = tips
        .iter()
        .map(|(id, tip)| json!({"lane":hex::encode(id), "tip":tip.to_string(), "blue_score":score}))
        .collect();
    let seed_miner = miner_payload_leaf(MinerPayloadLeafInput {
        block_hash: &h([0x69; 32]),
        blue_work_be_bytes: &[1],
        payload: b"fixture-start",
    });
    let old_tip = tips[&lane];
    let (start, mut seq) = anchor(&smt, key, old_tip, score, seed, context, seed_miner);
    let start_seq = seq;
    let mut blocks = Vec::new();
    let mut raw_blocks = Vec::new();
    let mut end = start.clone();
    let mut operation_number = 1;
    let mut lane_score = score;
    for (i, count) in [4, 0, 3, 3].into_iter().enumerate() {
        let blue_score = 101 + i as u64;
        let prev_timestamp = 1_800_000_000_100 + i as u64 * 100;
        let daa_score = 1001 + i as u64;
        let mut accepted = vec![tx(coinbase, 200 + i as u32, b"synthetic-coinbase".to_vec())];
        for _ in 0..count {
            accepted.push(tx(lane, operation_number, operation(operation_number)));
            operation_number += 1;
            accepted.push(tx(
                native,
                300 + accepted.len() as u32 + 20 * i as u32,
                vec![],
            ));
        }
        let context = mergeset_context_hash(&MergesetContext {
            timestamp: prev_timestamp,
            daa_score,
            blue_score,
        });
        let mut leaves: BTreeMap<[u8; 20], Vec<Hash>> = BTreeMap::new();
        let mut lane_txs = Vec::new();
        let mut records = Vec::new();
        for (merge_idx, tx) in accepted.iter().enumerate() {
            let id = tx.id();
            let lane_id = tx.subnetwork_id.into_bytes();
            leaves
                .entry(lane_id)
                .or_default()
                .push(activity_leaf(&id, 1, merge_idx as u32));
            let rest = transaction_v1_rest_preimage(tx);
            records.push(json!({"id": id.to_string(), "lane": hex::encode(lane_id), "version": 1, "payload": hex::encode(&tx.payload), "rest": hex::encode(&rest)}));
            if lane_id == lane {
                lane_txs.push(Tx {
                    payload: tx.payload.clone(),
                    rest,
                    merge_idx: merge_idx as u32,
                });
            }
        }
        for (lane, leaves) in leaves {
            let key = lane_key(&lane);
            let digest = activity_digest_lane(leaves.into_iter());
            let tip = lane_tip_next(&LaneTipInput {
                parent_ref: &tips[&lane],
                lane_key: &key,
                activity_digest: &digest,
                context_hash: &context,
            });
            tips.insert(lane, tip);
            smt.insert(
                key,
                smt_leaf_hash(&SmtLeafInput {
                    lane_tip: &tip,
                    blue_score,
                }),
            );
        }
        let miner_hash = h([0x60 + i as u8; 32]);
        let work = [1, i as u8];
        let miner_payload = b"synthetic-miner-payload";
        let miner_root = miner_payload_leaf(MinerPayloadLeafInput {
            block_hash: &miner_hash,
            blue_work_be_bytes: &work,
            payload: miner_payload,
        });
        if count > 0 {
            lane_score = blue_score;
        }
        let (a, next) = anchor(&smt, key, tips[&lane], lane_score, seq, context, miner_root);
        end = a;
        seq = next;
        let accepted_ids: Vec<String> = records
            .iter()
            .map(|r| r["id"].as_str().unwrap().to_owned())
            .collect();
        records.reverse(); // Body storage/arrival order deliberately differs from accepted order.
        raw_blocks.push(json!({"synthetic_block_hash": hex::encode([0x70 + i as u8; 32]), "prev_timestamp": prev_timestamp, "daa_score": daa_score,
            "blue_score": blue_score, "accepted_ids": accepted_ids, "bodies_in_arrival_order": records, "seq_commit": seq.to_string(),
            "miners":[{"hash":miner_hash.to_string(), "blue_work_be":hex::encode(work), "payload":hex::encode(miner_payload)}]}));
        blocks.push(Block {
            prev_timestamp,
            daa_score,
            blue_score,
            txs: lane_txs,
        });
    }
    let input = Input {
        lane,
        covenant: [0x55; 32],
        old_state: initial_state(),
        old_tip: bytes(old_tip),
        start,
        start_seq: bytes(start_seq),
        blocks,
        end,
    };
    let full = execute(&input);
    assert_eq!(full.operations, 10);
    assert_eq!(full.seq, bytes(seq));
    fs::write(
        dir.join("input.json"),
        serde_json::to_vec_pretty(&input).unwrap(),
    )
    .unwrap();
    save(
        dir,
        "kaspa-fixture.json",
        &json!({"kind": "SYNTHETIC_OFFLINE_NOT_TN10", "interval": "(start,end]", "lane": hex::encode(lane),
        "old_state": hex::encode(input.old_state), "old_tip": hex::encode(input.old_tip), "start_seq": hex::encode(input.start_seq),
        "initial_active_lanes":initial_lanes, "start_witness": input.start, "end_witness": input.end, "blocks": raw_blocks, "expected": full}),
    );
    input
}
fn omit(input: &Input) -> Input {
    let mut bad = input.clone();
    for b in &mut bad.blocks {
        b.txs
            .retain(|tx| ![3, 6, 9].iter().any(|n| tx.payload == operation(*n)));
    }
    bad
}
struct Accessor {
    block: Hash,
    seq: Hash,
    visible: bool,
}
impl SeqCommitAccessor for Accessor {
    fn is_chain_ancestor_from_pov(&self, block: Hash) -> Option<bool> {
        Some(self.visible && block == self.block)
    }
    fn seq_commitment_within_depth(&self, block: Hash) -> Option<Hash> {
        (self.visible && block == self.block).then_some(self.seq)
    }
}
fn settle(input: &Input, output: &Output, receipt: &Receipt, image: &[u8; 32]) -> Settlement {
    let s = receipt
        .inner
        .succinct()
        .expect("must be a real succinct receipt");
    let seal: Vec<u8> = s.seal.iter().flat_map(|x| x.to_le_bytes()).collect();
    let claim: [u8; 32] = s.claim.digest().into();
    let control: Vec<u8> = s
        .control_inclusion_proof
        .digests
        .iter()
        .flat_map(|d| <[u8; 32]>::from(*d))
        .collect();
    Settlement::build(&SettlementInput {
        covenant_id: h(input.covenant),
        pins: RedeemPins::Succinct(SuccinctPins {
            common: CommonPins {
                program_id: image,
                tx_image_id: &TX_DOMAIN,
                batch_image_id: &BATCH_DOMAIN,
                lane_key: &lane_key(&input.lane),
                permission_output_value: 0,
            },
        }),
        prev_state: &input.old_state,
        prev_lane_tip: &h(input.old_tip),
        new_state: &output.state,
        new_lane_tip: &h(output.tip),
        block_prove_to: h([0x73; 32]),
        prev_outpoint: TransactionOutpoint::new(h([0x66; 32]), 0),
        value: 1_000_000,
        witness: SettlementWitness::Succinct(SuccinctWitness {
            seal: &seal,
            claim: &claim,
            control_index: s.control_inclusion_proof.index,
            control_digests: &control,
            deposit_spk_hash: &[0; 32],
        }),
        permission_spk_hash: &[0; 32],
    })
}
fn verify(
    tx: &Transaction,
    authentic_redeem: &[u8],
    covenant: [u8; 32],
    accessor: &Accessor,
) -> Value {
    verify_limit(tx, authentic_redeem, covenant, accessor, false)
}
fn verify_limit(
    tx: &Transaction,
    authentic_redeem: &[u8],
    covenant: [u8; 32],
    accessor: &Accessor,
    bounded: bool,
) -> Value {
    let utxo = UtxoEntry::new(
        1_000_000,
        pay_to_script_hash_script(authentic_redeem),
        0,
        false,
        Some(h(covenant)),
    );
    let populated = PopulatedTransaction::new(tx, vec![utxo.clone()]);
    let cov = match CovenantsContext::from_tx(&populated) {
        Ok(c) => c,
        Err(e) => return json!({"accepted": false, "error": format!("covenant context: {e:?}")}),
    };
    let cache = Cache::new(1);
    let reused = SigHashReusedValuesUnsync::new();
    let context = EngineContext::new(&cache)
        .with_reused(&reused)
        .with_seq_commit_accessor(accessor)
        .with_covenants_ctx(&cov);
    let mut vm = TxScriptEngine::from_transaction_input_with_script_units_limit(
        &populated,
        &tx.inputs[0],
        0,
        &utxo,
        context,
        EngineFlags::default(),
        if bounded {
            tx.inputs[0].compute_commit.allowed_script_units()
        } else {
            kaspa_consensus_core::mass::units::ScriptUnits(u64::MAX)
        },
    );
    let now = Instant::now();
    let result = vm.execute();
    json!({"accepted": result.is_ok(), "error": result.err().map(|e| format!("{e:?}")), "script_units": vm.used_script_units().0,
        "verification_ms": now.elapsed().as_secs_f64()*1000.0})
}
fn prove(
    dir: &Path,
    name: &str,
    input: &Input,
    elf: &[u8],
    image: risc0_zkvm::sha::Digest,
) -> (Receipt, Value) {
    assert_eq!(
        std::env::var("RISC0_PROVER").as_deref(),
        Ok("ipc"),
        "offline proving requires the local r0vm IPC server"
    );
    let path = dir.join(format!("{name}.receipt.bin"));
    let now = Instant::now();
    let env = ExecutorEnv::builder()
        .write(input)
        .unwrap()
        .build()
        .unwrap();
    let info = default_prover()
        .prove_with_opts(env, elf, &ProverOpts::succinct())
        .expect("real CPU proving failed");
    let elapsed = now.elapsed().as_secs_f64();
    let receipt = info.receipt;
    receipt.verify(image).expect("receipt image verification");
    assert_eq!(receipt.journal.bytes, journal(input, &execute(input)));
    assert!(
        receipt.inner.succinct().is_ok(),
        "development/composite receipt rejected"
    );
    let encoded = bincode::serialize(&receipt).unwrap();
    fs::write(path, &encoded).unwrap();
    fs::write(
        dir.join(format!("{name}.journal.bin")),
        &receipt.journal.bytes,
    )
    .unwrap();
    (
        receipt,
        json!({"proof_seconds": elapsed, "receipt_bytes": encoded.len(), "journal_bytes": 352, "receipt_verified": true,
        "stats": format!("{:?}", info.stats)}),
    )
}
fn main() {
    assert!(
        std::env::var("RISC0_DEV_MODE").is_err(),
        "RISC0_DEV_MODE must be absent"
    );
    let args: Vec<_> = std::env::args().collect();
    let dir = Path::new(
        args.get(2)
            .map(String::as_str)
            .unwrap_or("evidence/offline"),
    );
    fs::create_dir_all(dir).unwrap();
    let input = fixture(dir);
    let full = execute(&input);
    let bad = omit(&input);
    let partial = execute(&bad);
    assert_eq!(partial.operations, 7);
    assert_ne!(partial.tip, full.tip);
    assert_ne!(partial.seq, full.seq);
    save(
        dir,
        "execution.json",
        &json!({"kind":"synthetic offline", "full":full, "omitted_3_6_9":partial, "same_end_anchor": partial.seq == full.seq}),
    );
    if args.get(1).map(String::as_str) == Some("fixture") {
        return;
    }
    let raw_elf = fs::read(
        args.get(3)
            .expect("usage: kpi-lane-host prove|verify EVIDENCE_DIR GUEST_ELF"),
    )
    .unwrap();
    // Same v1compat packaging as vProgs api/src/elf_binary.rs. RISC0 v3 expects
    // a ProgramBinary (guest + trusted kernel), not the raw linker ELF.
    let elf =
        risc0_binfmt::ProgramBinary::new(&raw_elf, risc0_zkos_v1compat::V1COMPAT_ELF).encode();
    let image = compute_image_id(&elf).unwrap();
    let image_bytes: [u8; 32] = image.into();
    fs::write(dir.join("guest.raw.elf"), &raw_elf).unwrap();
    fs::write(dir.join("guest.program.bin"), &elf).unwrap();
    if args[1] == "verify-full" {
        let receipt: Receipt =
            bincode::deserialize(&fs::read(dir.join("full.receipt.bin")).unwrap()).unwrap();
        receipt.verify(image).unwrap();
        assert_eq!(receipt.journal.bytes, journal(&input, &full));
        assert!(receipt.inner.succinct().is_ok());
        let s = settle(&input, &full, &receipt, &image_bytes);
        let accessor = Accessor {
            block: h([0x73; 32]),
            seq: h(full.seq),
            visible: true,
        };
        let result = verify(&s.transaction, &s.prev_redeem, input.covenant, &accessor);
        save(dir, "full-native-check.json", &result);
        println!("{result}");
        assert_eq!(result["accepted"], true, "real full receipt must settle");
        return;
    }
    let (full_receipt, full_cost, partial_receipt, partial_cost) = if args[1] == "verify" {
        let read = |name: &str| {
            bincode::deserialize::<Receipt>(
                &fs::read(dir.join(format!("{name}.receipt.bin"))).unwrap(),
            )
            .unwrap()
        };
        (
            read("full"),
            json!({"reverified":true}),
            read("omitted"),
            json!({"reverified":true}),
        )
    } else {
        let (r1, c1) = prove(dir, "full", &input, &elf, image);
        let (r2, c2) = prove(dir, "omitted", &bad, &elf, image);
        (r1, c1, r2, c2)
    };
    for (receipt, source) in [(&full_receipt, &input), (&partial_receipt, &bad)] {
        receipt.verify(image).unwrap();
        assert!(receipt.inner.succinct().is_ok());
        assert_eq!(receipt.journal.bytes, journal(source, &execute(source)));
    }
    let settlement = settle(&input, &full, &full_receipt, &image_bytes);
    let partial_settlement = settle(&bad, &partial, &partial_receipt, &image_bytes);
    let accessor = Accessor {
        block: h([0x73; 32]),
        seq: h(full.seq),
        visible: true,
    };
    let check = |tx: &Transaction| verify(tx, &settlement.prev_redeem, input.covenant, &accessor);
    let mut results = serde_json::Map::new();
    results.insert("full_interval".into(), check(&settlement.transaction));
    results.insert(
        "omit_three_same_interval".into(),
        check(&partial_settlement.transaction),
    );
    // A genuinely valid proof of seven ops is accepted under its own fabricated anchor:
    // this control proves the decisive dependency on the external L1 commitment.
    results.insert(
        "partial_executor_supplied_anchor_control".into(),
        verify(
            &partial_settlement.transaction,
            &settlement.prev_redeem,
            input.covenant,
            &Accessor {
                seq: h(partial.seq),
                ..accessor
            },
        ),
    );
    let mut forged = partial.clone();
    forged.tip = full.tip;
    forged.seq = full.seq;
    results.insert(
        "partial_proof_claims_full_tip".into(),
        check(&settle(&input, &forged, &partial_receipt, &image_bytes).transaction),
    );
    let mut wrong = full.clone();
    wrong.state[0] ^= 1;
    results.insert(
        "wrong_new_state".into(),
        check(&settle(&input, &wrong, &full_receipt, &image_bytes).transaction),
    );
    let mut wrong_input = input.clone();
    wrong_input.old_state[0] ^= 1;
    results.insert(
        "wrong_old_state".into(),
        check(&settle(&wrong_input, &full, &full_receipt, &image_bytes).transaction),
    );
    let mut wrong_input = input.clone();
    wrong_input.lane[1] ^= 1;
    results.insert(
        "cross_lane".into(),
        check(&settle(&wrong_input, &full, &full_receipt, &image_bytes).transaction),
    );
    let mut wrong_input = input.clone();
    wrong_input.covenant[0] ^= 1;
    results.insert(
        "cross_covenant".into(),
        check(&settle(&wrong_input, &full, &full_receipt, &image_bytes).transaction),
    );
    results.insert(
        "wrong_canonical_anchor".into(),
        verify(
            &settlement.transaction,
            &settlement.prev_redeem,
            input.covenant,
            &Accessor {
                seq: h([0x99; 32]),
                ..accessor
            },
        ),
    );
    results.insert(
        "unknown_or_orphan_anchor".into(),
        verify(
            &settlement.transaction,
            &settlement.prev_redeem,
            input.covenant,
            &Accessor {
                visible: false,
                ..accessor
            },
        ),
    );
    let mut malformed = settlement.transaction.clone();
    malformed.inputs[0].signature_script[10] ^= 1;
    results.insert("corrupt_claim".into(), check(&malformed));
    let mut malformed = settlement.transaction.clone();
    malformed.inputs[0].signature_script[1000] ^= 1;
    results.insert("corrupt_seal".into(), check(&malformed));
    let mut wrong_output = settlement.transaction.clone();
    wrong_output.outputs[0].value -= 1;
    results.insert("changed_continuation_value".into(), check(&wrong_output));
    results.insert(
        "replay_against_successor_state".into(),
        verify(
            &settlement.transaction,
            &settlement.next_redeem,
            input.covenant,
            &accessor,
        ),
    );
    for (name, value) in &results {
        let expected =
            name == "full_interval" || name == "partial_executor_supplied_anchor_control";
        assert_eq!(
            value["accepted"], expected,
            "unexpected settlement result: {name}: {value}"
        );
    }
    let units = settlement.covenant_input_script_units(h(input.covenant), &accessor);
    let budget = settlement.covenant_compute_budget(h(input.covenant), &accessor);
    let mut final_tx = settlement.transaction.clone();
    final_tx.inputs[0].compute_commit = budget.into();
    final_tx.finalize();
    let bounded = verify_limit(
        &final_tx,
        &settlement.prev_redeem,
        input.covenant,
        &accessor,
        true,
    );
    assert_eq!(bounded["accepted"], true);
    let mut underbudget = final_tx.clone();
    underbudget.inputs[0].compute_commit = ComputeBudget(0).into();
    let bounded_negative = verify_limit(
        &underbudget,
        &settlement.prev_redeem,
        input.covenant,
        &accessor,
        true,
    );
    assert_eq!(bounded_negative["accepted"], false);
    let calc = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS);
    let masses = calc.calc_non_contextual_masses(&final_tx);
    let entry = UtxoEntry::new(
        1_000_000,
        pay_to_script_hash_script(&settlement.prev_redeem),
        0,
        false,
        Some(h(input.covenant)),
    );
    let storage = calc
        .calc_contextual_masses(&PopulatedTransaction::new(&final_tx, vec![entry]))
        .unwrap()
        .storage_mass;
    final_tx.set_storage_mass(storage);
    let limits = &TESTNET_PARAMS.block_mass_limits;
    let floor = masses
        .normalized_max(&limits.cofactors())
        .checked_mul(100)
        .unwrap();
    let resource_fit = masses.compute_mass <= limits.compute
        && masses.transient_mass <= limits.transient
        && storage <= limits.storage;
    let report = json!({"scope": "REAL_PROOFS_NATIVE_SCRIPT_SYNTHETIC_L1_ANCHOR_ONLY", "guest_image_id": image.to_string(),
        "full_proof": full_cost, "partial_proof": partial_cost, "results": results, "script_units": units.0, "compute_budget": u16::from(budget),
        "signature_script_bytes": final_tx.inputs[0].signature_script.len(), "redeem_bytes": settlement.prev_redeem.len(),
        "settlement_id": final_tx.id().to_string(), "broadcast": false, "funded": false,
        "bounded_script_verification":bounded, "underbudget_rejected":bounded_negative,
        "estimated_transaction_bytes":transaction_estimated_serialized_size(&final_tx),
        "compute_mass_grams":masses.compute_mass, "transient_mass_grams":masses.transient_mass, "storage_mass_grams":storage,
        "fits_tn10_mass_limits_before_fee_inputs":resource_fit, "default_relay_fee_floor_sompi_before_fee_inputs":floor,
        "fee_paid_sompi":0, "fee_scope":"estimate for synthetic one-input no-fee body; not mempool validation or fees actually paid"});
    save(
        dir,
        if args[1] == "verify" {
            "reverification.json"
        } else {
            "report.json"
        },
        &report,
    );
    save(
        dir,
        "settlement-transaction.json",
        &serde_json::to_value(&final_tx).unwrap(),
    );
    save(dir, "omitted-settlement-transaction.json", &{
        let mut tx = partial_settlement.transaction.clone();
        tx.inputs[0].compute_commit = budget.into();
        tx.finalize();
        serde_json::to_value(&tx).unwrap()
    });
    println!("{}", serde_json::to_string_pretty(&report).unwrap());
}

#[cfg(test)]
mod tests {
    use super::*;
    fn sample() -> Input {
        let d = std::env::temp_dir().join(format!("kpi-lane-test-{}", std::process::id()));
        fs::create_dir_all(&d).unwrap();
        fixture(&d)
    }
    fn rejects(f: impl FnOnce()) {
        assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)).is_err());
    }
    #[test]
    fn adversarial_relation_checks() {
        let input = sample();
        let full = execute(&input);
        assert_ne!(execute(&omit(&input)).seq, full.seq);
        let mut b = input.clone();
        b.blocks[0].txs.swap(0, 1);
        rejects(|| {
            execute(&b);
        });
        let mut b = input.clone();
        b.blocks[0].txs[1].merge_idx = b.blocks[0].txs[0].merge_idx;
        rejects(|| {
            execute(&b);
        });
        let mut b = input.clone();
        b.blocks.swap(0, 1);
        rejects(|| {
            execute(&b);
        });
        let mut b = input.clone();
        b.end.siblings.pop();
        rejects(|| {
            execute(&b);
        });
        let mut b = input.clone();
        b.old_tip[0] ^= 1;
        rejects(|| {
            execute(&b);
        });
        let mut b = input.clone();
        b.blocks[0].txs[0].rest.pop();
        rejects(|| {
            execute(&b);
        });
        let mut b = input.clone();
        b.lane[19] = 1;
        rejects(|| {
            execute(&b);
        });
        let mut b = input.clone();
        b.blocks[0].blue_score = u64::MAX;
        rejects(|| {
            execute(&b);
        });
        let mut b = input.clone();
        b.blocks[0].txs[0].payload = operation(u32::MAX);
        assert_ne!(execute(&b).state, full.state);
        let mut b = input.clone();
        b.blocks[0].txs[0].payload = operation(0);
        assert_ne!(execute(&b).state, full.state);
        let mut b = input.clone();
        b.blocks[0].txs[0].payload = b"malformed".to_vec();
        assert_ne!(execute(&b).seq, full.seq);
    }
}
