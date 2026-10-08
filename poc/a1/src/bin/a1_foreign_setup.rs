//! Diagnostic foreign setups: never replace a reserve key, never persist keys.
//! Same-context rejection isolates immutable key pinning; changed-context/key
//! rejection is separately labeled and cannot demonstrate context-field binding.
use ark_bn254::Bn254;
use ark_groth16::{Groth16, VerifyingKey};
use ark_snark::SNARK;
use kaspa_consensus_core::tx::{
    ScriptPublicKey, Transaction, TransactionInput, TransactionOutpoint, TransactionOutput,
    UtxoEntry,
};
use kpi_poc_a1::{
    circuit::{self, ClaimCircuit, ClaimConstants},
    script, validator,
};
use rand::rngs::OsRng;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs,
    path::{Component, Path},
    time::Instant,
};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn decode(value: &Value) -> Result<Vec<u8>> {
    let s = value.as_str().ok_or("hex text")?;
    if s.len() % 2 != 0
        || !s
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("canonical hex required".into());
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

fn load(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}
fn sha(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn artifact(bundle: &Path, descriptor: &Value) -> Result<Vec<u8>> {
    let path = Path::new(descriptor["path"].as_str().ok_or("artifact path")?);
    if path.as_os_str().is_empty()
        || path
            .components()
            .any(|c| !matches!(c, Component::Normal(_)))
    {
        return Err("safe artifact path required".into());
    }
    let resolved = bundle.join(path).canonicalize()?;
    if !resolved.starts_with(bundle.canonicalize()?) {
        return Err("artifact escaped bundle".into());
    }
    let bytes = fs::read(resolved)?;
    if descriptor["bytes"].as_str() != Some(&bytes.len().to_string())
        || descriptor["sha256"] != sha(&bytes)
    {
        return Err("artifact descriptor mismatch".into());
    }
    Ok(bytes)
}

/// Independent conversion from retained public file transport into native types.
/// No defaults for missing fields, and no float/BigInt narrowing.
fn transaction(value: &Value) -> Result<Transaction> {
    if integer(&value["version"])? != 1 {
        return Err("original v1 required".into());
    }
    let mut inputs = vec![];
    for input in value["inputs"].as_array().ok_or("inputs")? {
        if integer(&input["sigOpCount"])? != 0 {
            return Err("mixed compute metadata".into());
        }
        let previous = &input["previousOutpoint"];
        inputs.push(TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(
                previous["transactionId"].as_str().ok_or("txid")?.parse()?,
                integer(&previous["index"])?.try_into()?,
            ),
            decode(&input["signatureScript"])?,
            integer(&input["sequence"])?,
            integer(&input["computeBudget"])?.try_into()?,
        ));
    }
    let mut outputs = vec![];
    for output in value["outputs"].as_array().ok_or("outputs")? {
        let full = decode(&output["scriptPublicKey"])?;
        if full.len() < 3 {
            return Err("full SPK shape".into());
        }
        let version = u16::from_be_bytes(full[..2].try_into()?);
        if version != 0 || output.get("covenant") != Some(&Value::Null) {
            return Err("original version0/None outputs required".into());
        }
        outputs.push(TransactionOutput::new(
            integer(&output["value"])?,
            ScriptPublicKey::from_vec(version, full[2..].to_vec()),
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

fn run(bundle: &Path, secret_path: &Path, oracle_path: &Path) -> Result<Value> {
    let manifest = load(&bundle.join("manifest.json"))?;
    let oracle = load(oracle_path)?;
    if oracle["schema"] != "kpi-a1-context-oracle/v1" {
        return Err("oracle schema".into());
    }
    let secret: [u8; 32] = fs::read(secret_path)?
        .try_into()
        .map_err(|_| "private secret32")?;
    let record = &manifest["branches"]["s0_terminal"];
    let prefix = decode(&record["context_hex"])?;
    let claim: [u8; 32] = decode(&manifest["claim_commitment_hex"])?
        .try_into()
        .map_err(|_| "claim32")?;
    if circuit::claim_commitment(&secret) != claim {
        return Err("private backup mismatch".into());
    }
    let original_vk_bytes = artifact(bundle, &record["vk"])?;
    let original_vk: VerifyingKey<Bn254> = circuit::parse_compressed(&original_vk_bytes)?;
    let redeem = artifact(bundle, &manifest["states"]["s0"]["redeem"])?;
    let request = load(&bundle.join("s0_terminal.validate.json"))?;
    let original = transaction(&request["transaction"])?;
    let entry: UtxoEntry = serde_json::from_value(request["entry"].clone())?;
    if original.inputs.len() != 1 {
        return Err("original one-input shape".into());
    }
    let op = original.inputs[0].previous_outpoint;
    let txid = op.transaction_id.as_bytes();
    let original_tag: [u8; 32] = decode(&oracle["branches"]["s0_terminal"]["original_tag_hex"])?
        .try_into()
        .map_err(|_| "oracle tag32")?;
    if original_tag != circuit::compute_tag(&prefix, &secret, &txid, op.index) {
        return Err("original independent tag mismatch".into());
    }
    let tv = validator::validator();
    validator::validate(&tv, &original, &entry)?;
    let original_constants = ClaimConstants {
        context_prefix: prefix.clone(),
        claim,
    };
    let original_r1cs_hash = circuit::normalized_r1cs(&original_constants)?.sha256;
    let mut foreign_prefix = prefix.clone();
    if foreign_prefix.len() < 86 {
        return Err("instance offset".into());
    }
    foreign_prefix[54] ^= 1;
    let instance_oracle = oracle["branches"]["s0_terminal"]["mutations"]
        .as_array()
        .ok_or("oracle mutations")?
        .iter()
        .find(|m| m["name"] == "instance")
        .ok_or("instance oracle missing")?;
    if decode(&instance_oracle["context_hex"])? != foreign_prefix {
        return Err("instance oracle context differs".into());
    }
    let foreign_context_tag: [u8; 32] = decode(&instance_oracle["tag_hex"])?
        .try_into()
        .map_err(|_| "tag32")?;
    if foreign_context_tag != circuit::compute_tag(&foreign_prefix, &secret, &txid, op.index) {
        return Err("instance oracle tag differs".into());
    }
    let mut results = vec![];
    for (name, context, tag, same_relation) in [
        (
            "same_relation_fresh_foreign_setup",
            prefix,
            original_tag,
            true,
        ),
        (
            "changed_instance_foreign_context_and_setup",
            foreign_prefix,
            foreign_context_tag,
            false,
        ),
    ] {
        let constants = ClaimConstants {
            context_prefix: context,
            claim,
        };
        let normalized = circuit::normalized_r1cs(&constants)?;
        if (normalized.sha256 == original_r1cs_hash) != same_relation {
            return Err("diagnostic relation hash oracle mismatch".into());
        }
        let start = Instant::now();
        let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(
            ClaimCircuit {
                constants: constants.clone(),
                secret: None,
                inputs: None,
            },
            &mut OsRng,
        )?;
        let setup_ms = start.elapsed().as_millis().to_string();
        let vk_bytes = circuit::compressed(&vk)?;
        if vk_bytes == original_vk_bytes || vk_bytes.len() != 424 {
            return Err("foreign key identity/shape".into());
        }
        let inputs = circuit::public_inputs(&txid, op.index, &tag);
        let proof = Groth16::<Bn254>::prove(
            &pk,
            ClaimCircuit {
                constants,
                secret: Some(secret),
                inputs: Some(inputs),
            },
            &mut OsRng,
        )?;
        if !Groth16::<Bn254>::verify(&vk, &inputs, &proof)? {
            return Err("foreign-key positive control failed".into());
        }
        if Groth16::<Bn254>::verify(&original_vk, &inputs, &proof)? {
            return Err("original VK accepted foreign proof".into());
        }
        let proof_bytes = circuit::compressed(&proof)?;
        if proof_bytes.len() != 128 {
            return Err("proof128".into());
        }
        let mut mutated = original.clone();
        mutated.inputs[0].signature_script =
            script::signature(&proof_bytes, &inputs, &[1], &redeem)?;
        mutated.finalize();
        validator::set_mass(&mutated, &entry)?;
        if mutated.id() != original.id() {
            return Err("proof-only/tag mutation changed transaction ID".into());
        }
        if same_relation
            && mutated.inputs[0].signature_script[..66] != original.inputs[0].signature_script[..66]
        {
            return Err("same-context diagnostic altered tag witness".into());
        }
        let error = validator::validate(&tv, &mutated, &entry)
            .err()
            .ok_or("native Full accepted foreign proof")?;
        if !error.contains("Groth16 verification failed") {
            return Err(format!("foreign proof rejected for unrelated cause: {error}").into());
        }
        results.push(json!({"case":name,"foreign_relation_equals_original":same_relation,
            "foreign_vk_sha256":sha(&vk_bytes),"foreign_proof_sha256":sha(&proof_bytes),"normalized_r1cs_sha256":hex::encode(normalized.sha256),
            "foreign_vk_positive":true,"original_vk_accepts":false,"native_full_accepts":false,
            "native_error":error,"setup_ms":setup_ms,"private_material_persisted":false,
            "scope":if same_relation {"immutable-key-pinning-only"} else {"foreign-key-and-context-rejection-not-original-field-binding"}}));
        // Keys and setup randomness remain ephemeral. This is still trusted
        // single-party diagnostic setup, not a ceremony or source attestation.
    }
    Ok(
        json!({"schema":"kpi-a1-foreign-setup-results/v1","branch":"s0_terminal","original_native_full_positive":true,
        "cases":results,"reserve_artifacts_modified":false,"setup_trust":"ephemeral-single-party-diagnostic",
        "scope":"two-executed-foreign-proof-tests-no-funding-no-chain-acceptance"}),
    )
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 3 {
        return Err("usage: a1_foreign_setup BUNDLE SECRET_FILE CONTEXT_ORACLE_JSON".into());
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&run(
            Path::new(&args[0]),
            Path::new(&args[1]),
            Path::new(&args[2])
        )?)?
    );
    Ok(())
}
