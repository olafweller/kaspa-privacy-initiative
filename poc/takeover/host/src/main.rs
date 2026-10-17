//! Real composition compatibility gate. Synthetic empty batch, no funding/RPC.
use kaspa_hashes::Hash;
use risc0_zkvm::{
    compute_image_id, default_executor, default_prover, ExecutorEnv, ProverOpts, Receipt,
};
use serde_json::{json, Value};
use std::{error::Error, fs, path::Path, time::Instant};
use vprogs_core_codec::Writer;
type Result<T> = std::result::Result<T, Box<dyn Error>>;

fn save(dir: &Path, name: &str, bytes: &[u8]) -> Result<()> {
    use std::io::Write;
    fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dir.join(name))?
        .write_all(bytes)?;
    Ok(())
}
fn env(
    input: &[u8],
    assumptions: &[Receipt],
    prefix: bool,
) -> Result<risc0_zkvm::ExecutorEnv<'static>> {
    let mut b = ExecutorEnv::builder();
    if prefix {
        b.write_slice(&[u32::try_from(input.len())?]);
    }
    b.write_slice(input).segment_limit_po2(20);
    for receipt in assumptions {
        b.add_assumption(receipt.clone());
    }
    Ok(b.build()?)
}
fn prove(
    dir: &Path,
    label: &str,
    input: &[u8],
    program: &[u8],
    assumptions: &[Receipt],
    prefix: bool,
    synthetic: bool,
) -> Result<Receipt> {
    let image = compute_image_id(program)?;
    let profile = default_executor().execute(env(input, assumptions, prefix)?, program)?;
    save(
        dir,
        &format!("{label}-profile.json"),
        &serde_json::to_vec_pretty(
            &json!({"scope":"EXECUTION_ONLY_NO_PROOF", "segments":profile.segments.iter().map(|s|s.po2).collect::<Vec<_>>() }),
        )?,
    )?;
    let started = Instant::now();
    let info = default_prover().prove_with_opts(
        env(input, assumptions, prefix)?,
        program,
        &ProverOpts::succinct(),
    )?;
    info.receipt.verify(image)?;
    assert_eq!(info.receipt.journal.bytes, profile.journal.bytes);
    let succinct = info.receipt.inner.succinct()?;
    save(
        dir,
        &format!("{label}-receipt.bin"),
        &bincode::serialize(&info.receipt)?,
    )?;
    save(
        dir,
        &format!("{label}-journal.bin"),
        &info.receipt.journal.bytes,
    )?;
    save(
        dir,
        &format!("{label}-report.json"),
        &serde_json::to_vec_pretty(
            &json!({"scope":"REAL_SUCCINCT_PROOF", "developmentMode":false, "syntheticEmptyBatch":synthetic,"seconds":started.elapsed().as_secs_f64(),"stats":format!("{:?}",info.stats),"image":image.to_string(),"controlId":succinct.control_id.to_string(),"journalBytes":info.receipt.journal.bytes.len(),"assumptionsSupplied":assumptions.len()}),
        )?,
    )?;
    Ok(info.receipt)
}
fn a32(v: &Value) -> [u8; 32] {
    serde_json::from_value(v.clone()).unwrap()
}
fn main() -> Result<()> {
    assert!(
        std::env::var("RISC0_DEV_MODE").is_err(),
        "development mode forbidden"
    );
    assert_eq!(
        std::env::var("RISC0_PROVER").as_deref(),
        Ok("ipc"),
        "real IPC prover required"
    );
    let args: Vec<_> = std::env::args().collect();
    if args.get(1).is_some_and(|s| s == "bundle") {
        return bundle(&args);
    }
    if args.len() != 6 || args[1] != "gate" {
        return Err("gate BATCH_PROGRAM AGGREGATE_PROGRAM PUBLIC_LANE_INPUT NEW_DIR".into());
    }
    let bp = fs::read(&args[2])?;
    let ap = fs::read(&args[3])?;
    let lane: Value = serde_json::from_slice(&fs::read(&args[4])?)?;
    let lane = if lane["lane"].is_object() {
        &lane["lane"]
    } else {
        &lane
    };
    let dir = Path::new(&args[5]);
    fs::create_dir(dir)?;
    let tx_image = [0x71; 32];
    let cov = [0x72; 32];
    let key = kaspa_seq_commit::hashing::lane_key(&serde_json::from_value::<[u8; 20]>(
        lane["lane"].clone(),
    )?);
    let tip = a32(&lane["old_tip"]);
    let score = lane["start"]["blue_score"].as_u64().unwrap();
    let mut input = vec![];
    input.write(&tx_image);
    input.write(&cov);
    input.write(&[0; 32]);
    input.write(key.as_slice());
    // Reference SMT wire format: five empty slices. Empty pre/post root, no resources.
    input.write_blob(&[0; 20]);
    input.write(&(score + 1).to_le_bytes());
    input.write(&1u64.to_le_bytes());
    input.write(&1u64.to_le_bytes());
    input.write(&[0; 32]);
    input.write(&tip);
    input.write(&score.to_le_bytes());
    input.write(&[0]);
    input.write_blob(&[]);
    save(dir, "batch-input.bin", &input)?;
    let batch = prove(dir, "batch", &input, &bp, &[], true, true)?;
    let mut agg = vec![];
    agg.write(<[u8; 32]>::from(compute_image_id(&bp)?).as_slice());
    // Public proof fields are used only to exercise the real encoding/recursion route.
    // Empty batch => its derived commitment is synthetic, never represented as native input.
    let anchor = &lane["end"];
    agg.write(&a32(&anchor["payload_ctx"]));
    agg.write(&a32(&anchor["parent_seq"]));
    agg.write(&a32(&anchor["shortcut"]));
    let mut smt = a32(&anchor["bitmap"]).to_vec();
    smt.push(1);
    smt.push(anchor["depth"].as_u64().unwrap().try_into()?);
    for h in anchor["siblings"].as_array().unwrap() {
        smt.write(&a32(h));
    }
    agg.write_blob(&smt);
    agg.write_blob(&batch.journal.bytes);
    save(dir, "aggregate-input.bin", &agg)?;
    assert!(
        default_executor()
            .execute(env(&agg, &[], true)?, &ap)
            .is_err(),
        "missing inner receipt must reject"
    );
    let receipt = prove(dir, "aggregate", &agg, &ap, &[batch], true, true)?;
    let expected = vprogs_zk_backend_risc0_covenant::script::succinct_consts::SUCCINCT_CONTROL_ID;
    assert_eq!(
        <[u8; 32]>::from(receipt.inner.succinct()?.control_id),
        expected,
        "reference resolve identity"
    );
    native_check(&receipt, &bp, &ap)?;
    save(
        dir,
        "complete.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"REAL_RECURSIVE_COMPATIBILITY_ONLY", "syntheticEmptyBatch":true,"nativeScriptEngineVerified":true,"actualTN10Settlement":false,"missingAssumptionRejected":true,"developmentMode":false}),
        )?,
    )?;
    Ok(())
}

fn bundle(args: &[String]) -> Result<()> {
    if args.len() != 5 {
        return Err("bundle PREPARED_DIR PROGRAM_DIR NEW_PROOF_DIR".into());
    }
    let source = Path::new(&args[2]);
    let programs = Path::new(&args[3]);
    let target = Path::new(&args[4]);
    fs::create_dir(target)?;
    let m: Value = serde_json::from_slice(&fs::read(source.join("bundle.json"))?)?;
    let tp = fs::read(programs.join("transaction.program.bin"))?;
    let bp = fs::read(programs.join("batch.program.bin"))?;
    let ap = fs::read(programs.join("aggregate.program.bin"))?;
    let mut batches = vec![];
    for batch in m["batches"].as_array().ok_or("batches")? {
        let mut transactions = vec![];
        for tx in batch["transactions"].as_array().ok_or("transactions")? {
            let stem = tx.as_str().ok_or("stem")?;
            let input: kpi_takeover_common::Input =
                serde_json::from_slice(&fs::read(source.join(format!("{stem}.json")))?)?;
            let wire: Vec<u8> = risc0_zkvm::serde::to_vec(&input)?
                .iter()
                .flat_map(|n| n.to_le_bytes())
                .collect();
            let receipt = prove(target, stem, &wire, &tp, &[], false, false)?;
            assert_eq!(
                receipt.journal.bytes,
                fs::read(source.join(format!("{stem}.journal.bin")))?
            );
            transactions.push(receipt);
        }
        let stem = batch["stem"].as_str().ok_or("stem")?;
        let input = fs::read(source.join(format!("{stem}.bin")))?;
        if !transactions.is_empty() {
            assert!(
                default_executor()
                    .execute(env(&input, &[], true)?, &bp)
                    .is_err(),
                "missing transaction receipt must reject"
            );
        }
        let receipt = prove(target, stem, &input, &bp, &transactions, true, false)?;
        assert_eq!(
            receipt.journal.bytes,
            fs::read(source.join(format!("{stem}.journal.bin")))?
        );
        batches.push(receipt);
    }
    let input = fs::read(source.join("aggregate.bin"))?;
    assert!(
        default_executor()
            .execute(env(&input, &[], true)?, &ap)
            .is_err(),
        "missing batch receipts must reject"
    );
    let receipt = prove(target, "aggregate", &input, &ap, &batches, true, false)?;
    assert_eq!(
        receipt.journal.bytes,
        fs::read(source.join("aggregate.journal.bin"))?
    );
    assert_eq!(
        <[u8; 32]>::from(receipt.inner.succinct()?.control_id),
        vprogs_zk_backend_risc0_covenant::script::succinct_consts::SUCCINCT_CONTROL_ID
    );
    native_check(&receipt, &bp, &ap)?;
    save(
        target,
        "complete.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"REAL_RECURSIVE_PUBLIC_BUNDLE", "developmentMode":false,"nativeScriptEngineVerifiedWithDerivedAnchor":true,"actualTN10Settlement":false,"stateRoot":m["stateRoot"],"spendableSompi":m["spendableSompi"],"omittedTransactions":m["omittedTransactions"]}),
        )?,
    )?;
    Ok(())
}

fn native_check(receipt: &Receipt, batch: &[u8], aggregate: &[u8]) -> Result<()> {
    use kaspa_consensus_core::tx::TransactionOutpoint;
    use risc0_zkvm::sha::Digestible;
    use vprogs_zk_backend_risc0_covenant::{
        script::{CommonPins, RedeemPins, SuccinctPins},
        Settlement, SettlementInput, SettlementWitness, SuccinctWitness,
    };
    struct Anchor(Hash);
    impl kaspa_txscript::seq_commit_accessor::SeqCommitAccessor for Anchor {
        fn is_chain_ancestor_from_pov(&self, _: Hash) -> Option<bool> {
            Some(true)
        }
        fn seq_commitment_within_depth(&self, _: Hash) -> Option<Hash> {
            Some(self.0)
        }
    }
    let j = &receipt.journal.bytes;
    assert_eq!(j.len(), 352);
    let h = |i| Hash::from_bytes(j[i..i + 32].try_into().unwrap());
    let s = receipt.inner.succinct()?;
    let seal: Vec<_> = s.seal.iter().flat_map(|n| n.to_le_bytes()).collect();
    let control: Vec<_> = s
        .control_inclusion_proof
        .digests
        .iter()
        .flat_map(|d| <[u8; 32]>::from(*d))
        .collect();
    let image = compute_image_id(aggregate)?.into();
    let bi = compute_image_id(batch)?.into();
    let claim = s.claim.digest().into();
    let lane = h(320);
    let cov = h(160);
    let settlement = Settlement::build(&SettlementInput {
        covenant_id: cov,
        pins: RedeemPins::Succinct(SuccinctPins {
            common: CommonPins {
                program_id: &image,
                tx_image_id: j[192..224].try_into()?,
                batch_image_id: &bi,
                lane_key: &lane,
                permission_output_value: 50_000_000,
            },
        }),
        prev_state: j[0..32].try_into()?,
        prev_lane_tip: &h(32),
        new_state: j[64..96].try_into()?,
        new_lane_tip: &h(96),
        block_prove_to: Hash::from_bytes([3; 32]),
        prev_outpoint: TransactionOutpoint::new(Hash::from_bytes([4; 32]), 0),
        value: 100_000_000,
        witness: SettlementWitness::Succinct(SuccinctWitness {
            seal: &seal,
            claim: &claim,
            control_index: s.control_inclusion_proof.index,
            control_digests: &control,
            deposit_spk_hash: j[288..320].try_into()?,
        }),
        permission_spk_hash: j[256..288].try_into()?,
    });
    let units = settlement.covenant_input_script_units(cov, &Anchor(h(128)));
    println!(
        "{}",
        json!({"syntheticNativeScriptEngineCheck":true,"scriptUnits":format!("{units:?}"),"actualTN10Settlement":false})
    );
    Ok(())
}
