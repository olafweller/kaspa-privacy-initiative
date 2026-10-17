//! Public capture -> reference batch/aggregate wires, no signing or proof generation.
use kaspa_consensus_core::{hashing::tx::transaction_v1_rest_preimage, tx::Transaction};
use kaspa_hashes::Hash;
use kaspa_rpc_core::{GetSeqCommitLaneProofResponse, RpcOptionalTransaction};
use kaspa_seq_commit::{
    hashing::{lane_key, mergeset_context_hash},
    types::MergesetContext,
};
use kpi_takeover_common::{self as common, app};
use risc0_zkvm::compute_image_id;
use serde_json::{json, Value};
use std::{error::Error, fs, path::Path, process::Command, str::FromStr};
use vprogs_core_codec::Writer;
type Result<T> = std::result::Result<T, Box<dyn Error>>;
fn save(root: &Path, name: &str, bytes: &[u8]) -> Result<()> {
    use std::io::Write;
    fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(root.join(name))?
        .write_all(bytes)?;
    Ok(())
}
fn record(c: &Value, label: &str) -> Result<Value> {
    let r = c["records"]
        .as_array()
        .ok_or("records")?
        .iter()
        .find(|r| r["label"] == label)
        .ok_or("label")?;
    let raw: Value = serde_json::from_str(r["raw"].as_str().ok_or("raw")?)?;
    Ok(raw["params"].clone())
}
fn h(v: &Value) -> Result<Hash> {
    Ok(Hash::from_str(v.as_str().ok_or("hash")?)?)
}
fn n(v: &Value) -> Result<u64> {
    v.as_u64().ok_or_else(|| "exact u64".into())
}
fn main() -> Result<()> {
    let a: Vec<_> = std::env::args().collect();
    if !(a.len() == 8 || a.len() == 9) {
        return Err("CAPTURE LANE COV STATE_JSON|empty PROGRAM_DIR NEW_OUTPUT_DIR RETAINED_VALIDATOR [OMIT_TXID]".into());
    }
    let capture: Value = serde_json::from_slice(&fs::read(&a[1])?)?;
    let lane: [u8; 20] = hex::decode(&a[2])?.try_into().map_err(|_| "lane length")?;
    let cov: [u8; 32] = Hash::from_str(&a[3])?.into();
    let root = Path::new(&a[6]);
    fs::create_dir(root)?;
    // Reuse the complete PR31 native-ID/selected-chain/SMT/order validator. Its
    // reconstruction supports native active intervals beyond the bounded guest.
    let valid = Command::new(&a[7])
        .args(["verify", &a[2], &a[1]])
        .output()?;
    save(root, "native-validator.stdout.json", &valid.stdout)?;
    save(root, "native-validator.stderr.log", &valid.stderr)?;
    if !valid.status.success() {
        return Err("retained native capture validation failed".into());
    }
    let mut state: app::State = if a[4] == "empty" {
        app::State::default()
    } else {
        serde_json::from_slice(&fs::read(&a[4])?)?
    };
    let initial_root = common::root(&state);
    let images = Path::new(&a[5]);
    let tximage: [u8; 32] =
        compute_image_id(&fs::read(images.join("transaction.program.bin"))?)?.into();
    let batchimage: [u8; 32] =
        compute_image_id(&fs::read(images.join("batch.program.bin"))?)?.into();
    let key = lane_key(&lane);
    let start = record(&capture, "start-block")?;
    let sp = record(&capture, "start-proof")?;
    let ep = record(&capture, "end-proof")?;
    let mut tip = h(&sp["lane"]["tip"])?;
    let mut score = n(&sp["lane"]["blueScore"])?;
    let mut parent_time = n(&start["block"]["header"]["timestamp"])?;
    let mut parent_seq = h(&start["block"]["header"]["acceptedIdMerkleRoot"])?;
    let start_header_score = n(&start["block"]["header"]["blueScore"])?;
    let accepted = record(&capture, "accepted")?;
    let count = n(&capture["intervalBlocks"])? as usize;
    let mut batches = vec![];
    let mut journals = vec![];
    let mut removed = 0;
    let mut ids = vec![];
    for (bi, b) in accepted["chainBlockAcceptedTransactions"]
        .as_array()
        .ok_or("chain")?[..count]
        .iter()
        .enumerate()
    {
        let header = &b["chainBlockHeader"];
        let blue = n(&header["blueScore"])?;
        let daa = n(&header["daaScore"])?;
        let ctx = mergeset_context_hash(&MergesetContext {
            timestamp: parent_time,
            daa_score: daa,
            blue_score: blue,
        });
        let mut txs = vec![];
        let mut txjournals = vec![];
        let before = state.clone();
        let mut native_count = 0;
        for (index, raw) in b["acceptedTransactions"]
            .as_array()
            .ok_or("bodies")?
            .iter()
            .enumerate()
        {
            let rpc: RpcOptionalTransaction = serde_json::from_value(raw.clone())?;
            let tx: Transaction = rpc.try_into()?;
            assert_eq!(tx.id(), h(&raw["verboseData"]["transactionId"])?);
            if tx.subnetwork_id.as_bytes() != &lane {
                continue;
            }
            native_count += 1;
            if a.get(8).is_some_and(|omit| omit == &tx.id().to_string()) {
                removed += 1;
                continue;
            }
            let input = common::Input {
                lane,
                covenant: cov,
                context: ctx.into(),
                state: state.clone(),
                tx: app::lane::Tx {
                    payload: tx.payload.clone(),
                    rest: transaction_v1_rest_preimage(&tx),
                    merge_idx: index.try_into()?,
                },
            };
            let (next, journal) = common::execute(&input);
            state = next;
            let stem = format!("b{bi:05}-t{index:05}");
            save(
                root,
                &format!("{stem}.json"),
                &serde_json::to_vec_pretty(&input)?,
            )?;
            save(root, &format!("{stem}.journal.bin"), &journal)?;
            txjournals.push(journal);
            txs.push(stem);
            ids.push(tx.id().to_string());
        }
        if native_count > 0 {
            // Native expiry stays unsupported. Exact endpoint binding also prevents a
            // reactivated lane from masquerading as an uninterrupted old-tip extension.
            assert!(
                blue > score
                    && blue - score
                        <= kaspa_consensus_core::config::params::TESTNET_PARAMS.finality_depth(),
                "native expiry unsupported"
            );
            let proof = common::proof(&before);
            let mut wire = vec![];
            let deposit = txjournals
                .iter()
                .map(|j| vprogs_zk_abi::transaction_processor::JournalEntries::decode(j).unwrap())
                .find_map(|j| match j.output_commitment {
                    vprogs_zk_abi::transaction_processor::OutputCommitment::Success {
                        deposit_spk_hash,
                        ..
                    } if *deposit_spk_hash != [0; 32] => Some(*deposit_spk_hash),
                    _ => None,
                })
                .unwrap_or([0; 32]);
            wire.write(&tximage);
            wire.write(&cov);
            wire.write(&deposit);
            wire.write(key.as_slice());
            wire.write_blob(&proof);
            wire.write(&blue.to_le_bytes());
            wire.write(&daa.to_le_bytes());
            wire.write(&parent_time.to_le_bytes());
            wire.write(parent_seq.as_slice());
            wire.write(tip.as_slice());
            wire.write(&score.to_le_bytes());
            wire.write(&[0]);
            let mut list = vec![];
            for j in &txjournals {
                list.write_blob(j)
            }
            wire.write_blob(&list);
            let mut v = vprogs_zk_abi::batch_processor::Verifier::new(&wire, |image, journal| {
                assert_eq!(image, &tximage);
                assert!(txjournals.iter().any(|j| j == journal));
            });
            let (new_tip, new_score) = v.verify_batch();
            let mut journal = vec![];
            v.commit_batch_transition::<vprogs_zk_backend_risc0_api::Sha256>(
                &mut journal,
                &new_tip,
                new_score,
            );
            assert_eq!(journal[0..32], common::root(&before));
            assert_eq!(journal[72..104], common::root(&state));
            let stem = format!("b{bi:05}");
            save(root, &format!("{stem}.bin"), &wire)?;
            save(root, &format!("{stem}.journal.bin"), &journal)?;
            batches.push(json!({"stem":stem,"transactions":txs,"blueScore":blue,"previousLastTouchBlueScore":score}));
            journals.push(journal);
            tip = new_tip;
            score = new_score;
        }
        parent_time = n(&header["timestamp"])?;
        parent_seq = h(&header["acceptedIdMerkleRoot"])?;
    }
    assert!(!batches.is_empty());
    assert_eq!(removed, usize::from(a.len() == 9));
    let mut agg = vec![];
    agg.write(&batchimage);
    agg.write(h(&ep["payloadAndCtxDigest"])?.as_slice());
    agg.write(h(&ep["parentSeqCommit"])?.as_slice());
    agg.write(h(&ep["inactivityShortcut"])?.as_slice());
    // Native JSON RPC serializes this Vec<u8> as a byte array, not hex text.
    let end_proof: GetSeqCommitLaneProofResponse = serde_json::from_value(ep.clone())?;
    agg.write_blob(&end_proof.smt_proof);
    for j in &journals {
        agg.write_blob(j)
    }
    let mut v = vprogs_zk_abi::batch_aggregator::Verifier::new(
        &agg,
        |image, journal| {
            assert_eq!(image, &batchimage);
            assert!(journals.iter().any(|j| j == journal));
        },
        vprogs_zk_backend_risc0_api::PermissionTreeAccumulator::new(),
    );
    let last = v.verify_batches();
    let mut journal = vec![];
    v.commit_state_transition(&mut journal, last);
    assert_eq!(journal[0..32], initial_root);
    assert_eq!(journal[64..96], common::root(&state));
    if removed == 0 {
        assert_eq!(journal[128..160], <[u8; 32]>::from(parent_seq));
        assert_eq!(tip, h(&ep["lane"]["tip"])?)
    }
    save(root, "aggregate.bin", &agg)?;
    save(root, "aggregate.journal.bin", &journal)?;
    save(root, "state.json", &serde_json::to_vec_pretty(&state)?)?;
    save(
        root,
        "bundle.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"PUBLIC_INPUT_PREPARATION_NO_PROOF", "batches":batches,"omittedTransactions":removed,"orderedIds":ids,"stateRoot":hex::encode(common::root(&state)),"spendableSompi":state.spendable(),"anchorSeqCommit":parent_seq.to_string(),"startHeaderBlueScore":start_header_score,"endHeaderBlueScore":n(&record(&capture,"end-block")?["block"]["header"]["blueScore"])?}),
        )?,
    )?;
    Ok(())
}
