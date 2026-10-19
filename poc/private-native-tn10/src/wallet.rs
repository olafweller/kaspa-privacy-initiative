//! Role-local wallet proving; no new setup, secret material or witnesses enter
//! the public batch package. These commands are not executed by the GPU service.
use super::*;
use kpi_private_note_wallet::wallet::{Address, Engine, Wallet};
pub fn prepare(
    trial_path: &Path,
    state_path: &Path,
    backup: &Path,
    parameters: &Path,
    kind: &str,
    out: &Path,
) -> Result<()> {
    let trial = read(trial_path)?;
    let s = state(state_path)?;
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
        "exit" => "bob",
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
            found.len() == 1 && found[0].0.value == 400_000_000,
            "Bob independently recovers 4 KAS current note",
        )?;
        let (note, index) = found[0].clone();
        let (siblings, bits) = ledger.tree.path(index)?;
        let recipient = h(&trial["bobNative"]["pubkey"])?;
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
            &json!({"trial":trial["trial"],"operationId":hex::encode(op.statement.id()),"operationPayloadHex":hex::encode(chain::operation_payload(op,*key)?)}),
        )?;
    }
    report(
        &out.join("report.json"),
        &json!({"scope":"ROLE_LOCAL_WALLET_PROOFS_FOR_PUBLIC_ACCEPTED_STATE","role":role,"sourceStateSha256":trusted::sha(&fs::read(state_path)?),"parameterSha256":PARAM_SHA,"walletVk":hex::encode(v.id()),"seconds":start.elapsed().as_secs_f64(),"secretMaterialPublished":false,"broadcast":false}),
    )
}
