mod fixtures;
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use kpi_private_note_chain::{
    self as chain, lane,
    wallet::{
        circuit::WalletCircuit,
        ledger::Ledger,
        protocol::*,
        wallet::{Engine, Wallet},
        ProofVerifier,
    },
    AcceleratedVerifier, Input, State,
};
use serde_json::json;
use std::{
    fs,
    io::Write,
    os::unix::fs::{OpenOptionsExt, PermissionsExt},
    path::Path,
    time::Instant,
};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
fn save(p: &Path, name: &str, raw: &[u8]) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(p.join(name))?;
    f.write_all(raw)?;
    f.sync_all()?;
    Ok(())
}
fn rest(serial: u8, deposit: Option<H>) -> Vec<u8> {
    use vprogs_zk_abi::withdrawal::StandardSpk;
    let script = if let Some(c) = deposit {
        StandardSpk::ScriptHash(&vprogs_zk_backend_risc0_api::delegate_entry_spk_hash(&c))
            .to_script_bytes()
            .as_slice()
            .to_vec()
    } else {
        vec![0x51]
    };
    let mut b = 1u16.to_le_bytes().to_vec();
    b.extend(1u64.to_le_bytes());
    b.extend([serial; 32]);
    b.extend(0u32.to_le_bytes());
    b.extend(0u64.to_le_bytes());
    b.extend(0u64.to_le_bytes());
    b.extend(1u64.to_le_bytes());
    b.extend(
        if deposit.is_some() {
            1_000_000_000u64
        } else {
            1000
        }
        .to_le_bytes(),
    );
    b.extend(0u16.to_le_bytes());
    b.extend((script.len() as u64).to_le_bytes());
    b.extend(script);
    b.push(0);
    b.extend(0u64.to_le_bytes());
    b.extend(chain::LANE);
    b.extend(0u64.to_le_bytes());
    b.extend(0u64.to_le_bytes());
    b
}
fn tx(serial: u8, payload: Vec<u8>, deposit: Option<H>) -> lane::Tx {
    lane::Tx {
        rest: rest(serial, deposit),
        payload,
        merge_idx: serial as u32,
    }
}
fn input(state: State, mut txs: Vec<lane::Tx>, score: u64, old_tip: H) -> Input {
    for (i, tx) in txs.iter_mut().enumerate() {
        tx.merge_idx = i as u32;
    }
    let a = lane::Anchor {
        parent_seq: [1; 32],
        payload_ctx: [2; 32],
        shortcut: [3; 32],
        blue_score: score,
        bitmap: [0; 32],
        depth: 0,
        siblings: vec![],
    };
    let key = chain_lane_key();
    let start_seq = lane::bytes(a.seq(key, lane::h(old_tip)));
    let mut end = a.clone();
    end.blue_score += 1;
    Input {
        lane: lane::Input {
            lane: chain::LANE,
            covenant: state.covenant,
            old_state: state.root(),
            old_tip,
            start: a,
            start_seq,
            blocks: vec![lane::Block {
                prev_timestamp: 1000,
                daa_score: 2000,
                blue_score: score + 1,
                txs,
            }],
            end,
        },
        state,
    }
}
fn chain_lane_key() -> kaspa_hashes::Hash {
    kaspa_seq_commit::hashing::lane_key(&chain::LANE)
}
fn generate(out: &Path) -> Result<()> {
    fs::create_dir(out)?;
    fs::set_permissions(out, fs::Permissions::from_mode(0o700))?;
    let start = Instant::now();
    let alice = Wallet::new();
    let bob = Wallet::new();
    let covenant = hash(b"unfunded native rehearsal covenant identity only");
    let deposit_tx = tx(
        1,
        chain::deposit_payload(alice.address.owner, 0),
        Some(covenant),
    );
    let reference = chain::deposit_reference(
        vprogs_l1_utils::tx_id_v1(&deposit_tx.payload, &deposit_tx.rest),
        0,
    );
    let initial = alice.note(1_000_000_000);
    let mut tree = Tree::default();
    tree.append(initial.commitment())?;
    let (path, bits) = tree.path(0)?;
    let outputs = [bob.note(400_000_000), alice.note(600_000_000)];
    let ds = [outputs[0].deliver()?, outputs[1].deliver()?];
    let mut statement = Statement::new(TRANSFER, [0; 32], tree.root());
    statement.nullifier = alice.nf(&initial);
    for i in 0..2 {
        statement.outputs[i] = ds[i].commitment;
        statement.delivery[i] = hash(&ds[i].ciphertext);
    }
    let circuit = WalletCircuit {
        statement: statement.clone(),
        witness: alice.witness(initial.clone(), outputs.clone(), path, bits),
    };
    let (constraints, satisfied) = circuit.check()?;
    assert!(satisfied);
    let setup = Instant::now();
    let engine = Engine::setup(circuit)?;
    let setup_seconds = setup.elapsed().as_secs_f64();
    let id = engine.id();
    let verifier = engine.verifier();
    save(out, "vk.bin", &engine.vk_bytes())?;
    let vk = ark_groth16::VerifyingKey::<ark_bn254::Bn254>::deserialize_compressed(
        engine.vk_bytes().as_slice(),
    )?;
    let mut raw = vec![];
    vk.serialize_uncompressed(&mut raw)?;
    save(out, "vk-uncompressed.bin", &raw)?;
    save(out, "vk-id.bin", &id)?;
    let accelerated = AcceleratedVerifier::checked(&engine.vk_bytes(), id)?;
    let genesis = State {
        covenant,
        ledger: Ledger::new(id),
    };
    let dep = input(genesis.clone(), vec![deposit_tx.clone()], 10, [0; 32]);
    let depout = chain::execute(&dep, &verifier);
    let mut credit = Statement::new(CREDIT, id, depout.state.ledger.tree.root());
    credit.deposit = reference;
    credit.deposit_owner = alice.address.owner;
    credit.deposit_value = 1_000_000_000;
    let credit = engine.prove(
        credit,
        alice.witness(
            alice.authority_note(),
            [initial.clone(), Note::dummy()],
            [[0; 32]; DEPTH],
            [false; DEPTH],
        ),
        [initial.deliver()?, Delivery::absent()],
    )?;
    let credit_tx = tx(2, chain::operation_payload(&credit, [0; 32])?, None);
    let credited_input = input(depout.state.clone(), vec![credit_tx.clone()], 11, [0; 32]);
    let credited = chain::execute(&credited_input, &verifier);
    let pay = engine.prove(
        statement,
        alice.witness(initial.clone(), outputs, path, bits),
        ds,
    )?;
    let pay_tx = tx(3, chain::operation_payload(&pay, [0; 32])?, None);
    let transfer_input = input(credited.state.clone(), vec![pay_tx.clone()], 12, [0; 32]);
    let transferred = chain::execute(&transfer_input, &verifier);
    let found = bob.discover(
        &transferred.state.ledger.deliveries,
        &transferred.state.ledger.tree,
        &transferred.state.ledger.nullifiers,
    );
    assert_eq!(found.len(), 1);
    // Save secret backup locally only; its bytes never enter public fixtures or guest input.
    save(out, "bob-local-secret-backup.bin", &bob.local_backup())?;
    save(
        out,
        "public-proving-parameters.bin",
        &engine.public_parameters()?,
    )?;
    let bob_restored = Wallet::restore_local(
        &fs::read(out.join("bob-local-secret-backup.bin"))?
            .try_into()
            .map_err(|_| "backup length")?,
    );
    let found_restored = bob_restored.discover(
        &transferred.state.ledger.deliveries,
        &transferred.state.ledger.tree,
        &transferred.state.ledger.nullifiers,
    );
    assert_eq!(found_restored.len(), 1);
    assert_eq!(found_restored[0].0.commitment(), found[0].0.commitment());
    let restore = Instant::now();
    let loaded =
        Engine::from_public_parameters(&fs::read(out.join("public-proving-parameters.bin"))?, id)?;
    let load_seconds = restore.elapsed().as_secs_f64();
    let destination_key: H =
        hex::decode("79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")?
            .try_into()
            .unwrap();
    let (note, index) = found_restored[0].clone();
    let (p, b) = transferred.state.ledger.tree.path(index)?;
    let mut exit = Statement::new(EXIT, id, transferred.state.ledger.tree.root());
    exit.nullifier = bob_restored.nf(&note);
    exit.exit_destination = chain::destination(&destination_key);
    exit.exit_value = 400_000_000;
    let exit = loaded.prove(
        exit,
        bob_restored.witness(note, [Note::dummy(), Note::dummy()], p, b),
        [Delivery::absent(), Delivery::absent()],
    )?;
    let exit_tx = tx(4, chain::operation_payload(&exit, destination_key)?, None);
    let mut competing = Statement::new(TRANSFER, id, tree.root());
    competing.nullifier = alice.nf(&initial);
    let ns = [bob.note(300_000_000), alice.note(700_000_000)];
    let d = [ns[0].deliver()?, ns[1].deliver()?];
    let competing = engine.prove(competing, alice.witness(initial.clone(), ns, path, bits), d)?;
    let mut recovery = Statement::new(RECOVER, id, depout.state.ledger.tree.root());
    recovery.deposit = reference;
    recovery.deposit_owner = alice.address.owner;
    recovery.deposit_value = 1_000_000_000;
    recovery.exit_value = 1_000_000_000;
    let refundkey: H =
        hex::decode("c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5")?
            .try_into()
            .unwrap();
    recovery.exit_destination = chain::destination(&refundkey);
    let recovery = engine.prove(
        recovery,
        alice.witness(
            alice.authority_note(),
            [Note::dummy(), Note::dummy()],
            [[0; 32]; DEPTH],
            [false; DEPTH],
        ),
        [Delivery::absent(), Delivery::absent()],
    )?;
    for (name, op) in [
        ("credit", &credit),
        ("transfer", &pay),
        ("exit", &exit),
        ("competing", &competing),
        ("recovery", &recovery),
    ] {
        verifier.verify(op)?;
        accelerated.verify(op)?;
        save(
            out,
            &format!("{name}.json"),
            &serde_json::to_vec_pretty(op)?,
        )?;
    }
    let pvk = ark_groth16::prepare_verifying_key(&vk);
    let backend = kpi_accelerated_bn254::Verifier::from_validated_program_key(&vk, id);
    let proof =
        ark_groth16::Proof::<ark_bn254::Bn254>::deserialize_compressed(pay.proof.as_slice())?;
    let inputs = pay.statement.inputs();
    assert!(ark_groth16::Groth16::<ark_bn254::Bn254>::verify_proof(
        &pvk, &proof, &inputs
    )?);
    assert!(backend.verify_inputs(&pay.proof, &inputs).is_ok());
    for i in 0..14 {
        let mut changed = inputs.clone();
        changed[i] += ark_bn254::Fr::from(1u64);
        assert!(!ark_groth16::Groth16::<ark_bn254::Bn254>::verify_proof(
            &pvk, &proof, &changed
        )?);
        assert_eq!(
            backend.verify_inputs(&pay.proof, &changed),
            Err("invalid proof")
        );
    }
    save(
        out,
        "restore-public-state.bin",
        &bincode::serialize(&transferred.state)?,
    )?;
    let mut invalid = pay.clone();
    let mut pr =
        ark_groth16::Proof::<ark_bn254::Bn254>::deserialize_compressed(pay.proof.as_slice())?;
    pr.c = -pr.c;
    invalid.proof.clear();
    pr.serialize_compressed(&mut invalid.proof)?;
    assert_eq!(accelerated.verify(&invalid), Err("invalid proof".into()));
    let invalidtx = tx(5, chain::operation_payload(&invalid, [0; 32])?, None);
    let mut malformed = pay.clone();
    malformed.proof[0] ^= 1;
    let malformedtx = tx(6, chain::operation_payload(&malformed, [0; 32])?, None);
    let cases = vec![
        ("deposit", dep),
        ("credit", credited_input),
        ("transfer", transfer_input),
        (
            "exit",
            input(
                transferred.state.clone(),
                vec![exit_tx.clone()],
                13,
                [0; 32],
            ),
        ),
        (
            "valid-invalid-valid",
            input(
                depout.state.clone(),
                vec![credit_tx.clone(), invalidtx.clone(), pay_tx.clone()],
                11,
                [0; 32],
            ),
        ),
        (
            "invalid-then-valid",
            input(
                credited.state.clone(),
                vec![invalidtx, pay_tx.clone()],
                12,
                [0; 32],
            ),
        ),
        (
            "malformed-then-valid",
            input(
                credited.state.clone(),
                vec![malformedtx, pay_tx.clone()],
                12,
                [0; 32],
            ),
        ),
        (
            "old-root-competing-next-batch",
            input(
                transferred.state.clone(),
                vec![tx(7, chain::operation_payload(&competing, [0; 32])?, None)],
                13,
                [0; 32],
            ),
        ),
        (
            "cross-batch-replay",
            input(transferred.state.clone(), vec![pay_tx], 13, [0; 32]),
        ),
        (
            "credit-then-recovery",
            input(
                credited.state.clone(),
                vec![tx(8, chain::operation_payload(&recovery, refundkey)?, None)],
                12,
                [0; 32],
            ),
        ),
        (
            "recovery-then-credit",
            input(
                depout.state.clone(),
                vec![
                    tx(8, chain::operation_payload(&recovery, refundkey)?, None),
                    credit_tx,
                ],
                12,
                [0; 32],
            ),
        ),
    ];
    let mut reports = vec![];
    for (name, case) in cases {
        let expected = chain::execute(&case, &verifier);
        let intended: Vec<u8> = match name {
            "deposit" | "credit" | "transfer" | "exit" => vec![0],
            "valid-invalid-valid" => vec![0, 1, 0],
            "invalid-then-valid" | "malformed-then-valid" => vec![1, 0],
            "recovery-then-credit" => vec![0, 1],
            _ => vec![1],
        };
        assert_eq!(
            expected
                .events
                .iter()
                .map(|e| e.verdict)
                .collect::<Vec<_>>(),
            intended,
            "intended state outcomes for {name}"
        );
        let actual = chain::execute(&case, &accelerated);
        assert_eq!(bincode::serialize(&expected)?, bincode::serialize(&actual)?);
        save(
            out,
            &format!("{name}.input.bin"),
            &bincode::serialize(&case)?,
        )?;
        save(
            out,
            &format!("{name}.expected.bin"),
            &bincode::serialize(&expected)?,
        )?;
        reports.push(json!({"case":name,"outcomes":expected.events.iter().map(|x|x.verdict).collect::<Vec<_>>(),"reserve":expected.state.ledger.reserve,"privateLiability":expected.state.ledger.private_liability,"exits":expected.exit_principals}));
    }
    save(
        out,
        "generation.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"LOCAL_NATIVE_PREIMAGE_FIXTURES_NO_TN10","walletVkId":hex::encode(id),"domain":hex::encode(domain()),"publicFields":14,"all14FieldInputMutationDifferentialChecks":true,"constraints":constraints,"setupSeconds":setup_seconds,"publicParameterReloadSeconds":load_seconds,"restoredBobDiscoveryAndExitProof":true,"secretBackupLocalOnly":true,"publicParameterBytes":fs::metadata(out.join("public-proving-parameters.bin"))?.len(),"seconds":start.elapsed().as_secs_f64(),"cases":reports}),
        )?,
    )?;
    println!("generated public scenarios; restored Bob exit verified; secrets remain local");
    Ok(())
}
fn restore(out: &Path, expected: H) -> Result<()> {
    let start = Instant::now();
    let file = out.join("bob-local-secret-backup.bin");
    assert_eq!(
        fs::metadata(&file)?.permissions().mode() & 0o777,
        0o600,
        "local secret backup mode"
    );
    let wallet = Wallet::restore_local(&fs::read(file)?.try_into().map_err(|_| "backup length")?);
    let state: State = bincode::deserialize(&fs::read(out.join("restore-public-state.bin"))?)?;
    assert_eq!(
        state.ledger.verifier, expected,
        "independent expected wallet key"
    );
    let found = wallet.discover(
        &state.ledger.deliveries,
        &state.ledger.tree,
        &state.ledger.nullifiers,
    );
    assert_eq!(found.len(), 1);
    let params = fs::read(out.join("public-proving-parameters.bin"))?;
    let parameter_sha = hex::encode(hash(&params));
    let engine = Engine::from_public_parameters(&params, expected)?;
    let reference: Operation = serde_json::from_slice(&fs::read(out.join("exit.json"))?)?;
    let (note, index) = found[0].clone();
    let (p, b) = state.ledger.tree.path(index)?;
    assert_eq!(wallet.nf(&note), reference.statement.nullifier);
    let op = engine.prove(
        reference.statement,
        wallet.witness(note, [Note::dummy(), Note::dummy()], p, b),
        [Delivery::absent(), Delivery::absent()],
    )?;
    let verifier = AcceleratedVerifier::checked(&engine.vk_bytes(), expected)?;
    verifier.verify(&op)?;
    let mut ledger = state.ledger;
    ledger.apply(&verifier, &op)?;
    save(
        out,
        "restored-bob-exit.json",
        &serde_json::to_vec_pretty(&op)?,
    )?;
    save(
        out,
        "restore-report.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"SEPARATE_LOCAL_WALLET_PROCESS_NOT_REMOTE_PROVING_OR_NATIVE_PAYOUT","expectedVkId":hex::encode(expected),"restoredOwnKeysOnly":true,"acceptedPublicDataOnly":true,"sameEconomicNullifier":true,"newActualExitProof":true,"newProofAcceptedByCurrentState":true,"publicParametersSha256":parameter_sha,"seconds":start.elapsed().as_secs_f64(),"secretMaterialPublished":false}),
        )?,
    )?;
    println!("separate restored wallet discovered its note and produced a valid fresh exit proof");
    Ok(())
}
fn profile(program: &Path, fixtures: &Path, case: &str, out: &Path, budget: u64) -> Result<()> {
    use risc0_zkvm::{compute_image_id, default_executor, ExecutorEnv};
    fs::create_dir(out)?;
    let program = fs::read(program)?;
    let expected_id = fs::read_to_string(fixtures.join("expected-image.txt"))?;
    let id = compute_image_id(&program)?;
    assert_eq!(
        id.to_string(),
        expected_id.trim(),
        "predeclared program identity"
    );
    let input = fs::read(fixtures.join(format!("{case}.input.bin")))?;
    let abort = fixtures.join(format!("{case}.abort.txt"));
    let auth = if abort.is_file() {
        Some(fs::read_to_string(abort)?)
    } else {
        None
    };
    let expected: Option<chain::Output> = if auth.is_none() {
        Some(bincode::deserialize(&fs::read(
            fixtures.join(format!("{case}.expected.bin")),
        )?)?)
    } else {
        None
    };
    if budget == 160_000_000 {
        let reference = expected
            .as_ref()
            .ok_or("160M calibration requires a complete reference")?;
        assert_eq!(
            reference.aggregate_journal.len(),
            352,
            "frozen native aggregate journal length"
        );
        assert_eq!(
            reference
                .events
                .iter()
                .map(|e| e.verdict)
                .collect::<Vec<_>>(),
            vec![0, 1, 0],
            "frozen credit-invalid-transfer-valid-transfer scenario"
        );
        save(out, "expected-journal.bin", &reference.aggregate_journal)?;
    }
    let mut b = ExecutorEnv::builder();
    b.write_slice(&[input.len() as u32])
        .write_slice(&input)
        .stdout(std::io::stdout())
        .segment_limit_po2(20)
        .session_limit(Some(budget));
    if case == "credit" {
        b.enable_profiler(out.join("accelerated-path.pprof"));
    }
    let start = Instant::now();
    let result = default_executor().execute(b.build()?, &program);
    let mut report = json!({"scope":"EXECUTION_ONLY_NOT_RECEIPT_OR_NATIVE_SETTLEMENT","case":case,"expectedImage":id.to_string(),"cycleBudget":budget,"profile":if budget==160_000_000 {"APPROVED_SEPARATE_160M_CALIBRATION"}else{"ORIGINAL_128M"},"wallLimitSeconds":900,"seconds":start.elapsed().as_secs_f64(),"developmentMode":false});
    match result {
        Ok(s) => {
            assert!(
                auth.is_none(),
                "authentication control unexpectedly completed"
            );
            assert_eq!(
                s.journal.bytes,
                expected.as_ref().unwrap().aggregate_journal,
                "exact independent reference output"
            );
            report["completed"] = json!(true);
            report["userCycles"] = json!(s.cycles());
            report["segments"] = json!(s.segments.iter().map(|x| x.po2).collect::<Vec<_>>());
            let padded: Vec<u64> = s.segments.iter().map(|x| 1u64 << x.po2).collect();
            report["segmentCount"] = json!(padded.len());
            report["paddedSegmentCycles"] = json!(padded);
            report["paddedTraceCycles"] = json!(padded.iter().sum::<u64>());
            report["paddedTraceUnit"] =
                json!("cycle slots (2^po2 per segment); not serialized trace bytes");
            report["expectedOutcomes"] = json!(expected
                .as_ref()
                .unwrap()
                .events
                .iter()
                .map(|e| e.verdict)
                .collect::<Vec<_>>());
            report["exactExpectedJournalMatched"] = json!(true);
            report["journalBytes"] = json!(s.journal.bytes.len());
            save(out, "journal.bin", &s.journal.bytes)?;
        }
        Err(e) => {
            let message = format!("{e:#}");
            if auth
                .as_ref()
                .is_some_and(|label| expected_authentication_abort(label, &message))
            {
                report["expectedAuthenticationFailureConfirmed"] = json!(true);
                report["authenticationAbort"] = json!(message);
                save(out, "report.json", &serde_json::to_vec_pretty(&report)?)?;
                return Ok(());
            }
            report["completed"] = json!(false);
            report["error"] = json!(message);
            save(out, "report.json", &serde_json::to_vec_pretty(&report)?)?;
            return Err(e.into());
        }
    }
    save(out, "report.json", &serde_json::to_vec_pretty(&report)?)?;
    Ok(())
}
fn execution_budget(command: &str, case: &str) -> Result<u64> {
    match (command, case) {
        ("profile", _) => Ok(128_000_000),
        ("profile-160m", "valid-invalid-valid") => Ok(160_000_000),
        _ => Err(
            "160M is approved only for the single frozen valid-invalid-valid calibration".into(),
        ),
    }
}
fn expected_authentication_abort(label: &str, message: &str) -> bool {
    [
        "authenticated prior private state",
        "config covenant",
        "wrong fixed lane",
        "start inclusion",
    ]
    .contains(&label)
        && message.starts_with("Guest panicked: assertion `left == right` failed: ")
        && message.contains(&format!("failed: {label}\n"))
        && message.contains("\n right: [")
}
#[cfg(test)]
mod host_tests {
    use super::*;
    #[test]
    fn larger_budget_requires_the_explicit_single_scenario_command() {
        assert_eq!(
            execution_budget("profile", "valid-invalid-valid").unwrap(),
            128_000_000
        );
        assert_eq!(execution_budget("profile", "credit").unwrap(), 128_000_000);
        assert_eq!(
            execution_budget("profile-160m", "valid-invalid-valid").unwrap(),
            160_000_000
        );
        for case in ["credit", "exit", "auth-prior-state", ""] {
            assert!(execution_budget("profile-160m", case).is_err());
        }
        assert!(execution_budget("profile-200m", "valid-invalid-valid").is_err());
    }
    #[test]
    fn resource_failures_are_not_rejection_evidence() {
        let label = "authenticated prior private state";
        assert!(expected_authentication_abort(label,"Guest panicked: assertion `left == right` failed: authenticated prior private state\n  left: [1]\n right: [2]"));
        for error in [
            "Session limit exceeded: 128000000 >= 128000000",
            "Session limit exceeded: 160000000 >= 160000000",
            "out of memory",
            "IPC failed",
            "Guest panicked: another check",
            "",
        ] {
            assert!(!expected_authentication_abort(label, error));
        }
    }
}
fn main() -> Result<()> {
    let a = std::env::args().collect::<Vec<_>>();
    match a.get(1).map(String::as_str) {
        Some("generate") if a.len() == 3 => generate(Path::new(&a[2])),
        Some("prepare") if a.len() == 4 => fixtures::prepare(Path::new(&a[2]), Path::new(&a[3])),
        Some("restore") if a.len() == 4 => restore(
            Path::new(&a[2]),
            hex::decode(&a[3])?
                .try_into()
                .map_err(|_| "expected key length")?,
        ),
        Some(command @ ("profile" | "profile-160m")) if a.len() == 6 => {
            let budget = execution_budget(command, &a[4])?;
            profile(
                Path::new(&a[2]),
                Path::new(&a[3]),
                &a[4],
                Path::new(&a[5]),
                budget,
            )
        }
        _ => Err("generate NEW_LOCAL_DIR | profile PROGRAM FIXTURES CASE NEW_OUTPUT".into()),
    }
}
