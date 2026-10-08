//! Original-circuit/original-key checks using independently calculated public tags.
//! No setup or proving calls. The original proof cannot establish validity of a
//! substituted tag, and CS checks independently exercise the fixed SHA relation.
use ark_bn254::Bn254;
use ark_groth16::{Groth16, Proof, VerifyingKey};
use ark_relations::gr1cs::{ConstraintSynthesizer, ConstraintSystem, OptimizationGoal};
use ark_snark::SNARK;
use kpi_poc_a1::circuit::{self, ClaimCircuit, ClaimConstants};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::{Component, Path},
    time::Instant,
};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

fn decode(value: &Value) -> Result<Vec<u8>> {
    let text = value.as_str().ok_or("hex text required")?;
    if text.len() % 2 != 0
        || !text
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("canonical lowercase hex required".into());
    }
    Ok(hex::decode(text)?)
}

fn artifact(bundle: &Path, descriptor: &Value) -> Result<Vec<u8>> {
    let path = Path::new(descriptor["path"].as_str().ok_or("artifact path")?);
    if path.as_os_str().is_empty()
        || path
            .components()
            .any(|c| !matches!(c, Component::Normal(_)))
    {
        return Err("safe relative artifact path required".into());
    }
    let resolved = bundle.join(path).canonicalize()?;
    if !resolved.starts_with(bundle.canonicalize()?) {
        return Err("artifact symlink escapes bundle".into());
    }
    let bytes = fs::read(resolved)?;
    if descriptor["bytes"].as_str() != Some(&bytes.len().to_string())
        || descriptor["sha256"].as_str() != Some(&hex::encode(Sha256::digest(&bytes)))
    {
        return Err("original artifact descriptor mismatch".into());
    }
    Ok(bytes)
}

fn expected_mutations(context: &[u8]) -> Result<BTreeMap<String, Vec<u8>>> {
    if context.len() < 177 || &context[..22] != b"KPI-A1/TN10/finite/v1\0" {
        return Err("original context shape".into());
    }
    let mut offsets: Vec<(String, usize)> = [
        ("domain", 0),
        ("genesis", 22),
        ("instance", 54),
        ("stage", 86),
        ("mode", 87),
        ("claim_commitment", 88),
        ("output_count", 176),
    ]
    .into_iter()
    .map(|(name, offset)| (name.into(), offset))
    .collect();
    for (index, name) in ["R", "L", "B", "fee", "next_R", "next_L", "next_B"]
        .iter()
        .enumerate()
    {
        offsets.push(((*name).into(), 120 + index * 8));
    }
    let mut starts = vec![];
    let mut cursor = 177;
    for index in 0..context[176] {
        if cursor + 12 > context.len() {
            return Err("truncated record".into());
        }
        let size = u32::from_le_bytes(context[cursor + 8..cursor + 12].try_into()?);
        let end = cursor
            .checked_add(13 + usize::try_from(size)?)
            .ok_or("record overflow")?;
        if size < 3 || end > context.len() || context[end - 1] != 0 {
            return Err("record shape".into());
        }
        starts.push((cursor, end));
        for (name, offset) in [
            ("value", cursor),
            ("spk_length", cursor + 8),
            ("spk_version", cursor + 13),
            ("script", cursor + 14),
            ("metadata", end - 1),
        ] {
            offsets.push((format!("output_{index}_{name}"), offset));
        }
        cursor = end;
    }
    if cursor != context.len() || !matches!(starts.len(), 1 | 2) {
        return Err("record count/trailing bytes".into());
    }
    let mut expected = BTreeMap::new();
    for (name, offset) in offsets {
        let mut changed = context.to_vec();
        changed[offset] ^= 1;
        expected.insert(name, changed);
    }
    if starts.len() == 2 {
        let mut swapped = context[..177].to_vec();
        swapped.extend(&context[starts[1].0..starts[1].1]);
        swapped.extend(&context[starts[0].0..starts[0].1]);
        expected.insert("output_order".into(), swapped);
    }
    expected.insert("wrong_secret_original_C".into(), context.to_vec());
    Ok(expected)
}

fn satisfied(
    constants: &ClaimConstants,
    secret: [u8; 32],
    txid: &[u8; 32],
    index: u32,
    tag: &[u8; 32],
) -> Result<bool> {
    let cs = ConstraintSystem::new_ref();
    cs.set_optimization_goal(OptimizationGoal::Constraints);
    ClaimCircuit {
        constants: constants.clone(),
        secret: Some(secret),
        inputs: Some(circuit::public_inputs(txid, index, tag)),
    }
    .generate_constraints(cs.clone())?;
    cs.finalize();
    Ok(cs.is_satisfied()?)
}

fn run(bundle: &Path, secret_path: &Path, oracle_path: &Path) -> Result<Value> {
    let manifest: Value = serde_json::from_slice(&fs::read(bundle.join("manifest.json"))?)?;
    let oracle: Value = serde_json::from_slice(&fs::read(oracle_path)?)?;
    if oracle["schema"] != "kpi-a1-context-oracle/v1" {
        return Err("oracle schema".into());
    }
    let secret: [u8; 32] = fs::read(secret_path)?
        .try_into()
        .map_err(|_| "private secret length")?;
    let claim: [u8; 32] = decode(&manifest["claim_commitment_hex"])?
        .try_into()
        .map_err(|_| "claim32")?;
    if circuit::claim_commitment(&secret) != claim {
        return Err("private backup mismatch".into());
    }
    let mut outcomes = vec![];
    let start = Instant::now();
    for branch in ["s0_continue", "s0_terminal", "s1_terminal"] {
        let record = &manifest["branches"][branch];
        let reference = &oracle["branches"][branch];
        let context = decode(&record["context_hex"])?;
        if decode(&reference["context_hex"])? != context
            || reference["context_sha256"] != hex::encode(Sha256::digest(&context))
        {
            return Err("oracle does not target original branch context".into());
        }
        let transaction: Value = serde_json::from_slice(&fs::read(
            bundle.join(format!("{branch}.transaction.json")),
        )?)?;
        let previous = &transaction["inputs"][0]["previousOutpoint"];
        if previous["transactionId"] != reference["txid_hex"]
            || previous["index"].as_u64().ok_or("index")?.to_string()
                != reference["index"].as_str().ok_or("oracle index")?
        {
            return Err("oracle dynamic outpoint differs".into());
        }
        let txid: [u8; 32] = decode(&reference["txid_hex"])?
            .try_into()
            .map_err(|_| "txid32")?;
        let index: u32 = reference["index"].as_str().ok_or("index text")?.parse()?;
        let original_tag: [u8; 32] = decode(&reference["original_tag_hex"])?
            .try_into()
            .map_err(|_| "tag32")?;
        let constants = ClaimConstants {
            context_prefix: context.clone(),
            claim,
        };
        let expected = expected_mutations(&context)?;
        let mut seen = BTreeSet::new();
        let vk: VerifyingKey<Bn254> = circuit::parse_compressed(&artifact(bundle, &record["vk"])?)?;
        let proof: Proof<Bn254> =
            circuit::parse_compressed(&fs::read(bundle.join(format!("{branch}.proof")))?)?;
        if vk.gamma_abc_g1.len() != 6
            || original_tag != circuit::compute_tag(&context, &secret, &txid, index)
            || !satisfied(&constants, secret, &txid, index, &original_tag)?
            || !Groth16::<Bn254>::verify(
                &vk,
                &circuit::public_inputs(&txid, index, &original_tag),
                &proof,
            )?
        {
            return Err("original-context positive control failed".into());
        }
        for mutation in reference["mutations"].as_array().ok_or("mutations")? {
            let name = mutation["name"].as_str().ok_or("mutation name")?;
            let changed_context = decode(&mutation["context_hex"])?;
            if !seen.insert(name.to_string()) || expected.get(name) != Some(&changed_context) {
                return Err("missing/duplicate/mislabeled context mutation".into());
            }
            let wrong_secret = mutation["wrong_secret"]
                .as_bool()
                .ok_or("wrong_secret bool")?;
            let mut witness = secret;
            if wrong_secret {
                witness[0] ^= 1;
            }
            if wrong_secret != (name == "wrong_secret_original_C")
                || (!wrong_secret && changed_context == context)
                || (wrong_secret && changed_context != context)
            {
                return Err("mutation definition mismatch".into());
            }
            let changed_tag: [u8; 32] = decode(&mutation["tag_hex"])?
                .try_into()
                .map_err(|_| "tag32")?;
            // Cross-check the independently generated expected tag. This does
            // not generate the expected value: Python and retained oracle did.
            if changed_tag == original_tag
                || changed_tag != circuit::compute_tag(&changed_context, &witness, &txid, index)
            {
                return Err("independent oracle tag mismatch".into());
            }
            let cs_satisfied = satisfied(&constants, witness, &txid, index, &changed_tag)?;
            let original_proof_valid = Groth16::<Bn254>::verify(
                &vk,
                &circuit::public_inputs(&txid, index, &changed_tag),
                &proof,
            )?;
            if cs_satisfied || original_proof_valid {
                return Err(format!(
                    "unexpected original relation/key acceptance: {branch}/{name}"
                )
                .into());
            }
            outcomes.push(json!({"branch":branch,"mutation":name,"original_constants_retained":true,
                "original_vk_retained":true,"constraint_satisfied":false,"original_proof_with_changed_inputs_verified":false,
                "layer":"circuit-and-original-key-verification","new_proof_generated":false}));
        }
        if seen.len() != expected.len() {
            return Err("incomplete context-negative corpus".into());
        }
    }
    Ok(
        json!({"schema":"kpi-a1-context-negative-results/v1","positive_branches":3,"negative_cases":outcomes.len(),
        "outcomes":outcomes,"elapsed_ms":start.elapsed().as_millis().to_string(),
        "scope":"original-relation-context-binding-no-foreign-setup-no-new-proofs-no-chain-acceptance"}),
    )
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 3 {
        return Err("usage: a1_context_negatives BUNDLE SECRET_FILE ORACLE_JSON".into());
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
