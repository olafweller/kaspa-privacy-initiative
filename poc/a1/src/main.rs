//! File-only A1 falsification runner. No RPC, funding or broadcasting API.
use ark_bn254::Bn254;
use ark_groth16::{Groth16, ProvingKey};
use ark_snark::SNARK;
use kaspa_consensus_core::{
    hashing,
    tx::{
        ScriptPublicKey, Transaction, TransactionInput, TransactionOutpoint, TransactionOutput,
        UtxoEntry,
    },
};
use kaspa_hashes::Hash;
use kaspa_txscript::{pay_to_script_hash_script, script_builder::ScriptBuilder};
use kpi_poc_a1::{
    circuit::{self, ClaimCircuit, ClaimConstants},
    model::{self, Branch, BranchContext, Terms},
    script::{self, ScriptPolicy},
    validator,
};
use rand::{RngCore, rngs::OsRng};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    time::Instant,
};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
fn sha(b: &[u8]) -> String {
    hex::encode(Sha256::digest(b))
}
fn write_new(p: &Path, b: &[u8], private: bool) -> Result<()> {
    let mut o = OpenOptions::new();
    o.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        o.mode(if private { 0o600 } else { 0o644 });
    }
    let mut f = o.open(p)?;
    f.write_all(b)?;
    f.sync_all()?;
    Ok(())
}
fn json_new(p: &Path, v: &Value) -> Result<()> {
    write_new(p, &serde_json::to_vec_pretty(v)?, false)
}
fn descriptor(root: &Path, path: &str, b: &[u8]) -> Result<Value> {
    write_new(&root.join(path), b, false)?;
    Ok(json!({"path":path,"bytes":b.len().to_string(),"sha256":sha(b)}))
}
fn run_git(args: &[&str]) -> Result<String> {
    let o = std::process::Command::new("git").args(args).output()?;
    if !o.status.success() {
        return Err("git pin check failed".into());
    }
    Ok(String::from_utf8(o.stdout)?.trim().into())
}
fn spk(b: &[u8]) -> Result<ScriptPublicKey> {
    model::full_spk(b)?;
    Ok(ScriptPublicKey::from_vec(0, b[2..].to_vec()))
}
fn artifact_path(bundle: &Path, name: &str) -> Result<PathBuf> {
    let relative = Path::new(name);
    if relative.is_absolute()
        || relative
            .components()
            .any(|p| !matches!(p, std::path::Component::Normal(_)))
    {
        return Err("unsafe artifact path".into());
    }
    let root = bundle.canonicalize()?;
    let path = root.join(relative).canonicalize()?;
    if !path.starts_with(&root) {
        return Err("escaping artifact symlink".into());
    }
    Ok(path)
}
fn private_secret(path: &Path) -> Result<[u8; 32]> {
    let meta = fs::symlink_metadata(path)?;
    if !meta.is_file() {
        return Err("private backup must be regular file".into());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        if meta.permissions().mode() & 0o077 != 0 {
            return Err("private backup permissions must exclude group/other".into());
        }
    }
    Ok(fs::read(path)?.try_into().map_err(|_| "secret32")?)
}
fn check_backup(bundle: &Path, secret: &Path, key: &Path) -> Result<Value> {
    let manifest = kpi_poc_a1::artifact::manifest(&fs::read(bundle.join("manifest.json"))?)?;
    let s = private_secret(secret)?;
    if hex::encode(circuit::claim_commitment(&s)) != text(&manifest["claim_commitment_hex"])? {
        return Err("wrong claim backup".into());
    }
    let raw = private_secret(key)?;
    let key = secp256k1::SecretKey::from_slice(&raw)?;
    let pair = secp256k1::Keypair::from_secret_key(&secp256k1::Secp256k1::new(), &key);
    let (pubkey, _) = pair.x_only_public_key();
    let expected = format!("000020{}ac", hex::encode(pubkey.serialize()));
    if expected != text(&manifest["recipient"]["spk_hex"])? {
        return Err("wrong recipient private recovery key".into());
    }
    Ok(
        json!({"claim_secret_matches":true,"recipient_private_key_matches":true,"private_material_printed":false,"scope":"private backup correspondence only, not history availability"}),
    )
}
fn policy(c: &BranchContext) -> Result<ScriptPolicy> {
    Ok(ScriptPolicy {
        reserve: c.reserve,
        outputs: c
            .outputs
            .iter()
            .map(|o| Ok((o.value, spk(&o.spk)?)))
            .collect::<Result<_>>()?,
    })
}
fn tx_for(
    c: &BranchContext,
    op: TransactionOutpoint,
    sig: Vec<u8>,
    budget: u16,
) -> Result<Transaction> {
    Ok(Transaction::new(
        1,
        vec![TransactionInput::new_with_compute_budget(
            op,
            sig,
            u64::MAX,
            budget,
        )],
        c.outputs
            .iter()
            .map(|o| Ok(TransactionOutput::new(o.value, spk(&o.spk)?)))
            .collect::<Result<_>>()?,
        0,
        Default::default(),
        0,
        vec![],
    ))
}
fn num(v: &Value) -> Result<u64> {
    if let Some(n) = v.as_u64() {
        Ok(n)
    } else {
        let s = v.as_str().ok_or("unsigned integer")?;
        if s.is_empty()
            || !s.bytes().all(|b| b.is_ascii_digit())
            || (s.len() > 1 && s.starts_with('0'))
        {
            return Err("canonical decimal".into());
        }
        Ok(s.parse()?)
    }
}
fn text(v: &Value) -> Result<&str> {
    Ok(v.as_str().ok_or("text required")?)
}
fn hexbytes(v: &Value) -> Result<Vec<u8>> {
    let s = text(v)?;
    if s.len() % 2 != 0
        || !s
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("canonical hex".into());
    }
    Ok(hex::decode(s)?)
}
/// File/archive transport is exact u64 decimal text, never floating-point JSON.
fn tx_json(tx: &Transaction) -> Value {
    json!({"version":tx.version,"id":tx.id().to_string(),"inputs":tx.inputs.iter().map(|i|json!({"previousOutpoint":{"transactionId":i.previous_outpoint.transaction_id.to_string(),"index":i.previous_outpoint.index},"signatureScript":hex::encode(&i.signature_script),"sequence":i.sequence.to_string(),"sigOpCount":0,"computeBudget":i.compute_commit.compute_budget().unwrap()})).collect::<Vec<_>>(),"outputs":tx.outputs.iter().map(|o|json!({"value":o.value.to_string(),"scriptPublicKey":hex::encode(script::encode_spk(&o.script_public_key)),"covenant":o.covenant})).collect::<Vec<_>>(),"lockTime":tx.lock_time.to_string(),"subnetworkId":tx.subnetwork_id.to_string(),"gas":tx.gas.to_string(),"payload":hex::encode(&tx.payload),"storageMass":tx.storage_mass().to_string()})
}
fn parse_tx(v: &Value) -> Result<Transaction> {
    if num(&v["version"])? != 1 {
        return Err("A1 version1 only".into());
    }
    let mut inputs = vec![];
    for i in v["inputs"].as_array().ok_or("inputs")? {
        if num(&i["sigOpCount"])? != 0 {
            return Err("mixed compute metadata".into());
        }
        inputs.push(TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(
                text(&i["previousOutpoint"]["transactionId"])?.parse()?,
                num(&i["previousOutpoint"]["index"])?.try_into()?,
            ),
            hexbytes(&i["signatureScript"])?,
            num(&i["sequence"])?,
            num(&i["computeBudget"])?.try_into()?,
        ));
    }
    let mut outputs = vec![];
    for o in v["outputs"].as_array().ok_or("outputs")? {
        if o.get("covenant").is_none() {
            return Err("explicit covenant required".into());
        }
        let mut out =
            TransactionOutput::new(num(&o["value"])?, spk(&hexbytes(&o["scriptPublicKey"])?)?);
        out.covenant = serde_json::from_value(o["covenant"].clone())?;
        outputs.push(out);
    }
    let t = Transaction::new(
        1,
        inputs,
        outputs,
        num(&v["lockTime"])?,
        text(&v["subnetworkId"])?.parse()?,
        num(&v["gas"])?,
        hexbytes(&v["payload"])?,
    );
    t.set_storage_mass(num(&v["storageMass"])?);
    if t.id().to_string() != text(&v["id"])? {
        return Err("decoded transaction ID mismatch".into());
    }
    Ok(t)
}
fn validate_body(p: &Path) -> Result<Value> {
    let v: Value = serde_json::from_slice(&fs::read(p)?)?;
    let tx = parse_tx(&v["transaction"])?;
    let entry: UtxoEntry = serde_json::from_value(v["entry"].clone())?;
    let fee = validator::validate(&validator::validator(), &tx, &entry)?;
    let populated = kaspa_consensus_core::tx::PopulatedTransaction::new(
        &tx,
        vec![entry.clone(); tx.inputs.len()],
    );
    let calculator = kaspa_consensus_core::mass::MassCalculator::new_with_consensus_params(
        &kaspa_consensus_core::config::params::TESTNET_PARAMS,
    );
    let non_contextual = calculator.calc_non_contextual_masses(&tx);
    let masses = calculator
        .calc_contextual_masses(&populated)
        .ok_or("decoded native mass undefined")?;
    Ok(
        json!({"txid":tx.id().to_string(),"full_hash":hashing::tx::hash(&tx).to_string(),"full_valid":true,"fee":fee.to_string(),
        "native_masses":{"compute":non_contextual.compute_mass,"storage":masses.storage_mass,"transient":non_contextual.transient_mass},
        "consensus_full_hash_preimage_bytes":kpi_poc_a1::encoding::full_transaction_bytes(&tx)?.len(),
        "mass_scope":"fresh native calculation from exact decoded transaction and supplied UTXO context; not chain acceptance"}),
    )
}
struct Artifact {
    constants: ClaimConstants,
    pk: ProvingKey<Bn254>,
    vk: Vec<u8>,
    record: Value,
    measure: Value,
}
fn setup(root: &Path, branch: Branch, context: &BranchContext) -> Result<Artifact> {
    let prefix = context.encode()?;
    let constants = ClaimConstants {
        context_prefix: prefix.clone(),
        claim: context.claim,
    };
    let start = Instant::now();
    let normalized = circuit::normalized_r1cs(&constants)?;
    let normalize_ms = start.elapsed().as_secs_f64() * 1000.;
    let layout = circuit::inspect_layout(&constants)?;
    let start = Instant::now();
    let (pk, vk) = Groth16::<Bn254>::circuit_specific_setup(
        ClaimCircuit {
            constants: constants.clone(),
            secret: None,
            inputs: None,
        },
        &mut OsRng,
    )?;
    let setup_ms = start.elapsed().as_secs_f64() * 1000.;
    let pkbytes = circuit::compressed(&pk)?;
    let vkbytes = circuit::compressed(&vk)?;
    if vkbytes.len() != 424 {
        return Err("frozen VK size contradicted".into());
    }
    let name = branch.name();
    let mut r1cs = descriptor(root, &format!("{name}.r1cs"), &normalized.bytes)?;
    r1cs["format"] = json!("KPI-A1/R1CS/v1");
    let record = json!({"stage":context.stage.to_string(),"mode":context.mode.to_string(),"selector_hex":format!("{:02x}",branch.selector()),"fee":context.fee.to_string(),"next_R":context.next_reserve.to_string(),"next_L":context.next_principal.to_string(),"next_B":context.next_credit.to_string(),"outputs":context.outputs.iter().enumerate().map(|(i,o)|json!({"index":i.to_string(),"value":o.value.to_string(),"spk_hex":hex::encode(&o.spk),"covenant":null})).collect::<Vec<_>>(),"context_hex":hex::encode(&prefix),"context_sha256":sha(&prefix),"relation_id":circuit::RELATION_ID,"r1cs":r1cs,"pk":descriptor(root,&format!("{name}.pk"),&pkbytes)?,"vk":descriptor(root,&format!("{name}.vk"),&vkbytes)?});
    write_new(
        &root.join(format!("{name}.context.hex")),
        hex::encode(&prefix).as_bytes(),
        false,
    )?;
    json_new(
        &root.join(format!("{name}.layout.json")),
        &json!({"context_bytes":layout.context_bytes,"public_range_constraints":layout.public_range_constraints,"secret_byte_constraints":layout.secret_byte_constraints,"claim_hash_constraints":layout.claim_hash_constraints,"claim_equality_constraints":layout.claim_equality_constraints,"context_tag_hash_constraints":layout.context_tag_hash_constraints,"tag_equality_constraints":layout.tag_equality_constraints}),
    )?;
    Ok(Artifact {
        constants,
        pk,
        vk: vkbytes.clone(),
        record,
        measure: json!({"constraints":normalized.constraint_count,"variables":normalized.variable_count,"public_inputs":normalized.public_count,"normalized_bytes":normalized.bytes.len(),"normalization_ms":normalize_ms,"setup_ms":setup_ms,"pk_bytes":pkbytes.len(),"vk_bytes":vkbytes.len()}),
    })
}
fn raw_sig(items: &[Vec<u8>]) -> Result<Vec<u8>> {
    let mut b = ScriptBuilder::new();
    for item in items {
        b.add_data(item)?;
    }
    Ok(b.drain())
}
fn fixture(
    root: &Path,
    branch: Branch,
    a: &Artifact,
    c: &BranchContext,
    secret: [u8; 32],
    op: TransactionOutpoint,
    redeem: &[u8],
    entry: &UtxoEntry,
) -> Result<(Transaction, Value)> {
    let txid = op.transaction_id.as_bytes();
    let tag = circuit::compute_tag(&a.constants.context_prefix, &secret, &txid, op.index);
    let inputs = circuit::public_inputs(&txid, op.index, &tag);
    let start = Instant::now();
    let proof = Groth16::<Bn254>::prove(
        &a.pk,
        ClaimCircuit {
            constants: a.constants.clone(),
            secret: Some(secret),
            inputs: Some(inputs),
        },
        &mut OsRng,
    )?;
    let prove_ms = start.elapsed().as_secs_f64() * 1000.;
    let start = Instant::now();
    if !Groth16::<Bn254>::verify(&a.pk.vk, &inputs, &proof)? {
        return Err("standalone proof rejected".into());
    }
    let verify_ms = start.elapsed().as_secs_f64() * 1000.;
    let bytes = circuit::compressed(&proof)?;
    if bytes.len() != 128 {
        return Err("frozen proof size contradicted".into());
    }
    let mut tx = tx_for(
        c,
        op,
        script::signature(&bytes, &inputs, &[branch.selector()], redeem)?,
        2000,
    )?;
    validator::set_mass(&tx, entry)?;
    let preliminary = validator::meter(&tx, entry, &a.vk)?;
    let units = preliminary["script_units"].as_u64().ok_or("units")?;
    let budget: u16 =
        ((11u64.checked_mul(units).ok_or("budget overflow")? + 99_999) / 100_000).try_into()?;
    tx.inputs[0].compute_commit = kaspa_consensus_core::mass::ComputeBudget(budget).into();
    tx.finalize();
    validator::set_mass(&tx, entry)?;
    let encoded = tx_json(&tx);
    let decoded = parse_tx(&encoded)?;
    let start = Instant::now();
    let fee = validator::validate(&validator::validator(), &decoded, entry)?;
    let full_ms = start.elapsed().as_secs_f64() * 1000.;
    if fee != c.fee {
        return Err("fee mismatch".into());
    }
    let meter = validator::meter(&decoded, entry, &a.vk)?;
    let relay = validator::relay_policy(&decoded, entry, fee)?;
    if meter["compute_mass"].as_u64().unwrap() > 500_000
        || meter["storage_mass"].as_u64().unwrap() > 500_000
        || meter["transient_mass"].as_u64().unwrap() > 1_000_000
    {
        return Err("hard TN10 block mass exceeded".into());
    }
    let binary = borsh::to_vec(&decoded)?;
    let consensus_preimage = kpi_poc_a1::encoding::full_transaction_bytes(&decoded)?;
    if kpi_poc_a1::encoding::full_transaction_hash(&decoded)? != hashing::tx::hash(&decoded) {
        return Err("independent full encoding/hash mismatch".into());
    }
    json_new(
        &root.join(format!("{}.transaction.json", branch.name())),
        &encoded,
    )?;
    json_new(
        &root.join(format!("{}.validate.json", branch.name())),
        &json!({"transaction":encoded,"entry":entry}),
    )?;
    write_new(
        &root.join(format!("{}.proof", branch.name())),
        &bytes,
        false,
    )?;
    let measure = json!({"setup":a.measure,"prove_ms":prove_ms,"standalone_verify_ms":verify_ms,"native_full_ms":full_ms,"proof_bytes":bytes.len(),"redeem_bytes":redeem.len(),"signature_bytes":decoded.inputs[0].signature_script.len(),"spk_bytes_full":script::encode_spk(&entry.script_public_key).len(),"output_script_bytes":decoded.outputs.iter().map(|o|o.script_public_key.script().len()).collect::<Vec<_>>(),"native_borsh_bytes":binary.len(),"native_borsh_sha256":sha(&binary),"consensus_full_hash_preimage_bytes":consensus_preimage.len(),"consensus_full_hash_preimage_sha256":sha(&consensus_preimage),"estimated_consensus_bytes":kaspa_consensus_core::mass::transaction_estimated_serialized_size(&decoded),"transport_json_bytes":serde_json::to_vec(&encoded)?.len(),"compute_budget":budget,"fee_sompi":fee,"txid":decoded.id().to_string(),"full_hash":hashing::tx::hash(&decoded).to_string(),"meter":meter,"relay_policy":relay});
    json_new(
        &root.join(format!("{}.measurement.json", branch.name())),
        &measure,
    )?;
    Ok((decoded, measure))
}
fn case(
    cases: &mut Vec<Value>,
    name: String,
    mut tx: Transaction,
    entry: &UtxoEntry,
    expected: bool,
    layer: &str,
) -> Result<()> {
    tx.finalize();
    validator::set_mass(&tx, entry)?;
    let start = Instant::now();
    let result = validator::validate(&validator::validator(), &tx, entry);
    let accepted = result.is_ok();
    let error = result.as_ref().err().map(String::as_str).unwrap_or("");
    let observed = if accepted {
        "success"
    } else if error.starts_with("isolation:") {
        "native-isolation"
    } else if error.contains("ZkIntegrity") {
        "native-Groth16-verifier"
    } else if error.contains("Budget") || error.contains("script units") {
        "native-budget"
    } else if error.contains("Signature") {
        "native-script-VM"
    } else {
        "native-UTXO-context"
    };
    cases.push(json!({"case":name,"expected":expected,"accepted":accepted,"expected_check":layer,"observed_layer":observed,"result":format!("{result:?}"),"milliseconds":start.elapsed().as_secs_f64()*1000.}));
    if accepted != expected {
        return Err(format!("falsification mismatch: {}", cases.last().unwrap()).into());
    }
    Ok(())
}
fn negatives(
    branch: Branch,
    tx: &Transaction,
    a: &Artifact,
    secret: [u8; 32],
    redeem: &[u8],
    entry: &UtxoEntry,
    cases: &mut Vec<Value>,
) -> Result<()> {
    let op = tx.inputs[0].previous_outpoint;
    let id = op.transaction_id.as_bytes();
    let tag = circuit::compute_tag(&a.constants.context_prefix, &secret, &id, op.index);
    let inputs = circuit::public_inputs(&id, op.index, &tag);
    let scalars = circuit::public_scalar_bytes(&inputs);
    let proof: Vec<u8> = {
        let p: Value = serde_json::from_slice(&serde_json::to_vec(&tx_json(tx))?)?;
        let sig = hexbytes(&p["inputs"][0]["signatureScript"])?;
        if sig.get(0) != Some(&0x20)
            || sig.get(33) != Some(&0x20)
            || sig.get(66..68) != Some(&[0x4c, 0x80][..])
        {
            return Err("fixture proof framing not canonical".into());
        }
        let first = 33 + 33;
        sig[first + 2..first + 2 + 128].to_vec()
    };
    let base = vec![
        scalars[4].to_vec(),
        scalars[3].to_vec(),
        proof.clone(),
        vec![branch.selector()],
        redeem.to_vec(),
    ];
    for selector in 0..=255u8 {
        let mut items = base.clone();
        items[3] = vec![selector];
        let mut t = tx.clone();
        t.inputs[0].signature_script = raw_sig(&items)?;
        case(
            cases,
            format!("{}/selector_{selector:02x}", branch.name()),
            t,
            entry,
            selector == branch.selector(),
            "redeem-script",
        )?;
    }
    for selector in [
        vec![],
        vec![0, 0],
        vec![1, 0],
        vec![0, 0x80],
        vec![1, 0x80],
        vec![0, 1],
    ] {
        let mut items = base.clone();
        items[3] = selector.clone();
        let mut t = tx.clone();
        t.inputs[0].signature_script = raw_sig(&items)?;
        case(
            cases,
            format!(
                "{}/selector_length_{}",
                branch.name(),
                hex::encode(selector)
            ),
            t,
            entry,
            false,
            "redeem-script",
        )?;
    }
    for index in 0..5 {
        let mut items = base.clone();
        items.remove(index);
        let mut t = tx.clone();
        t.inputs[0].signature_script = raw_sig(&items)?;
        case(
            cases,
            format!("{}/missing_{index}", branch.name()),
            t,
            entry,
            false,
            "native-P2SH-or-redeem-depth",
        )?;
    }
    for position in 0..=5 {
        for value in [vec![], vec![1]] {
            let mut items = base.clone();
            items.insert(position, value.clone());
            let mut t = tx.clone();
            t.inputs[0].signature_script = raw_sig(&items)?;
            case(
                cases,
                format!("{}/extra_{position}_{}", branch.name(), hex::encode(value)),
                t,
                entry,
                false,
                "P2SH-or-redeem-depth",
            )?;
        }
    }
    for (i, j) in (0..5).flat_map(|i| (i + 1..5).map(move |j| (i, j))) {
        let mut items = base.clone();
        items.swap(i, j);
        let mut t = tx.clone();
        t.inputs[0].signature_script = raw_sig(&items)?;
        case(
            cases,
            format!("{}/wrong_order_{i}_{j}", branch.name()),
            t,
            entry,
            false,
            "redeem-or-verifier",
        )?;
    }
    for i in 0..3 {
        for n in [base[i].len() - 1, base[i].len() + 1] {
            let mut items = base.clone();
            items[i].resize(n, 0);
            let mut t = tx.clone();
            t.inputs[0].signature_script = raw_sig(&items)?;
            case(
                cases,
                format!("{}/element_{i}_size_{n}", branch.name()),
                t,
                entry,
                false,
                "redeem-size",
            )?;
        }
    }
    for i in [0, 1] {
        let mut items = base.clone();
        items[i][16] = 1;
        let mut t = tx.clone();
        t.inputs[0].signature_script = raw_sig(&items)?;
        case(
            cases,
            format!("{}/scalar_high_bit_{i}", branch.name()),
            t,
            entry,
            false,
            "Groth16-public-range",
        )?;
        let mut items = base.clone();
        items[i] = vec![255; 32];
        let mut t = tx.clone();
        t.inputs[0].signature_script = raw_sig(&items)?;
        case(
            cases,
            format!("{}/scalar_noncanonical_{i}", branch.name()),
            t,
            entry,
            false,
            "native-verifier-scalar-parse",
        )?;
    }
    let mut items = base.clone();
    items[2] = vec![0; 128];
    let mut t = tx.clone();
    t.inputs[0].signature_script = raw_sig(&items)?;
    case(
        cases,
        format!("{}/identity_proof", branch.name()),
        t,
        entry,
        false,
        "native-verifier",
    )?;
    // Same witness byte value using PUSHDATA1 and PUSHDATA2 is deliberately permitted.
    for wide in [false, true] {
        let mut sig = raw_sig(&base[..3])?;
        if wide {
            sig.extend([0x4d, 1, 0, branch.selector()]);
        } else {
            sig.extend([0x4c, 1, branch.selector()]);
        }
        sig.extend(raw_sig(&base[4..])?);
        let mut t = tx.clone();
        t.inputs[0].signature_script = sig;
        case(
            cases,
            format!("{}/equivalent_push_{wide}", branch.name()),
            t,
            entry,
            true,
            "native-push-only-and-redeem",
        )?;
    }
    for index in 0..tx.outputs.len() {
        for delta in [-1i64, 1] {
            let mut t = tx.clone();
            t.outputs[index].value = (t.outputs[index].value as i64 + delta) as u64;
            case(
                cases,
                format!("{}/output_value_{index}_{delta}", branch.name()),
                t,
                entry,
                false,
                "redeem-amount",
            )?;
        }
        let mut t = tx.clone();
        let mut s = script::encode_spk(&t.outputs[index].script_public_key);
        s[4] ^= 1;
        t.outputs[index].script_public_key = spk(&s)?;
        case(
            cases,
            format!("{}/output_spk_{index}", branch.name()),
            t,
            entry,
            false,
            "redeem-SPK",
        )?;
        let mut t = tx.clone();
        t.outputs[index].script_public_key =
            ScriptPublicKey::from_vec(1, t.outputs[index].script_public_key.script().to_vec());
        case(
            cases,
            format!("{}/output_spk_version_{index}", branch.name()),
            t,
            entry,
            false,
            "redeem-full-SPK-version",
        )?;
        let mut t = tx.clone();
        t.outputs[index].covenant = Some(kaspa_consensus_core::tx::CovenantBinding {
            authorizing_input: 0,
            covenant_id: Hash::from_bytes([0; 32]),
        });
        case(
            cases,
            format!("{}/output_covenant_zero_{index}", branch.name()),
            t,
            entry,
            false,
            "native-covenant-or-redeem-metadata",
        )?;
    }
    let mut t = tx.clone();
    t.outputs.push(t.outputs[0].clone());
    case(
        cases,
        format!("{}/extra_output", branch.name()),
        t,
        entry,
        false,
        "native-conservation-or-redeem-count",
    )?;
    let mut t = tx.clone();
    t.inputs.push(t.inputs[0].clone());
    case(
        cases,
        format!("{}/extra_input", branch.name()),
        t,
        entry,
        false,
        "native-duplicate-or-redeem-count",
    )?;
    for idx in [0, 1, u32::MAX].into_iter().filter(|i| *i != op.index) {
        let mut t = tx.clone();
        t.inputs[0].previous_outpoint.index = idx;
        case(
            cases,
            format!("{}/wrong_index_{idx}", branch.name()),
            t,
            entry,
            false,
            "native-verifier-outpoint",
        )?;
    }
    let mut t = tx.clone();
    t.inputs[0].previous_outpoint.transaction_id = Hash::from_bytes([0xff; 32]);
    case(
        cases,
        format!("{}/wrong_txid", branch.name()),
        t,
        entry,
        false,
        "native-verifier-outpoint",
    )?;
    let mut t = tx.clone();
    t.lock_time = 1;
    case(
        cases,
        format!("{}/locktime", branch.name()),
        t,
        entry,
        false,
        "redeem-envelope",
    )?;
    let mut t = tx.clone();
    t.payload = vec![0];
    case(
        cases,
        format!("{}/payload", branch.name()),
        t,
        entry,
        false,
        "native-envelope-or-redeem",
    )?;
    let mut t = tx.clone();
    t.gas = 1;
    case(
        cases,
        format!("{}/gas", branch.name()),
        t,
        entry,
        false,
        "native-envelope-or-redeem",
    )?;
    let mut t = tx.clone();
    t.subnetwork_id = format!("01{}", "00".repeat(19)).parse()?;
    case(
        cases,
        format!("{}/subnetwork", branch.name()),
        t,
        entry,
        false,
        "native-or-redeem-subnetwork",
    )?;
    let mut t = tx.clone();
    t.version = 0;
    case(
        cases,
        format!("{}/version", branch.name()),
        t,
        entry,
        false,
        "native-or-redeem-version",
    )?;
    let mut t = tx.clone();
    t.inputs[0].signature_script.insert(0, 0x76);
    case(
        cases,
        format!("{}/nonpush_witness", branch.name()),
        t,
        entry,
        false,
        "native-P2SH-push-only",
    )?;
    let mut t = tx.clone();
    t.inputs[0].compute_commit = kaspa_consensus_core::mass::ComputeBudget(1).into();
    case(
        cases,
        format!("{}/insufficient_budget", branch.name()),
        t,
        entry,
        false,
        "native-budget",
    )?;
    Ok(())
}
fn experiment(root: &Path) -> Result<Value> {
    if root.exists() {
        return Err("output must not already exist (no overwrite)".into());
    }
    fs::create_dir_all(root)?;
    let terms = Terms {
        l0: 1_000_000_000,
        b0: 70_000_000,
        w: 400_000_000,
        f0: 30_000_000,
        fc: 30_000_000,
        f1: 30_000_000,
    };
    let q = terms.checked()?;
    let mut secret = [0; 32];
    let mut instance = [0; 32];
    OsRng.fill_bytes(&mut secret);
    OsRng.fill_bytes(&mut instance);
    let claim = circuit::claim_commitment(&secret);
    // Explicit known fixture recovery key 1, only an UNFUNDED local instance.
    // Real funding is unavailable in this executable and requires a separate review.
    let recipient =
        hex::decode("00002079be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac")?;
    let source = run_git(&["rev-parse", "HEAD"])?;
    let lock = fs::read(Path::new(env!("CARGO_MANIFEST_DIR")).join("Cargo.lock"))?;
    let pins = json!({"kpi_source_commit":source,"rusty_kaspa_commit":"01b532e8b553523216471682649693af92f0fd16","rust_toolchain":"1.91.0","target":"x86_64-unknown-linux-gnu","cargo_lock_sha256":sha(&lock),"dependency_versions":{"arkworks":"0.6.0","sha2":"0.10.9"},"sdk_archive_sha256":"ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124","node_archive_sha256":"5ba61c05c013a4856491a8a17666fa73f7bd2aecbfed8affe8ffdc077361dad8","build_commands":["cargo +1.91.0 build --locked --release"],"checker_source_commit":source});
    let intent = json!({"schema":"kpi-a1-intent/v1","scope":"local-unfunded-fixture","genesis_hex":model::GENESIS_HEX,"instance_hex":hex::encode(instance),"claim_commitment_hex":hex::encode(claim),"recipient_spk_hex":hex::encode(&recipient),"terms":{"l0":q.l0.to_string(),"b0":q.b0.to_string(),"w":q.w.to_string(),"f0":q.f0.to_string(),"fc":q.fc.to_string(),"f1":q.f1.to_string()},"pins":pins});
    json_new(&root.join("owner-intent.json"), &intent)?;
    if let Some(retained) = std::env::var_os("KPI_A1_RETAIN_INTENT") {
        json_new(Path::new(&retained), &intent)?;
    }
    write_new(&root.join("claim-secret.bin"), &secret, true)?;
    write_new(
        &root.join("recipient-key.bin"),
        &{
            let mut b = [0; 32];
            b[31] = 1;
            b
        },
        true,
    )?;
    eprintln!("S1 setup (unfunded fixture)");
    let c1 =
        BranchContext::from_terms(Branch::S1Terminal, terms, instance, claim, &recipient, &[])?;
    let a1 = setup(root, Branch::S1Terminal, &c1)?;
    let d1 = script::build_s1(&a1.vk, &policy(&c1)?)?;
    let s1 = pay_to_script_hash_script(&d1);
    let s1bytes = script::encode_spk(&s1);
    eprintln!("S0 continuation setup binds exact S1 SPK");
    let cc = BranchContext::from_terms(
        Branch::S0Continue,
        terms,
        instance,
        claim,
        &recipient,
        &s1bytes,
    )?;
    let ac = setup(root, Branch::S0Continue, &cc)?;
    eprintln!("S0 terminal setup");
    let ct =
        BranchContext::from_terms(Branch::S0Terminal, terms, instance, claim, &recipient, &[])?;
    let at = setup(root, Branch::S0Terminal, &ct)?;
    let d0 = script::build_s0(&ac.vk, &at.vk, &policy(&cc)?, &policy(&ct)?)?;
    let s0 = pay_to_script_hash_script(&d0);
    // Only a synthetic temporary-consensus funding BODY, never submitted to TN10.
    // Its ID is constructed after all setup/scripts; no future txid is a constant.
    let bootstrap = UtxoEntry::new(
        q.r0.checked_add(1_000_000).ok_or("bootstrap overflow")?,
        ScriptPublicKey::from_vec(0, vec![0x51]),
        0,
        false,
        None,
    );
    let funding = Transaction::new(
        1,
        vec![TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(Hash::from_bytes([0x40; 32]), 7),
            vec![],
            u64::MAX,
            1,
        )],
        vec![TransactionOutput::new(q.r0, s0.clone())],
        0,
        Default::default(),
        0,
        vec![],
    );
    validator::set_mass(&funding, &bootstrap)?;
    validator::validate(&validator::validator(), &funding, &bootstrap)?;
    json_new(
        &root.join("synthetic-funding.transaction.json"),
        &tx_json(&funding),
    )?;
    json_new(
        &root.join("synthetic-funding.validate.json"),
        &json!({"transaction":tx_json(&funding),"entry":bootstrap}),
    )?;
    let op0 = TransactionOutpoint::new(funding.id(), 0);
    let e0 = UtxoEntry::new(q.r0, s0.clone(), 0, false, None);
    let e1 = UtxoEntry::new(q.r1, s1.clone(), 0, false, None);
    eprintln!("Proving three paths / native Full / decoded measurement");
    let (tc, mc) = fixture(root, Branch::S0Continue, &ac, &cc, secret, op0, &d0, &e0)?;
    let (tt, mt) = fixture(root, Branch::S0Terminal, &at, &ct, secret, op0, &d0, &e0)?;
    let op1 = TransactionOutpoint::new(tc.id(), 0);
    let (t1, m1) = fixture(root, Branch::S1Terminal, &a1, &c1, secret, op1, &d1, &e1)?;
    let mut cases = vec![];
    for (b, t, a, d, e) in [
        (Branch::S0Continue, &tc, &ac, &d0, &e0),
        (Branch::S0Terminal, &tt, &at, &d0, &e0),
        (Branch::S1Terminal, &t1, &a1, &d1, &e1),
    ] {
        negatives(b, t, a, secret, d, e, &mut cases)?;
    }
    for (name, target, foreign) in [
        ("continue_with_terminal_proof", &tc, &tt),
        ("terminal_with_continue_proof", &tt, &tc),
        ("S1_with_S0proof", &t1, &tt),
    ] {
        let mut t = target.clone();
        let mut sig = t.inputs[0].signature_script.clone();
        let foreign_sig = &foreign.inputs[0].signature_script;
        sig[68..196].copy_from_slice(&foreign_sig[68..196]);
        t.inputs[0].signature_script = sig;
        case(
            &mut cases,
            name.into(),
            t,
            if name.starts_with("S1") { &e1 } else { &e0 },
            false,
            "matching-immutable-VK-and-relation",
        )?;
    }
    if tc.outputs.len() == 2 {
        let mut t = tc.clone();
        t.outputs.swap(0, 1);
        case(
            &mut cases,
            "continue_output_order".into(),
            t,
            &e0,
            false,
            "redeem-output-order",
        )?;
    }
    let stateful = json!({"status":"pending separate stateful command","reason":"local Full cannot establish spentness or native accepted-state rollback"});
    let d0desc = descriptor(root, "s0.redeem", &d0)?;
    let d1desc = descriptor(root, "s1.redeem", &d1)?;
    let budgets = json!({"s0_continue":mc["compute_budget"].as_u64().unwrap().to_string(),"s0_terminal":mt["compute_budget"].as_u64().unwrap().to_string(),"s1_terminal":m1["compute_budget"].as_u64().unwrap().to_string()});
    let address = kaspa_addresses::Address::new(
        kaspa_addresses::Prefix::Testnet,
        kaspa_addresses::Version::PubKey,
        &recipient[3..35],
    )
    .to_string();
    let manifest = json!({"schema":"kpi-a1-artifacts/v1","protocol":"KPI-A1/TN10/finite/v1","network":"testnet-10","genesis_hex":model::GENESIS_HEX,"instance_hex":hex::encode(instance),"claim_commitment_hex":hex::encode(claim),"recipient":{"address":address,"spk_version":"0","spk_hex":hex::encode(&recipient)},"states":{"s0":{"stage":"0","R":q.r0.to_string(),"L":q.l0.to_string(),"B":q.b0.to_string(),"redeem":d0desc,"spk_hex":hex::encode(script::encode_spk(&s0))},"s1":{"stage":"1","R":q.r1.to_string(),"L":q.l1.to_string(),"B":q.b1.to_string(),"redeem":d1desc,"spk_hex":hex::encode(s1bytes)}},"branches":{"s0_continue":ac.record,"s0_terminal":at.record,"s1_terminal":a1.record},"abi":{"verifier_tag_hex":"20","public_inputs":circuit::PUBLIC_NAMES,"scalar_bytes":"32","proof_bytes":"128","vk_bytes":"424","witness_order":["tag_hi","tag_lo","proof","selector","redeem"]},"envelope":{"tx_version":"1","subnetwork_hex":"00".repeat(20),"gas":"0","payload_hex":"","lock_time":"0","sequence_policy":"relative-lock-disabled","compute_budgets":budgets},"pins":pins,"inspection":{"normalized_r1cs_sha256":{"s0_continue":ac.record["r1cs"]["sha256"],"s0_terminal":at.record["r1cs"]["sha256"],"s1_terminal":a1.record["r1cs"]["sha256"]},"script_disassembly_sha256":"not-yet-inspected","checker_report_sha256":"not-yet-inspected","setup_observation_receipt_sha256":"not-independently-observed"},"recovery":{"source_id":"pending-independent-archive","network_genesis_hex":model::GENESIS_HEX,"retention_start_hash":"unfunded-no-chain-checkpoint","retention_policy":"pending","locator_schema":"kpi-a1-locator/v1","private_backup_items":["claim-secret.bin","recipient-key.bin"],"public_artifact_items":["manifest.json","all PK/VK/context/R1CS/scripts/source/pins"]}});
    json_new(&root.join("manifest.json"), &manifest)?;
    json_new(&root.join("cases.json"), &json!(cases))?;
    let report = json!({"scope":"unfunded-local-fixture-no-public-TN10-acceptance","G2_three_paths_native_full":true,"G3_synthetic_native_stateful":stateful,"G4_decoded_measurements":{"s0_continue":mc,"s0_terminal":mt,"s1_terminal":m1},"cases":cases.len(),"G5_independent_history":"pending","G6":"not-authorized","setup_provenance":"single-party local fixture; see separately retained observation, never an audited ceremony"});
    json_new(&root.join("report.json"), &report)?;
    Ok(report)
}
fn stateful_bundle(root: &Path) -> Result<Value> {
    let req: Value = serde_json::from_slice(&fs::read(root.join("s0_continue.validate.json"))?)?;
    let tc = parse_tx(&req["transaction"])?;
    let e: UtxoEntry = serde_json::from_value(req["entry"].clone())?;
    let tt = parse_tx(&serde_json::from_slice(&fs::read(
        root.join("s0_terminal.transaction.json"),
    )?)?)?;
    let mut alternate = tc.clone();
    alternate.inputs[0].sequence -= 1;
    alternate.finalize();
    validator::set_mass(&alternate, &e)?;
    let fundreq: Value =
        serde_json::from_slice(&fs::read(root.join("synthetic-funding.validate.json"))?)?;
    let fund = parse_tx(&fundreq["transaction"])?;
    let bootstrap: UtxoEntry = serde_json::from_value(fundreq["entry"].clone())?;
    let t1 = parse_tx(&serde_json::from_slice(&fs::read(
        root.join("s1_terminal.transaction.json"),
    )?)?)?;
    let result = json!({"continue_vs_continue":kpi_poc_a1::stateful::competing_and_reorg(&tc,&alternate,&e)?,"continue_vs_terminal":kpi_poc_a1::stateful::competing_and_reorg(&tc,&tt,&e)?,"accepted_direct_terminal":kpi_poc_a1::stateful::accept_path(&[fund.clone(),tt],&bootstrap)?,"accepted_continue_snapshot":kpi_poc_a1::stateful::accept_path(&[fund.clone(),tc.clone()],&bootstrap)?,"accepted_continue_terminal":kpi_poc_a1::stateful::accept_path(&[fund,tc,t1],&bootstrap)?});
    json_new(&root.join("stateful.json"), &result)?;
    Ok(result)
}
fn native_path(request: &Path) -> Result<Value> {
    let v = kpi_poc_a1::artifact::strict_json(&fs::read(request)?)?;
    let initial: UtxoEntry = serde_json::from_value(v["initial_entry"].clone())?;
    let txs = v["transactions"]
        .as_array()
        .ok_or("transactions array")?
        .iter()
        .map(parse_tx)
        .collect::<Result<Vec<_>>>()?;
    Ok(kpi_poc_a1::stateful::accept_path(&txs, &initial)?)
}
fn fresh_proof(
    bundle: &Path,
    branch: Branch,
    secret_file: &Path,
    request: &Path,
    output: &Path,
) -> Result<Value> {
    let m = kpi_poc_a1::artifact::manifest(&fs::read(bundle.join("manifest.json"))?)?;
    let secret = private_secret(secret_file)?;
    let r = &m["branches"][branch.name()];
    let prefix = hexbytes(&r["context_hex"])?;
    let context = BranchContext::decode(&prefix)?;
    if circuit::claim_commitment(&secret) != context.claim {
        return Err("wrong private claim secret".into());
    }
    let bytes = fs::read(artifact_path(bundle, text(&r["pk"]["path"])?)?)?;
    if sha(&bytes) != text(&r["pk"]["sha256"])? {
        return Err("PK artifact hash".into());
    }
    let pk: ProvingKey<Bn254> = circuit::parse_compressed(&bytes)?;
    let req: Value = serde_json::from_slice(&fs::read(request)?)?;
    let entry: UtxoEntry = serde_json::from_value(req["entry"].clone())?;
    let stage = if branch == Branch::S1Terminal {
        "s1"
    } else {
        "s0"
    };
    if entry.amount != context.reserve
        || entry.covenant_id.is_some()
        || hex::encode(script::encode_spk(&entry.script_public_key))
            != text(&m["states"][stage]["spk_hex"])?
    {
        return Err("current authenticated UTXO does not match artifact".into());
    }
    let op = TransactionOutpoint::new(
        text(&req["txid"])?.parse()?,
        num(&req["index"])?.try_into()?,
    );
    let tag = circuit::compute_tag(&prefix, &secret, &op.transaction_id.as_bytes(), op.index);
    let inputs = circuit::public_inputs(&op.transaction_id.as_bytes(), op.index, &tag);
    let start = Instant::now();
    let proof = Groth16::<Bn254>::prove(
        &pk,
        ClaimCircuit {
            constants: ClaimConstants {
                context_prefix: prefix,
                claim: context.claim,
            },
            secret: Some(secret),
            inputs: Some(inputs),
        },
        &mut OsRng,
    )?;
    if !Groth16::<Bn254>::verify(&pk.vk, &inputs, &proof)? {
        return Err("fresh proof invalid".into());
    }
    let redeem = fs::read(artifact_path(
        bundle,
        text(&m["states"][stage]["redeem"]["path"])?,
    )?)?;
    if sha(&redeem) != text(&m["states"][stage]["redeem"]["sha256"])? {
        return Err("redeem artifact hash".into());
    }
    let sig = script::signature(
        &circuit::compressed(&proof)?,
        &inputs,
        &[branch.selector()],
        &redeem,
    )?;
    let tx = tx_for(
        &context,
        op,
        sig,
        num(&m["envelope"]["compute_budgets"][branch.name()])?.try_into()?,
    )?;
    validator::set_mass(&tx, &entry)?;
    let fee = validator::validate(&validator::validator(), &tx, &entry)?;
    json_new(output, &tx_json(&tx))?;
    Ok(
        json!({"fresh_proof":true,"native_full":true,"txid":tx.id().to_string(),"fee":fee.to_string(),"elapsed_ms":start.elapsed().as_secs_f64()*1000.,"scope":"known-authenticated-utxo-spendability-only-not-history-discovery"}),
    )
}
fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let result=match args.first().map(String::as_str){
        Some("experiment") if args.len()==2 => experiment(&PathBuf::from(&args[1]))?,
        Some("stateful") if args.len()==2 => stateful_bundle(Path::new(&args[1]))?,
        Some("validate-body") if args.len()==2 => validate_body(Path::new(&args[1]))?,
        Some("check-backup") if args.len()==4 => check_backup(Path::new(&args[1]),Path::new(&args[2]),Path::new(&args[3]))?,
        Some("native-path") if args.len()==2 => native_path(Path::new(&args[1]))?,
        Some("fresh-continue") if args.len()==5 => fresh_proof(Path::new(&args[1]),Branch::S0Continue,Path::new(&args[2]),Path::new(&args[3]),Path::new(&args[4]))?,
        Some("fresh-terminal") if args.len()==6 => fresh_proof(Path::new(&args[1]),match args[2].as_str(){"s0_terminal"=>Branch::S0Terminal,"s1_terminal"=>Branch::S1Terminal,_=>return Err("terminal branch required".into())},Path::new(&args[3]),Path::new(&args[4]),Path::new(&args[5]))?,
        _=>return Err("Usage: kpi-poc-a1 experiment NEW_DIRECTORY | stateful BUNDLE | validate-body REQUEST.json | check-backup BUNDLE SECRET KEY | fresh-terminal BUNDLE s0_terminal|s1_terminal SECRET REQUEST OUTPUT".into())
    };
    println!("{}", serde_json::to_string_pretty(&result)?);
    Ok(())
}
