//! Captures are checked by the existing native validator before any exported
//! guest input is used. Expectations belong to the trusted controller, not GPU.
use super::*;
use std::process::Command;
pub fn record(c: &Value, label: &str) -> Result<Value> {
    let found: Vec<_> = c["records"]
        .as_array()
        .ok_or("records")?
        .iter()
        .filter(|r| r["label"] == label)
        .collect();
    require(found.len() == 1, "missing/duplicate capture record")?;
    let raw: Value = serde_json::from_str(found[0]["raw"].as_str().ok_or("wire record")?)?;
    require(raw.get("error").is_none(), "RPC error")?;
    Ok(raw["params"].clone())
}
pub fn export(validator: &Path, sha: &str, capture: &Path, cov: H) -> Result<lane::Input> {
    require(
        trusted::sha(&fs::read(validator)?) == sha,
        "independently expected native validator binary",
    )?;
    let output = Command::new(validator)
        .args(["verify", &hex::encode(chain::LANE)])
        .arg(capture)
        .output()?;
    require(
        output.status.success(),
        "native capture validation/export failed; retain capture and inspect validator separately",
    )?;
    // The old validator's `export` additionally executes its original 100-score
    // demo guest. Reuse its full native reconstruction (`verify`) but map the
    // already-verified bodies directly for the reviewed long-gap private guest.
    from_capture(&read(capture)?, cov)
}
pub(crate) fn from_capture(c: &Value, cov: H) -> Result<lane::Input> {
    use kaspa_rpc_core::GetSeqCommitLaneProofResponse;
    use kaspa_smt::proof::{OwnedSmtProof, ProofTerminal};
    fn anchor(v: Value) -> Result<lane::Anchor> {
        let p: GetSeqCommitLaneProofResponse = serde_json::from_value(v)?;
        let active = p
            .lane
            .ok_or("inactive/expired lane requires a new activation and trial seed")?;
        let proof = OwnedSmtProof::from_bytes(&p.smt_proof)?;
        let depth = match proof.terminal {
            ProofTerminal::Collapsed { depth } => depth,
            _ => return Err("active collapsed lane inclusion required".into()),
        };
        Ok(lane::Anchor {
            parent_seq: p.parent_seq_commit.into(),
            payload_ctx: p.payload_and_ctx_digest.into(),
            shortcut: p.inactivity_shortcut.into(),
            blue_score: active.blue_score,
            bitmap: proof.bitmap,
            depth,
            siblings: proof.siblings.into_iter().map(Into::into).collect(),
        })
    }
    let sp: GetSeqCommitLaneProofResponse = serde_json::from_value(record(c, "start-proof")?)?;
    let old_tip: H = sp.lane.ok_or("inactive lane start")?.tip.into();
    let start = record(c, "start-block")?;
    let accepted = record(c, "accepted")?;
    let count = n(&c["intervalBlocks"])? as usize;
    let mut timestamp = n(&start["block"]["header"]["timestamp"])?;
    let mut blocks = vec![];
    let rawblocks = accepted["chainBlockAcceptedTransactions"]
        .as_array()
        .ok_or("accepted blocks")?;
    require(rawblocks.len() >= count, "truncated complete interval")?;
    for b in rawblocks.iter().take(count) {
        let mut txs = vec![];
        for (index, raw) in b["acceptedTransactions"]
            .as_array()
            .ok_or("accepted bodies")?
            .iter()
            .enumerate()
        {
            let rpc: kaspa_rpc_core::RpcOptionalTransaction = serde_json::from_value(raw.clone())?;
            let tx: Transaction = rpc.try_into()?;
            if tx.subnetwork_id.as_bytes() == &chain::LANE {
                require(tx.version == 1, "native v1 required")?;
                let mut t = native::lane_tx(&tx);
                t.merge_idx = u32::try_from(index)?;
                txs.push(t);
            }
        }
        blocks.push(lane::Block {
            prev_timestamp: timestamp,
            daa_score: n(&b["chainBlockHeader"]["daaScore"])?,
            blue_score: n(&b["chainBlockHeader"]["blueScore"])?,
            txs,
        });
        timestamp = n(&b["chainBlockHeader"]["timestamp"])?;
    }
    Ok(lane::Input {
        lane: chain::LANE,
        covenant: cov,
        old_state: [0; 32],
        old_tip,
        start_seq: h(&start["block"]["header"]["acceptedIdMerkleRoot"])?,
        start: anchor(record(c, "start-proof")?)?,
        end: anchor(record(c, "end-proof")?)?,
        blocks,
    })
}
pub fn seed(validator: &Path, sha: &str, capture: &Path, out: &Path) -> Result<()> {
    let frozen = out.with_extension("capture.json");
    save(&frozen, &fs::read(capture)?)?;
    let capture = frozen.as_path();
    let lane = export(validator, sha, capture, [0; 32])?;
    let c = read(capture)?;
    let end = record(&c, "end-block")?;
    let ep: kaspa_rpc_core::GetSeqCommitLaneProofResponse =
        serde_json::from_value(record(&c, "end-proof")?)?;
    let tip = ep.lane.ok_or("active end lane required")?.tip;
    report(
        out,
        &json!({"scope":"VERIFIED_NATIVE_LANE_SEED","lane":hex::encode(chain::LANE),
        "tip":tip.to_string(),"lastTouch":lane.end.blue_score,
        "endBlock":end["block"]["header"]["hash"],"seq":end["block"]["header"]["acceptedIdMerkleRoot"],
        "captureSha256":trusted::sha(&fs::read(capture)?),"validatorSha256":sha}),
    )
}
pub fn target(path: &Path, expected_sha: &str) -> Result<Value> {
    let bytes = fs::read(path)?;
    require(
        trusted::sha(&bytes) == expected_sha,
        "trusted target hash; never use GPU metadata",
    )?;
    let t: Value = serde_json::from_slice(&bytes)?;
    require(
        t["schema"] == "KPI_RECOVERY_TN10_FROZEN_BATCH_V1"
            && t["image"] == IMAGE
            && t["join"] == JOIN
            && t["programSha256"] == PROGRAM_SHA,
        "frozen identities",
    )?;
    let stage = t["stage"].as_str().ok_or("stage")?;
    require(CASES.contains(&stage), "fixed six stages")?;
    require(
        t["cycleLimit"] == 160000000
            && t["aggregateProofSeconds"] == 3600
            && t["automaticRetry"] == false
            && t["segmentPo2"]
                == if stage == "credit-transfer" || stage.ends_with("-exit") {
                    20
                } else {
                    16
                },
        "fixed proof profile",
    )?;
    let j = hex::decode(t["journalHex"].as_str().ok_or("journal")?)?;
    require(
        j.len() == 352 && trusted::sha(&j) == t["journalSha256"],
        "full expected journal",
    )?;
    Ok(t)
}
pub fn verify_target(t: &Value, r: &risc0_zkvm::Receipt) -> Result<()> {
    require(
        r.journal.bytes == hex::decode(t["journalHex"].as_str().ok_or("journal")?)?,
        "receipt journal differs from independently frozen target",
    )?;
    trusted::verify_claim(
        r,
        trusted::digest(IMAGE)?,
        &hex::decode(t["journalHex"].as_str().ok_or("journal")?)?,
        trusted::digest(JOIN)?,
    )
}
pub fn verify(path: &Path, sha: &str, receipt: &Path, out: &Path) -> Result<()> {
    let t = target(path, sha)?;
    let r = trusted::read_receipt(receipt)?;
    verify_target(&t, &r)?;
    let neg = trusted::crypto_negatives(&r, trusted::digest(IMAGE)?)?;
    mkdir(out)?;
    report(
        &out.join("verification.json"),
        &json!({"scope":"INDEPENDENT_CPU_REAL_CHAIN_INPUT_RECEIPT_NOT_CHAIN_ACCEPTANCE",
        "targetSha256":sha,"receiptSha256":trusted::sha(&fs::read(receipt)?),"image":IMAGE,"join":JOIN,"journalSha256":t["journalSha256"],
        "noUnresolvedAssumptions":true,"developmentMode":false,"negativeControls":neg}),
    )
}
/// Future producer entry point. Its caller must put the entire process group
/// under the shared external deadline and independent lease guard. Preparation
/// and tests never call this function.
pub fn prove(path: &Path, sha: &str, out: &Path) -> Result<()> {
    use risc0_zkvm::{default_prover, ExecutorEnv, ProverOpts};
    require(
        std::env::var("RISC0_PROVER").as_deref() == Ok("ipc"),
        "real IPC prover required",
    )?;
    require(
        std::env::var("KPI_TN10_EXTERNAL_DEADLINE").as_deref() == Ok("3600"),
        "external shared process-group deadline required",
    )?;
    let t = target(path, sha)?;
    let dir = path.parent().ok_or("target parent")?;
    let program = fs::read(dir.join("guest.program.bin"))?;
    let bytes = fs::read(dir.join("input.bin"))?;
    require(
        trusted::sha(&program) == PROGRAM_SHA
            && risc0_zkvm::compute_image_id(&program)?.to_string() == IMAGE
            && trusted::sha(&bytes) == t["inputSha256"],
        "fixed input and guest bytes",
    )?;
    let input: Input = bincode::deserialize(&bytes)?;
    require(bincode::serialize(&input)? == bytes, "canonical input")?;
    let expected = app::execute(&input, &verifier());
    require(
        hex::encode(&expected.journal) == t["journalHex"]
            && trusted::sha(&bincode::serialize(&expected.state)?) == t["stateSha256"],
        "CPU recomputation differs from trusted target",
    )?;
    require(
        t["cycleLimit"] == 160000000 && t["aggregateProofSeconds"] == 3600,
        "fixed proof limits",
    )?;
    let po2 = match t["stage"].as_str() {
        Some("deposit" | "bob-reconcile" | "alice-reconcile") => 16,
        Some("credit-transfer" | "bob-exit" | "alice-exit") => 20,
        _ => return Err("stage".into()),
    };
    require(t["segmentPo2"] == po2, "segment setting")?;
    mkdir(out)?;
    let start = Instant::now();
    let mut env = ExecutorEnv::builder();
    env.write_slice(&[u32::try_from(bytes.len())?])
        .write_slice(&bytes)
        .segment_limit_po2(po2 as u32)
        .session_limit(Some(160_000_000));
    let info = default_prover().prove_with_opts(env.build()?, &program, &ProverOpts::succinct())?;
    let receipt = bincode::serialize(&info.receipt)?;
    // Preserve returned candidate before checking it, including on failure.
    save(&out.join("candidate-receipt.bin"), &receipt)?;
    report(&out.join("stats.json"), &serde_json::to_value(&info.stats)?)?;
    verify_target(&t, &info.receipt)?;
    require(info.stats.user_cycles <= 160_000_000, "cycle limit")?;
    save(&out.join("receipt.bin"), &receipt)?;
    report(
        &out.join("complete.json"),
        &json!({"targetSha256":sha,"receiptSha256":trusted::sha(&receipt),"seconds":start.elapsed().as_secs_f64(),"independentCpuVerificationRequired":true,"nativeChainAcceptance":false}),
    )
}
pub(crate) fn lifecycle(stage: &str, s: &State) -> Result<()> {
    let a = s.accounting()?;
    let (reserve, private, pending, unpaid) = match stage {
        "deposit" => (1_000_000_000, 0, 1_000_000_000, 0),
        "credit-transfer" => (1_000_000_000, 1_000_000_000, 0, 0),
        "bob-exit" => (1_000_000_000, 600_000_000, 0, 400_000_000),
        "bob-reconcile" => (600_000_000, 600_000_000, 0, 0),
        "alice-exit" => (600_000_000, 0, 0, 600_000_000),
        "alice-reconcile" => (0, 0, 0, 0),
        _ => return Err("unknown lifecycle stage".into()),
    };
    require(
        (
            a.reserve_principal,
            a.private_liability,
            a.pending_deposits,
            a.unpaid_exits,
        ) == (reserve, private, pending, unpaid),
        "actual batch does not achieve intended lifecycle checkpoint",
    )
}
pub fn freeze(
    validator: &Path,
    sha: &str,
    program: &Path,
    stage: &str,
    capture: &Path,
    checkpoint: &Path,
    out: &Path,
) -> Result<()> {
    let cp = read(checkpoint)?;
    require(
        cp["schema"] == "KPI_RECOVERY_TN10_CHECKPOINT_V1"
            && cp["status"] == "CAPTURED_NATIVE_ACCEPTANCE_OFFLINE_RECHECK_REQUIRED",
        "accepted checkpoint required",
    )?;
    let expected = match cp["completed"].as_str() {
        Some("initialize") => "deposit",
        Some("deposit") => "credit-transfer",
        Some("credit-transfer") => "bob-exit",
        Some("bob-exit") => "bob-reconcile",
        Some("bob-reconcile") => "alice-exit",
        Some("alice-exit") => "alice-reconcile",
        _ => return Err("checkpoint stage".into()),
    };
    require(stage == expected, "stage order")?;
    let state_path = checkpoint
        .parent()
        .ok_or("checkpoint parent")?
        .join("state.bin");
    let prior = state(&state_path)?;
    require(
        trusted::sha(&fs::read(&state_path)?) == cp["stateSha256"]
            && hex::encode(prior.root()) == cp["stateRoot"],
        "checkpoint state hash",
    )?;
    let program_bytes = fs::read(program)?;
    require(
        trusted::sha(&program_bytes) == PROGRAM_SHA
            && risc0_zkvm::compute_image_id(&program_bytes)?.to_string() == IMAGE,
        "reviewed guest only",
    )?;
    // Copy first: the verified bytes, frozen input and retained evidence must
    // refer to one immutable capture, not a file changing between subprocesses.
    mkdir(out)?;
    save(&out.join("capture.json"), &fs::read(capture)?)?;
    let mut lane = export(validator, sha, &out.join("capture.json"), prior.covenant)?;
    let c = read(out.join("capture.json"))?;
    require(
        record(&c, "start-block")?["block"]["header"]["hash"] == cp["nextCaptureStart"],
        "capture gap or restart from wrong endpoint",
    )?;
    require(
        lane.old_tip == prior.lane_tip && lane.start.blue_score == prior.last_touch,
        "proof-wait anchor changed lane tip/last-touch; reconstruct complete interval instead",
    )?;
    lane.old_state = prior.root();
    let input = Input { state: prior, lane };
    let output = app::execute(&input, &verifier());
    lifecycle(stage, &output.state)?;
    let bytes = bincode::serialize(&input)?;
    require(
        bytes.len() <= 1024 * 1024,
        "reviewed guest input limit exceeded; do not silently change guest",
    )?;
    save(&out.join("input.bin"), &bytes)?;
    save(&out.join("prior-state.bin"), &fs::read(state_path)?)?;
    save(&out.join("state.bin"), &bincode::serialize(&output.state)?)?;
    save(&out.join("expected.bin"), &bincode::serialize(&output)?)?;
    save(&out.join("journal.bin"), &output.journal)?;
    save(&out.join("guest.program.bin"), &program_bytes)?;
    save(&out.join("prior-checkpoint.json"), &fs::read(checkpoint)?)?;
    let end = record(&c, "end-block")?["block"]["header"]["hash"].clone();
    let t = json!({"schema":"KPI_RECOVERY_TN10_FROZEN_BATCH_V1","trial":cp["trial"],"stage":stage,"image":IMAGE,"join":JOIN,"programSha256":PROGRAM_SHA,
        "inputSha256":trusted::sha(&bytes),"priorStateSha256":trusted::sha(&fs::read(out.join("prior-state.bin"))?),"stateSha256":trusted::sha(&bincode::serialize(&output.state)?),
        "checkpointSha256":trusted::sha(&fs::read(checkpoint)?),"captureSha256":trusted::sha(&fs::read(out.join("capture.json"))?),"validatorSha256":sha,
        "stateOutpoint":cp["stateOutpoint"],"startBlock":cp["nextCaptureStart"],"endBlock":end,
        "journalHex":hex::encode(&output.journal),"journalSha256":trusted::sha(&output.journal),
        "cycleLimit":160000000,"segmentPo2":if stage=="credit-transfer"||stage.ends_with("-exit"){20}else{16},
        "aggregateProofSeconds":3600,"automaticRetry":false,"proofStarted":false,"networkAcceptance":false});
    report(&out.join("target.json"), &t)?;
    report(
        &out.join("freeze-report.json"),
        &json!({"targetSha256":trusted::sha(&fs::read(out.join("target.json"))?),"accounting":output.state.accounting()?,"events":output.events}),
    )?;
    println!("{}", trusted::sha(&fs::read(out.join("target.json"))?));
    Ok(())
}

// Confirm the exact signed tx occurs in the *complete validated* accepted
// interval. A submitTransaction response or a tx-id-shaped string is insufficient.
pub fn accepted(capture: &Value, txid: &str) -> Result<()> {
    let accepted = record(capture, "accepted")?;
    let count = n(&capture["intervalBlocks"])? as usize;
    let mut found = 0;
    for b in accepted["chainBlockAcceptedTransactions"]
        .as_array()
        .ok_or("accepted blocks")?
        .iter()
        .take(count)
    {
        for raw in b["acceptedTransactions"]
            .as_array()
            .ok_or("accepted bodies")?
        {
            let rpc: kaspa_rpc_core::RpcOptionalTransaction = serde_json::from_value(raw.clone())?;
            let tx: Transaction = rpc.try_into()?;
            if tx.id().to_string() == txid {
                found += 1;
            }
        }
    }
    require(
        found == 1,
        "required exact native transaction missing/duplicated in accepted interval",
    )
}

pub fn checkpoint(
    validator: &Path,
    sha: &str,
    capture: &Path,
    signed: &Path,
    previous: &Path,
    out: &Path,
) -> Result<()> {
    let tx = read(signed)?;
    let prev = read(previous)?;
    let kind = tx["kind"].as_str().ok_or("kind")?;
    let (s, start, completed) = if kind == "initialize" {
        require(
            prev["kind"] == "bootstrap" && prev["trial"] == tx["trial"],
            "bootstrap lineage",
        )?;
        let s: State = bincode::deserialize(&hex::decode(
            tx["details"]["stateHex"].as_str().ok_or("genesis state")?,
        )?)?;
        require(
            state_script(&s)
                == hex::decode(
                    prev["details"]["stateRedeem"]
                        .as_str()
                        .ok_or("genesis script")?,
                )?,
            "genesis restriction",
        )?;
        (
            s,
            prev["details"]["seed"]["endBlock"].clone(),
            "initialize".to_string(),
        )
    } else {
        require(
            kind == "settlement",
            "checkpoint only after initialization/settlement",
        )?;
        let t = target(
            previous,
            tx["details"]["targetSha256"]
                .as_str()
                .ok_or("target hash")?,
        )?;
        require(tx["trial"] == t["trial"], "checkpoint trial")?;
        // Re-run receipt verification. A report saying verified is not proof.
        let request = read(signed.parent().ok_or("signed parent")?.join("request.json"))?;
        verify_target(
            &t,
            &trusted::read_receipt(Path::new(
                request["receiptPath"].as_str().ok_or("receiptPath")?,
            ))?,
        )?;
        let s = state(previous.parent().ok_or("target parent")?.join("state.bin"))?;
        require(
            trusted::sha(&bincode::serialize(&s)?) == t["stateSha256"],
            "post-state pin",
        )?;
        (
            s,
            t["endBlock"].clone(),
            t["stage"].as_str().ok_or("stage")?.to_string(),
        )
    };
    mkdir(out)?;
    let frozen = out.join("acceptance-capture.json");
    save(&frozen, &fs::read(capture)?)?;
    let capture = frozen.as_path();
    export(validator, sha, capture, s.covenant)?;
    let c = read(capture)?;
    require(
        record(&c, "start-block")?["block"]["header"]["hash"] == start,
        "acceptance capture must cover frozen endpoint through settlement",
    )?;
    accepted(&c, tx["transactionId"].as_str().ok_or("txid")?)?;
    if kind == "initialize" {
        accepted(&c, prev["transactionId"].as_str().ok_or("bootstrap txid")?)?;
    }
    let rpc: kaspa_rpc_core::RpcTransaction = serde_json::from_value(tx["transaction"].clone())?;
    let native: Transaction = rpc.try_into()?;
    require(
        native.id().to_string() == tx["transactionId"]
            && native.outputs[0].value == app::STATE_RENT
            && native.outputs[0].script_public_key
                == kaspa_txscript::standard::pay_to_script_hash_script(&state_script(&s))
            && native.outputs[0].covenant
                == Some(CovenantBinding::new(0, Hash::from_bytes(s.covenant))),
        "exact accepted continuation",
    )?;
    save(&out.join("state.bin"), &bincode::serialize(&s)?)?;
    report(
        &out.join("checkpoint.json"),
        &json!({"schema":"KPI_RECOVERY_TN10_CHECKPOINT_V1","status":"CAPTURED_NATIVE_ACCEPTANCE_OFFLINE_RECHECK_REQUIRED","trial":tx["trial"],"completed":completed,
        "stateRoot":hex::encode(s.root()),"stateSha256":trusted::sha(&bincode::serialize(&s)?),"stateOutpoint":{"transactionId":native.id().to_string(),"index":0},
        "nextCaptureStart":start,"acceptanceCaptureSha256":trusted::sha(&fs::read(capture)?),"signedRecordSha256":trusted::sha(&fs::read(signed)?),"previousSha256":trusted::sha(&fs::read(previous)?),
        "accounting":s.accounting()?,"freshLiveUtxoAndSelectedChainCheckBeforeSpending":true}),
    )
}
