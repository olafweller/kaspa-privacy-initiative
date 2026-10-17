//! Real composition compatibility gate. Synthetic empty batch, no funding/RPC.
use kaspa_hashes::Hash;
use risc0_zkvm::{
    compute_image_id, default_executor, default_prover, ExecutorEnv, ProverOpts, Receipt,
};
use serde_json::{json, Value};
use std::{error::Error, fs, path::Path, time::Instant};
use vprogs_core_codec::Writer;
type Result<T> = std::result::Result<T, Box<dyn Error>>;
#[path = "../../../accelerated-bn254/host.rs"]
mod accelerated_bn254;
#[path = "../../../groth16-comparison/host.rs"]
mod groth16_comparison;
#[path = "../../../outer-proof-128m/host.rs"]
mod outer_proof_128m;
#[path = "../../../proof-classification/host.rs"]
mod proof_classification;
#[path = "../../../shielded-design/compat/host.rs"]
mod wallet_compat;

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
fn reject_execution(
    dir: &Path,
    label: &str,
    input: &[u8],
    program: &[u8],
    assumptions: &[Receipt],
) -> Result<()> {
    let result = default_executor().execute(env(input, assumptions, true)?, program);
    let error = result
        .err()
        .ok_or("negative execution unexpectedly succeeded")?;
    save(
        dir,
        &format!("{label}-rejected.json"),
        &serde_json::to_vec_pretty(
            &json!({"scope":"EXECUTION_LAYER_REJECTION_NOT_TN10", "error":format!("{error:#}")}),
        )?,
    )
}
fn a32(v: &Value) -> [u8; 32] {
    serde_json::from_value(v.clone()).unwrap()
}
fn main() -> Result<()> {
    assert!(
        std::env::var("RISC0_DEV_MODE").is_err(),
        "development mode forbidden"
    );
    let args: Vec<_> = std::env::args().collect();
    if args.get(1).is_some_and(|s| s == "wallet-image") {
        let id = compute_image_id(&fs::read(args.get(2).ok_or("wallet program")?)?)?;
        println!("pub const WALLET_IMAGE: [u32; 8] = {:?};", id.as_words());
        return Ok(());
    }
    if args.get(1).is_some_and(|s| s == "wrap") {
        if args.len() != 4 {
            return Err("wrap RAW_ELF NEW_PROGRAM".into());
        }
        let raw = fs::read(&args[2])?;
        let program =
            risc0_binfmt::ProgramBinary::new(&raw, risc0_zkos_v1compat::V1COMPAT_ELF).encode();
        let output = Path::new(&args[3]);
        save(
            output.parent().ok_or("output directory")?,
            output
                .file_name()
                .ok_or("output name")?
                .to_str()
                .ok_or("output UTF-8")?,
            &program,
        )?;
        println!("{}", compute_image_id(&program)?);
        return Ok(());
    }
    if args.get(1).is_some_and(|s| s == "verify-retained") {
        return verify_retained(&args);
    }
    assert_eq!(
        std::env::var("RISC0_PROVER").as_deref(),
        Ok("ipc"),
        "real IPC prover required"
    );
    if args.get(1).is_some_and(|s| s == "wallet-compat") {
        return wallet_compat::run(&args);
    }
    if args.get(1).is_some_and(|s| s == "wallet-metrics") {
        return wallet_compat::metrics(&args);
    }
    if args.get(1).is_some_and(|s| s == "classifier") {
        return proof_classification::run(&args);
    }
    if args.get(1).is_some_and(|s| s == "groth16") {
        return groth16_comparison::run(&args);
    }
    if args.get(1).is_some_and(|s| s == "accelerated-bn254") {
        return accelerated_bn254::run(&args);
    }
    if args.get(1).is_some_and(|s| s == "outer-proof-128m") {
        return outer_proof_128m::run(&args);
    }
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
    native_check(&receipt, &bp, &ap, None)?;
    save(
        dir,
        "complete.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"REAL_RECURSIVE_COMPATIBILITY_ONLY", "syntheticEmptyBatch":true,"nativeScriptEngineVerified":true,"actualTN10Settlement":false,"missingAssumptionRejected":true,"developmentMode":false}),
        )?,
    )?;
    Ok(())
}

/// Reverify existing cryptographic artifacts without invoking an executor/prover.
fn verify_retained(args: &[String]) -> Result<()> {
    if args.len() != 4 {
        return Err("verify-retained GATE_DIR PROGRAM_DIR".into());
    }
    let source = Path::new(&args[2]);
    let programs = Path::new(&args[3]);
    let bp = fs::read(programs.join("batch.program.bin"))?;
    let ap = fs::read(programs.join("aggregate.program.bin"))?;
    let batch: Receipt = bincode::deserialize(&fs::read(source.join("batch-receipt.bin"))?)?;
    let aggregate: Receipt =
        bincode::deserialize(&fs::read(source.join("aggregate-receipt.bin"))?)?;
    batch.verify(compute_image_id(&bp)?)?;
    aggregate.verify(compute_image_id(&ap)?)?;
    for (name, receipt) in [("batch", &batch), ("aggregate", &aggregate)] {
        assert_eq!(
            receipt.journal.bytes,
            fs::read(source.join(format!("{name}-journal.bin")))?
        );
    }
    assert_eq!(
        <[u8; 32]>::from(aggregate.inner.succinct()?.control_id),
        vprogs_zk_backend_risc0_covenant::script::succinct_consts::SUCCINCT_CONTROL_ID
    );
    native_check(&aggregate, &bp, &ap, None)?;
    let mut changed = aggregate.clone();
    changed.journal.bytes[0] ^= 1;
    assert!(
        changed.verify(compute_image_id(&ap)?).is_err(),
        "changed journal rejected by SDK"
    );
    assert!(
        native_check(&changed, &bp, &ap, None).is_err(),
        "changed journal rejected by native script"
    );
    println!(
        "{}",
        json!({"scope":"REVERIFY_RETAINED_SYNTHETIC_GATE", "batchReceiptVerified":true,"aggregateReceiptVerified":true,"nativeScriptEngineVerified":true,"actualTN10Settlement":false})
    );
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
            reject_execution(
                target,
                &format!("{stem}-missing-transaction"),
                &input,
                &bp,
                &[],
            )?;
        }
        let receipt = prove(target, stem, &input, &bp, &transactions, true, false)?;
        assert_eq!(
            receipt.journal.bytes,
            fs::read(source.join(format!("{stem}.journal.bin")))?
        );
        let proof_len = u32::from_le_bytes(input[128..132].try_into()?) as usize;
        let mut expired = input.clone();
        expired[228 + proof_len] = 1;
        assert!(
            vprogs_zk_abi::batch_processor::Inputs::decode(&expired)?
                .batch
                .lane_expired
        );
        reject_execution(
            target,
            &format!("{stem}-expired-lane"),
            &expired,
            &bp,
            &transactions,
        )?;
        batches.push(receipt);
    }
    let input = fs::read(source.join("aggregate.bin"))?;
    reject_execution(target, "aggregate-missing-batches", &input, &ap, &[])?;
    let receipt = prove(target, "aggregate", &input, &ap, &batches, true, false)?;
    // A genuine aggregate receipt cannot satisfy a batch-image assumption.
    reject_execution(
        target,
        "aggregate-wrong-image",
        &input,
        &ap,
        std::slice::from_ref(&receipt),
    )?;
    // An omission control may leave every batch empty. Such a batch has no
    // transaction assumption, so a wrong transaction receipt cannot be tested.
    if let Some(first) = m["batches"].as_array().ok_or("batches")?.iter().find(|b| {
        b["transactions"]
            .as_array()
            .is_some_and(|txs| !txs.is_empty())
    }) {
        let stem = first["stem"].as_str().ok_or("stem")?;
        let first_batch = fs::read(source.join(format!("{stem}.bin")))?;
        reject_execution(
            target,
            "batch-wrong-transaction-image",
            &first_batch,
            &bp,
            std::slice::from_ref(&receipt),
        )?;
    }
    assert_eq!(
        receipt.journal.bytes,
        fs::read(source.join("aggregate.journal.bin"))?
    );
    assert_eq!(
        <[u8; 32]>::from(receipt.inner.succinct()?.control_id),
        vprogs_zk_backend_risc0_covenant::script::succinct_consts::SUCCINCT_CONTROL_ID
    );
    assert_eq!(
        receipt.journal.bytes[192..224],
        <[u8; 32]>::from(compute_image_id(&tp)?)
    );
    native_check(&receipt, &bp, &ap, None)?;
    let expected: Hash = m["anchorSeqCommit"]
        .as_str()
        .ok_or("fixed captured anchor missing")?
        .parse()?;
    let fixed = native_check(&receipt, &bp, &ap, Some(expected));
    let omitted = m["omittedTransactions"].as_u64().ok_or("omitted count")?;
    assert_eq!(
        fixed.is_ok(),
        omitted == 0,
        "fixed captured anchor acceptance"
    );
    let mut wrong: [u8; 32] = expected.into();
    wrong[0] ^= 1;
    assert!(
        native_check(&receipt, &bp, &ap, Some(Hash::from_bytes(wrong))).is_err(),
        "wrong anchor rejected"
    );
    save(
        target,
        "complete.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"REAL_RECURSIVE_PUBLIC_BUNDLE", "developmentMode":false,"nativeScriptEngineVerifiedWithDerivedAnchor":true,"fixedCapturedAnchorAccepted":fixed.is_ok(),"wrongAnchorRejected":true,"actualTN10Settlement":false,"stateRoot":m["stateRoot"],"spendableSompi":m["spendableSompi"],"omittedTransactions":m["omittedTransactions"]}),
        )?,
    )?;
    Ok(())
}

fn native_check(
    receipt: &Receipt,
    batch: &[u8],
    aggregate: &[u8],
    expected: Option<Hash>,
) -> Result<()> {
    use kaspa_consensus_core::{hashing::sighash::SigHashReusedValuesUnsync, tx::*};
    use kaspa_txscript::{
        caches::Cache, covenants::CovenantsContext, engine_context::EngineContext,
        standard::pay_to_script_hash_script, EngineFlags, TxScriptEngine,
    };
    use risc0_zkvm::sha::Digestible;
    use vprogs_zk_backend_risc0_covenant::{
        script::{CommonPins, RedeemPins, SuccinctPins},
        Settlement, SettlementInput, SettlementWitness, SuccinctWitness,
    };
    struct Anchor(Hash);
    impl kaspa_txscript::seq_commit_accessor::SeqCommitAccessor for Anchor {
        fn is_chain_ancestor_from_pov(&self, block: Hash) -> Option<bool> {
            Some(block == Hash::from_bytes([3; 32]))
        }
        fn seq_commitment_within_depth(&self, block: Hash) -> Option<Hash> {
            (block == Hash::from_bytes([3; 32])).then_some(self.0)
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
    // Return the actual script error for negative controls; do not classify any
    // unrelated panic/build failure as a cryptographic rejection.
    let utxo = UtxoEntry::new(
        100_000_000,
        pay_to_script_hash_script(&settlement.prev_redeem),
        0,
        false,
        Some(cov),
    );
    let pop = PopulatedTransaction::new(&settlement.transaction, vec![utxo.clone()]);
    let ctx = CovenantsContext::from_tx(&pop)?;
    let cache = Cache::new(1);
    let reused = SigHashReusedValuesUnsync::new();
    let anchor = Anchor(expected.unwrap_or(h(128)));
    let ec = EngineContext::new(&cache)
        .with_reused(&reused)
        .with_seq_commit_accessor(&anchor)
        .with_covenants_ctx(&ctx);
    let mut vm = TxScriptEngine::from_transaction_input(
        &pop,
        &settlement.transaction.inputs[0],
        0,
        &utxo,
        ec,
        EngineFlags::default(),
    );
    vm.execute()?;
    let units = vm.used_script_units();
    println!(
        "{}",
        json!({"syntheticNativeScriptEngineCheck":true,"scriptUnits":format!("{units:?}"),"actualTN10Settlement":false})
    );
    Ok(())
}
