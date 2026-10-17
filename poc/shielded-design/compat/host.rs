//! Bounded local wallet -> transaction -> reference batch/aggregate experiment.
use super::*;
#[path = "types.rs"]
mod types;
fn wire<T: serde::Serialize>(value: &T) -> Result<Vec<u8>> {
    Ok(risc0_zkvm::serde::to_vec(value)?
        .into_iter()
        .flat_map(u32::to_le_bytes)
        .collect())
}
fn rejection(
    dir: &Path,
    name: &str,
    bytes: &[u8],
    program: &[u8],
    assumptions: &[Receipt],
) -> Result<()> {
    let result = default_executor().execute(super::env(bytes, assumptions, false)?, program);
    let error = result
        .err()
        .ok_or("invalid operation unexpectedly executed")?;
    save(
        dir,
        &format!("{name}-rejected.json"),
        &serde_json::to_vec_pretty(&json!({
            "scope":"LOCAL_EXECUTION_ABORT_NOT_PROVEN_NOOP_OR_NATIVE_REJECTION", "error":format!("{error:#}")
        }))?,
    )
}
pub(super) fn run(args: &[String]) -> Result<()> {
    if args.len() != 6 {
        return Err(
            "wallet-compat PREPARED_DIR REFERENCE_PROGRAM_DIR COMPAT_PROGRAM_DIR NEW_RESULT_DIR"
                .into(),
        );
    }
    let prepared = Path::new(&args[2]);
    let reference = Path::new(&args[3]);
    let programs = Path::new(&args[4]);
    let out = Path::new(&args[5]);
    fs::create_dir(out)?;
    let manifest: Value = serde_json::from_slice(&fs::read(prepared.join("bundle.json"))?)?;
    assert_eq!(manifest["batches"].as_array().unwrap().len(), 1);
    let batch_stem = manifest["batches"][0]["stem"]
        .as_str()
        .ok_or("batch stem")?;
    let txs = manifest["batches"][0]["transactions"]
        .as_array()
        .ok_or("transactions")?;
    assert_eq!(txs.len(), 1);
    let tx_stem = txs[0].as_str().ok_or("transaction stem")?;
    let native: kpi_takeover_common::Input =
        serde_json::from_slice(&fs::read(prepared.join(format!("{tx_stem}.json")))?)?;
    let wallet_program = fs::read(programs.join("wallet.program.bin"))?;
    let adapter_program = fs::read(programs.join("adapter.program.bin"))?;
    let batch_program = fs::read(reference.join("batch.program.bin"))?;
    let aggregate_program = fs::read(reference.join("aggregate.program.bin"))?;
    let fixture = types::WalletInput {
        native_id: kpi_takeover_common::app::lane_id(&native.tx),
        synthetic_secret: [7; 32],
        amount: 1_000_000_000,
        pay: 400_000_000,
        change: 600_000_000,
        fee: 0,
    };
    save(
        out,
        "synthetic-wallet-input.json",
        &serde_json::to_vec_pretty(&fixture)?,
    )?;
    let mut invalid = fixture.clone();
    invalid.pay += 1;
    rejection(
        out,
        "wallet-inflation",
        &wire(&invalid)?,
        &wallet_program,
        &[],
    )?;
    let wallet = prove(
        out,
        "wallet",
        &wire(&fixture)?,
        &wallet_program,
        &[],
        false,
        false,
    )?;
    assert_eq!(wallet.journal.bytes.len(), 96);
    let input = types::AdapterInput {
        native: native.clone(),
        wallet_journal: wallet.journal.bytes.clone(),
        host_requests_skip: false,
    };
    rejection(out, "missing-wallet", &wire(&input)?, &adapter_program, &[])?;
    let mut wrong = input.clone();
    wrong.wallet_journal[32] ^= 1;
    rejection(
        out,
        "wrong-wallet-journal",
        &wire(&wrong)?,
        &adapter_program,
        std::slice::from_ref(&wallet),
    )?;
    let mut skip = input.clone();
    skip.host_requests_skip = true;
    rejection(
        out,
        "host-forged-reject",
        &wire(&skip)?,
        &adapter_program,
        std::slice::from_ref(&wallet),
    )?;
    let mut changed = wallet.clone();
    changed.journal.bytes[32] ^= 1;
    assert!(changed.verify(compute_image_id(&wallet_program)?).is_err());
    let baseline_program = fs::read(reference.join("transaction.program.bin"))?;
    let baseline =
        default_executor().execute(super::env(&wire(&native)?, &[], false)?, &baseline_program)?;
    save(
        out,
        "baseline-profile.json",
        &serde_json::to_vec_pretty(&json!({
            "scope":"EXECUTION_ONLY_NOT_PROOF", "segments":baseline.segments.iter().map(|s|s.po2).collect::<Vec<_>>()
        }))?,
    )?;
    let adapter = prove(
        out,
        "adapter",
        &wire(&input)?,
        &adapter_program,
        std::slice::from_ref(&wallet),
        false,
        false,
    )?;
    assert_eq!(
        adapter.journal.bytes,
        fs::read(prepared.join(format!("{tx_stem}.journal.bin")))?
    );
    let mut batch_input = fs::read(prepared.join(format!("{batch_stem}.bin")))?;
    batch_input[..32].copy_from_slice(&<[u8; 32]>::from(compute_image_id(&adapter_program)?));
    let mut verifier = vprogs_zk_abi::batch_processor::Verifier::new(&batch_input, |image, j| {
        assert_eq!(
            image,
            &<[u8; 32]>::from(compute_image_id(&adapter_program).unwrap())
        );
        assert_eq!(j, adapter.journal.bytes);
    });
    let (tip, score) = verifier.verify_batch();
    let mut batch_journal = vec![];
    verifier.commit_batch_transition::<vprogs_zk_backend_risc0_api::Sha256>(
        &mut batch_journal,
        &tip,
        score,
    );
    save(out, "batch-input.bin", &batch_input)?;
    let batch = prove(
        out,
        "batch",
        &batch_input,
        &batch_program,
        &[adapter],
        true,
        false,
    )?;
    assert_eq!(batch.journal.bytes, batch_journal);
    let original = fs::read(prepared.join("aggregate.bin"))?;
    let proof_len = u32::from_le_bytes(original[128..132].try_into()?) as usize;
    let mut aggregate_input = original[..132 + proof_len].to_vec();
    aggregate_input.write_blob(&batch_journal);
    save(out, "aggregate-input.bin", &aggregate_input)?;
    let aggregate = prove(
        out,
        "aggregate",
        &aggregate_input,
        &aggregate_program,
        &[batch],
        true,
        false,
    )?;
    assert_eq!(
        aggregate.journal.bytes[192..224],
        <[u8; 32]>::from(compute_image_id(&adapter_program)?)
    );
    assert_eq!(
        <[u8; 32]>::from(aggregate.inner.succinct()?.control_id),
        vprogs_zk_backend_risc0_covenant::script::succinct_consts::SUCCINCT_CONTROL_ID
    );
    let fixed: Hash = manifest["anchorSeqCommit"]
        .as_str()
        .ok_or("anchor")?
        .parse()?;
    native_check(&aggregate, &batch_program, &aggregate_program, Some(fixed))?;
    let mut bad: [u8; 32] = fixed.into();
    bad[0] ^= 1;
    assert!(native_check(
        &aggregate,
        &batch_program,
        &aggregate_program,
        Some(Hash::from_bytes(bad))
    )
    .is_err());
    save(
        out,
        "complete.json",
        &serde_json::to_vec_pretty(&json!({
            "scope":"LOCAL_SYNTHETIC_WALLET_COMPOSITION_WITH_REFERENCE_NATIVE_SCRIPT",
            "realSuccinctReceipts":4,"actualTN10Settlement":false,"developmentMode":false,
            "walletImage":compute_image_id(&wallet_program)?.to_string(),
            "adapterImage":compute_image_id(&adapter_program)?.to_string(),
            "resolvedWalletThroughAggregate":true,"fixedCapturedAnchorScriptAccepted":true,
            "wrongAnchorScriptRejected":true,"changedWalletJournalSdkRejected":true,
            "invalidProofCanBeProvenNoop":false,
            "invalidProofHandlingBlocker":"env::verify composition establishes validity; missing/wrong evidence aborts. No cryptographically proved invalidity/no-op classifier implemented.",
            "fullPrivateCircuit":false,"ownershipMembershipNullifierCiphertextConstraints":false,
            "fixture":"Public archived deposit relation plus synthetic preimage and checked sum; not an actual private payment."
        }))?,
    )?;
    Ok(())
}

/// One isolated wallet proof for peak-memory measurement, plus matched execution
/// profiles. The profile delta includes decoding/binding and the assumption call,
/// not an ordinary full cryptographic verifier running inside the guest.
pub(super) fn metrics(args: &[String]) -> Result<()> {
    if args.len() != 7 {
        return Err(
            "wallet-metrics PREPARED REFERENCE_PROGRAMS COMPAT_PROGRAMS FIRST_RESULT NEW_RESULT"
                .into(),
        );
    }
    let prepared = Path::new(&args[2]);
    let reference = Path::new(&args[3]);
    let programs = Path::new(&args[4]);
    let first = Path::new(&args[5]);
    let out = Path::new(&args[6]);
    fs::create_dir(out)?;
    let fixture: types::WalletInput =
        serde_json::from_slice(&fs::read(first.join("synthetic-wallet-input.json"))?)?;
    let wallet_program = fs::read(programs.join("wallet.program.bin"))?;
    let wallet = prove(
        out,
        "wallet",
        &wire(&fixture)?,
        &wallet_program,
        &[],
        false,
        false,
    )?;
    assert_eq!(
        wallet.journal.bytes,
        fs::read(first.join("wallet-journal.bin"))?
    );
    let manifest: Value = serde_json::from_slice(&fs::read(prepared.join("bundle.json"))?)?;
    let stem = manifest["batches"][0]["transactions"][0]
        .as_str()
        .ok_or("transaction")?;
    let native: kpi_takeover_common::Input =
        serde_json::from_slice(&fs::read(prepared.join(format!("{stem}.json")))?)?;
    let baseline = default_executor().execute(
        super::env(&wire(&native)?, &[], false)?,
        &fs::read(reference.join("transaction.program.bin"))?,
    )?;
    let adapted = types::AdapterInput {
        native,
        wallet_journal: wallet.journal.bytes.clone(),
        host_requests_skip: false,
    };
    let adapter = default_executor().execute(
        super::env(&wire(&adapted)?, &[wallet], false)?,
        &fs::read(programs.join("adapter.program.bin"))?,
    )?;
    assert_eq!(baseline.journal.bytes, adapter.journal.bytes);
    save(
        out,
        "matched-execution.json",
        &serde_json::to_vec_pretty(&json!({
            "scope":"EXECUTION_PROFILES_NOT_ADDITIONAL_OUTER_PROOFS",
            "baselineUserCycles":baseline.cycles(),"adapterUserCycles":adapter.cycles(),
            "additionalUserCycles":adapter.cycles().checked_sub(baseline.cycles()).ok_or("negative delta")?,
            "baselinePo2":baseline.segments.iter().map(|s|s.po2).collect::<Vec<_>>(),
            "adapterPo2":adapter.segments.iter().map(|s|s.po2).collect::<Vec<_>>(),
            "journalIdentical":true,"includesDecodingBindingAndCompositionCall":true
        }))?,
    )?;
    Ok(())
}
