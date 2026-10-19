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
/// Preserve upstream self-reconstruction: guards live AFTER the fixed prefix,
/// and the length embedded in suffix extraction includes those guard bytes.
pub fn state_redeem(
    root: &H,
    tip: &Hash,
    pins: &vprogs_zk_backend_risc0_covenant::script::RedeemPins<'_>,
) -> Vec<u8> {
    use vprogs_zk_backend_risc0_covenant::script::{
        build_redeem_script, redeem_script_len, REDEEM_PREFIX_LEN,
    };
    let guard = app::restricted::lane_guard();
    let mut len = redeem_script_len(root, pins) + guard.len() as i64;
    loop {
        let mut bytes = build_redeem_script(root, tip, len, pins);
        bytes.splice(
            REDEEM_PREFIX_LEN as usize..REDEEM_PREFIX_LEN as usize,
            guard.clone(),
        );
        if bytes.len() as i64 == len {
            return bytes;
        }
        len = bytes.len() as i64;
    }
}
pub fn restrict_settlement(
    built: &mut vprogs_zk_backend_risc0_covenant::Settlement,
    prev: &H,
    prev_tip: &Hash,
    next: &H,
    next_tip: &Hash,
    pins: &vprogs_zk_backend_risc0_covenant::script::RedeemPins<'_>,
) -> Result<()> {
    let old_push = ScriptBuilder::new().add_data(&built.prev_redeem)?.drain();
    let sig = &mut built.transaction.inputs[0].signature_script;
    if !sig.ends_with(&old_push) {
        return Err("unexpected upstream redeem push".into());
    }
    sig.truncate(sig.len() - old_push.len());
    built.prev_redeem = state_redeem(prev, prev_tip, pins);
    sig.extend_from_slice(&ScriptBuilder::new().add_data(&built.prev_redeem)?.drain());
    built.next_redeem = state_redeem(next, next_tip, pins);
    built.transaction.outputs[0].script_public_key = pay_to_script_hash_script(&built.next_redeem);
    Ok(())
}
/// Non-broadcastable skeleton. Signature witnesses are intentionally absent.
/// A later new receipt must authorize the same ID through the real state script.
pub fn settlement_template(
    state: &State,
    exit: Option<H>,
    previous: TransactionOutpoint,
    sponsor: TransactionOutpoint,
) -> Transaction {
    let mut outputs = vec![TransactionOutput::with_covenant(
        app::STATE_RENT,
        pay_to_script_hash_script(&state_script(state)),
        Some(CovenantBinding::new(0, Hash::from_bytes(state.covenant))),
    )];
    if let Some(eid) = exit {
        let spk = StandardSpk::ScriptHash(&app::permission_hash(state, eid)).to_script_bytes();
        outputs.push(TransactionOutput::with_covenant(
            app::PERMISSION_RENT,
            ScriptPublicKey::new(0, spk.as_slice().to_vec().into()),
            Some(CovenantBinding::new(0, Hash::from_bytes(state.covenant))),
        ));
    }
    Transaction::new(
        1,
        vec![
            TransactionInput::new_with_compute_budget(previous, vec![], 0, 1),
            TransactionInput::new_with_compute_budget(sponsor, vec![], 0, 1),
        ],
        outputs,
        0,
        chain::LANE.into(),
        0,
        exit.map(app::permission_payload).unwrap_or_default(),
    )
}
pub fn state_script(state: &State) -> Vec<u8> {
    use vprogs_zk_backend_risc0_covenant::script::{CommonPins, RedeemPins, SuccinctPins};
    let image: H = hex::decode(include_str!("../../evidence/expected-image.txt").trim())
        .unwrap()
        .try_into()
        .unwrap();
    let tx = hash(b"KPI-recovery-native-tx-domain-v1");
    let batch = hash(b"KPI-recovery-native-batch-domain-v1");
    let lane = kaspa_seq_commit::hashing::lane_key(&chain::LANE);
    state_redeem(
        &state.root(),
        &Hash::from_bytes(state.lane_tip),
        &RedeemPins::SuccinctJoin(SuccinctPins {
            common: CommonPins {
                program_id: &image,
                tx_image_id: &tx,
                batch_image_id: &batch,
                lane_key: &lane,
                permission_output_value: app::PERMISSION_RENT,
            },
        }),
    )
}
pub fn payout(state: &State, eid: H, attack: &str) -> Result<(Transaction, Vec<UtxoEntry>)> {
    payout_backend(state, eid, attack, false)
}
/// Unrestricted upstream form is retained ONLY to compare the reviewed failure
/// with the deliberate new native restrictions. Never issued by the new guest.
pub fn payout_backend(
    state: &State,
    eid: H,
    attack: &str,
    legacy: bool,
) -> Result<(Transaction, Vec<UtxoEntry>)> {
    let p = &state.permissions[&eid];
    let e = &state.ledger.exits[&eid];
    let key = &state.exit_keys[&eid];
    let reserve = &state.exit_reserves[&eid];
    let value = &state.reserves[reserve];
    let dest = StandardSpk::PubKey(key);
    let empty = PermissionTreeAccumulator::hash_empty();
    let leaf = PermissionTreeAccumulator::hash_leaf(dest, e.amount);
    let root = PermissionTreeAccumulator::hash_branch(&leaf, &empty);
    let redeem = if legacy {
        build_permission_redeem_script(&root, 1, 1)
    } else {
        app::restricted::permission_redeem(state, eid)
    };
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
        "top-up" => {
            outputs[0].value += 1;
            outputs[2].value -= 1;
        }
        "default-lane"
        | "extra-sponsor-input"
        | "extra-sponsor-output"
        | "partial"
        | "partial-three-outputs"
        | "foreign-reserve"
        | "versioned-sponsor-output" => (),
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
    let mut t = Transaction::new(
        1,
        vec![
            TransactionInput::new_with_compute_budget(op(&p.outpoint), b.drain(), 0, 1),
            TransactionInput::new_with_compute_budget(op(reserve), ds, 0, 1),
            TransactionInput::new_with_compute_budget(
                // Distinct deterministic public fixture UTXO for each exit.
                // A sponsor input consumed by Bob cannot also fund Alice.
                TransactionOutpoint::new(
                    Hash::from_bytes(hash(
                        &[b"KPI-recovery-payout-sponsor-v1".as_slice(), &eid].concat(),
                    )),
                    0,
                ),
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
    let mut entries = vec![
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
    if attack == "default-lane" {
        t.subnetwork_id = kaspa_consensus_core::subnets::SUBNETWORK_ID_NATIVE;
    }
    if attack == "foreign-reserve" {
        t.inputs[1].previous_outpoint.transaction_id = Hash::from_bytes([0x98; 32]);
    }
    if attack == "versioned-sponsor-output" {
        // A different script version is not the actual v0 delegate, even
        // when its raw bytes match. It is a sponsor-funded output only.
        t.outputs[2].script_public_key =
            ScriptPublicKey::new(1, app::delegate(&state.covenant).into());
    }
    if attack == "extra-sponsor-input" {
        t.inputs.push(TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(Hash::from_bytes([0x97; 32]), 0),
            vec![],
            0,
            1,
        ));
        entries.push(UtxoEntry::new(
            1_000_000,
            ScriptPublicKey::new(0, vec![0x51].into()),
            0,
            false,
            None,
        ));
        t.outputs[2].value += 1_000_000;
    }
    if attack == "extra-sponsor-output" {
        t.outputs[2].value -= 1;
        t.outputs.push(TransactionOutput::new(
            1,
            ScriptPublicKey::new(0, vec![0x51].into()),
        ));
    }
    if ["partial", "partial-three-outputs"].contains(&attack) {
        let deduct = e.amount / 2;
        let remaining = PermissionTreeAccumulator::hash_leaf(dest, e.amount - deduct);
        let root = PermissionTreeAccumulator::hash_branch(&remaining, &empty);
        let continuation = build_permission_redeem_script(&root, 1, 1);
        let mut b = ScriptBuilder::new();
        for _ in 0..2 {
            b.add_data(&empty)?.add_i64(0)?;
        }
        b.add_data(dest.to_script_bytes().as_slice())?
            .add_data(&e.amount.to_le_bytes())?
            .add_i64(deduct as i64)?
            .add_data(&redeem)?;
        t.inputs[0].signature_script = b.drain();
        let sponsor_change = t.outputs[2].clone();
        t.outputs = vec![
            TransactionOutput::new(
                deduct,
                ScriptPublicKey::new(0, dest.to_script_bytes().as_slice().to_vec().into()),
            ),
            TransactionOutput::with_covenant(
                p.rent,
                pay_to_script_hash_script(&continuation),
                Some(CovenantBinding::new(0, Hash::from_bytes(state.covenant))),
            ),
            TransactionOutput::new(value - deduct, pay_to_script_hash_script(&delegate_redeem)),
            sponsor_change,
        ];
        if attack == "partial-three-outputs" {
            t.outputs.pop();
        }
    }
    if *value == e.amount && !attack.starts_with("partial") {
        t.outputs.remove(1);
    }
    sign_sponsor(&mut t, &mut entries)?;
    Ok((t, entries))
}
/// Public test-only key, never funded. Sign AFTER every mutation so native
/// acceptance cannot be attributed to an unsigned OP_TRUE sponsor fixture.
pub fn sign_sponsor(t: &mut Transaction, entries: &mut [UtxoEntry]) -> Result<()> {
    use kaspa_consensus_core::hashing::{
        sighash::calc_schnorr_signature_hash, sighash_type::SIG_HASH_ALL,
    };
    let key = secp256k1::Keypair::from_seckey_slice(secp256k1::SECP256K1, &[0x37; 32])?;
    let pk = key.public_key().x_only_public_key().0.serialize();
    let spk = ScriptPublicKey::new(
        0,
        StandardSpk::PubKey(&pk)
            .to_script_bytes()
            .as_slice()
            .to_vec()
            .into(),
    );
    for i in 2..entries.len() {
        entries[i].script_public_key = spk.clone();
    }
    if t.outputs.last().unwrap().covenant.is_none()
        && t.outputs.last().unwrap().script_public_key == ScriptPublicKey::new(0, vec![0x51].into())
    {
        t.outputs.last_mut().unwrap().script_public_key = spk;
    }
    for i in 2..entries.len() {
        let pop = PopulatedTransaction::new(t, entries.to_vec());
        let h =
            calc_schnorr_signature_hash(&pop, i, SIG_HASH_ALL, &SigHashReusedValuesUnsync::new());
        let sig = key.sign_schnorr(secp256k1::Message::from_digest_slice(&h.as_bytes())?);
        t.inputs[i].signature_script =
            [vec![65], sig.as_ref().to_vec(), vec![SIG_HASH_ALL.to_u8()]].concat();
    }
    t.finalize();
    Ok(())
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
