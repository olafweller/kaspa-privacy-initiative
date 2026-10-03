//! Native verifier semantics against fabricated, unfunded diagnostic UTXOs.
//! Mutated redeem scripts are never claimed admissible reserve artifacts.
//! Original P2SH binding is preserved in every negative by deriving the matching
//! diagnostic SPK; thus rejection must come from the intended native verifier.
use kaspa_consensus_core::tx::{
    ScriptPublicKey, Transaction, TransactionInput, TransactionOutpoint, TransactionOutput,
    UtxoEntry,
};
use kaspa_txscript::pay_to_script_hash_script;
use kpi_poc_a1::{circuit, script, validator};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs,
    path::{Component, Path},
};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
fn sha(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}
fn load(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}
fn decode(value: &Value) -> Result<Vec<u8>> {
    let s = value.as_str().ok_or("hex text")?;
    if s.len() % 2 != 0
        || !s
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("canonical hex".into());
    }
    Ok(hex::decode(s)?)
}
fn integer(value: &Value) -> Result<u64> {
    if let Some(number) = value.as_u64() {
        return Ok(number);
    }
    let text = value.as_str().ok_or("integer")?;
    if text.is_empty()
        || !text.bytes().all(|b| b.is_ascii_digit())
        || (text.len() > 1 && text.starts_with('0'))
    {
        return Err("canonical decimal".into());
    }
    Ok(text.parse()?)
}
fn artifact(bundle: &Path, descriptor: &Value) -> Result<Vec<u8>> {
    let relative = Path::new(descriptor["path"].as_str().ok_or("artifact path")?);
    if relative.as_os_str().is_empty()
        || relative
            .components()
            .any(|c| !matches!(c, Component::Normal(_)))
    {
        return Err("safe relative artifact path".into());
    }
    let path = bundle.join(relative).canonicalize()?;
    if !path.starts_with(bundle.canonicalize()?) {
        return Err("artifact escaped bundle".into());
    }
    let bytes = fs::read(path)?;
    if descriptor["bytes"].as_str() != Some(&bytes.len().to_string())
        || descriptor["sha256"] != sha(&bytes)
    {
        return Err("artifact descriptor mismatch".into());
    }
    Ok(bytes)
}
fn transaction(value: &Value) -> Result<Transaction> {
    if integer(&value["version"])? != 1 {
        return Err("original v1 required".into());
    }
    let mut inputs = vec![];
    for input in value["inputs"].as_array().ok_or("inputs")? {
        if integer(&input["sigOpCount"])? != 0 {
            return Err("mixed compute metadata".into());
        }
        let op = &input["previousOutpoint"];
        inputs.push(TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(
                op["transactionId"].as_str().ok_or("txid")?.parse()?,
                integer(&op["index"])?.try_into()?,
            ),
            decode(&input["signatureScript"])?,
            integer(&input["sequence"])?,
            integer(&input["computeBudget"])?.try_into()?,
        ));
    }
    let mut outputs = vec![];
    for output in value["outputs"].as_array().ok_or("outputs")? {
        let spk = decode(&output["scriptPublicKey"])?;
        if spk.len() < 3 || &spk[..2] != [0, 0] || output.get("covenant") != Some(&Value::Null) {
            return Err("original version0/None output".into());
        }
        outputs.push(TransactionOutput::new(
            integer(&output["value"])?,
            ScriptPublicKey::from_vec(0, spk[2..].to_vec()),
        ));
    }
    let tx = Transaction::new(
        1,
        inputs,
        outputs,
        integer(&value["lockTime"])?,
        value["subnetworkId"]
            .as_str()
            .ok_or("subnetwork")?
            .parse()?,
        integer(&value["gas"])?,
        decode(&value["payload"])?,
    );
    tx.set_storage_mass(integer(&value["storageMass"])?);
    if tx.id().to_string() != value["id"].as_str().ok_or("ID")? {
        return Err("original decoded ID mismatch".into());
    }
    Ok(tx)
}

fn run(bundle: &Path) -> Result<Value> {
    let manifest = load(&bundle.join("manifest.json"))?;
    let request = load(&bundle.join("s0_terminal.validate.json"))?;
    let original = transaction(&request["transaction"])?;
    let entry: UtxoEntry = serde_json::from_value(request["entry"].clone())?;
    if original.inputs.len() != 1 || entry.script_public_key.version() != 0 {
        return Err("original input shape/version".into());
    }
    let redeem = artifact(bundle, &manifest["states"]["s0"]["redeem"])?;
    let vk = artifact(bundle, &manifest["branches"]["s0_terminal"]["vk"])?;
    let proof = fs::read(bundle.join("s0_terminal.proof"))?;
    let signature = &original.inputs[0].signature_script;
    if proof.len() != 128
        || signature.len() < 197
        || signature[0] != 0x20
        || signature[33] != 0x20
        || signature[66..68] != [0x4c, 0x80]
        || signature[68..196] != proof
        || signature[196] != 0x51
    {
        return Err("canonical original terminal proof witness required".into());
    }
    let mut tag = [0u8; 32];
    tag[..16].copy_from_slice(&signature[34..50]);
    tag[16..].copy_from_slice(&signature[1..17]);
    let op = original.inputs[0].previous_outpoint;
    let inputs = circuit::public_inputs(&op.transaction_id.as_bytes(), op.index, &tag);
    if script::signature(&proof, &inputs, &[1], &redeem)? != *signature
        || pay_to_script_hash_script(&redeem) != entry.script_public_key
    {
        return Err("original witness/redeem binding mismatch".into());
    }
    let tv = validator::validator();
    validator::validate(&tv, &original, &entry)?;
    if vk.len() != 424 {
        return Err("original VK424 required".into());
    }
    let positions: Vec<_> = redeem
        .windows(vk.len())
        .enumerate()
        .filter_map(|(index, window)| (window == vk).then_some(index))
        .collect();
    if positions.len() != 1 {
        return Err("exact terminal VK occurrence".into());
    }
    let start = positions[0];
    let end = start + vk.len();
    if start < 5
        || redeem.get(start - 5..start) != Some(&[0x55, 0x6c, 0x4d, 0xa8, 0x01][..])
        || redeem.get(end..end + 3) != Some(&[0x01, 0x20, 0xa6][..])
    {
        return Err("frozen verifier epilogue mapping".into());
    }
    let mut count = redeem.clone();
    count[start - 5] = 0x54; // Four valid Fr inputs; gamma_abc arity mismatch, not stack underflow.
    let mut unknown_tag = redeem.clone();
    unknown_tag[end + 1] = 0x22;
    let mut trailing_key = redeem[..start - 3].to_vec();
    trailing_key.extend([0x4d, 0xa9, 0x01]);
    trailing_key.extend(&vk);
    trailing_key.push(0);
    trailing_key.extend(&redeem[end..]);
    let mut results = vec![];
    // Explicit matching-P2SH positive control uses the exact original template.
    let diagnostic_positive = entry.clone();
    validator::validate(&tv, &original, &diagnostic_positive)?;
    for (name, changed, expected_error) in [
        ("wrong_public_input_count", count, "arity"),
        ("unknown_verifier_tag", unknown_tag, "Unknown tag"),
        (
            "trailing_immutable_vk_byte",
            trailing_key,
            "verifying key has trailing bytes",
        ),
    ] {
        let mut diagnostic_entry = entry.clone();
        diagnostic_entry.script_public_key = pay_to_script_hash_script(&changed);
        let mut tx = original.clone();
        tx.inputs[0].signature_script = script::signature(&proof, &inputs, &[1], &changed)?;
        tx.finalize();
        validator::set_mass(&tx, &diagnostic_entry)?;
        let error = validator::validate(&tv, &tx, &diagnostic_entry)
            .err()
            .ok_or("native verifier diagnostic unexpectedly accepted")?;
        if !error.contains("ZkIntegrity")
            || !error
                .to_lowercase()
                .contains(&expected_error.to_lowercase())
        {
            return Err(format!("diagnostic rejected for unrelated cause: {name}: {error}").into());
        }
        results.push(json!({"case":name,"native_accepted":false,"observed_layer":"native-verifier-semantics",
            "expected_error_fragment":expected_error,"native_error":error,"matching_diagnostic_P2SH":true,
            "diagnostic_redeem_sha256":sha(&changed),"admissible_A1_artifact":false}));
    }
    // Native unknown-version semantics intentionally accept without executing
    // the invalid empty witness. This is NEVER admissible A1 funding/spending.
    let mut unknown_entry = entry.clone();
    unknown_entry.script_public_key =
        ScriptPublicKey::from_vec(1, entry.script_public_key.script().to_vec());
    let mut unknown_tx = original.clone();
    unknown_tx.inputs[0].signature_script.clear();
    unknown_tx.finalize();
    validator::set_mass(&unknown_tx, &unknown_entry)?;
    validator::validate(&tv, &unknown_tx, &unknown_entry)?;
    results.push(json!({"case":"unknown_input_SPK_version1_skips_invalid_empty_witness","native_accepted":true,
        "admissible_A1_artifact":false,"observed_layer":"native-unknown-SPK-version-skip",
        "scope":"upstream-diagnostic-only-A1-inspection-must-reject-version1"}));
    Ok(
        json!({"schema":"kpi-a1-native-verifier-diagnostics/v1","original_native_full_positive":true,
        "matching_P2SH_positive":true,"cases":results,"original_reserve_artifacts_modified":false,
        "scope":"fabricated-unfunded-UTXO-native-semantics-not-A1-acceptance-not-chain-state"}),
    )
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 1 {
        return Err("usage: a1_verifier_diagnostics BUNDLE".into());
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&run(Path::new(&args[0]))?)?
    );
    Ok(())
}
