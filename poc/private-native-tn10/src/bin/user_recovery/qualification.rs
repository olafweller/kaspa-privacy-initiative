//! Fresh synthetic experiment, never uses any earlier trial's role secrets.
use super::*;
use kaspa_consensus_core::{hashing::tx::transaction_v1_rest_preimage, tx::*};
use kaspa_hashes::Hash;
use kaspa_txscript::{script_builder::ScriptBuilder, standard::pay_to_script_hash_script};
use vprogs_zk_abi::withdrawal::StandardSpk;
use vprogs_zk_backend_risc0_api::{build_delegate_entry_script, PermissionTreeAccumulator};

fn child(args: &[&str]) -> Result<String> {
    let p = std::process::Command::new(std::env::current_exe()?)
        .args(args)
        .output()?;
    require(
        p.status.success(),
        &format!(
            "user subprocess failed: {}",
            String::from_utf8_lossy(&p.stderr)
        ),
    )?;
    Ok(String::from_utf8(p.stdout)?)
}
fn path(p: &Path) -> &str {
    p.to_str().unwrap()
}
fn fixture_tx(payload: Vec<u8>, outputs: Vec<TransactionOutput>, nonce: u8) -> lane::Tx {
    native::lane_tx(&Transaction::new(
        1,
        vec![TransactionInput::new(
            TransactionOutpoint::new(Hash::from_bytes([nonce; 32]), 0),
            vec![],
            0,
            1,
        )],
        outputs,
        0,
        chain::LANE.into(),
        0,
        payload,
    ))
}
fn linked(state: State, mut txs: Vec<lane::Tx>, score: u64) -> app::Input {
    for (i, tx) in txs.iter_mut().enumerate() {
        tx.merge_idx = i as u32;
    }
    let start = lane::Anchor {
        parent_seq: [1; 32],
        payload_ctx: [2; 32],
        shortcut: [3; 32],
        blue_score: state.last_touch,
        bitmap: [0; 32],
        depth: 0,
        siblings: vec![],
    };
    let mut end = start.clone();
    end.blue_score = score;
    app::Input {
        lane: lane::Input {
            lane: chain::LANE,
            covenant: state.covenant,
            old_state: state.root(),
            old_tip: state.lane_tip,
            start_seq: lane::bytes(start.seq(
                kaspa_seq_commit::hashing::lane_key(&chain::LANE),
                lane::h(state.lane_tip),
            )),
            start,
            blocks: vec![lane::Block {
                prev_timestamp: score * 1000,
                daa_score: score * 10,
                blue_score: score,
                txs,
            }],
            end,
        },
        state,
    }
}
pub fn terminal_tx(c: &terminal::Claim) -> Result<(app::Outpoint, Transaction, Vec<UtxoEntry>)> {
    let permission = app::Outpoint {
        id: hash(&c.commitment()),
        index: 1,
    };
    let empty = PermissionTreeAccumulator::hash_empty();
    let dest = StandardSpk::PubKey(&c.recipient);
    let redeem = c.redeem()?;
    let mut b = ScriptBuilder::new();
    for _ in 0..2 {
        b.add_data(&empty)?.add_i64(0)?;
    }
    b.add_data(dest.to_script_bytes().as_slice())?
        .add_data(&c.amount().to_le_bytes())?
        .add_i64(i64::try_from(c.amount())?)?
        .add_data(&redeem)?;
    let delegate = build_delegate_entry_script(&c.prior.covenant);
    let mut tx = Transaction::new(
        1,
        vec![
            TransactionInput::new(native::op(&permission), b.drain(), 0, 1),
            TransactionInput::new(
                native::op(&c.reserve),
                ScriptBuilder::new().add_data(&delegate)?.drain(),
                0,
                1,
            ),
            TransactionInput::new(
                TransactionOutpoint::new(Hash::from_bytes([0x98; 32]), 0),
                vec![],
                0,
                1,
            ),
        ],
        vec![
            TransactionOutput::new(
                c.amount() + app::PERMISSION_RENT,
                ScriptPublicKey::new(0, dest.to_script_bytes().as_slice().to_vec().into()),
            ),
            TransactionOutput::new(199_900_000, ScriptPublicKey::new(0, vec![0x51].into())),
        ],
        0,
        chain::LANE.into(),
        0,
        app::payout_payload(c.eid),
    );
    let mut entries = vec![
        UtxoEntry::new(
            app::PERMISSION_RENT,
            pay_to_script_hash_script(&redeem),
            0,
            false,
            Some(Hash::from_bytes(c.prior.covenant)),
        ),
        UtxoEntry::new(
            c.amount(),
            pay_to_script_hash_script(&delegate),
            0,
            false,
            None,
        ),
        UtxoEntry::new(
            200_000_000,
            ScriptPublicKey::new(0, vec![0x51].into()),
            0,
            false,
            None,
        ),
    ];
    native::sign_sponsor(&mut tx, &mut entries)?;
    Ok((permission, tx, entries))
}
pub fn run(parameters: &Path, out: &Path) -> Result<()> {
    mkdir(out)?;
    let alice_dir = out.join("alice-local");
    init(&alice_dir)?;
    let bob_dir = out.join("bob-local");
    child(&["init", path(&bob_dir)])?;
    // Only PUBLIC receiving data crosses from the Bob subprocess.
    let receive: serde_json::Value =
        serde_json::from_slice(&fs::read(bob_dir.join("receive.json"))?)?;
    require(
        receive["domain"] == hex::encode(domain()),
        "receiving domain",
    )?;
    let bob_address = kpi_private_note_wallet::wallet::Address {
        owner: h(receive["owner"].as_str().unwrap())?,
        incoming: h(receive["incoming"].as_str().unwrap())?,
    };
    let alice = own(&alice_dir)?;
    let engine = engine(parameters)?;
    let v = verifier();
    let genesis = State::genesis(
        hash(b"fresh unfunded local recovery covenant"),
        v.id(),
        [0; 32],
        10,
    );
    let deposit = fixture_tx(
        [
            chain::DEPOSIT_TAG,
            &alice.address.owner,
            &0u32.to_le_bytes(),
        ]
        .concat(),
        vec![TransactionOutput::new(
            1_000_000_000,
            ScriptPublicKey::new(0, app::delegate(&genesis.covenant).into()),
        )],
        1,
    );
    let a = linked(genesis.clone(), vec![deposit.clone()], 11);
    let s = app::execute(&a, &v).state;
    let initial = alice.note(1_000_000_000);
    let mut st = Statement::new(CREDIT, v.id(), s.ledger.tree.root());
    st.deposit = *s.ledger.deposits.keys().next().unwrap();
    st.deposit_owner = alice.address.owner;
    st.deposit_value = initial.value;
    let credit = engine.prove(
        st,
        alice.witness(
            alice.authority_note(),
            [initial.clone(), Note::dummy()],
            [[0; 32]; DEPTH],
            [false; DEPTH],
        ),
        [initial.deliver()?, Delivery::absent()],
    )?;
    let ct = fixture_tx(
        chain::operation_payload(&credit, [0; 32])?,
        vec![TransactionOutput::new(
            1,
            ScriptPublicKey::new(0, vec![0x51].into()),
        )],
        2,
    );
    let sc = app::apply(&s, &ct, &v)?.0;
    let (path_s, bits) = sc.ledger.tree.path(0)?;
    let notes = [
        Note::for_address(&bob_address, 400_000_000),
        alice.note(600_000_000),
    ];
    let deliveries = [notes[0].deliver()?, notes[1].deliver()?];
    let mut st = Statement::new(TRANSFER, v.id(), sc.ledger.tree.root());
    st.nullifier = alice.nf(&initial);
    let pay = engine.prove(st, alice.witness(initial, notes, path_s, bits), deliveries)?;
    let pt = fixture_tx(
        chain::operation_payload(&pay, [0; 32])?,
        vec![TransactionOutput::new(
            1,
            ScriptPublicKey::new(0, vec![0x51].into()),
        )],
        3,
    );
    let b = linked(s, vec![ct, pt], 12);
    let before_bob = app::execute(&b, &v).state;
    let public = out.join("public");
    mkdir(&public)?;
    for (name, input) in [("deposit", &a), ("credit-transfer", &b)] {
        save(
            &public.join(format!("{name}.input.bin")),
            &bincode::serialize(input)?,
        )?;
    }
    let saved = public.join("before-bob.state.bin");
    save(&saved, &bincode::serialize(&before_bob)?)?;
    // Rename the directory, then rebuild on a clean destination from public
    // history. No original wallet cache, note plaintext or operator service.
    let restored = out.join("bob-restored");
    fs::rename(&bob_dir, &restored)?;
    let recovered = out.join("reconstructed.bin");
    let replay = child(&[
        "rebuild",
        &hex::encode(genesis.root()),
        &hex::encode(before_bob.root()),
        path(&recovered),
        path(&public.join("deposit.input.bin")),
        path(&public.join("credit-transfer.input.bin")),
    ])?;
    require(
        fs::read(&recovered)? == fs::read(&saved)?,
        "exact clean replay state",
    )?;
    let scan = child(&[
        "scan",
        path(&recovered),
        &hex::encode(before_bob.root()),
        path(&restored),
    ])?;
    let bob_out = out.join("bob-exit-public");
    child(&[
        "exit",
        path(&recovered),
        &hex::encode(before_bob.root()),
        path(&restored),
        path(parameters),
        path(&bob_out),
    ])?;
    let op: Operation = serde_json::from_slice(&fs::read(bob_out.join("exit.json"))?)?;
    // The sender never needs Bob's native key. It is disclosed only by Bob's
    // public, proof-bound exit result when he chooses to withdraw.
    let exit_public: serde_json::Value =
        serde_json::from_slice(&fs::read(bob_out.join("public.json"))?)?;
    let bob_key = h(exit_public["nativePubkey"]
        .as_str()
        .ok_or("exit recipient")?)?;
    let payload = hex::decode(exit_public["payloadHex"].as_str().ok_or("exit payload")?)?;
    require(
        payload == chain::operation_payload(&op, bob_key)?
            && exit_public["sourceRoot"] == hex::encode(before_bob.root())
            && exit_public["operationId"] == hex::encode(op.statement.id()),
        "public exit result binding",
    )?;
    let tx = fixture_tx(
        payload,
        vec![TransactionOutput::new(
            1,
            ScriptPublicKey::new(0, vec![0x51].into()),
        )],
        4,
    );
    let bob_claim = app::apply(&before_bob, &tx, &v)?.0;
    let grant = native::issuance(&bob_claim, op.statement.id());
    let registered = app::apply(&bob_claim, &native::lane_tx(&grant), &v)?.0;
    let (payout, entries) = native::payout(&registered, op.statement.id(), "")?;
    let bob_units = native::scripts(&payout, &entries)??;
    let after_bob = app::apply(&registered, &native::lane_tx(&payout), &v)?.0;
    let final_input = public.join("pre-full-exit.state.bin");
    save(&final_input, &bincode::serialize(&after_bob)?)?;
    let alice_out = out.join("alice-exit-public");
    child(&[
        "exit",
        path(&final_input),
        &hex::encode(after_bob.root()),
        path(&alice_dir),
        path(parameters),
        path(&alice_out),
    ])?;
    let op: Operation = serde_json::from_slice(&fs::read(alice_out.join("exit.json"))?)?;
    let claim = terminal::Claim::admit(&after_bob, &op, recipient(&alice_dir)?)?;
    let (permission, tx, entries) = terminal_tx(&claim)?;
    let terminal_units = native::scripts(&tx, &entries)??;
    let final_state = claim.reconcile_accepted_body(&permission, &tx)?;
    require(
        final_state.reserves.is_empty()
            && final_state.ledger.reserve == 0
            && final_state.ledger.private_liability == 0
            && final_state.ledger.exits.values().all(|e| e.paid),
        "all users paid, zero backing/liabilities",
    )?;
    save(
        &public.join("alice-exit.json"),
        &fs::read(alice_out.join("exit.json"))?,
    )?;
    save(
        &public.join("final.state.bin"),
        &bincode::serialize(&final_state)?,
    )?;
    report(
        &public.join("terminal.json"),
        &json!({"recipient":hex::encode(claim.recipient),"claimCommitment":hex::encode(claim.commitment()),"nativeTxid":tx.id().to_string(),"canonicalRestHex":hex::encode(transaction_v1_rest_preimage(&tx)),"redeemHex":hex::encode(claim.redeem()?),"permissionOutpoint":{"id":hex::encode(permission.id),"index":permission.index}}),
    )?;
    report(
        &public.join("qualification.json"),
        &json!({"scope":"LOCAL_REAL_WALLET_PROOFS_AND_NATIVE_SCRIPT_FIXTURES_NOT_NEW_OUTER_PROOFS_OR_TN10", "separateUserProcesses":true,"independentAdministrationEstablished":false,"originalServicesContacted":false,"publicHistoryReconstructedByteExactly":true,"replay":serde_json::from_str::<serde_json::Value>(&replay)?,"bobScan":serde_json::from_str::<serde_json::Value>(&scan)?,"bobPaidPrincipalSompi":400_000_000,"alicePaidPrincipalSompi":600_000_000,"permissionRefundPerUser":app::PERMISSION_RENT,"stateRentRemainsSeparate":app::STATE_RENT,"bobScriptUnits":bob_units,"terminalScriptUnits":terminal_units,"finalAccounting":final_state.accounting()?,"terminalOutputs":2,"zeroValueReserveOutput":false,"newOuterProofs":0,"onChainAccepted":false,"userSecretsIncluded":false}),
    )?;
    println!("Local qualification complete; publish only the public subdirectory. User backups remain in private role directories.");
    Ok(())
}
