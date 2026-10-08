//! Independent reviewed relation reconstruction, not the production circuit.
//! Shared Arkworks/SHA256 gadget correctness remains an explicit dependency.
//! No setup, proving, original-module import or broadcast functionality.
use ark_bn254::Bn254;
use ark_bn254::Fr;
use ark_crypto_primitives::crh::sha256::constraints::Sha256Gadget;
use ark_ff::{BigInteger, PrimeField, Zero};
use ark_groth16::{ProvingKey, VerifyingKey};
use ark_r1cs_std::{
    alloc::AllocVar, boolean::Boolean, convert::ToBitsGadget, eq::EqGadget, fields::fp::FpVar,
    uint8::UInt8,
};
use ark_relations::gr1cs::{
    ConstraintSystem, OptimizationGoal, R1CS_PREDICATE_LABEL, SynthesisMode,
};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, env, fs};

fn number(v: &serde_json::Value) -> Result<u64, Box<dyn std::error::Error>> {
    if let Some(n) = v.as_u64() {
        return Ok(n);
    }
    let s = v.as_str().ok_or("missing native integer")?;
    if s.is_empty() || !s.bytes().all(|b| b.is_ascii_digit()) || (s.len() > 1 && s.starts_with('0'))
    {
        return Err("noncanonical native integer".into());
    }
    Ok(s.parse()?)
}
fn body_hash(path: &str) -> Result<(), Box<dyn std::error::Error>> {
    use kaspa_consensus_core::{
        hashing,
        tx::{
            ScriptPublicKey, Transaction, TransactionInput, TransactionOutpoint, TransactionOutput,
        },
    };
    let body: serde_json::Value = serde_json::from_slice(&fs::read(path)?)?;
    let text = |v: &serde_json::Value| -> Result<String, Box<dyn std::error::Error>> {
        Ok(v.as_str().ok_or("missing native hex")?.to_owned())
    };
    let version: u16 = number(&body["version"])?.try_into()?;
    if version > 1 {
        return Err("unsupported transaction version".into());
    }
    let mut inputs = Vec::new();
    for item in body["inputs"].as_array().ok_or("inputs missing")? {
        let op = TransactionOutpoint::new(
            text(&item["previousOutpoint"]["transactionId"])?.parse()?,
            number(&item["previousOutpoint"]["index"])?.try_into()?,
        );
        let sig = decode(&text(&item["signatureScript"])?)?;
        let sequence = number(&item["sequence"])?;
        let input = if version == 0 {
            TransactionInput::new(op, sig, sequence, number(&item["sigOpCount"])?.try_into()?)
        } else {
            TransactionInput::new_with_compute_budget(
                op,
                sig,
                sequence,
                number(&item["computeBudget"])?.try_into()?,
            )
        };
        inputs.push(input);
    }
    let mut outputs = Vec::new();
    for item in body["outputs"].as_array().ok_or("outputs missing")? {
        let raw = decode(&text(&item["scriptPublicKey"])?)?;
        if raw.len() < 2 {
            return Err("SPK missing version".into());
        }
        let mut output = TransactionOutput::new(
            number(&item["value"])?,
            ScriptPublicKey::from_vec(u16::from_be_bytes(raw[..2].try_into()?), raw[2..].to_vec()),
        );
        if version == 1 {
            if item.get("covenant").is_none() {
                return Err("covenant Full field missing".into());
            }
            output.covenant = serde_json::from_value(item["covenant"].clone())?;
        }
        outputs.push(output);
    }
    let tx = Transaction::new(
        version,
        inputs,
        outputs,
        number(&body["lockTime"])?,
        text(&body["subnetworkId"])?.parse()?,
        number(&body["gas"])?,
        decode(&text(&body["payload"])?)?,
    );
    let mass = body
        .get("storageMass")
        .or_else(|| body.get("mass"))
        .ok_or("Full storage mass missing")?;
    tx.set_storage_mass(number(mass)?);
    println!(
        "{}",
        serde_json::json!({"txid":tx.id().to_string(),"full_hash":hashing::tx::hash(&tx).to_string(),"full_valid":false,"scope":"native-body-hashes-not-consensus-acceptance"})
    );
    Ok(())
}

fn decode(s: &str) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    if s.len() % 2 != 0
        || !s
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("canonical lowercase hex required".into());
    }
    (0..s.len())
        .step_by(2)
        .map(|i| Ok(u8::from_str_radix(&s[i..i + 2], 16)?))
        .collect()
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    if args.len() == 3 && args[1] == "--body" {
        return body_hash(&args[2]);
    }
    if args.len() == 4 && args[1] == "--keys" {
        let pkbytes = fs::read(&args[2])?;
        let vkbytes = fs::read(&args[3])?;
        let mut p = &pkbytes[..];
        let mut v = &vkbytes[..];
        let pk = ProvingKey::<Bn254>::deserialize_compressed(&mut p)?;
        let vk = VerifyingKey::<Bn254>::deserialize_compressed(&mut v)?;
        if !p.is_empty() || !v.is_empty() || pk.vk != vk || vk.gamma_abc_g1.len() != 6 {
            return Err("invalid/trailing/mismapped PK/VK".into());
        }
        let mut canonical = Vec::new();
        vk.serialize_compressed(&mut canonical)?;
        if canonical != vkbytes {
            return Err("noncanonical VK".into());
        }
        println!(
            "{{\"validated\":true,\"gamma_abc_count\":6,\"scope\":\"validated-arkworks-encoding-not-CRS-provenance\"}}"
        );
        return Ok(());
    }
    if args.len() != 4 {
        return Err("usage: a1_reference CONTEXT_HEX_FILE CLAIM_HEX OUTPUT_R1CS".into());
    }
    let context = decode(fs::read_to_string(&args[1])?.trim())?;
    let claim = decode(&args[2])?;
    if claim.len() != 32 || context.len() < 177 || &context[..22] != b"KPI-A1/TN10/finite/v1\0" {
        return Err("context/claim shape".into());
    }
    let system = ConstraintSystem::<Fr>::new_ref();
    system.set_optimization_goal(OptimizationGoal::Constraints);
    system.set_mode(SynthesisMode::Setup);
    let mut public_bytes: Vec<Vec<UInt8<Fr>>> = Vec::new();
    for width in [128usize, 128, 32, 128, 128] {
        let input = FpVar::<Fr>::new_input(system.clone(), || Ok(Fr::zero()))?;
        let bits = input.to_bits_le()?;
        for bit in bits.iter().skip(width) {
            bit.enforce_equal(&Boolean::constant(false))?;
        }
        let bytes = bits[..width].chunks(8).map(UInt8::from_bits_le).collect();
        public_bytes.push(bytes);
    }
    let mut secret = Vec::new();
    for _ in 0..32 {
        secret.push(UInt8::<Fr>::new_witness(system.clone(), || Ok(0u8))?);
    }
    let first = Sha256Gadget::digest(&secret)?;
    first.0.enforce_equal(&UInt8::constant_vec(&claim))?;
    let mut message = UInt8::constant_vec(&context);
    message.extend(secret);
    for bytes in &public_bytes[..3] {
        message.extend(bytes.iter().cloned());
    }
    let second = Sha256Gadget::digest(&message)?;
    let expected: Vec<_> = public_bytes[3..].iter().flatten().cloned().collect();
    second.0.enforce_equal(&expected)?;
    system.finalize();
    let matrices = system.to_matrices()?;
    if matrices.len() != 1 || system.num_instance_variables() != 6 {
        return Err("unexpected public allocation/predicate".into());
    }
    let abc = matrices
        .get(R1CS_PREDICATE_LABEL)
        .ok_or("no R1CS matrices")?;
    let rows = system.num_constraints();
    let variables = system.num_instance_variables() + system.num_witness_variables();
    if abc.len() != 3 || abc.iter().any(|m| m.len() != rows) {
        return Err("matrix dimension mismatch".into());
    }
    let mut output = b"KPI-A1/R1CS/v1\0".to_vec();
    output.extend(5u32.to_le_bytes());
    output.extend((variables as u64).to_le_bytes());
    output.extend((rows as u64).to_le_bytes());
    for row in 0..rows {
        for matrix in abc {
            let mut sparse = BTreeMap::new();
            for (coefficient, index) in &matrix[row] {
                if *index >= variables {
                    return Err("variable out of range".into());
                }
                let entry = sparse.entry(*index).or_insert(Fr::zero());
                *entry += coefficient;
            }
            sparse.retain(|_, c| !c.is_zero());
            output.extend((sparse.len() as u64).to_le_bytes());
            for (index, coefficient) in sparse {
                output.extend((index as u64).to_le_bytes());
                let mut bytes = coefficient.into_bigint().to_bytes_le();
                bytes.resize(32, 0);
                output.extend(bytes);
            }
        }
    }
    let digest = Sha256::digest(&output);
    fs::write(&args[3], &output)?;
    println!(
        "{{\"public_count\":5,\"variable_count\":{variables},\"constraint_count\":{rows},\"sha256\":\"{}\",\"scope\":\"independent-wiring-shared-arkworks-gadget\"}}",
        digest
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect::<String>()
    );
    Ok(())
}
