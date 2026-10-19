use super::*;
#[test]
fn whole_native_history_rejects_reused_transfer_and_payout_inputs() {
    let p = fixtures::scenarios().unwrap();
    let scan = |p: &fixtures::Prepared| {
        fixtures::native_history(
            p.cases
                .iter()
                .map(|(name, input, _)| (name.as_str(), input)),
        )
        .unwrap()
    };
    let good = scan(&p);
    assert_eq!(good["transactionCount"], 13);
    assert_eq!(good["inputCount"], good["uniqueInputs"]);
    fixtures::require_single_spend(&good).unwrap();

    // Reproduce both reviewed bugs independently. Changing app validity does
    // not release the funding UTXO, and each payout consumes its sponsor UTXO.
    let mut transfer = p.clone();
    let valid_rest = transfer.cases[1].1.lane.blocks[0].txs[3].rest.clone();
    transfer.cases[1].1.lane.blocks[0].txs[2].rest = valid_rest;
    let bad = scan(&transfer);
    assert_eq!(bad["conflicts"].as_array().unwrap().len(), 1);
    assert_eq!(bad["conflicts"][0]["first"]["stage"], "credit-transfer");
    assert_eq!(bad["conflicts"][0]["again"]["stage"], "credit-transfer");
    assert!(fixtures::require_single_spend(&bad).is_err());

    let mut payout = p.clone();
    let sponsor_offset = 2 + 8 + 2 * (32 + 4 + 8 + 8);
    let bob = payout.cases[3].1.lane.blocks[0].txs[1].rest.clone();
    payout.cases[5].1.lane.blocks[0].txs[1].rest[sponsor_offset..sponsor_offset + 36]
        .copy_from_slice(&bob[sponsor_offset..sponsor_offset + 36]);
    let bad = scan(&payout);
    assert_eq!(bad["conflicts"].as_array().unwrap().len(), 1);
    assert_eq!(bad["conflicts"][0]["first"]["stage"], "bob-reconcile");
    assert_eq!(bad["conflicts"][0]["again"]["stage"], "alice-reconcile");
    assert!(fixtures::require_single_spend(&bad).is_err());
}
#[test]
fn six_linked_batches_keep_exits_backed_until_both_payouts() {
    let p = fixtures::scenarios().unwrap();
    assert_eq!(p.cases.len(), 6);
    for pair in p.cases.windows(2) {
        assert_eq!(pair[0].2.state.root(), pair[1].1.state.root());
        assert_eq!(pair[0].2.state.lane_tip, pair[1].1.state.lane_tip);
    }
    for (n, amount) in [(2, 400_000_000), (4, 600_000_000)] {
        let s = &p.cases[n].2.state;
        assert_eq!(s.accounting().unwrap().unpaid_exits, amount);
        let next = &p.cases[n + 1].2.state;
        assert_eq!(next.accounting().unwrap().unpaid_exits, 0);
    }
    assert_eq!(p.cases[5].2.state.ledger.reserve, 0);
    assert_eq!(
        p.cases[5]
            .2
            .state
            .accounting()
            .unwrap()
            .state_covenant_rent_excluded,
        100_000_000
    );
}
#[test]
fn native_payout_forms_and_sponsor_topups_reconcile_without_tags() {
    let p = fixtures::scenarios().unwrap();
    for n in [2, 4] {
        let s = &p.cases[n].2.state;
        let registered = app::apply(s, &native::lane_tx(&p.templates[n]), &verifier())
            .unwrap()
            .0;
        let eid = *registered.permissions.keys().next().unwrap();
        for attack in ["", "top-up", "versioned-sponsor-output"] {
            let (mut tx, es) = native::payout(&registered, eid, attack).unwrap();
            tx.payload.clear();
            native::sign_sponsor(&mut tx, &mut es.clone()).unwrap();
            assert!(native::scripts(&tx, &es).unwrap().is_ok());
            let next = app::apply(&registered, &native::lane_tx(&tx), &verifier())
                .unwrap()
                .0;
            assert_eq!(next.ledger.reserve, if n == 2 { 600_000_000 } else { 0 });
            assert_eq!(next.permissions.len(), 0);
        }
    }
}
#[test]
fn native_semantic_negatives_preserve_original_policy_for_both_forms() {
    use kaspa_txscript_errors::TxScriptError;
    let p = fixtures::scenarios().unwrap();
    for n in [2, 4] {
        let s = &p.cases[n].2.state;
        let registered = app::apply(s, &native::lane_tx(&p.templates[n]), &verifier())
            .unwrap()
            .0;
        let eid = *registered.permissions.keys().next().unwrap();
        for attack in [
            "underpay",
            "wrong-recipient",
            "default-lane",
            "foreign-reserve",
            "extra-sponsor-input",
            "extra-sponsor-output",
            "partial",
            "partial-three-outputs",
        ] {
            let (tx, entries) = native::payout(&registered, eid, attack).unwrap();
            let r = native::scripts(&tx, &entries).unwrap();
            assert!(
                matches!(
                    r,
                    Err(TxScriptError::VerifyError | TxScriptError::EvalFalse)
                ),
                "{n}/{attack}: {r:?}"
            );
        }
    }
}
#[test]
fn wrong_permission_and_exit_replay_are_rejected() {
    let p = fixtures::scenarios().unwrap();
    for n in [2, 4] {
        let mut grant = p.templates[n].clone();
        grant.outputs[1].value -= 1;
        grant.finalize();
        assert!(app::apply(&p.cases[n].2.state, &native::lane_tx(&grant), &verifier()).is_err());
        let tx = &p.cases[n].1.lane.blocks[0].txs[1];
        assert!(app::apply(&p.cases[n + 1].2.state, tx, &verifier()).is_err());
    }
}
#[test]
fn exact_selected_reserve_drain_preserves_a_second_pending_deposit() {
    use kaspa_consensus_core::tx::*;
    use kaspa_hashes::Hash;
    let p = fixtures::scenarios().unwrap();
    let before = &p.cases[3].2.state;
    let tx = Transaction::new(
        1,
        vec![TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(Hash::from_bytes([0x68; 32]), 0),
            vec![],
            0,
            1,
        )],
        vec![TransactionOutput::new(
            1,
            ScriptPublicKey::new(0, app::delegate(&before.covenant).into()),
        )],
        0,
        chain::LANE.into(),
        0,
        [chain::DEPOSIT_TAG, &[0x49; 32], &0u32.to_le_bytes()].concat(),
    );
    let deposited = app::apply(before, &native::lane_tx(&tx), &verifier())
        .unwrap()
        .0;
    let second = app::Outpoint {
        id: tx.id().as_bytes(),
        index: 0,
    };
    let exited = app::apply(&deposited, &p.cases[4].1.lane.blocks[0].txs[1], &verifier())
        .unwrap()
        .0;
    let eid = *exited.ledger.exits.iter().find(|(_, e)| !e.paid).unwrap().0;
    assert_eq!(exited.reserves[&exited.exit_reserves[&eid]], 600_000_000);
    let grant = native::settlement_template(
        &exited,
        Some(eid),
        TransactionOutpoint::new(Hash::from_bytes([0x69; 32]), 0),
        TransactionOutpoint::new(Hash::from_bytes([0x70; 32]), 0),
    );
    let registered = app::apply(&exited, &native::lane_tx(&grant), &verifier())
        .unwrap()
        .0;
    let (payout, entries) = native::payout(&registered, eid, "").unwrap();
    assert_eq!(payout.outputs.len(), 2);
    assert!(native::scripts(&payout, &entries).unwrap().is_ok());
    let final_state = app::apply(&registered, &native::lane_tx(&payout), &verifier())
        .unwrap()
        .0;
    assert_eq!(final_state.reserves[&second], 1);
    assert_eq!(final_state.accounting().unwrap().pending_deposits, 1);
    assert_eq!(final_state.ledger.reserve, 1);
    assert_eq!(final_state.ledger.private_liability, 0);
}
#[test]
fn exact_reserve_must_not_create_a_zero_reserve_output() {
    use kaspa_consensus_core::tx::*;
    let p = fixtures::scenarios().unwrap();
    let exited = &p.cases[4].2.state;
    let registered = app::apply(exited, &native::lane_tx(&p.templates[4]), &verifier())
        .unwrap()
        .0;
    let eid = *registered.permissions.keys().next().unwrap();
    let (mut tx, mut entries) = native::payout(&registered, eid, "").unwrap();
    tx.outputs.insert(
        1,
        TransactionOutput::new(
            0,
            ScriptPublicKey::new(0, app::delegate(&registered.covenant).into()),
        ),
    );
    native::sign_sponsor(&mut tx, &mut entries).unwrap();
    assert!(matches!(
        native::scripts(&tx, &entries).unwrap(),
        Err(kaspa_txscript_errors::TxScriptError::VerifyError
            | kaspa_txscript_errors::TxScriptError::EvalFalse)
    ));
}
#[test]
fn exit_amount_range_is_explicit_and_cannot_wrap_permission_refund() {
    let p = fixtures::scenarios().unwrap();
    let before = &p.cases[4].1.state;
    for amount in [0, (i64::MAX as u64) - app::PERMISSION_RENT + 1, u64::MAX] {
        let mut tx = p.cases[4].1.lane.blocks[0].txs[1].clone();
        let offset = chain::OP_TAG.len() + 4 + 362;
        tx.payload[offset..offset + 8].copy_from_slice(&amount.to_le_bytes());
        assert!(
            matches!(app::apply(before,&tx,&verifier()),Err(e) if e=="native exit amount/rent range")
        );
    }
}
#[cfg(feature = "proof")]
#[test]
fn verifier_rejects_old_real_receipts_and_fakes_under_fixed_new_identity() {
    use risc0_zkvm::{FakeReceipt, InnerReceipt, Receipt, ReceiptClaim};
    let old =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("../../tn10-live/evidence/receipts/exit.bin");
    let r = kpi_private_note_proof::read_receipt(&old).unwrap();
    for stage in ["bob-exit", "alice-exit"] {
        assert!(receipt::verify(stage, &r).is_err());
        let j = receipt::target(stage).unwrap();
        let fake = Receipt::new(
            InnerReceipt::Fake(FakeReceipt::new(ReceiptClaim::ok(
                kpi_private_note_proof::digest(
                    include_str!("../../evidence/expected-image.txt").trim(),
                )
                .unwrap(),
                j.clone(),
            ))),
            j,
        );
        assert!(receipt::verify(stage, &fake).is_err());
    }
    assert!(receipt::target("arbitrary-host-claim").is_err());
}
