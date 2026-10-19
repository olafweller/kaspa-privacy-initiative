use super::*;
fn evidence() -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../user-recovery/evidence/local")
}
fn claim() -> terminal::Claim {
    let p = evidence();
    let state: State = decode(&p.join("pre-full-exit.state.bin")).unwrap();
    let op: Operation =
        serde_json::from_slice(&fs::read(p.join("alice-exit.json")).unwrap()).unwrap();
    let target: serde_json::Value =
        serde_json::from_slice(&fs::read(p.join("terminal.json")).unwrap()).unwrap();
    terminal::Claim::admit(
        &state,
        &op,
        h(target["recipient"].as_str().unwrap()).unwrap(),
    )
    .unwrap()
}
#[test]
fn new_user_files_are_private_and_never_overwritten() {
    let p = std::env::temp_dir().join(format!("kpi-recovery-{}", rand::random::<u64>()));
    init(&p).unwrap();
    assert_eq!(
        fs::metadata(p.join("wallet.backup"))
            .unwrap()
            .permissions()
            .mode()
            & 0o777,
        0o600
    );
    assert_eq!(
        fs::metadata(&p).unwrap().permissions().mode() & 0o777,
        0o700
    );
    assert!(init(&p).is_err());
    let receive: serde_json::Value =
        serde_json::from_slice(&fs::read(p.join("receive.json")).unwrap()).unwrap();
    assert_eq!(
        receive
            .as_object()
            .unwrap()
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>(),
        ["domain", "incoming", "owner", "schema"],
        "shared receive data must never link a native payout key"
    );
    assert_eq!(receive["schema"], "KPI_USER_RECEIVE_V1");
    assert_eq!(receive["domain"], hex::encode(domain()));
    assert_eq!(
        own(&p).unwrap().address.owner,
        own(&p).unwrap().address.owner
    );
    fs::remove_dir_all(p).unwrap();
}
#[test]
fn exact_state_root_rejects_modified_spentness_and_missing_deliveries() {
    let p = evidence().join("pre-full-exit.state.bin");
    let s: State = decode(&p).unwrap();
    assert!(public_state(&p, s.root()).is_ok());
    let mut wrong = s.root();
    wrong[0] ^= 1;
    assert!(public_state(&p, wrong).is_err());
    let mut changed = s.clone();
    changed.ledger.deliveries.pop();
    assert_ne!(s.root(), changed.root());
    let mut changed = s.clone();
    changed.ledger.nullifiers.clear();
    assert_ne!(s.root(), changed.root());
}
#[test]
fn terminal_native_acceptance_and_accounting_drain_exact_reserve() {
    let c = claim();
    let (p, tx, entries) = qualification::terminal_tx(&c).unwrap();
    assert!(native::scripts(&tx, &entries).unwrap().is_ok());
    let next = c.reconcile_accepted_body(&p, &tx).unwrap();
    assert_eq!(next.ledger.reserve, 0);
    assert_eq!(next.ledger.private_liability, 0);
    assert!(next.reserves.is_empty());
    assert!(next.ledger.exits.values().all(|e| e.paid));
    assert_eq!(
        next.accounting().unwrap().state_covenant_rent_excluded,
        app::STATE_RENT
    );
    let op: Operation =
        serde_json::from_slice(&fs::read(evidence().join("alice-exit.json")).unwrap()).unwrap();
    assert!(
        terminal::Claim::admit(&next, &op, c.recipient).is_err(),
        "current nullifier replay"
    );
}
#[test]
fn sponsor_topup_preserves_only_authorized_liability_deduction() {
    let c = claim();
    let (p, mut tx, mut entries) = qualification::terminal_tx(&c).unwrap();
    tx.outputs[0].value += 1;
    tx.outputs[1].value -= 1;
    native::sign_sponsor(&mut tx, &mut entries).unwrap();
    assert!(native::scripts(&tx, &entries).unwrap().is_ok());
    assert_eq!(
        c.reconcile_accepted_body(&p, &tx).unwrap().ledger.reserve,
        0
    );
}
#[test]
fn native_terminal_policy_rejects_signed_unsupported_forms() {
    use kaspa_consensus_core::tx::*;
    use kaspa_hashes::Hash;
    use kaspa_txscript_errors::TxScriptError;
    let c = claim();
    let (_, tx, entries) = qualification::terminal_tx(&c).unwrap();
    for mode in 0..13 {
        let mut x = tx.clone();
        let mut es = entries.clone();
        match mode {
            0 => {
                x.outputs[0].value -= 1;
                x.outputs[1].value += 1;
            }
            1 => x.outputs[0].script_public_key = x.outputs[1].script_public_key.clone(),
            2 => x.subnetwork_id = [0; 20].into(),
            3 => x.inputs[1].previous_outpoint.index += 1,
            4 => {
                es[1].amount += 1;
                x.outputs[1].value += 1;
            }
            5 => {
                x.outputs.push(TransactionOutput::new(
                    1,
                    x.outputs[1].script_public_key.clone(),
                ));
                x.outputs[1].value -= 1;
            }
            6 => {
                x.outputs[1].script_public_key =
                    ScriptPublicKey::new(0, app::delegate(&c.prior.covenant).into())
            }
            7 => {
                x.inputs.push(TransactionInput::new(
                    TransactionOutpoint::new(Hash::from_bytes([0x44; 32]), 0),
                    vec![],
                    0,
                    1,
                ));
                es.push(es[2].clone());
                x.outputs[1].value += es[2].amount;
            }
            8 => {
                // Missing refund even with fully paid principal.
                x.outputs[0].value -= app::PERMISSION_RENT;
                x.outputs[1].value += app::PERMISSION_RENT;
            }
            9 => {
                es[1].amount -= 1;
                x.outputs[1].value -= 1;
            }
            10 => {
                use kaspa_txscript::script_builder::ScriptBuilder;
                use vprogs_zk_abi::withdrawal::StandardSpk;
                use vprogs_zk_backend_risc0_api::PermissionTreeAccumulator;
                let empty = PermissionTreeAccumulator::hash_empty();
                let dest = StandardSpk::PubKey(&c.recipient);
                let mut witness = ScriptBuilder::new();
                for _ in 0..2 {
                    witness.add_data(&empty).unwrap().add_i64(0).unwrap();
                }
                witness
                    .add_data(dest.to_script_bytes().as_slice())
                    .unwrap()
                    .add_data(&c.amount().to_le_bytes())
                    .unwrap()
                    .add_i64((c.amount() / 2) as i64)
                    .unwrap()
                    .add_data(&c.redeem().unwrap())
                    .unwrap();
                x.inputs[0].signature_script = witness.drain();
                x.outputs[0].value -= c.amount() / 2;
                x.outputs[1].value += c.amount() / 2;
            }
            11 => x.inputs[1].previous_outpoint.transaction_id = Hash::from_bytes([0x99; 32]),
            _ => {
                x.outputs[0].script_public_key =
                    ScriptPublicKey::new(1, x.outputs[0].script_public_key.script().to_vec().into())
            }
        }
        native::sign_sponsor(&mut x, &mut es).unwrap();
        assert!(
            matches!(
                native::scripts(&x, &es).unwrap(),
                Err(TxScriptError::VerifyError | TxScriptError::EvalFalse)
            ),
            "mode {mode} must be a semantic native rejection"
        );
    }
}
#[test]
fn old_guest_policy_is_preserved_instead_of_silently_upgraded() {
    use kaspa_consensus_core::tx::*;
    let c = claim();
    let op: Operation =
        serde_json::from_slice(&fs::read(evidence().join("alice-exit.json")).unwrap()).unwrap();
    let tx = Transaction::new(
        1,
        vec![TransactionInput::new(
            native::op(&app::Outpoint {
                id: [0x88; 32],
                index: 0,
            }),
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
        chain::operation_payload(&op, c.recipient).unwrap(),
    );
    let result = app::apply(&c.prior, &native::lane_tx(&tx), &verifier());
    assert!(matches!(result, Err(e) if e.contains("positive change")));
}
#[test]
fn real_proof_binds_destination_and_current_state() {
    let c = claim();
    let op: Operation =
        serde_json::from_slice(&fs::read(evidence().join("alice-exit.json")).unwrap()).unwrap();
    let mut wrong = c.recipient;
    wrong[0] ^= 1;
    assert!(terminal::Claim::admit(&c.prior, &op, wrong).is_err());
    let mut changed = op.clone();
    changed.statement.exit_destination[0] ^= 1;
    assert!(verifier().verify(&changed).is_err());
    let mut state = c.prior.clone();
    state.ledger.nullifiers.insert(op.statement.nullifier);
    assert!(terminal::Claim::admit(&state, &op, c.recipient).is_err());
    let mut state = c.prior.clone();
    state.reserves.values_mut().for_each(|v| *v += 1);
    state.ledger.reserve += 1;
    // A matching arithmetical balance alone is not an exact reserve/valid state.
    assert!(terminal::Claim::admit(&state, &op, c.recipient).is_err());
}
