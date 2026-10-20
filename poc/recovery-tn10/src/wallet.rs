//! Role-local wallet proving; no new setup, secret material or witnesses enter
//! the public batch package. These commands are not executed by the GPU service.
use super::*;
use kpi_private_note_wallet::wallet::{Address, Engine, Wallet};
pub fn prepare(
    trial_path: &Path,
    state_path: &Path,
    expected_root: &str,
    backup: &Path,
    parameters: &Path,
    kind: &str,
    out: &Path,
) -> Result<()> {
    let trial = read(trial_path)?;
    let s = state(state_path)?;
    require(
        trial["schema"] == "KPI_RECOVERY_TN10_TRIAL_V1"
            && trial["guestImage"] == IMAGE
            && trial["network"] == "testnet-10"
            && trial["domain"] == hex::encode(domain()),
        "new recovery trial required",
    )?;
    require(
        hex::encode(s.root()) == expected_root,
        "independently expected accepted state root",
    )?;
    let v = verifier();
    let raw = fs::read(parameters)?;
    require(
        trusted::sha(&raw) == PARAM_SHA,
        "reviewed public parameter bytes",
    )?;
    let engine = Engine::from_public_parameters(&raw, v.id())?;
    let wallet = Wallet::restore_local(
        &secret(backup)?
            .try_into()
            .map_err(|_| "own wallet backup length")?,
    );
    let role = match kind {
        "credit-transfer" => "alice",
        "bob-exit" => "bob",
        "alice-exit" => "alice",
        _ => return Err("wallet action".into()),
    };
    require(
        hex::encode(wallet.address.owner) == trial[role]["owner"]
            && hex::encode(wallet.address.incoming) == trial[role]["incoming"],
        "wrong role wallet",
    )?;
    let mut ledger = s.ledger.clone();
    let mut ops = vec![];
    let start = Instant::now();
    if kind == "credit-transfer" {
        let pending: Vec<_> = ledger
            .deposits
            .iter()
            .filter(|(_, d)| d.status == 0 && d.owner == wallet.address.owner)
            .collect();
        require(
            pending.len() == 1 && pending[0].1.amount == 1_000_000_000,
            "one actual accepted 10 KAS deposit belonging to Alice",
        )?;
        let reference = *pending[0].0;
        // Use one note and its matching encrypted delivery throughout.
        let initial = wallet.note(1_000_000_000);
        let mut st = Statement::new(CREDIT, v.id(), ledger.tree.root());
        st.deposit = reference;
        st.deposit_owner = wallet.address.owner;
        st.deposit_value = initial.value;
        let delivery = initial.deliver()?;
        let credit = engine.prove(
            st,
            wallet.witness(
                wallet.authority_note(),
                [initial.clone(), Note::dummy()],
                [[0; 32]; DEPTH],
                [false; DEPTH],
            ),
            [delivery, Delivery::absent()],
        )?;
        ledger.apply(&v, &credit)?;
        ops.push(("credit", credit, [0; 32]));
        let found = wallet.discover(&ledger.deliveries, &ledger.tree, &ledger.nullifiers);
        require(found.len() == 1, "Alice credit recovery")?;
        let (note, index) = found[0].clone();
        let (siblings, bits) = ledger.tree.path(index)?;
        let bob = Address {
            owner: h(&trial["bob"]["owner"])?,
            incoming: h(&trial["bob"]["incoming"])?,
        };
        let notes = [
            Note::for_address(&bob, 400_000_000),
            wallet.note(600_000_000),
        ];
        let deliveries = [notes[0].deliver()?, notes[1].deliver()?];
        let mut st = Statement::new(TRANSFER, v.id(), ledger.tree.root());
        st.nullifier = wallet.nf(&note);
        let pay = engine.prove(st, wallet.witness(note, notes, siblings, bits), deliveries)?;
        ledger.apply(&v, &pay)?;
        ops.push(("transfer", pay, [0; 32]));
    } else {
        let found = wallet.discover(&ledger.deliveries, &ledger.tree, &ledger.nullifiers);
        require(
            found.len() == 1
                && found[0].0.value
                    == if role == "bob" {
                        400_000_000
                    } else {
                        600_000_000
                    },
            "user independently recovers the intended current note",
        )?;
        let (note, index) = found[0].clone();
        let (siblings, bits) = ledger.tree.path(index)?;
        let key_path = backup
            .parent()
            .ok_or("wallet directory")?
            .join("native.key");
        let key = secp256k1::SecretKey::from_slice(&secret(&key_path)?)?;
        let recipient = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &key)
            .x_only_public_key()
            .0
            .serialize();
        secp256k1::XOnlyPublicKey::from_slice(&recipient)?;
        require(
            recipient
                != hex::decode("79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")?
                    .as_slice(),
            "fixture recipient forbidden",
        )?;
        let mut st = Statement::new(EXIT, v.id(), ledger.tree.root());
        st.nullifier = wallet.nf(&note);
        st.exit_value = note.value;
        st.exit_destination = chain::destination(&recipient);
        let exit = engine.prove(
            st,
            wallet.witness(note, [Note::dummy(), Note::dummy()], siblings, bits),
            [Delivery::absent(), Delivery::absent()],
        )?;
        ledger.apply(&v, &exit)?;
        ops.push(("exit", exit, recipient));
    }
    mkdir(out)?;
    for (name, op, key) in &ops {
        v.verify(op)?;
        report(
            &out.join(format!("{name}.json")),
            &serde_json::to_value(op)?,
        )?;
        report(
            &out.join(format!("{name}-payload.json")),
            &json!({"trial":trial["trial"],"operationId":hex::encode(op.statement.id()),"operationPayloadHex":hex::encode(chain::operation_payload(op,*key)?),"sourceRoot":expected_root,"nativePubkey":if *key==[0;32]{Value::Null}else{json!(hex::encode(key))},"witnessExported":false}),
        )?;
    }
    report(
        &out.join("report.json"),
        &json!({"scope":"ROLE_LOCAL_WALLET_PROOFS_FOR_PUBLIC_ACCEPTED_STATE","role":role,"sourceStateSha256":trusted::sha(&fs::read(state_path)?),"parameterSha256":PARAM_SHA,"walletVk":hex::encode(v.id()),"seconds":start.elapsed().as_secs_f64(),"secretMaterialPublished":false,"broadcast":false}),
    )
}
