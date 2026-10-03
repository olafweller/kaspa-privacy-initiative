//! Offline experiment: genuine proof and production consensus validation, supplied UTXO fixture.
//! This program cannot submit transactions, fund reserves, or establish live TN10 acceptance.
mod circuit;
mod live;
use ark_bn254::{Bn254, Fr};
use ark_groth16::{Groth16, Proof};
use ark_serialize::CanonicalSerialize;
use ark_snark::SNARK;
use kaspa_consensus::processes::transaction_validator::{
    TransactionValidator, tx_validation_in_utxo_context::TxValidationFlags,
};
use kaspa_consensus_core::{
    config::params::TESTNET_PARAMS,
    mass::{ComputeBudget, MassCalculator, transaction_estimated_serialized_size},
    tx::{
        GenesisCovenantGroup, PopulatedTransaction, ScriptPublicKey, Transaction, TransactionInput,
        TransactionOutpoint, TransactionOutput, UtxoEntry,
    },
};
use kaspa_hashes::Hash;
use kaspa_txscript::{
    EngineCtx, SigCacheKey, TxScriptEngine,
    caches::{Cache, TxScriptCacheCounters},
    opcodes::codes::*,
    pay_to_script_hash_script, pay_to_script_hash_signature_script_with_flags,
    script_builder::ScriptBuilder,
};
use rand::{RngCore, rngs::OsRng};
use serde_json::{Value, json};
use std::{sync::Arc, time::Instant};

const AMOUNT: u64 = 1_000_000_000;
const FEE: u64 = 20_000_000;
const RESERVE: u64 = AMOUNT + FEE;
const BUDGET: u16 = 1700;

fn compressed<T: CanonicalSerialize>(x: &T) -> Vec<u8> {
    let mut bytes = vec![];
    x.serialize_compressed(&mut bytes).unwrap();
    bytes
}
fn field(x: Fr) -> Vec<u8> {
    compressed(&x)
}

// Consensus OpTxOutputSpk encoding: two-byte big-endian version, then script.
// The upstream SpkEncoding trait is private; encode its documented byte ABI here.
fn encode_spk(spk: &ScriptPublicKey) -> Vec<u8> {
    let mut bytes = spk.version().to_be_bytes().to_vec();
    bytes.extend_from_slice(spk.script());
    bytes
}

#[derive(Clone)]
struct Policy {
    prefix: Vec<u8>,
    claim: [u8; 32],
    recipient: ScriptPublicKey,
}

fn policy(secret: &[u8; 32]) -> Policy {
    // Fresh recipient secret exists only in memory; no funds are used by this executable.
    let key = secp256k1::Keypair::new(&secp256k1::Secp256k1::new(), &mut OsRng);
    let (public, _) = key.x_only_public_key();
    let recipient = ScriptPublicKey::new(
        0,
        ScriptBuilder::new()
            .add_data(&public.serialize())
            .unwrap()
            .add_op(OpCheckSig)
            .unwrap()
            .drain()
            .into(),
    );
    policy_for_recipient(secret, recipient)
}

fn context_prefix(recipient: &ScriptPublicKey, state: &[u8; 32]) -> Vec<u8> {
    let mut prefix = b"KPI-A0/TN10/terminal/v1\0".to_vec();
    prefix.extend_from_slice(&TESTNET_PARAMS.genesis.hash.as_bytes());
    prefix.extend_from_slice(state);
    for n in [RESERVE, AMOUNT, FEE] {
        prefix.extend_from_slice(&n.to_le_bytes());
    }
    prefix.extend_from_slice(&(encode_spk(&recipient).len() as u32).to_le_bytes());
    prefix.extend_from_slice(&encode_spk(&recipient));
    prefix.push(1); // terminal state marker: zero remaining user liability
    prefix
}

fn policy_for_recipient(secret: &[u8; 32], recipient: ScriptPublicKey) -> Policy {
    let mut state = [0u8; 32];
    OsRng.fill_bytes(&mut state);
    Policy {
        prefix: context_prefix(&recipient, &state),
        claim: circuit::claim_commitment(secret),
        recipient,
    }
}

fn redeem(vk: &[u8], policy: &Policy) -> Vec<u8> {
    let mut b = ScriptBuilder::new();
    // All transaction economics and output bytes are exact; no fee from user liability.
    b.add_op(OpTxInputCount)
        .unwrap()
        .add_i64(1)
        .unwrap()
        .add_op(OpEqualVerify)
        .unwrap();
    b.add_op(OpTxOutputCount)
        .unwrap()
        .add_i64(1)
        .unwrap()
        .add_op(OpEqualVerify)
        .unwrap();
    b.add_i64(0)
        .unwrap()
        .add_op(OpTxInputAmount)
        .unwrap()
        .add_i64(RESERVE as i64)
        .unwrap()
        .add_op(OpEqualVerify)
        .unwrap();
    b.add_i64(0)
        .unwrap()
        .add_op(OpTxOutputAmount)
        .unwrap()
        .add_i64(AMOUNT as i64)
        .unwrap()
        .add_op(OpEqualVerify)
        .unwrap();
    b.add_i64(0)
        .unwrap()
        .add_op(OpTxOutputSpk)
        .unwrap()
        .add_data(&encode_spk(&policy.recipient))
        .unwrap()
        .add_op(OpEqualVerify)
        .unwrap();
    b.add_i64(0)
        .unwrap()
        .add_op(OpOutputAuthorizingInput)
        .unwrap()
        .add_i64(-1)
        .unwrap()
        .add_op(OpEqualVerify)
        .unwrap();
    // Stack initially T_high, T_low, proof. Save proof; construct actual outpoint fields.
    b.add_op(OpToAltStack).unwrap();
    // NUM2BIN max size is 8. Every u32 index is positive in i64; append 24 zeros.
    b.add_i64(0)
        .unwrap()
        .add_op(OpOutpointIndex)
        .unwrap()
        .add_i64(8)
        .unwrap()
        .add_op(OpNum2Bin)
        .unwrap()
        .add_data(&[0; 24])
        .unwrap()
        .add_op(OpCat)
        .unwrap();
    for (start, end) in [(16, 32), (0, 16)] {
        b.add_i64(0)
            .unwrap()
            .add_op(OpOutpointTxId)
            .unwrap()
            .add_i64(start)
            .unwrap()
            .add_i64(end)
            .unwrap()
            .add_op(OpSubstr)
            .unwrap()
            .add_data(&[0; 16])
            .unwrap()
            .add_op(OpCat)
            .unwrap();
    }
    b.add_i64(5)
        .unwrap()
        .add_op(OpFromAltStack)
        .unwrap()
        .add_data(vk)
        .unwrap()
        .add_data(&[0x20])
        .unwrap()
        .add_op(OpZkPrecompile)
        .unwrap();
    b.drain()
}

fn signature(proof: &[u8], inputs: &[Fr], redeem: &[u8]) -> Vec<u8> {
    let mut b = ScriptBuilder::new();
    b.add_data(&field(inputs[4]))
        .unwrap()
        .add_data(&field(inputs[3]))
        .unwrap()
        .add_data(proof)
        .unwrap();
    pay_to_script_hash_signature_script_with_flags(redeem.to_vec(), b.drain(), Default::default())
        .unwrap()
}

fn validator() -> TransactionValidator {
    let p = TESTNET_PARAMS;
    TransactionValidator::new(
        p.max_tx_inputs,
        p.max_tx_outputs,
        p.max_signature_script_len,
        p.max_script_public_key_len,
        p.coinbase_payload_script_public_key_max_len,
        p.coinbase_maturity(),
        p.ghostdag_k(),
        Arc::new(TxScriptCacheCounters::default()),
        MassCalculator::new_with_consensus_params(&p),
        p.mass_per_sig_op,
    )
}
fn mass(tx: &Transaction, entry: &UtxoEntry) {
    if tx.outputs.iter().all(|o| o.value > 0) {
        let pop = PopulatedTransaction::new(tx, vec![entry.clone(); tx.inputs.len()]);
        if let Some(m) =
            MassCalculator::new_with_consensus_params(&TESTNET_PARAMS).calc_contextual_masses(&pop)
        {
            tx.set_storage_mass(m.storage_mass);
        }
    }
}
fn validate(tv: &TransactionValidator, tx: &Transaction, entry: &UtxoEntry) -> Result<u64, String> {
    validate_at(tv, tx, entry, 1_000_000_000, 1_000_000_000)
}
fn validate_at(
    tv: &TransactionValidator,
    tx: &Transaction,
    entry: &UtxoEntry,
    daa: u64,
    median: u64,
) -> Result<u64, String> {
    tv.validate_tx_in_isolation(tx)
        .map_err(|e| format!("isolation: {e:?}"))?;
    let pop = PopulatedTransaction::new(tx, vec![entry.clone(); tx.inputs.len()]);
    tv.validate_populated_transaction_and_get_fee(
        &pop,
        daa,
        median,
        TxValidationFlags::Full,
        None,
        None,
    )
    .map_err(|e| format!("utxo: {e:?}"))
}
fn record(
    tv: &TransactionValidator,
    name: &str,
    mut tx: Transaction,
    entry: UtxoEntry,
    expected: bool,
    results: &mut Vec<Value>,
) {
    tx.finalize();
    mass(&tx, &entry);
    let start = Instant::now();
    let result = validate(tv, &tx, &entry);
    let elapsed = start.elapsed().as_secs_f64() * 1000.;
    assert_eq!(result.is_ok(), expected, "case {name}: {result:?}");
    results.push(json!({"case":name,"accepted":result.is_ok(),"expected_accept":expected,"validation_ms":elapsed,"result":format!("{result:?}")}));
}

fn main() {
    if std::env::args().nth(1).as_deref() == Some("live") {
        if let Err(error) = live::run() {
            // Adapter errors contain static check names, public transaction fields or
            // library error categories, never secret/key byte contents.
            eprintln!("A0 live preparation/check failed: {error}");
            std::process::exit(1);
        }
        return;
    }
    let started = Instant::now();
    let mut secret = [0u8; 32];
    OsRng.fill_bytes(&mut secret);
    let policy = policy(&secret);
    let mut txid = [0u8; 32];
    OsRng.fill_bytes(&mut txid);
    let index = 7u32;
    let circuit = new_circuit(policy.prefix.clone(), policy.claim, secret, txid, index);
    let inputs = circuit.inputs.unwrap();
    eprintln!(
        "Generating fresh Groth16 setup (experimental single-party toxic waste, never fund)..."
    );
    let setup_start = Instant::now();
    let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(circuit.clone(), &mut OsRng).unwrap();
    let setup_ms = setup_start.elapsed().as_secs_f64() * 1000.;
    eprintln!("Proving SHA256 claim and context...");
    let proving_start = Instant::now();
    let proof = Groth16::<Bn254>::prove(&pk, circuit.clone(), &mut OsRng).unwrap();
    let proving_ms = proving_start.elapsed().as_secs_f64() * 1000.;
    let verify_start = Instant::now();
    assert!(Groth16::<Bn254>::verify(&vk, &inputs, &proof).unwrap());
    let standalone_verify_ms = verify_start.elapsed().as_secs_f64() * 1000.;
    let vk_bytes = compressed(&vk);
    let proof_bytes = compressed(&proof);
    let redeem = redeem(&vk_bytes, &policy);
    let sig = signature(&proof_bytes, &inputs, &redeem);
    let entry = UtxoEntry::new(RESERVE, pay_to_script_hash_script(&redeem), 0, false, None);
    let tx = Transaction::new(
        1,
        vec![TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(Hash::from_bytes(txid), index),
            sig,
            u64::MAX,
            BUDGET,
        )],
        vec![TransactionOutput::new(AMOUNT, policy.recipient.clone())],
        0,
        Default::default(),
        0,
        vec![],
    );
    mass(&tx, &entry);
    let tv = validator();
    let mut results = vec![];
    let populated = PopulatedTransaction::new(&tx, vec![entry.clone()]);
    let cache: Cache<SigCacheKey, bool> = Cache::new(10);
    let reused = kaspa_consensus_core::hashing::sighash::SigHashReusedValuesUnsync::new();
    let mut engine = TxScriptEngine::from_transaction_input_with_script_units_limit(
        &populated,
        &tx.inputs[0],
        0,
        &entry,
        EngineCtx::new(&cache).with_reused(&reused),
        Default::default(),
        tx.inputs[0].compute_commit.allowed_script_units(),
    );
    engine.execute().expect("metered real engine");
    let used_script_units = engine.used_script_units().0;
    record(
        &tv,
        "valid_terminal_release",
        tx.clone(),
        entry.clone(),
        true,
        &mut results,
    );
    let mut bad = proof_bytes.clone();
    bad[0] ^= 0xff;
    let mut t = tx.clone();
    t.inputs[0].signature_script = signature(&bad, &inputs, &redeem);
    record(
        &tv,
        "malformed_proof",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut trailing = proof_bytes.clone();
    trailing.push(0);
    let mut t = tx.clone();
    t.inputs[0].signature_script = signature(&trailing, &inputs, &redeem);
    record(
        &tv,
        "proof_trailing_bytes",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    for size in [31usize, 33] {
        let mut raw = ScriptBuilder::new();
        raw.add_data(&vec![1u8; size])
            .unwrap()
            .add_data(&field(inputs[3]))
            .unwrap()
            .add_data(&proof_bytes)
            .unwrap();
        let mut t = tx.clone();
        t.inputs[0].signature_script = pay_to_script_hash_signature_script_with_flags(
            redeem.clone(),
            raw.drain(),
            Default::default(),
        )
        .unwrap();
        record(
            &tv,
            &format!("public_input_length_{size}"),
            t,
            entry.clone(),
            false,
            &mut results,
        );
    }
    let mut t = tx.clone();
    t.inputs[0].signature_script =
        signature(&compressed(&Proof::<Bn254>::default()), &inputs, &redeem);
    record(
        &tv,
        "missing_authorization_identity_proof",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.inputs[0].signature_script = vec![];
    record(
        &tv,
        "missing_authorization_empty",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.inputs[0].previous_outpoint.transaction_id = Hash::from_bytes([0x55; 32]);
    record(
        &tv,
        "replay_other_outpoint_txid",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.inputs[0].previous_outpoint.index += 1;
    record(
        &tv,
        "replay_other_outpoint_index",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.inputs[0].previous_outpoint.index = u32::MAX;
    record(
        &tv,
        "outpoint_index_u32_max",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    for (name, amount) in [
        ("wrong_amount_underpay", AMOUNT - 1),
        ("wrong_amount_overpay", AMOUNT + 1),
        ("amount_zero", 0),
        ("amount_u64_max", u64::MAX),
    ] {
        let mut t = tx.clone();
        t.outputs[0].value = amount;
        record(&tv, name, t, entry.clone(), false, &mut results);
    }
    let mut t = tx.clone();
    t.outputs[0].script_public_key = ScriptPublicKey::new(0, vec![OpTrue].into());
    record(
        &tv,
        "wrong_recipient",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.outputs[0].script_public_key =
        ScriptPublicKey::new(1, policy.recipient.script().to_vec().into());
    record(
        &tv,
        "wrong_recipient_spk_version",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.outputs
        .push(TransactionOutput::new(1, policy.recipient.clone()));
    record(
        &tv,
        "modified_outputs_extra",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.populate_genesis_covenants(&[GenesisCovenantGroup::new(0, vec![0])])
        .unwrap();
    record(
        &tv,
        "modified_output_covenant_metadata",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.outputs.clear();
    record(
        &tv,
        "modified_outputs_missing",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.inputs.push(t.inputs[0].clone());
    record(
        &tv,
        "duplicate_reserve_input",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut t = tx.clone();
    let mut second = t.inputs[0].clone();
    second.previous_outpoint.index += 1;
    t.inputs.push(second);
    record(
        &tv,
        "extra_distinct_reserve_input",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut e = entry.clone();
    e.amount += 1;
    record(
        &tv,
        "wrong_reserve_value",
        tx.clone(),
        e,
        false,
        &mut results,
    );
    let mut t = tx.clone();
    t.inputs[0].compute_commit = ComputeBudget(0).into();
    record(
        &tv,
        "insufficient_compute_budget",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut invalid_inputs = inputs.clone();
    invalid_inputs[3] += Fr::from(1u64);
    let mut t = tx.clone();
    t.inputs[0].signature_script = signature(&proof_bytes, &invalid_inputs, &redeem);
    record(
        &tv,
        "invalid_public_inputs_tag",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    let mut raw = ScriptBuilder::new();
    raw.add_data(&[0xff; 32])
        .unwrap()
        .add_data(&field(inputs[3]))
        .unwrap()
        .add_data(&proof_bytes)
        .unwrap();
    let mut t = tx.clone();
    t.inputs[0].signature_script = pay_to_script_hash_signature_script_with_flags(
        redeem.clone(),
        raw.drain(),
        Default::default(),
    )
    .unwrap();
    record(
        &tv,
        "noncanonical_field_input",
        t,
        entry.clone(),
        false,
        &mut results,
    );
    // Valid proofs for changed constants use different verification keys. Present both under original reserve.
    for (name, position) in [
        ("wrong_domain", 0),
        ("wrong_state", b"KPI-A0/TN10/terminal/v1\0".len() + 32),
    ] {
        let mut prefix = policy.prefix.clone();
        prefix[position] ^= 1;
        let wrong = new_circuit(prefix, policy.claim, secret, txid, index);
        let wrong_inputs = wrong.inputs.unwrap();
        let (other_pk, other_vk) =
            Groth16::<Bn254>::circuit_specific_setup(wrong.clone(), &mut OsRng).unwrap();
        let other_proof = Groth16::<Bn254>::prove(&other_pk, wrong, &mut OsRng).unwrap();
        assert!(Groth16::<Bn254>::verify(&other_vk, &wrong_inputs, &other_proof).unwrap());
        let mut t = tx.clone();
        t.inputs[0].signature_script = signature(&compressed(&other_proof), &wrong_inputs, &redeem);
        record(&tv, name, t, entry.clone(), false, &mut results);
        let other_redeem = redeem_fn(&compressed(&other_vk), &policy);
        let mut t = tx.clone();
        t.inputs[0].signature_script =
            signature(&compressed(&other_proof), &wrong_inputs, &other_redeem);
        record(
            &tv,
            &format!("{name}_replacement_verifier"),
            t,
            entry.clone(),
            false,
            &mut results,
        );
    }
    // Exact replay passes stateless validation: UTXO-set membership MUST reject a spent outpoint.
    record(
        &tv,
        "exact_replay_stateless_boundary",
        tx.clone(),
        entry.clone(),
        true,
        &mut results,
    );
    let calculator = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS);
    let masses = calculator.calc_non_contextual_masses(&tx);
    assert!(masses.compute_mass <= TESTNET_PARAMS.block_mass_limits.compute);
    assert!(masses.transient_mass <= TESTNET_PARAMS.block_mass_limits.transient);
    assert!(tx.storage_mass() <= TESTNET_PARAMS.block_mass_limits.storage);
    // Sanity-check the default policy floor; this does not execute the mempool.
    let fee_mass = masses.normalized_max(&TESTNET_PARAMS.block_mass_limits.cofactors());
    let minimum_relay_fee_sompi = fee_mass.checked_mul(100).unwrap();
    assert!(FEE >= minimum_relay_fee_sompi);
    println!("{}",serde_json::to_string_pretty(&json!({"scope":"offline production TransactionValidator::Full with supplied UTXO; NOT live TN10; no UTXO membership test", "upstream_revision":"01b532e8b553523216471682649693af92f0fd16", "network":"testnet-10", "proof_system":"Groth16 BN254 / arkworks 0.6.0", "setup":"fresh OS randomness, single party trusted setup; unsuitable for deposits", "proof_bytes":proof_bytes.len(),"verifying_key_bytes":vk_bytes.len(),"redeem_script_bytes":redeem.len(),"signature_script_bytes":tx.inputs[0].signature_script.len(),"estimated_transaction_bytes":transaction_estimated_serialized_size(&tx),"compute_mass_grams":masses.compute_mass,"storage_mass_grams":tx.storage_mass(),"transient_mass_grams":masses.transient_mass,"compute_budget":BUDGET,"default_minimum_relay_fee_sompi":minimum_relay_fee_sompi,"reserve_sompi":RESERVE,"user_liability_sompi":AMOUNT,"fee_buffer_sompi":FEE,"used_script_units":used_script_units,"standalone_verify_ms":standalone_verify_ms,"setup_ms":setup_ms,"proving_ms":proving_ms,"total_ms":started.elapsed().as_secs_f64()*1000.,"cases":results})).unwrap());
}
fn redeem_fn(vk: &[u8], policy: &Policy) -> Vec<u8> {
    redeem(vk, policy)
}

fn new_circuit(
    prefix: Vec<u8>,
    claim: [u8; 32],
    secret: [u8; 32],
    txid: [u8; 32],
    index: u32,
) -> circuit::ClaimCircuit {
    let tag = circuit::compute_tag(&prefix, &secret, &txid, index);
    circuit::ClaimCircuit {
        constants: circuit::ClaimConstants {
            context_prefix: prefix,
            claim,
        },
        secret: Some(secret),
        inputs: Some(circuit::public_inputs(&txid, index, &tag)),
    }
}
