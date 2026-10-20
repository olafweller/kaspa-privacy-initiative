use super::*;
use kaspa_consensus_core::{hashing::covenant_id::covenant_id, sign::sign};
use kaspa_txscript::{script_builder::ScriptBuilder, standard::pay_to_script_hash_script};
use std::path::PathBuf;
fn temp() -> PathBuf {
    let p = std::env::temp_dir().join(format!(
        "kpi-recovery-tn10-{}-{}",
        std::process::id(),
        rand::random::<u64>()
    ));
    mkdir(&p).unwrap();
    p
}
fn init_tx() -> (Transaction, Vec<UtxoEntry>, State, secp256k1::Keypair) {
    let tip = [9; 32];
    let touch = 123;
    let point = TransactionOutpoint::new(Hash::from_bytes([7; 32]), 0);
    let (output, cov) = bootstrap::output(tip, touch, point).unwrap();
    assert_eq!(
        covenant_id(point, std::iter::once((0, &output))),
        Hash::from_bytes(cov)
    );
    let s = State::genesis(cov, verifier().id(), tip, touch);
    let key = secp256k1::Keypair::from_secret_key(
        secp256k1::SECP256K1,
        &secp256k1::SecretKey::from_slice(&[42; 32]).unwrap(),
    );
    let pk = key.x_only_public_key().0.serialize();
    let spk = kaspa_txscript::pay_to_address_script(&kaspa_addresses::Address::new(
        kaspa_addresses::Prefix::Testnet,
        kaspa_addresses::Version::PubKey,
        &pk,
    ));
    let sig = ScriptBuilder::new()
        .add_data(&bootstrap::redeem(tip, touch).unwrap())
        .unwrap()
        .drain();
    let tx = Transaction::new(
        1,
        vec![
            TransactionInput::new_with_compute_budget(
                TransactionOutpoint::new(Hash::from_bytes([8; 32]), 0),
                sig.clone(),
                0,
                1,
            ),
            TransactionInput::new_with_compute_budget(point, vec![], 0, 1),
        ],
        vec![
            TransactionOutput::with_covenant(
                app::STATE_RENT,
                pay_to_script_hash_script(&state_script(&s)),
                Some(CovenantBinding::new(0, Hash::from_bytes(cov))),
            ),
            TransactionOutput::new(190_000_000, spk.clone()),
        ],
        0,
        chain::LANE.into(),
        0,
        vec![],
    );
    let entries = vec![
        UtxoEntry::new(
            app::STATE_RENT,
            output.script_public_key,
            0,
            false,
            Some(Hash::from_bytes(cov)),
        ),
        UtxoEntry::new(200_000_000, spk, 0, false, None),
    ];
    let mut tx = sign(MutableTransaction::with_entries(tx, entries.clone()), key).tx;
    tx.inputs[0].signature_script = sig;
    tx.finalize();
    (tx, entries, s, key)
}
fn resign(mut tx: Transaction, entries: &[UtxoEntry], key: secp256k1::Keypair) -> Transaction {
    let sig = tx.inputs[0].signature_script.clone();
    tx = sign(MutableTransaction::with_entries(tx, entries.to_vec()), key).tx;
    tx.inputs[0].signature_script = sig;
    tx.finalize();
    tx
}
#[test]
fn actual_genesis_id_initializes_exact_reviewed_state() {
    let (tx, es, s, _) = init_tx();
    let a = transaction::Anchor(Hash::from_bytes([0; 32]), Hash::from_bytes([0; 32]));
    let units = transaction::execute(&tx, &es, &a).unwrap();
    assert_eq!(units.len(), 2);
    assert!(units[0] > 0);
    assert_eq!(s.accounting().unwrap().reserve_principal, 0);
    assert!(state_script(&s)
        .windows(app::restricted::lane_guard().len())
        .any(|w| w == app::restricted::lane_guard()));
}
#[test]
fn initializer_rejects_wrong_root_lane_rent_auth_and_extra_outputs() {
    let (tx, es, _, key) = init_tx();
    let a = transaction::Anchor(Hash::from_bytes([0; 32]), Hash::from_bytes([0; 32]));
    let mut mutations = vec![];
    let mut x = tx.clone();
    x.outputs[0].script_public_key = pay_to_script_hash_script(&[0x51]);
    mutations.push(x);
    let mut x = tx.clone();
    x.subnetwork_id = [0; 20].into();
    mutations.push(x);
    let mut x = tx.clone();
    x.outputs[0].value -= 1;
    x.outputs[1].value += 1;
    mutations.push(x);
    let mut x = tx.clone();
    x.outputs[0].covenant = None;
    mutations.push(x);
    let mut x = tx.clone();
    x.outputs[0].covenant = Some(CovenantBinding::new(1, Hash::from_bytes([5; 32])));
    mutations.push(x);
    let mut x = tx.clone();
    x.outputs.push(TransactionOutput::new(
        1,
        ScriptPublicKey::new(0, vec![0x51].into()),
    ));
    x.outputs[1].value -= 1;
    mutations.push(x);
    for x in mutations {
        let signed = resign(x, &es, key);
        assert!(transaction::execute(&signed, &es, &a).is_err());
    }
}
#[test]
fn genesis_depends_on_output_and_outpoint_without_root_cycle() {
    let p = TransactionOutpoint::new(Hash::from_bytes([4; 32]), 0);
    let (a, id) = bootstrap::output([1; 32], 2, p).unwrap();
    let (_, other) =
        bootstrap::output([1; 32], 2, TransactionOutpoint::new(p.transaction_id, 1)).unwrap();
    assert_ne!(id, other);
    let (_, other) = bootstrap::output([1; 32], 3, p).unwrap();
    assert_ne!(id, other);
    let mut changed = a;
    changed.value += 1;
    assert_ne!(
        Hash::from_bytes(id),
        covenant_id(p, std::iter::once((0, &changed)))
    );
}
#[test]
fn full_signed_size_and_fee_checks_are_not_unsigned_estimates() {
    let (mut tx, es, _, key) = init_tx();
    let a = transaction::Anchor(Hash::from_bytes([0; 32]), Hash::from_bytes([0; 32]));
    let units = transaction::execute(&tx, &es, &a).unwrap();
    for (i, u) in units.iter().enumerate() {
        tx.inputs[i].compute_commit =
            kaspa_consensus_core::mass::ComputeBudget::checked_covering_script_units(
                kaspa_consensus_core::mass::ScriptUnits(*u),
            )
            .unwrap()
            .into();
    }
    tx = resign(tx, &es, key);
    vprogs_l1_wallet::build::commit_storage_mass(&TESTNET_PARAMS, &tx, &es);
    let r = transaction::check(&tx, &es, &a, 100).unwrap();
    assert!(
        r["estimatedSerializedBytes"].as_u64().unwrap()
            > tx.inputs[0].signature_script.len() as u64
    );
    let mut unsigned = tx.clone();
    unsigned.inputs[1].signature_script.clear();
    assert!(transaction::check(&unsigned, &es, &a, 100).is_err());
    tx.outputs[1].value += 9_999_999;
    tx = resign(tx, &es, key);
    vprogs_l1_wallet::build::commit_storage_mass(&TESTNET_PARAMS, &tx, &es);
    assert!(transaction::check(&tx, &es, &a, 100).is_err());
}
fn rpc_utxo(
    point: TransactionOutpoint,
    value: u64,
    spk: ScriptPublicKey,
    cov: Option<Hash>,
) -> Value {
    serde_json::to_value(kaspa_rpc_core::RpcUtxosByAddressesEntry {
        address: None,
        outpoint: point.into(),
        utxo_entry: kaspa_rpc_core::RpcUtxoEntry::new(value, spk, 0, false, cov),
    })
    .unwrap()
}

fn init_test(out: &Path) {
    use kpi_private_note_wallet::wallet::Wallet;
    let root = out.parent().unwrap();
    for role in ["alice", "bob"] {
        let w = Wallet::new();
        report(&root.join(format!("{role}.json")),&json!({"schema":"KPI_USER_RECEIVE_V1","domain":hex::encode(domain()),"owner":hex::encode(w.address.owner),"incoming":hex::encode(w.address.incoming)})).unwrap();
    }
    init(&root.join("alice.json"), &root.join("bob.json"), out).unwrap();
}
#[test]
fn public_only_trial_has_no_user_secrets_and_rejects_receive_extensions() {
    let p = temp();
    let trial = p.join("trial");
    init_test(&trial);
    assert!(!trial.join("alice").exists() && !trial.join("bob").exists());
    let t = read(trial.join("trial.json")).unwrap();
    assert_eq!(t["fundingAuthorized"], false);
    assert!(t.get("bobNative").is_none() && t.get("aliceNative").is_none());
    let mut bad = read(p.join("alice.json")).unwrap();
    bad["nativePubkey"] = json!("00".repeat(32));
    report(&p.join("bad.json"), &bad).unwrap();
    assert!(init(
        &p.join("bad.json"),
        &p.join("bob.json"),
        &p.join("bad-trial")
    )
    .is_err());
    assert!(!p.join("bad-trial").exists());
    fs::remove_dir_all(p).unwrap();
}
fn local_target(stage: &str) -> Value {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../recovery-native/evidence");
    let v = read(root.join("targets.json")).unwrap();
    let b = &v["batches"][stage];
    json!({"schema":"KPI_RECOVERY_TN10_FROZEN_BATCH_V1","trial":"11".repeat(32),"stage":stage,"image":IMAGE,"join":JOIN,"programSha256":PROGRAM_SHA,"inputSha256":b["inputSha256"],"journalHex":b["expectedJournalHex"],"journalSha256":b["expectedJournalSha256"],"stateSha256":trusted::sha(&fs::read(root.join(format!("fixtures/{stage}.state.bin"))).unwrap()),"segmentPo2":b["segmentPo2"],"cycleLimit":160000000,"aggregateProofSeconds":3600,"automaticRetry":false})
}
#[test]
fn six_retained_genuine_receipts_verify_exact_dynamic_targets_and_accounting() {
    let p = temp();
    for c in CASES {
        let target = local_target(c);
        let path = p.join(format!("{c}.json"));
        report(&path, &target).unwrap();
        let sha = trusted::sha(&fs::read(&path).unwrap());
        let t = batch::target(&path, &sha).unwrap();
        let base = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../recovery-proof/gpu-2026-10-20/evidence/results/returned/proofs");
        let r = trusted::read_receipt(&base.join(c).join("receipt.bin")).unwrap();
        batch::verify_target(&t, &r).unwrap();
        let state = state(Path::new(env!("CARGO_MANIFEST_DIR")).join(format!(
            "../recovery-native/evidence/fixtures/{c}.state.bin"
        )))
        .unwrap();
        batch::lifecycle(c, &state).unwrap();
        let mut bad = target.clone();
        bad["journalHex"] = json!("00".repeat(352));
        bad["journalSha256"] = json!(trusted::sha(&vec![0; 352]));
        assert!(batch::verify_target(&bad, &r).is_err());
    }
    fs::remove_dir_all(p).unwrap();
}
#[test]
fn genuine_bob_partial_issuance_and_payout() {
    prove_exit_builder("bob-exit")
}
#[test]
fn genuine_alice_full_issuance_and_payout() {
    prove_exit_builder("alice-exit")
}
fn prove_exit_builder(case: &str) {
    // Regression only: the retained receipt necessarily binds the old fixture
    // recipient/context. This configuration is never a fresh/live trial.
    let p = temp();
    let trial = p.join("trial");
    init_test(&trial);
    let mut t = read(trial.join("trial.json")).unwrap();
    let fixtures =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../recovery-native/evidence/fixtures");
    let input: Input =
        bincode::deserialize(&fs::read(fixtures.join(&format!("{case}.input.bin"))).unwrap())
            .unwrap();
    let after: app::Output =
        bincode::deserialize(&fs::read(fixtures.join(&format!("{case}.expected.bin"))).unwrap())
            .unwrap();
    let eid = *after
        .state
        .ledger
        .exits
        .iter()
        .find(|(_, e)| !e.paid)
        .unwrap()
        .0;
    t["bobNative"]["pubkey"] = json!(hex::encode(after.state.exit_keys[&eid]));
    let trial_json = p.join("fixture-trial.json");
    report(&trial_json, &t).unwrap();
    let target_dir = p.join("target");
    mkdir(&target_dir).unwrap();
    save(
        &target_dir.join("prior-state.bin"),
        &bincode::serialize(&input.state).unwrap(),
    )
    .unwrap();
    save(
        &target_dir.join("state.bin"),
        &bincode::serialize(&after.state).unwrap(),
    )
    .unwrap();
    let mut target = local_target(case);
    target["trial"] = t["trial"].clone();
    target["stateOutpoint"] = json!({"transactionId":hex::encode([0x83;32]),"index":0});
    target["endBlock"] = json!(hex::encode([3; 32]));
    let target_path = target_dir.join("target.json");
    report(&target_path, &target).unwrap();
    let target_sha = trusted::sha(&fs::read(&target_path).unwrap());
    let pk = h(&t["sponsorNative"]["pubkey"]).unwrap();
    let spk = kaspa_txscript::pay_to_address_script(&kaspa_addresses::Address::new(
        kaspa_addresses::Prefix::Testnet,
        kaspa_addresses::Version::PubKey,
        &pk,
    ));
    let receipt = Path::new(env!("CARGO_MANIFEST_DIR")).join(format!(
        "../recovery-proof/gpu-2026-10-20/evidence/results/returned/proofs/{case}/receipt.bin"
    ));
    let mut r = json!({"trial":t["trial"],"kind":"settlement","server":{"networkId":"testnet-10","isSynced":true,"virtualDaaScore":1},"feeRateSompiPerGram":100,
        "sponsorUtxo":rpc_utxo(TransactionOutpoint::new(Hash::from_bytes([84;32]),0),10_000_000_000,spk.clone(),None),
        "stateUtxo":rpc_utxo(TransactionOutpoint::new(Hash::from_bytes([0x83;32]),0),app::STATE_RENT,pay_to_script_hash_script(&state_script(&input.state)),Some(Hash::from_bytes(input.state.covenant))),
        "targetPath":target_path,"targetSha256":target_sha,"receiptPath":receipt,
        "anchorBlock":{"block":{"header":{"hash":hex::encode([3;32]),"acceptedIdMerkleRoot":hex::encode(&after.journal[128..160]),"blueScore":10000},"verboseData":{"isChainBlock":true}}},
        "selectedParentBlock":{"block":{"header":{"blueScore":10001}}}});
    let req = p.join("settlement-request.json");
    report(&req, &r).unwrap();
    let grant_dir = p.join("grant");
    let key = trial.join("sponsor/native.key");
    transaction::build(&trial_json, &req, &key, &grant_dir).unwrap();
    let grant = read(grant_dir.join("transaction.json")).unwrap();
    assert!(
        grant["qualification"]["inputComputeBudgets"][0]
            .as_u64()
            .unwrap()
            >= 2500,
        "single-input signing must preserve the measured ZK budget"
    );
    let rpc: kaspa_rpc_core::RpcTransaction =
        serde_json::from_value(grant["transaction"].clone()).unwrap();
    let tx: Transaction = rpc.try_into().unwrap();
    let registered = app::apply(&after.state, &native::lane_tx(&tx), &verifier())
        .unwrap()
        .0;
    assert_eq!(registered.permissions[&eid].outpoint.id, H::from(tx.id()));
    let reserve = &registered.exit_reserves[&eid];
    r["kind"] = json!("payout");
    r["publicStatePath"] = json!(target_dir.join("state.bin"));
    r["exitId"] = json!(hex::encode(eid));
    r["permissionTransactionPath"] = json!(grant_dir.join("transaction.json"));
    r["permissionUtxo"] = rpc_utxo(
        TransactionOutpoint::new(tx.id(), 1),
        app::PERMISSION_RENT,
        tx.outputs[1].script_public_key.clone(),
        Some(Hash::from_bytes(registered.covenant)),
    );
    r["reserveUtxo"] = rpc_utxo(
        native::op(reserve),
        registered.reserves[reserve],
        ScriptPublicKey::new(0, app::delegate(&registered.covenant).into()),
        None,
    );
    r["sponsorUtxo"] = rpc_utxo(
        TransactionOutpoint::new(tx.id(), 2),
        tx.outputs[2].value,
        spk,
        None,
    );
    let req = p.join("payout-request.json");
    report(&req, &r).unwrap();
    let out = p.join("payout");
    transaction::build(&trial_json, &req, &key, &out).unwrap();
    let record = read(out.join("transaction.json")).unwrap();
    let rpc: kaspa_rpc_core::RpcTransaction =
        serde_json::from_value(record["transaction"].clone()).unwrap();
    let payout: Transaction = rpc.try_into().unwrap();
    let final_state = app::apply(&registered, &native::lane_tx(&payout), &verifier())
        .unwrap()
        .0;
    assert_eq!(
        final_state.accounting().unwrap().reserve_principal,
        if case == "bob-exit" { 600_000_000 } else { 0 }
    );
    assert_eq!(final_state.accounting().unwrap().unpaid_exits, 0);
    // Actual signed mutations, balancing sponsor change and re-signing it.
    let mut es = vec![];
    for field in ["permissionUtxo", "reserveUtxo", "sponsorUtxo"] {
        let entry: kaspa_rpc_core::RpcUtxosByAddressesEntry =
            serde_json::from_value(r[field].clone()).unwrap();
        es.push(entry.utxo_entry.into());
    }
    let sk =
        secp256k1::SecretKey::from_slice(&hex::decode(secret(&key).unwrap()).unwrap()).unwrap();
    let kp = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &sk);
    for kind in ["underpay", "recipient", "lane"] {
        let mut bad = payout.clone();
        match kind {
            "underpay" => {
                bad.outputs[0].value -= 1;
                bad.outputs.last_mut().unwrap().value += 1;
            }
            "reserve" => {
                bad.outputs[1].value -= 1;
                bad.outputs.last_mut().unwrap().value += 1;
            }
            "recipient" => {
                bad.outputs[0].script_public_key =
                    bad.outputs.last().unwrap().script_public_key.clone()
            }
            _ => bad.subnetwork_id = [0; 20].into(),
        }
        bad = transaction::sign_fee_input(bad, &es, kp);
        bad.finalize();
        let error = transaction::execute(
            &bad,
            &es,
            &transaction::Anchor(Hash::from_bytes([0; 32]), Hash::from_bytes([0; 32])),
        )
        .unwrap_err();
        assert!(matches!(error.downcast_ref::<kaspa_txscript_errors::TxScriptError>(),
            Some(kaspa_txscript_errors::TxScriptError::EvalFalse|kaspa_txscript_errors::TxScriptError::VerifyError)),
            "{kind}: resource/signature/builder failure must not count as native attack rejection: {error}");
    }
    fs::remove_dir_all(p).unwrap();
}

#[test]
#[ignore = "requires retained public parameters; run separately, no outer proof"]
fn fresh_local_wallet_credit_and_both_recovered_exits() {
    use kpi_private_note_wallet::wallet::Wallet;
    let p = temp();
    for (i, role) in ["alice", "bob"].iter().enumerate() {
        mkdir(&p.join(role)).unwrap();
        let w = Wallet::new();
        save(&p.join(role).join("wallet.backup"), &w.local_backup()).unwrap();
        save(&p.join(role).join("native.key"), &[31 + i as u8; 32]).unwrap();
        report(&p.join(format!("{role}.json")),&json!({"schema":"KPI_USER_RECEIVE_V1","domain":hex::encode(domain()),"owner":hex::encode(w.address.owner),"incoming":hex::encode(w.address.incoming)})).unwrap();
    }
    let trial = p.join("trial");
    init(&p.join("alice.json"), &p.join("bob.json"), &trial).unwrap();
    let tp = trial.join("trial.json");
    let t = read(&tp).unwrap();
    let mut state = State::genesis([88; 32], verifier().id(), [4; 32], 10);
    let deposit = Transaction::new(
        1,
        vec![TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(Hash::from_bytes([91; 32]), 0),
            vec![],
            0,
            1,
        )],
        vec![TransactionOutput::new(
            1_000_000_000,
            ScriptPublicKey::new(0, app::delegate(&state.covenant).into()),
        )],
        0,
        chain::LANE.into(),
        0,
        chain::deposit_payload(h(&t["alice"]["owner"]).unwrap(), 0),
    );
    state = app::apply(&state, &native::lane_tx(&deposit), &verifier())
        .unwrap()
        .0;
    let params = PathBuf::from(
        std::env::var("KPI_RECOVERY_TEST_PARAMETERS").expect("public parameters path"),
    );
    let mut nonce = 100u8;
    for (role, kind) in [
        ("alice", "credit-transfer"),
        ("bob", "bob-exit"),
        ("alice", "alice-exit"),
    ] {
        let path = p.join(format!("{kind}.state.bin"));
        save(&path, &bincode::serialize(&state).unwrap()).unwrap();
        let out = p.join(format!("{kind}-operations"));
        wallet::prepare(
            &tp,
            &path,
            &hex::encode(state.root()),
            &p.join(role).join("wallet.backup"),
            &params,
            kind,
            &out,
        )
        .unwrap();
        for name in if kind == "credit-transfer" {
            vec!["credit", "transfer"]
        } else {
            vec!["exit"]
        } {
            let op: Operation =
                serde_json::from_value(read(out.join(format!("{name}.json"))).unwrap()).unwrap();
            let data = read(out.join(format!("{name}-payload.json"))).unwrap();
            assert_eq!(data["witnessExported"], false);
            let payload = hex::decode(data["operationPayloadHex"].as_str().unwrap()).unwrap();
            nonce += 1;
            let tx = Transaction::new(
                1,
                vec![TransactionInput::new_with_compute_budget(
                    TransactionOutpoint::new(Hash::from_bytes([nonce; 32]), 0),
                    vec![],
                    0,
                    1,
                )],
                vec![TransactionOutput::new(
                    1,
                    ScriptPublicKey::new(0, vec![0x51].into()),
                )],
                0,
                chain::LANE.into(),
                0,
                payload,
            );
            let result = app::apply(&state, &native::lane_tx(&tx), &verifier()).unwrap();
            state = result.0;
            assert!(verifier().verify(&op).is_ok());
        }
        if kind != "credit-transfer" {
            let eid = *state.ledger.exits.iter().find(|(_, e)| !e.paid).unwrap().0;
            nonce += 1;
            let grant = native::settlement_template(
                &state,
                Some(eid),
                TransactionOutpoint::new(Hash::from_bytes([nonce; 32]), 0),
                TransactionOutpoint::new(Hash::from_bytes([nonce + 1; 32]), 0),
            );
            state = app::apply(&state, &native::lane_tx(&grant), &verifier())
                .unwrap()
                .0;
            let (payout, entries) = native::payout(&state, eid, "").unwrap();
            native::scripts(&payout, &entries).unwrap().unwrap();
            state = app::apply(&state, &native::lane_tx(&payout), &verifier())
                .unwrap()
                .0;
        }
    }
    let a = state.accounting().unwrap();
    assert_eq!(a.reserve_principal, 0);
    assert_eq!(a.private_liability, 0);
    assert_eq!(a.unpaid_exits, 0);
    assert_eq!(a.state_covenant_rent_excluded, 100_000_000);
    fs::remove_dir_all(p).unwrap();
}
