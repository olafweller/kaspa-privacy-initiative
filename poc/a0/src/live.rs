//! File-only adapter around the original A0 circuit/covenant. No RPC or bypass.
//! Private setup/claim material stays in a mode-0700 directory outside Git.
use super::*;
use ark_groth16::ProvingKey;
use ark_serialize::CanonicalDeserialize;
use kaspa_addresses::{Address, Prefix};
use kaspa_txscript::{extract_script_pub_key_address, pay_to_address_script};
use std::{
    fs,
    io::{Cursor, Write},
    os::unix::fs::{OpenOptionsExt, PermissionsExt},
    path::Path,
};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

pub(super) fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn unhex(value: &str) -> Result<Vec<u8>> {
    if !value.is_ascii() || value.len() % 2 != 0 {
        return Err("invalid hex encoding".into());
    }
    (0..value.len())
        .step_by(2)
        .map(|i| Ok(u8::from_str_radix(&value[i..i + 2], 16)?))
        .collect()
}
fn num(value: &Value) -> Result<u64> {
    if let Some(n) = value.as_u64() {
        Ok(n)
    } else {
        Ok(value.as_str().ok_or("unsigned integer required")?.parse()?)
    }
}
fn text(value: &Value) -> Result<&str> {
    Ok(value.as_str().ok_or("string required")?)
}
fn load(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(path)?)?)
}
fn write_new(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}
fn private_read(path: &Path) -> Result<Vec<u8>> {
    let meta = fs::symlink_metadata(path)?;
    if !meta.is_file() || meta.permissions().mode() & 0o077 != 0 {
        return Err("private material must be a restricted regular file".into());
    }
    Ok(fs::read(path)?)
}
fn outside_repo(dir: &Path) -> Result<()> {
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .canonicalize()?;
    if dir.canonicalize()?.starts_with(repo)
        || fs::symlink_metadata(dir)?.permissions().mode() & 0o077 != 0
    {
        return Err("proving material requires an external mode-0700 directory".into());
    }
    Ok(())
}
fn policy_from_manifest(manifest: &Value) -> Result<Policy> {
    let address = Address::try_from(text(&manifest["recipient_address"])?)?;
    if address.prefix != Prefix::Testnet {
        return Err("testnet recipient required".into());
    }
    let recipient = pay_to_address_script(&address);
    if hex(&encode_spk(&recipient)) != text(&manifest["recipient_spk_hex"])? {
        return Err("recipient script metadata mismatch".into());
    }
    let prefix = unhex(text(&manifest["context_prefix_hex"])?)?;
    let offset = b"KPI-A0/TN10/terminal/v1\0".len() + 32;
    let state: [u8; 32] = prefix
        .get(offset..offset + 32)
        .ok_or("missing state")?
        .try_into()?;
    if text(&manifest["network"])? != "testnet-10"
        || text(&manifest["genesis"])? != TESTNET_PARAMS.genesis.hash.to_string()
        || num(&manifest["compute_budget"])? != u64::from(BUDGET)
        || prefix != context_prefix(&recipient, &state)
        || num(&manifest["reserve_sompi"])? != RESERVE
        || num(&manifest["payout_sompi"])? != AMOUNT
        || num(&manifest["fee_sompi"])? != FEE
    {
        return Err("changed immutable A0 terms".into());
    }
    Ok(Policy {
        prefix,
        recipient,
        claim: unhex(text(&manifest["claim_commitment_hex"])?)?
            .try_into()
            .map_err(|_| "claim length")?,
    })
}
fn reload(dir: &Path) -> Result<(Value, Policy, [u8; 32], ProvingKey<Bn254>)> {
    outside_repo(dir)?;
    let manifest = load(&dir.join("manifest.json"))?;
    let policy = policy_from_manifest(&manifest)?;
    let secret: [u8; 32] = private_read(&dir.join("claim-secret.bin"))?
        .try_into()
        .map_err(|_| "secret length")?;
    if circuit::claim_commitment(&secret) != policy.claim {
        return Err("claim mismatch".into());
    }
    let bytes = private_read(&dir.join("proving-key.bin"))?;
    let mut reader = Cursor::new(&bytes);
    let pk = ProvingKey::<Bn254>::deserialize_compressed(&mut reader)?;
    if reader.position() != bytes.len() as u64 {
        return Err("trailing proving key".into());
    }
    let vk = compressed(&pk.vk);
    let redeem_bytes = redeem(&vk, &policy);
    if extract_script_pub_key_address(&pay_to_script_hash_script(&redeem_bytes), Prefix::Testnet)?
        .to_string()
        != text(&manifest["reserve_address"])?
    {
        return Err("reserve address mismatch".into());
    }
    if hex(&vk) != text(&manifest["verifying_key_hex"])?
        || hex(&redeem_bytes) != text(&manifest["redeem_script_hex"])?
        || hex(&encode_spk(&pay_to_script_hash_script(&redeem_bytes)))
            != text(&manifest["reserve_spk_hex"])?
    {
        return Err("key/script reload mismatch".into());
    }
    Ok((manifest, policy, secret, pk))
}
fn init(dir: &Path, recipient: &str) -> Result<Value> {
    fs::create_dir(dir)?;
    fs::set_permissions(dir, fs::Permissions::from_mode(0o700))?;
    outside_repo(dir)?;
    let address = Address::try_from(recipient)?;
    if address.prefix != Prefix::Testnet {
        return Err("testnet recipient required".into());
    }
    let mut secret = [0u8; 32];
    OsRng.fill_bytes(&mut secret);
    let policy = policy_for_recipient(&secret, pay_to_address_script(&address));
    // This pre-funding sample validates spendability; never presented as a live outpoint.
    let circuit = new_circuit(policy.prefix.clone(), policy.claim, secret, [0x42; 32], 7);
    let started = Instant::now();
    let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(circuit, &mut OsRng)?;
    let redeem_bytes = redeem(&compressed(&vk), &policy);
    let spk = pay_to_script_hash_script(&redeem_bytes);
    let manifest = json!({
        "network":"testnet-10", "genesis":TESTNET_PARAMS.genesis.hash.to_string(),
        "recipient_address":recipient, "recipient_spk_hex":hex(&encode_spk(&policy.recipient)),
        "reserve_address":extract_script_pub_key_address(&spk, Prefix::Testnet)?.to_string(),
        "reserve_spk_hex":hex(&encode_spk(&spk)), "redeem_script_hex":hex(&redeem_bytes),
        "context_prefix_hex":hex(&policy.prefix), "claim_commitment_hex":hex(&policy.claim),
        "verifying_key_hex":hex(&compressed(&vk)), "reserve_sompi":RESERVE,
        "payout_sompi":AMOUNT,"fee_sompi":FEE,"compute_budget":BUDGET,
        "setup_ms":started.elapsed().as_secs_f64()*1000.,
        "upstream_revision":"01b532e8b553523216471682649693af92f0fd16"
    });
    write_new(&dir.join("claim-secret.bin"), &secret)?;
    write_new(&dir.join("proving-key.bin"), &compressed(&pk))?;
    write_new(
        &dir.join("manifest.json"),
        &serde_json::to_vec_pretty(&manifest)?,
    )?;
    let (_, _, _, reloaded) = reload(dir)?;
    if compressed(&reloaded.vk) != compressed(&vk) {
        return Err("reload changed key".into());
    }
    let backup = dir.join("backup");
    fs::create_dir(&backup)?;
    fs::set_permissions(&backup, fs::Permissions::from_mode(0o700))?;
    for name in ["claim-secret.bin", "proving-key.bin", "manifest.json"] {
        write_new(&backup.join(name), &private_read(&dir.join(name))?)?;
    }
    let (_, backup_policy, backup_secret, backup_pk) = reload(&backup)?;
    if backup_policy.prefix != policy.prefix
        || backup_secret != secret
        || compressed(&backup_pk.vk) != compressed(&vk)
    {
        return Err("backup reload mismatch".into());
    }
    Ok(manifest)
}
fn spk(value: &Value) -> Result<ScriptPublicKey> {
    let bytes = unhex(text(value)?)?;
    if bytes.len() < 2 {
        return Err("SPK missing version".into());
    }
    Ok(ScriptPublicKey::new(
        u16::from_be_bytes([bytes[0], bytes[1]]),
        bytes[2..].to_vec().into(),
    ))
}
fn reserve(input: &Value, manifest: &Value) -> Result<(TransactionOutpoint, UtxoEntry, u64, u64)> {
    let outpoint = TransactionOutpoint::new(
        text(&input["outpoint"]["transactionId"])?.parse()?,
        u32::try_from(num(&input["outpoint"]["index"])?)?,
    );
    let entry = &input["utxoEntry"];
    if entry.get("covenantId") != Some(&Value::Null)
        || num(&entry["amount"])? != RESERVE
        || text(&entry["scriptPublicKeyHex"])? != text(&manifest["reserve_spk_hex"])?
    {
        return Err("reserve amount/script/covenant mismatch".into());
    }
    let entry = UtxoEntry::new(
        RESERVE,
        spk(&entry["scriptPublicKeyHex"])?,
        num(&entry["blockDaaScore"])?,
        entry["isCoinbase"]
            .as_bool()
            .ok_or("coinbase flag required")?,
        None,
    );
    if entry.is_coinbase {
        return Err("A0 funding must be non-coinbase".into());
    }
    Ok((
        outpoint,
        entry,
        num(&input["virtualDaaScore"])?,
        num(&input["pastMedianTime"])?,
    ))
}
fn transaction_json(tx: &Transaction) -> Value {
    json!({"version":tx.version,"id":tx.id().to_string(),
        "inputs":tx.inputs.iter().map(|i| json!({"previousOutpoint":{"transactionId":i.previous_outpoint.transaction_id.to_string(),"index":i.previous_outpoint.index},
            "signatureScript":hex(&i.signature_script),"sequence":i.sequence.to_string(),"sigOpCount":0,"computeBudget":i.compute_commit.compute_budget().unwrap()})).collect::<Vec<_>>(),
        "outputs":tx.outputs.iter().map(|o| json!({"value":o.value.to_string(),"scriptPublicKey":hex(&encode_spk(&o.script_public_key)),"covenant":o.covenant})).collect::<Vec<_>>(),
        "lockTime":tx.lock_time.to_string(),"subnetworkId":tx.subnetwork_id.to_string(),"gas":tx.gas.to_string(),"payload":hex(&tx.payload),"storageMass":tx.storage_mass().to_string()})
}
fn parse_transaction(value: &Value) -> Result<Transaction> {
    let version = u16::try_from(num(&value["version"])?)?;
    if version > 1 {
        return Err("unsupported transaction version".into());
    }
    let inputs = value["inputs"]
        .as_array()
        .ok_or("inputs required")?
        .iter()
        .map(|i| {
            let outpoint = TransactionOutpoint::new(
                text(&i["previousOutpoint"]["transactionId"])?.parse()?,
                u32::try_from(num(&i["previousOutpoint"]["index"])?)?,
            );
            let signature = unhex(text(&i["signatureScript"])?)?;
            let sequence = num(&i["sequence"])?;
            if (version == 0 && num(&i["computeBudget"])? != 0)
                || (version == 1 && num(&i["sigOpCount"])? != 0)
            {
                return Err("incompatible compute commitment metadata".into());
            }
            Ok(if version == 0 {
                TransactionInput::new(
                    outpoint,
                    signature,
                    sequence,
                    u8::try_from(num(&i["sigOpCount"])?)?,
                )
            } else {
                TransactionInput::new_with_compute_budget(
                    outpoint,
                    signature,
                    sequence,
                    u16::try_from(num(&i["computeBudget"])?)?,
                )
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let outputs = value["outputs"]
        .as_array()
        .ok_or("outputs required")?
        .iter()
        .map(|o| {
            if o.get("covenant").is_none() {
                return Err("explicit covenant metadata required".into());
            }
            let mut output = TransactionOutput::new(num(&o["value"])?, spk(&o["scriptPublicKey"])?);
            output.covenant = serde_json::from_value(o["covenant"].clone())?;
            Ok(output)
        })
        .collect::<Result<Vec<_>>>()?;
    let tx = Transaction::new(
        version,
        inputs,
        outputs,
        num(&value["lockTime"])?,
        text(&value["subnetworkId"])?.parse()?,
        num(&value["gas"])?,
        unhex(text(&value["payload"])?)?,
    );
    tx.set_storage_mass(num(&value["storageMass"])?);
    if tx.id().to_string() != text(&value["id"])? {
        return Err("transaction ID round-trip changed".into());
    }
    Ok(tx)
}
fn prepare(dir: &Path, input: &Value) -> Result<Value> {
    let (manifest, policy, secret, pk) = reload(dir)?;
    let (outpoint, entry, daa, median) = reserve(input, &manifest)?;
    let circuit = new_circuit(
        policy.prefix.clone(),
        policy.claim,
        secret,
        outpoint.transaction_id.as_bytes(),
        outpoint.index,
    );
    let inputs = circuit.inputs.ok_or("public inputs absent")?;
    let started = Instant::now();
    let proof = Groth16::<Bn254>::prove(&pk, circuit, &mut OsRng)?;
    let proving_ms = started.elapsed().as_secs_f64() * 1000.;
    if !Groth16::<Bn254>::verify(&pk.vk, &inputs, &proof)? {
        return Err("proof verification failed".into());
    }
    let redeem_bytes = redeem(&compressed(&pk.vk), &policy);
    let tx = Transaction::new(
        1,
        vec![TransactionInput::new_with_compute_budget(
            outpoint,
            signature(&compressed(&proof), &inputs, &redeem_bytes),
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
    let started = Instant::now();
    let fee = validate_at(&validator(), &tx, &entry, daa, median)?;
    let validation_ms = started.elapsed().as_secs_f64() * 1000.;
    if fee != FEE {
        return Err("wrong fee".into());
    }
    let encoded = transaction_json(&tx);
    let roundtrip = parse_transaction(&encoded)?;
    if tx != roundtrip || validate_at(&validator(), &roundtrip, &entry, daa, median)? != FEE {
        return Err("transaction roundtrip failed".into());
    }
    let mut replay = tx.clone();
    replay.inputs[0].sequence = u64::MAX - 1;
    replay.finalize();
    if replay.id() == tx.id() || validate_at(&validator(), &replay, &entry, daa, median)? != FEE {
        return Err("distinct replay fixture failed".into());
    }
    let masses =
        MassCalculator::new_with_consensus_params(&TESTNET_PARAMS).calc_non_contextual_masses(&tx);
    if FEE
        < masses
            .normalized_max(&TESTNET_PARAMS.block_mass_limits.cofactors())
            .checked_mul(100)
            .ok_or("fee overflow")?
    {
        return Err("fee below relay floor".into());
    }
    Ok(
        json!({"transaction":encoded,"distinct_replay_transaction":transaction_json(&replay),
        "proof_hex":hex(&compressed(&proof)),"public_inputs_hex":inputs.iter().map(|i|hex(&field(*i))).collect::<Vec<_>>(),
        "proving_ms":proving_ms,"full_validation_ms":validation_ms,"fee_sompi":fee,
        "proof_bytes":compressed(&proof).len(),"consensus_borsh_bytes":borsh::to_vec(&tx)?.len(),
        "estimated_transaction_bytes":transaction_estimated_serialized_size(&tx),
        "compute_mass_grams":masses.compute_mass,"transient_mass_grams":masses.transient_mass,"storage_mass_grams":tx.storage_mass(),
        "scope":"original A0 proof/covenant; exact file roundtrip fully validated; spentness not established"}),
    )
}
pub(super) fn run() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(2).collect();
    let result = match args.first().map(String::as_str) {
        Some("init") if args.len() == 3 => init(Path::new(&args[1]), &args[2])?,
        Some("prepare") if args.len() == 3 => {
            prepare(Path::new(&args[1]), &load(Path::new(&args[2]))?)?
        }
        Some("check") if args.len() == 4 => {
            let manifest = load(&Path::new(&args[1]).join("manifest.json"))?;
            policy_from_manifest(&manifest)?;
            let input = load(Path::new(&args[2]))?;
            let (outpoint, entry, daa, median) = reserve(&input, &manifest)?;
            let tx = parse_transaction(&load(Path::new(&args[3]))?)?;
            if tx.version != 1 || tx.inputs.len() != 1 || tx.inputs[0].previous_outpoint != outpoint
            {
                return Err("transaction must consume the observed reserve outpoint".into());
            }
            let fee = validate_at(&validator(), &tx, &entry, daa, median)?;
            json!({"transaction_id":tx.id().to_string(),"accepted_locally":true,"fee_sompi":fee})
        }
        Some("check-generic") if args.len() == 3 => {
            let context = load(Path::new(&args[1]))?;
            let tx = parse_transaction(&load(Path::new(&args[2]))?)?;
            let raw_entries = context["entries"].as_array().ok_or("entries required")?;
            if raw_entries.len() != tx.inputs.len() {
                return Err("entry count mismatch".into());
            }
            let entries = raw_entries
                .iter()
                .zip(&tx.inputs)
                .map(|(u, i)| {
                    if text(&u["outpoint"]["transactionId"])?
                        != i.previous_outpoint.transaction_id.to_string()
                        || num(&u["outpoint"]["index"])? != u64::from(i.previous_outpoint.index)
                        || u.get("covenantId") != Some(&Value::Null)
                    {
                        return Err("generic input metadata mismatch".into());
                    }
                    Ok(UtxoEntry::new(
                        num(&u["amount"])?,
                        spk(&u["scriptPublicKeyHex"])?,
                        num(&u["blockDaaScore"])?,
                        u["isCoinbase"].as_bool().ok_or("coinbase flag required")?,
                        None,
                    ))
                })
                .collect::<Result<Vec<_>>>()?;
            let tv = validator();
            tv.validate_tx_in_isolation(&tx)?;
            let pop = PopulatedTransaction::new(&tx, entries);
            let fee = tv.validate_populated_transaction_and_get_fee(
                &pop,
                num(&context["virtualDaaScore"])?,
                num(&context["pastMedianTime"])?,
                TxValidationFlags::Full,
                None,
                None,
            )?;
            json!({"transaction_id":tx.id().to_string(),"accepted_locally":true,"fee_sompi":fee})
        }
        _ => return Err(
            "usage: live init DIR RECIPIENT | prepare DIR UTXO_JSON | check DIR UTXO_JSON TX_JSON"
                .into(),
        ),
    };
    println!("{}", serde_json::to_string_pretty(&result)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn encoded() -> Value {
        let mut output =
            TransactionOutput::new(AMOUNT, ScriptPublicKey::new(0, vec![OpTrue].into()));
        output.covenant = Some(kaspa_consensus_core::tx::CovenantBinding::new(
            0,
            Hash::from_bytes([7; 32]),
        ));
        let tx = Transaction::new(
            1,
            vec![TransactionInput::new_with_compute_budget(
                TransactionOutpoint::new(Hash::from_bytes([8; 32]), u32::MAX),
                vec![1, 2, 3],
                u64::MAX,
                BUDGET,
            )],
            vec![output],
            u64::MAX,
            Default::default(),
            0,
            vec![],
        );
        tx.set_storage_mass(20);
        transaction_json(&tx)
    }

    #[test]
    fn transport_roundtrip_preserves_u64_and_covenant_metadata() {
        let raw = encoded();
        let tx = parse_transaction(&raw).unwrap();
        assert_eq!(tx.inputs[0].sequence, u64::MAX);
        assert_eq!(tx.inputs[0].previous_outpoint.index, u32::MAX);
        assert_eq!(tx.storage_mass(), 20);
        assert!(tx.outputs[0].covenant.is_some());
        assert_eq!(transaction_json(&tx), raw);
    }

    #[test]
    fn malformed_transport_values_and_missing_metadata_fail() {
        for (location, invalid) in [
            ("/inputs/0/sequence", json!("18446744073709551616")),
            ("/inputs/0/previousOutpoint/index", json!(4294967296u64)),
            ("/inputs/0/computeBudget", json!(65536)),
            ("/inputs/0/sigOpCount", json!(1)),
            ("/outputs/0/value", json!(-1)),
            ("/outputs/0/scriptPublicKey", json!("éé")),
            ("/outputs/0/scriptPublicKey", json!("000")),
        ] {
            let mut raw = encoded();
            *raw.pointer_mut(location).unwrap() = invalid;
            assert!(parse_transaction(&raw).is_err());
        }
        let mut raw = encoded();
        raw["outputs"][0]
            .as_object_mut()
            .unwrap()
            .remove("covenant");
        assert!(parse_transaction(&raw).is_err());
    }

    #[test]
    fn changed_outpoint_or_amount_cannot_keep_the_original_transaction_id() {
        for location in ["/inputs/0/previousOutpoint/index", "/outputs/0/value"] {
            let mut raw = encoded();
            *raw.pointer_mut(location).unwrap() = json!(1);
            assert!(parse_transaction(&raw).is_err());
        }
    }
}
