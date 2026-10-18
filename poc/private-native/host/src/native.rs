//! Actual pinned script-engine checks plus a local UTXO spentness fixture.
//! This is not canonical chain acceptance or a new outer receipt.
use super::*;
use kaspa_consensus_core::{
    hashing::sighash::SigHashReusedValuesUnsync,
    hashing::tx::transaction_v1_rest_preimage,
    tx::{
        CovenantBinding, PopulatedTransaction, ScriptPublicKey, Transaction, TransactionInput,
        TransactionOutpoint, TransactionOutput, UtxoEntry,
    },
};
use kaspa_hashes::Hash;
use kaspa_txscript::{
    caches::Cache, covenants::CovenantsContext, engine_context::EngineContext,
    script_builder::ScriptBuilder, standard::pay_to_script_hash_script, EngineFlags,
    TxScriptEngine,
};
use vprogs_zk_abi::withdrawal::StandardSpk;
use vprogs_zk_backend_risc0_api::{
    build_delegate_entry_script, build_permission_redeem_script, PermissionTreeAccumulator,
};

pub fn op(o: &app::Outpoint) -> TransactionOutpoint {
    TransactionOutpoint::new(Hash::from_bytes(o.id), o.index)
}
pub fn lane_tx(t: &Transaction) -> lane::Tx {
    lane::Tx {
        payload: t.payload.clone(),
        rest: transaction_v1_rest_preimage(t),
        merge_idx: 0,
    }
}
pub fn issuance(state: &State, eid: H) -> Transaction {
    let e = &state.ledger.exits[&eid];
    let key = &state.exit_keys[&eid];
    let spk = StandardSpk::ScriptHash(&app::permission_hash(key, e.amount)).to_script_bytes();
    use vprogs_zk_backend_risc0_covenant::script::{
        build_redeem_script, redeem_script_len, CommonPins, RedeemPins, SuccinctPins,
    };
    let image: H = hex::decode(include_str!("../../evidence/expected-image.txt").trim())
        .unwrap()
        .try_into()
        .unwrap();
    let tx_domain = hash(b"KPI-private-native-tx-domain-v1");
    let batch_domain = hash(b"KPI-private-native-batch-domain-v1");
    let lane_key = kaspa_seq_commit::hashing::lane_key(&chain::LANE);
    let pins = RedeemPins::SuccinctJoin(SuccinctPins {
        common: CommonPins {
            program_id: &image,
            tx_image_id: &tx_domain,
            batch_image_id: &batch_domain,
            lane_key: &lane_key,
            permission_output_value: app::PERMISSION_RENT,
        },
    });
    let root = state.root();
    let len = redeem_script_len(&root, &pins);
    let continuation = build_redeem_script(&root, &Hash::from_bytes(state.lane_tip), len, &pins);
    // The new exit receipt does not exist during CPU preparation. This accepted-
    // lane fixture is explicitly synthetic; issuance script acceptance is NOT
    // claimed by the local payout tests below.
    Transaction::new(
        1,
        vec![
            TransactionInput::new(
                TransactionOutpoint::new(Hash::from_bytes([0x83; 32]), 0),
                vec![],
                0,
                1,
            ),
            TransactionInput::new(
                TransactionOutpoint::new(Hash::from_bytes([0x84; 32]), 0),
                vec![],
                0,
                1,
            ),
        ],
        vec![
            TransactionOutput::with_covenant(
                app::STATE_RENT,
                pay_to_script_hash_script(&continuation),
                Some(CovenantBinding::new(0, Hash::from_bytes(state.covenant))),
            ),
            TransactionOutput::with_covenant(
                app::PERMISSION_RENT,
                ScriptPublicKey::new(0, spk.as_slice().to_vec().into()),
                Some(CovenantBinding::new(0, Hash::from_bytes(state.covenant))),
            ),
        ],
        0,
        chain::LANE.into(),
        0,
        app::permission_payload(eid),
    )
}
pub fn payout(state: &State, eid: H, attack: &str) -> Result<(Transaction, Vec<UtxoEntry>)> {
    let p = &state.permissions[&eid];
    let e = &state.ledger.exits[&eid];
    let key = &state.exit_keys[&eid];
    let (reserve, value) = state.reserves.iter().next().ok_or("missing reserve")?;
    let dest = StandardSpk::PubKey(key);
    let empty = PermissionTreeAccumulator::hash_empty();
    let leaf = PermissionTreeAccumulator::hash_leaf(dest, e.amount);
    let root = PermissionTreeAccumulator::hash_branch(&leaf, &empty);
    let redeem = build_permission_redeem_script(&root, 1, 1);
    let delegate_redeem = build_delegate_entry_script(&state.covenant);
    let mut b = ScriptBuilder::new();
    for _ in 0..2 {
        b.add_data(&empty)?.add_i64(0)?;
    }
    b.add_data(dest.to_script_bytes().as_slice())?
        .add_data(&e.amount.to_le_bytes())?
        .add_i64(i64::try_from(e.amount)?)?
        .add_data(&redeem)?;
    let ds = ScriptBuilder::new().add_data(&delegate_redeem)?.drain();
    let fee = 100_000;
    let sponsor = 200_000_000;
    let mut outputs = vec![
        TransactionOutput::new(
            e.amount + p.rent,
            ScriptPublicKey::new(0, dest.to_script_bytes().as_slice().to_vec().into()),
        ),
        TransactionOutput::new(
            value - e.amount,
            pay_to_script_hash_script(&delegate_redeem),
        ),
        TransactionOutput::new(sponsor - fee, ScriptPublicKey::new(0, vec![0x51].into())),
    ];
    match attack {
        "underpay" => {
            outputs[0].value -= 1;
            outputs[2].value += 1;
        }
        "reserve-diversion" => {
            outputs[1].value -= 1;
            outputs[2].value += 1;
        }
        "wrong-recipient" => {
            outputs[0].script_public_key = ScriptPublicKey::new(0, vec![0x51].into())
        }
        "" => (),
        _ => return Err("unknown native attack".into()),
    }
    let t = Transaction::new(
        1,
        vec![
            TransactionInput::new(op(&p.outpoint), b.drain(), 0, 1),
            TransactionInput::new(op(reserve), ds, 0, 1),
            TransactionInput::new(
                TransactionOutpoint::new(Hash::from_bytes([0x85; 32]), 0),
                vec![],
                0,
                1,
            ),
        ],
        outputs,
        0,
        chain::LANE.into(),
        0,
        app::payout_payload(eid),
    );
    let entries = vec![
        UtxoEntry::new(
            p.rent,
            pay_to_script_hash_script(&redeem),
            0,
            false,
            Some(Hash::from_bytes(state.covenant)),
        ),
        UtxoEntry::new(
            *value,
            pay_to_script_hash_script(&delegate_redeem),
            0,
            false,
            None,
        ),
        UtxoEntry::new(
            sponsor,
            ScriptPublicKey::new(0, vec![0x51].into()),
            0,
            false,
            None,
        ),
    ];
    Ok((t, entries))
}
/// Execute all input scripts with actual covenant context. Report exact script
/// errors: no build/resource/panic failure is a passing negative control.
pub fn scripts(
    t: &Transaction,
    entries: &[UtxoEntry],
) -> Result<std::result::Result<Vec<u64>, kaspa_txscript_errors::TxScriptError>> {
    let pop = PopulatedTransaction::new(t, entries.to_vec());
    let ctx = CovenantsContext::from_tx(&pop)?;
    let cache = Cache::new(100);
    let reused = SigHashReusedValuesUnsync::new();
    let mut budgets = vec![];
    for (i, e) in entries.iter().enumerate() {
        let ec = EngineContext::new(&cache)
            .with_reused(&reused)
            .with_covenants_ctx(&ctx);
        let mut vm = TxScriptEngine::from_transaction_input(
            &pop,
            &t.inputs[i],
            i,
            e,
            ec,
            EngineFlags::default(),
        );
        if let Err(e) = vm.execute() {
            return Ok(Err(e));
        }
        budgets.push(vm.used_script_units().0);
    }
    Ok(Ok(budgets))
}
pub fn campaign(state: &State, eid: H) -> Result<serde_json::Value> {
    let mut negative = vec![];
    for name in ["underpay", "reserve-diversion", "wrong-recipient"] {
        let (tx, entries) = payout(state, eid, name)?;
        let error = scripts(&tx, &entries)?.expect_err("native mutation must reject");
        if !matches!(
            error,
            kaspa_txscript_errors::TxScriptError::EvalFalse
                | kaspa_txscript_errors::TxScriptError::VerifyError
        ) {
            return Err(format!("unexpected rejection type for {name}: {error}").into());
        }
        negative.push(json!({"case":name,"layer":"actual native TxScriptEngine","error":error.to_string(),"rejected":true}));
    }
    let (tx, entries) = payout(state, eid, "")?;
    let units = scripts(&tx, &entries)?.map_err(|e| format!("positive script: {e}"))?;
    let mut unspent: std::collections::BTreeSet<_> = tx
        .inputs
        .iter()
        .map(|i| app::Outpoint {
            id: i.previous_outpoint.transaction_id.into(),
            index: i.previous_outpoint.index,
        })
        .collect();
    for i in &tx.inputs {
        assert!(unspent.remove(&app::Outpoint {
            id: i.previous_outpoint.transaction_id.into(),
            index: i.previous_outpoint.index
        }));
    }
    let mut replay = tx.clone();
    replay.lock_time += 1;
    replay.finalize();
    assert_ne!(tx.id(), replay.id());
    let missing = replay.inputs.iter().any(|i| {
        !unspent.contains(&app::Outpoint {
            id: i.previous_outpoint.transaction_id.into(),
            index: i.previous_outpoint.index,
        })
    });
    assert!(missing);
    negative.push(json!({"case":"distinct-payout-replay","layer":"local UTXO spentness fixture, not script re-verification or live consensus","differentNativeId":true,"missingSpentPermissionAndReserve":true,"rejected":true}));
    let total_in: u64 = entries.iter().map(|x| x.amount).sum();
    let total_out: u64 = tx.outputs.iter().map(|x| x.value).sum();
    Ok(
        json!({"scope":"ACTUAL_PAYOUT_SCRIPTS_WITH_SYNTHETIC_PERMISSION_ISSUANCE_AND_LOCAL_UTXO_SET","positiveNativeScriptsAccepted":true,"permissionIssuanceReceiptVerified":false,"scriptUnits":units,"negativeControls":negative,"principalPaidSompi":400_000_000u64,"permissionRentRefundSompi":50_000_000u64,"recipientNativeOutputSompi":tx.outputs[0].value,"delegateChangeSompi":tx.outputs[1].value,"sponsorInputSompi":entries[2].amount,"sponsorChangeSompi":tx.outputs[2].value,"nativeFeeSompi":total_in-total_out,"stateRentExcludedSompi":app::STATE_RENT,"actualTN10Broadcast":false}),
    )
}
