//! Public native-preimage fixtures. No setup, wallet keys or witness input.
use super::*;
fn tip(out: &chain::Output) -> H {
    out.aggregate_journal[96..128].try_into().unwrap()
}
fn linked(state: State, txs: Vec<lane::Tx>, score: u64, previous: &chain::Output) -> Input {
    let i = input(state, txs, score, tip(previous));
    assert_eq!(
        i.lane.start_seq,
        previous.aggregate_journal[128..160],
        "fixture native endpoint continuity"
    );
    i
}
pub(super) fn prepare(source: &Path, out: &Path) -> Result<()> {
    fs::create_dir(out)?;
    let raw = fs::read(source.join("vk.bin"))?;
    let id: H = fs::read(source.join("vk-id.bin"))?.try_into().unwrap();
    let verifier = chain::wallet::wallet::Verifier::from_bytes(&raw, id)?;
    let accelerated = AcceleratedVerifier::checked(&raw, id)?;
    let load = |name: &str| -> Result<Operation> {
        Ok(serde_json::from_slice(&fs::read(
            source.join(format!("{name}.json")),
        )?)?)
    };
    let credit = load("credit")?;
    let pay = load("transfer")?;
    let exit = load("exit")?;
    let competing = load("competing")?;
    let recovery = load("recovery")?;
    let covenant = hash(b"unfunded native rehearsal covenant identity only");
    let key: H = hex::decode("79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")?
        .try_into()
        .unwrap();
    let refund: H =
        hex::decode("c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5")?
            .try_into()
            .unwrap();
    let dep_tx = tx(
        1,
        chain::deposit_payload(credit.statement.deposit_owner, 0),
        Some(covenant),
    );
    assert_eq!(
        chain::deposit_reference(vprogs_l1_utils::tx_id_v1(&dep_tx.payload, &dep_tx.rest), 0),
        credit.statement.deposit
    );
    let credit_tx = tx(2, chain::operation_payload(&credit, [0; 32])?, None);
    let pay_tx = tx(3, chain::operation_payload(&pay, [0; 32])?, None);
    let exit_tx = tx(4, chain::operation_payload(&exit, key)?, None);
    let genesis = State {
        covenant,
        ledger: Ledger::new(id),
    };
    let deposit_input = input(genesis, vec![dep_tx.clone()], 10, [0; 32]);
    let dep = chain::execute(&deposit_input, &verifier);
    let credit_input = linked(dep.state.clone(), vec![credit_tx.clone()], 11, &dep);
    let credited = chain::execute(&credit_input, &verifier);
    let transfer_input = linked(credited.state.clone(), vec![pay_tx.clone()], 12, &credited);
    let transferred = chain::execute(&transfer_input, &verifier);
    let exit_input = linked(
        transferred.state.clone(),
        vec![exit_tx.clone()],
        13,
        &transferred,
    );
    let exited = chain::execute(&exit_input, &verifier);
    assert_eq!(exited.state.ledger.reserve, 1_000_000_000);
    assert_eq!(exited.state.ledger.private_liability, 600_000_000);
    assert_eq!(exited.exit_principals, vec![400_000_000]);
    let mut bad = pay.clone();
    let mut proof =
        ark_groth16::Proof::<ark_bn254::Bn254>::deserialize_compressed(pay.proof.as_slice())?;
    proof.c = -proof.c;
    bad.proof.clear();
    proof.serialize_compressed(&mut bad.proof)?;
    assert_eq!(accelerated.verify(&bad), Err("invalid proof".into()));
    let badtx = tx(5, chain::operation_payload(&bad, [0; 32])?, None);
    let mut malformed = pay.clone();
    malformed.proof[0] ^= 1;
    let malformedtx = tx(6, chain::operation_payload(&malformed, [0; 32])?, None);
    let refundtx = tx(8, chain::operation_payload(&recovery, refund)?, None);
    let mut cases: Vec<(&str, Input, Vec<u8>)> = vec![
        ("deposit", deposit_input.clone(), vec![0]),
        ("credit", credit_input, vec![0]),
        ("transfer", transfer_input, vec![0]),
        ("exit", exit_input, vec![0]),
        (
            "valid-invalid-valid",
            linked(
                dep.state.clone(),
                vec![credit_tx.clone(), badtx.clone(), pay_tx.clone()],
                11,
                &dep,
            ),
            vec![0, 1, 0],
        ),
        (
            "invalid-then-valid",
            linked(
                credited.state.clone(),
                vec![badtx, pay_tx.clone()],
                12,
                &credited,
            ),
            vec![1, 0],
        ),
        (
            "malformed-then-valid",
            linked(
                credited.state.clone(),
                vec![malformedtx, pay_tx.clone()],
                12,
                &credited,
            ),
            vec![1, 0],
        ),
        (
            "old-root-competing-next-batch",
            linked(
                transferred.state.clone(),
                vec![tx(7, chain::operation_payload(&competing, [0; 32])?, None)],
                13,
                &transferred,
            ),
            vec![1],
        ),
        (
            "cross-batch-replay",
            linked(
                transferred.state.clone(),
                vec![pay_tx.clone()],
                13,
                &transferred,
            ),
            vec![1],
        ),
        (
            "credit-then-recovery",
            linked(
                credited.state.clone(),
                vec![refundtx.clone()],
                12,
                &credited,
            ),
            vec![1],
        ),
        (
            "recovery-then-credit",
            linked(
                dep.state.clone(),
                vec![refundtx, credit_tx.clone()],
                11,
                &dep,
            ),
            vec![0, 1],
        ),
        (
            "duplicate-deposit",
            linked(dep.state.clone(), vec![dep_tx.clone()], 11, &dep),
            vec![1],
        ),
        (
            "wrong-native-destination",
            linked(
                transferred.state.clone(),
                vec![tx(9, chain::operation_payload(&exit, refund)?, None)],
                13,
                &transferred,
            ),
            vec![1],
        ),
    ];
    for (mode, name) in [
        "zero-native-deposit",
        "wrong-native-script",
        "missing-native-output",
        "zero-deposit-owner",
        "covenant-bound-deposit",
    ]
    .iter()
    .enumerate()
    {
        let mut t = dep_tx.clone();
        match mode {
            0 => t.rest[70..78].fill(0),
            1 => t.rest[88] ^= 1,
            2 => t.payload[chain::DEPOSIT_TAG.len() + 32..].copy_from_slice(&1u32.to_le_bytes()),
            3 => t.payload[chain::DEPOSIT_TAG.len()..chain::DEPOSIT_TAG.len() + 32].fill(0),
            _ => {
                t.rest[123] = 1;
                t.rest.splice(124..124, [0u8; 34]);
            }
        }
        cases.push((
            name,
            input(deposit_input.state.clone(), vec![t], 10, [0; 32]),
            vec![1],
        ));
    }
    let mut reports = vec![];
    for (name, case, intended) in cases {
        let expected = chain::execute(&case, &verifier);
        let actual = chain::execute(&case, &accelerated);
        let outcomes = expected
            .events
            .iter()
            .map(|e| e.verdict)
            .collect::<Vec<_>>();
        assert_eq!(outcomes, intended, "expected outcomes {name}");
        assert_eq!(
            bincode::serialize(&expected)?,
            bincode::serialize(&actual)?,
            "reference/backend {name}"
        );
        for e in &expected.events {
            if e.verdict != 0 {
                assert_eq!(e.before, e.after, "atomic rejected monetary state {name}");
            }
        }
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
        reports.push(json!({"case":name,"outcomes":outcomes,"privateLiability":expected.state.ledger.private_liability,"reserve":expected.state.ledger.reserve,"aggregateBytes":expected.aggregate_journal.len()}));
    }
    for n in [
        "vk.bin",
        "vk-id.bin",
        "credit.json",
        "transfer.json",
        "exit.json",
        "competing.json",
        "recovery.json",
    ] {
        save(out, n, &fs::read(source.join(n))?)?;
    }
    let mut auths = vec![];
    for (name, label) in [
        ("auth-prior-state", "authenticated prior private state"),
        ("auth-covenant", "config covenant"),
        ("auth-lane", "wrong fixed lane"),
        ("auth-start", "start inclusion"),
    ] {
        let mut bad = deposit_input.clone();
        match name {
            "auth-prior-state" => {
                bad.state.ledger.batch = 1;
            }
            "auth-covenant" => bad.lane.covenant[0] ^= 1,
            "auth-lane" => bad.lane.lane[1] ^= 1,
            _ => bad.lane.start_seq[0] ^= 1,
        }
        save(
            out,
            &format!("{name}.input.bin"),
            &bincode::serialize(&bad)?,
        )?;
        save(out, &format!("{name}.abort.txt"), label.as_bytes())?;
        auths.push(name);
    }
    let full = linked(
        dep.state.clone(),
        vec![
            credit_tx.clone(),
            tx(5, chain::operation_payload(&bad, [0; 32])?, None),
            pay_tx.clone(),
        ],
        11,
        &dep,
    );
    let genuine = chain::execute(&full, &verifier);
    for mode in 0..3 {
        let mut changed = full.clone();
        match mode {
            0 => {
                changed.lane.blocks[0].txs.remove(1);
            }
            1 => changed.lane.blocks[0].txs.swap(1, 2),
            _ => changed.lane.blocks[0].txs[1].payload[0] ^= 1,
        }
        for (i, t) in changed.lane.blocks[0].txs.iter_mut().enumerate() {
            t.merge_idx = i as u32;
        }
        let result = chain::execute(&changed, &verifier);
        assert_ne!(
            &result.aggregate_journal[96..160],
            &genuine.aggregate_journal[96..160],
            "omission/reorder/substitution must alter native endpoint"
        );
    }
    save(
        out,
        "preparation.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"NATIVE_PREIMAGE_FIXTURE_EXECUTION_NOT_CANONICAL_TN10_OR_RECEIPT","walletVkId":hex::encode(id),"domain":hex::encode(domain()),"nativeEndpointContinuityAcrossFourBatches":true,"cases":reports,"guestAuthenticationCases":auths,"omissionReorderSubstitutionChangeEndpoint":true,"nativeScriptReceiptVerification":false,"actualNativePayout":false}),
        )?,
    )?;
    println!("public fixtures: native endpoint/state continuity, exact expected outcomes and reference/backend agreement checked");
    Ok(())
}
