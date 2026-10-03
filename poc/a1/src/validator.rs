//! Native full transaction validation against explicit supplied UTXO fixtures.
//! This establishes no chain acceptance or spentness; stateful.rs handles those.
use kaspa_consensus::processes::transaction_validator::{
    TransactionValidator, tx_validation_in_utxo_context::TxValidationFlags,
};
use kaspa_consensus_core::{
    config::params::TESTNET_PARAMS,
    mass::{ComputeBudget, MassCalculator, SCRIPT_UNITS_PER_GRAM, ScriptUnits},
    tx::{PopulatedTransaction, Transaction, UtxoEntry},
};
use kaspa_txscript::{
    EngineCtx, SigCacheKey, TxScriptEngine,
    caches::{Cache, TxScriptCacheCounters},
};
use serde_json::{Value, json};
use std::{collections::BTreeMap, sync::Arc};

pub fn validator() -> TransactionValidator {
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
pub fn set_mass(tx: &Transaction, entry: &UtxoEntry) -> Result<(), String> {
    let pop = PopulatedTransaction::new(tx, vec![entry.clone(); tx.inputs.len()]);
    let m = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS)
        .calc_contextual_masses(&pop)
        .ok_or("native mass undefined")?;
    tx.set_storage_mass(m.storage_mass);
    Ok(())
}
/// Reproduce pinned relay standardness rules with native class/scanner/mass
/// helpers. This is an offline policy check, not remote mempool admission.
pub fn relay_policy(tx: &Transaction, entry: &UtxoEntry, fee: u64) -> Result<Value, String> {
    use kaspa_txscript::{p2sh_sig_scanner, script_class::ScriptClass};
    if entry.script_public_key.version() != 0
        || ScriptClass::from_script(&entry.script_public_key) != ScriptClass::ScriptHash
    {
        return Err("A1 reserve must be standard version-zero P2SH".into());
    }
    let mut sigops = 0;
    for i in &tx.inputs {
        let n = p2sh_sig_scanner(&i.signature_script, &entry.script_public_key);
        if n > 15 {
            return Err("standard P2SH sigop limit".into());
        }
        sigops += n;
    }
    for o in &tx.outputs {
        if o.script_public_key.version() != 0
            || ScriptClass::from_script(&o.script_public_key) == ScriptClass::NonStandard
        {
            return Err("standard output class/version".into());
        }
    }
    let masses =
        MassCalculator::new_with_consensus_params(&TESTNET_PARAMS).calc_non_contextual_masses(tx);
    let normalized_transient = masses.transient_mass.div_ceil(2);
    let mass = masses.compute_mass.max(normalized_transient);
    let rate = 100_000u64;
    let mut floor = mass.checked_mul(rate).ok_or("relay floor overflow")? / 1000;
    if floor == 0 {
        floor = rate;
    }
    floor = floor.min(crate::model::MAX_SOMPI);
    if fee < floor {
        return Err("fixed fee below pinned relay floor".into());
    }
    Ok(
        json!({"passed":true,"scope":"offline pinned standardness/class/sigop/fee rules; no remote admission","relay_fee_mass":mass,"normalized_transient_mass":normalized_transient,"relay_rate_sompi_per_kg":rate,"minimum_relay_fee_sompi":floor,"P2SH_sigops":sigops,"storage_has_no_additional_relay_floor":true}),
    )
}
pub fn validate(
    tv: &TransactionValidator,
    tx: &Transaction,
    entry: &UtxoEntry,
) -> Result<u64, String> {
    validate_at(tv, tx, entry, 1_000_000_000, 1_000_000_000)
}
pub fn validate_at(
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

/// Native opcode log snapshots are captured *before* each opcode, including skipped
/// branch instructions. Filter execution using the VM's single-level conditional
/// semantics; retain the original log so a reviewer can inspect this reduction.
pub fn meter(tx: &Transaction, entry: &UtxoEntry, expected_vk: &[u8]) -> Result<Value, String> {
    if tx.inputs.len() != 1 || entry.script_public_key.version() != 0 {
        return Err("meter fixture shape/version".into());
    }
    let pop = PopulatedTransaction::new(tx, vec![entry.clone()]);
    let cache: Cache<SigCacheKey, bool> = Cache::new(10);
    let reused = kaspa_consensus_core::hashing::sighash::SigHashReusedValuesUnsync::new();
    let mut log = vec![];
    let (units, final_main, final_alt) = {
        let mut engine = TxScriptEngine::from_transaction_input_with_script_units_limit(
            &pop,
            &tx.inputs[0],
            0,
            entry,
            EngineCtx::new(&cache).with_reused(&reused),
            Default::default(),
            tx.inputs[0].compute_commit.allowed_script_units(),
        )
        .with_opcode_execution_log_buffer(&mut log);
        engine.execute().map_err(|e| format!("meter: {e:?}"))?;
        (
            engine.used_script_units().0,
            engine.stacks().dstack.to_vec(),
            engine.stacks().astack.to_vec(),
        )
    };
    let log = String::from_utf8(log).map_err(|e| e.to_string())?;
    let parsed_signature = kaspa_txscript::parse_script::<
        PopulatedTransaction<'_>,
        kaspa_consensus_core::hashing::sighash::SigHashReusedValuesUnsync,
    >(&tx.inputs[0].signature_script)
    .collect::<Result<Vec<_>, _>>()
    .map_err(|e| e.to_string())?;
    let redeem = parsed_signature.last().ok_or("empty witness")?.get_data();
    let mut native_counted_ops = vec![];
    let mut largest_element = 0usize;
    for script in [
        &tx.inputs[0].signature_script[..],
        entry.script_public_key.script(),
        redeem,
    ] {
        let mut count = 0;
        for op in kaspa_txscript::parse_script::<
            PopulatedTransaction<'_>,
            kaspa_consensus_core::hashing::sighash::SigHashReusedValuesUnsync,
        >(script)
        {
            let op = op.map_err(|e| e.to_string())?;
            if !op.is_push_opcode() {
                count += 1;
            }
            largest_element = largest_element.max(op.get_data().len());
        }
        native_counted_ops.push(count);
    }
    let mut peak = final_main.len() + final_alt.len();
    let mut active = true;
    let mut inside_if = false;
    let mut count = 0;
    let mut executed_non_push = 0;
    let mut verifiers = 0;
    let mut output_amount = 0;
    let mut output_spk = 0;
    let mut metadata = 0;
    let mut verifier_stack = Value::Null;
    let mut executed_opcodes = BTreeMap::<String, u64>::new();
    for line in log.lines() {
        let line = line
            .strip_prefix("Executing opcode: ")
            .ok_or("native trace prefix")?;
        let (opcode, rest) = line.split_once(", astack: ").ok_or("native trace opcode")?;
        let (alt, main) = rest.split_once(", dstack: ").ok_or("native trace stacks")?;
        let alt: Vec<String> = serde_json::from_str(alt).map_err(|e| e.to_string())?;
        let main: Vec<String> = serde_json::from_str(main).map_err(|e| e.to_string())?;
        peak = peak.max(alt.len() + main.len());
        if opcode == "OpIf" {
            *executed_opcodes.entry(opcode.to_string()).or_default() += 1;
            if inside_if {
                return Err("unexpected nested conditional in A1 trace".into());
            }
            inside_if = true;
            active = main.last().is_some_and(|s| s != "0x" && s != "0x00");
            count += 1;
            executed_non_push += 1;
            continue;
        }
        if opcode == "OpElse" {
            *executed_opcodes.entry(opcode.to_string()).or_default() += 1;
            active = !active;
            count += 1;
            executed_non_push += 1;
            continue;
        }
        if opcode == "OpEndIf" {
            *executed_opcodes.entry(opcode.to_string()).or_default() += 1;
            active = true;
            inside_if = false;
            count += 1;
            executed_non_push += 1;
            continue;
        }
        if !active {
            continue;
        }
        count += 1;
        let name = opcode.split(' ').next().unwrap_or(opcode);
        *executed_opcodes.entry(name.to_string()).or_default() += 1;
        let small_push = matches!(
            name,
            "OpFalse"
                | "OpTrue"
                | "Op1Negate"
                | "Op1"
                | "Op2"
                | "Op3"
                | "Op4"
                | "Op5"
                | "Op6"
                | "Op7"
                | "Op8"
                | "Op9"
                | "Op10"
                | "Op11"
                | "Op12"
                | "Op13"
                | "Op14"
                | "Op15"
                | "Op16"
        );
        if !small_push && !name.starts_with("OpData") && !name.starts_with("OpPushData") {
            executed_non_push += 1;
        }
        if opcode == "OpTxOutputAmount" {
            output_amount += 1;
        }
        if opcode == "OpTxOutputSpk" {
            output_spk += 1;
        }
        if opcode == "OpOutputAuthorizingInput" {
            metadata += 1;
        }
        if opcode == "OpZkPrecompile" {
            verifiers += 1;
            let expected = format!("0x{}", hex::encode(expected_vk));
            if !alt.is_empty()
                || main.len() != 9
                || main[7] != expected
                || main[8] != "0x20"
                || main[5] != "0x05"
            {
                return Err("native pre-verifier stack/VK/tag/count mismatch".into());
            }
            verifier_stack = json!({"main":main,"alternate":alt});
        }
    }
    if verifiers != 1
        || output_amount != tx.outputs.len()
        || output_spk != tx.outputs.len()
        || metadata != tx.outputs.len()
        || final_main.len() != 1
        || final_main[0].as_slice() != [1]
        || !final_alt.is_empty()
    {
        return Err("native trace mandatory body/final stack mismatch".into());
    }
    for (name, expected) in [
        ("OpTxVersion", 1),
        ("OpTxSubnetId", 1),
        ("OpTxGas", 1),
        ("OpTxPayloadLen", 1),
        ("OpTxLockTime", 1),
        ("OpDepth", 1),
        ("OpTxInputCount", 1),
        ("OpTxInputIndex", 1),
        ("OpTxInputAmount", 1),
        ("OpTxOutputCount", 1),
        ("OpOutpointIndex", 1),
        ("OpOutpointTxId", 2),
    ] {
        if executed_opcodes.get(name).copied() != Some(expected) {
            return Err(format!(
                "native mandatory opcode execution count mismatch: {name}"
            ));
        }
    }
    let calculator = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS);
    let masses = calculator
        .calc_contextual_masses(&pop)
        .ok_or("native masses undefined")?;
    let non_contextual = calculator.calc_non_contextual_masses(tx);
    let required_budget = ComputeBudget::checked_covering_script_units(ScriptUnits(units))
        .ok_or("execution exceeds u16 budget")?;
    Ok(
        json!({"script_units":units,"executed_grams_ceil":units.div_ceil(SCRIPT_UNITS_PER_GRAM),"native_counted_ops_per_script_signature_spk_redeem":native_counted_ops,"largest_pushed_element_bytes":largest_element,"minimum_compute_budget":required_budget.0,"peak_combined_stack":peak,"executed_instructions":count,"executed_non_push_ops":executed_non_push,
        "matching_vk_verifiers":verifiers,"output_amount_checks":output_amount,"output_spk_checks":output_spk,
        "metadata_checks":metadata,"verifier_stack":verifier_stack,"compute_mass":non_contextual.compute_mass,
        "storage_mass":masses.storage_mass,"transient_mass":non_contextual.transient_mass,
        "executed_opcode_counts":executed_opcodes,"native_opcode_log":log,"final_main_hex":["01"],"final_alt":[]}),
    )
}
