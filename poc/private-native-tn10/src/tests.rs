use super::*;
use kaspa_consensus_core::{hashing::covenant_id::covenant_id, sign::sign};
use kaspa_txscript::{script_builder::ScriptBuilder, standard::pay_to_script_hash_script};
use std::path::PathBuf;
fn temp() -> PathBuf {
    let p = std::env::temp_dir().join(format!(
        "kpi-private-tn10-{}-{}",
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
fn fresh_trial_roles_are_unfunded_and_private() {
    let p = temp();
    let d = p.join("trial");
    init(&d).unwrap();
    let t = read(d.join("trial.json")).unwrap();
    assert_eq!(t["fundingAuthorized"], false);
    assert_ne!(t["alice"]["owner"], t["bob"]["owner"]);
    assert_eq!(
        fs::metadata(d.join("bob/native.key"))
            .unwrap()
            .permissions()
            .mode()
            & 0o777,
        0o600
    );
    assert!(init(&d).is_err());
    fs::remove_dir_all(p).unwrap();
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
fn local_target(stage: &str) -> Value {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../private-native/evidence");
    let all = read(p.join("targets.json")).unwrap();
    json!({"schema":"KPI_TN10_FROZEN_BATCH_V1","image":IMAGE,"join":JOIN,"programSha256":PROGRAM_SHA,"journalHex":all["batches"][stage]["expectedJournalHex"],"journalSha256":all["batches"][stage]["expectedJournalSha256"]})
}
#[test]
fn trusted_target_and_old_fixture_receipt_cannot_substitute_real_target() {
    let p = temp();
    let t = local_target("deposit");
    let path = p.join("target.json");
    report(&path, &t).unwrap();
    let sha = trusted::sha(&fs::read(&path).unwrap());
    assert!(batch::target(&path, &sha).is_ok());
    assert!(batch::target(&path, &"0".repeat(64)).is_err());
    let mut wrong = t.clone();
    wrong["image"] = json!("00".repeat(32));
    let path2 = p.join("wrong.json");
    report(&path2, &wrong).unwrap();
    assert!(batch::target(&path2, &trusted::sha(&fs::read(&path2).unwrap())).is_err());
    let journal = hex::decode(t["journalHex"].as_str().unwrap()).unwrap();
    let fake = risc0_zkvm::Receipt::new(
        risc0_zkvm::InnerReceipt::Fake(risc0_zkvm::FakeReceipt::new(risc0_zkvm::ReceiptClaim::ok(
            trusted::digest(IMAGE).unwrap(),
            journal.clone(),
        ))),
        journal,
    );
    assert!(batch::verify_target(&t, &fake).is_err());
    fs::remove_dir_all(p).unwrap();
}
#[test]
fn retained_relation_still_connects_all_four_states_and_tips() {
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../private-native/evidence");
    let mut last: Option<State> = None;
    for case in ["deposit", "credit-transfer", "exit", "reconcile"] {
        let i: Input =
            bincode::deserialize(&fs::read(p.join(format!("{case}.input.bin"))).unwrap()).unwrap();
        if let Some(s) = last {
            assert_eq!(s.root(), i.state.root());
            assert_eq!(s.lane_tip, i.state.lane_tip);
        }
        let o = app::execute(&i, &verifier());
        assert_eq!(
            o.journal,
            fs::read(p.join(format!("{case}.journal.bin"))).unwrap()
        );
        last = Some(o.state);
    }
}
#[test]
fn deposit_reference_includes_actual_txid_and_index() {
    let a = chain::deposit_reference([4; 32], 0);
    assert_ne!(a, chain::deposit_reference([4; 32], 1));
    assert_ne!(a, chain::deposit_reference([5; 32], 0));
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
#[test]
fn offline_signed_bootstrap_initialize_and_deposit_have_actual_lineage() {
    let p = temp();
    let trial = p.join("trial");
    init(&trial).unwrap();
    let t = read(trial.join("trial.json")).unwrap();
    let pubkey = h(&t["sponsorNative"]["pubkey"]).unwrap();
    let spk = kaspa_txscript::pay_to_address_script(&kaspa_addresses::Address::new(
        kaspa_addresses::Prefix::Testnet,
        kaspa_addresses::Version::PubKey,
        &pubkey,
    ));
    let seed = p.join("seed.json");
    report(&seed,&json!({"scope":"VERIFIED_NATIVE_LANE_SEED","lane":hex::encode(chain::LANE),"tip":hex::encode([9;32]),"lastTouch":123,"endBlock":hex::encode([6;32])})).unwrap();
    let mut r = json!({"trial":t["trial"],"server":{"networkId":"testnet-10","isSynced":true,"virtualDaaScore":1},"feeRateSompiPerGram":100,
        "kind":"bootstrap","seedPath":seed,"seedSha256":trusted::sha(&fs::read(&seed).unwrap()),
        "sponsorUtxo":rpc_utxo(TransactionOutpoint::new(Hash::from_bytes([3;32]),0),10_000_000_000,spk.clone(),None)});
    let key = trial.join("sponsor/native.key");
    let mut last: Option<(Value, Transaction)> = None;
    for kind in ["bootstrap", "initialize", "deposit"] {
        r["kind"] = json!(kind);
        if let Some((prev, tx)) = &last {
            let tx: &Transaction = tx;
            r["sponsorUtxo"] = rpc_utxo(
                TransactionOutpoint::new(tx.id(), 1),
                tx.outputs[1].value,
                spk.clone(),
                None,
            );
            if kind == "initialize" {
                r["bootstrapPath"] = json!(p.join("bootstrap/transaction.json"));
                r["stateUtxo"] = rpc_utxo(
                    TransactionOutpoint::new(tx.id(), 0),
                    tx.outputs[0].value,
                    tx.outputs[0].script_public_key.clone(),
                    tx.outputs[0].covenant.map(|c| c.covenant_id),
                );
                r["covenantId"] = prev["details"]["covenantId"].clone();
            }
            if kind == "deposit" {
                // Synthetic accepted checkpoint for this offline builder test.
                // Live checkpoints must instead be made by batch::checkpoint.
                let genesis = state(p.join("initialize/state.bin")).unwrap();
                let cp = p.join("initialize/synthetic-checkpoint.json");
                report(&cp,&json!({"trial":t["trial"],"completed":"initialize","status":"CAPTURED_NATIVE_ACCEPTANCE_OFFLINE_RECHECK_REQUIRED","stateRoot":hex::encode(genesis.root()),"stateOutpoint":{"transactionId":tx.id().to_string(),"index":0}})).unwrap();
                r["checkpointPath"] = json!(cp);
                r["stateUtxo"] = rpc_utxo(
                    TransactionOutpoint::new(tx.id(), 0),
                    tx.outputs[0].value,
                    tx.outputs[0].script_public_key.clone(),
                    tx.outputs[0].covenant.map(|c| c.covenant_id),
                );
            }
        }
        let path = p.join(format!("{kind}-request.json"));
        report(&path, &r).unwrap();
        let out = p.join(kind);
        transaction::build(&trial.join("trial.json"), &path, &key, &out).unwrap();
        let record = read(out.join("transaction.json")).unwrap();
        assert_eq!(record["qualification"]["allInputScriptsExecuted"], true);
        let rpc: kaspa_rpc_core::RpcTransaction =
            serde_json::from_value(record["transaction"].clone()).unwrap();
        let tx: Transaction = rpc.try_into().unwrap();
        last = Some((record, tx));
    }
    let (_, deposit) = last.unwrap();
    let s = state(p.join("initialize/state.bin")).unwrap();
    let (after, _, _) = app::apply(&s, &native::lane_tx(&deposit), &verifier()).unwrap();
    assert_eq!(
        after.ledger.deposits[&chain::deposit_reference(deposit.id().into(), 0)].owner,
        h(&t["alice"]["owner"]).unwrap()
    );
    assert_eq!(after.accounting().unwrap().pending_deposits, 1_000_000_000);
    fs::remove_dir_all(p).unwrap();
}

#[test]
fn real_retained_receipts_verify_only_their_exact_regression_targets() {
    let p = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../private-native-proof/gpu-2026-10-18-02/evidence/returned/proofs");
    for stage in ["deposit", "credit-transfer", "exit", "reconcile"] {
        let receipt = trusted::read_receipt(&p.join(stage).join("receipt.bin")).unwrap();
        let target = local_target(stage);
        batch::verify_target(&target, &receipt).unwrap();
        let mut different = target.clone();
        let mut j = hex::decode(target["journalHex"].as_str().unwrap()).unwrap();
        j[0] ^= 1;
        different["journalHex"] = json!(hex::encode(&j));
        different["journalSha256"] = json!(trusted::sha(&j));
        assert!(batch::verify_target(&different, &receipt).is_err());
        trusted::crypto_negatives(&receipt, trusted::digest(IMAGE).unwrap()).unwrap();
    }
}

#[test]
fn real_fixture_exit_receipt_builds_signed_permission_and_reconciled_payout() {
    // Regression only: the retained receipt necessarily binds the old fixture
    // recipient/context. This configuration is never a fresh/live trial.
    let p = temp();
    let trial = p.join("trial");
    init(&trial).unwrap();
    let mut t = read(trial.join("trial.json")).unwrap();
    let fixtures = Path::new(env!("CARGO_MANIFEST_DIR")).join("../private-native/evidence");
    let input: Input =
        bincode::deserialize(&fs::read(fixtures.join("exit.input.bin")).unwrap()).unwrap();
    let after: app::Output =
        bincode::deserialize(&fs::read(fixtures.join("exit.expected.bin")).unwrap()).unwrap();
    let eid = *after.state.ledger.exits.keys().next().unwrap();
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
    let mut target = local_target("exit");
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
    let receipt = Path::new(env!("CARGO_MANIFEST_DIR")).join(
        "../private-native-proof/gpu-2026-10-18-02/evidence/returned/proofs/exit/receipt.bin",
    );
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
        600_000_000
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
    for kind in ["underpay", "reserve", "recipient", "lane"] {
        let mut bad = payout.clone();
        match kind {
            "underpay" => {
                bad.outputs[0].value -= 1;
                bad.outputs[2].value += 1;
            }
            "reserve" => {
                bad.outputs[1].value -= 1;
                bad.outputs[2].value += 1;
            }
            "recipient" => {
                bad.outputs[0].script_public_key = bad.outputs[2].script_public_key.clone()
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
fn mapped_capture_preserves_long_gap_public_inputs_and_journal() {
    // Only tests conversion; not a replacement for the native `verify` call.
    use kaspa_rpc_core::{GetSeqCommitLaneProofResponse, RpcLaneEntry, RpcTransaction};
    use kaspa_smt::proof::{OwnedSmtProof, ProofTerminal};
    let p = Path::new(env!("CARGO_MANIFEST_DIR")).join("../private-native/evidence");
    let input: Input =
        bincode::deserialize(&fs::read(p.join("credit-transfer.input.bin")).unwrap()).unwrap();
    assert!(input.lane.end.blue_score - input.lane.start.blue_score > 100);
    let proof = |a: &lane::Anchor, tip: H| {
        serde_json::to_value(GetSeqCommitLaneProofResponse {
            smt_proof: OwnedSmtProof {
                bitmap: a.bitmap,
                siblings: a.siblings.iter().copied().map(Hash::from_bytes).collect(),
                terminal: ProofTerminal::Collapsed { depth: a.depth },
            }
            .to_bytes(),
            lane: Some(RpcLaneEntry {
                tip: Hash::from_bytes(tip),
                blue_score: a.blue_score,
            }),
            payload_and_ctx_digest: Hash::from_bytes(a.payload_ctx),
            parent_seq_commit: Hash::from_bytes(a.parent_seq),
            inactivity_shortcut: Hash::from_bytes(a.shortcut),
        })
        .unwrap()
    };
    let output = app::execute(&input, &verifier());
    let mut blocks = vec![];
    for b in &input.lane.blocks {
        let mut txs = vec![];
        for t in &b.txs {
            let n = app::NativeTx::parse(&t.rest).unwrap();
            let tx = Transaction::new(
                1,
                n.inputs
                    .iter()
                    .map(|o| TransactionInput::new_with_compute_budget(native::op(o), vec![], 0, 1))
                    .collect(),
                n.outputs
                    .into_iter()
                    .map(|o| {
                        TransactionOutput::with_covenant(
                            o.value,
                            ScriptPublicKey::new(o.version, o.script.into()),
                            o.covenant.map(|(index, id)| {
                                CovenantBinding::new(index, Hash::from_bytes(id))
                            }),
                        )
                    })
                    .collect(),
                0,
                chain::LANE.into(),
                0,
                t.payload.clone(),
            );
            assert_eq!(native::lane_tx(&tx).rest, t.rest);
            assert_eq!(t.merge_idx, txs.len() as u32);
            txs.push(serde_json::to_value(RpcTransaction::from(&tx)).unwrap());
        }
        blocks.push(json!({"chainBlockHeader":{"daaScore":b.daa_score,"blueScore":b.blue_score,"timestamp":b.prev_timestamp+1000},"acceptedTransactions":txs}));
    }
    let mut records = vec![];
    for (label, value) in [
        ("start-proof", proof(&input.lane.start, input.lane.old_tip)),
        ("end-proof", proof(&input.lane.end, output.state.lane_tip)),
        (
            "start-block",
            json!({"block":{"header":{"timestamp":input.lane.blocks[0].prev_timestamp,"acceptedIdMerkleRoot":hex::encode(input.lane.start_seq)}}}),
        ),
        ("accepted", json!({"chainBlockAcceptedTransactions":blocks})),
    ] {
        records.push(
            json!({"label":label,"raw":serde_json::to_string(&json!({"params":value})).unwrap()}),
        );
    }
    let c = json!({"scope":"SYNTHETIC_CONVERSION_ONLY_NOT_NATIVE_CAPTURE","intervalBlocks":input.lane.blocks.len(),"records":records});
    let mut mapped = batch::from_capture(&c, input.state.covenant).unwrap();
    mapped.old_state = input.state.root();
    assert_eq!(
        bincode::serialize(&mapped).unwrap(),
        bincode::serialize(&input.lane).unwrap()
    );
    assert_eq!(
        app::execute(
            &Input {
                state: input.state,
                lane: mapped
            },
            &verifier()
        )
        .journal,
        output.journal
    );
}
