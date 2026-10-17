//! Specialized circuit comparison only. No shielded KAS or production setup.
use ark_bn254::{Bn254, Fr};
use ark_ff::ToConstraintField;
use ark_groth16::{Groth16, PreparedVerifyingKey, Proof};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
#[cfg(feature = "circuit")]
pub mod circuit;
#[path = "../../../proof-classification/protocol.rs"]
#[allow(dead_code)]
pub mod proxy;

pub const PROOF_BYTES: usize = 128;
pub const CLASSIFIER_CYCLE_BUDGET: u64 = 32_000_000;
pub fn encode<T: CanonicalSerialize>(v: &T) -> Vec<u8> {
    let mut out = vec![];
    v.serialize_compressed(&mut out)
        .expect("serialize public artifact");
    out
}
pub fn key_id(vk: &[u8]) -> [u8; 32] {
    proxy::tagged(b"KPI-specialized-G16-v1", vk)
}
pub fn public_inputs(journal: &[u8]) -> Vec<Fr> {
    assert_eq!(journal.len(), 96);
    journal.to_field_elements().unwrap()
}
pub fn classify(op: &[u8], id: [u8; 32], pvk: &PreparedVerifyingKey<Bn254>) -> u8 {
    if op.len() > proxy::MAX_OPERATION || op.len() < proxy::INTENT_LEN + 4 {
        return 1;
    }
    let intent = &op[..proxy::INTENT_LEN];
    if !proxy::intent_valid(intent, id) {
        return 1;
    }
    let mut r = proxy::Reader(&op[proxy::INTENT_LEN..]);
    let Ok(bytes) = r.blob(PROOF_BYTES) else {
        return 2;
    };
    if bytes.len() != PROOF_BYTES || !r.0.is_empty() {
        return 2;
    }
    // Canonical checked decoding: validates curve/subgroup membership. Never
    // deserialize unchecked or accept a host-supplied validity bit.
    let mut rest = bytes;
    let Ok(proof) = Proof::<Bn254>::deserialize_compressed(&mut rest) else {
        return 2;
    };
    if !rest.is_empty() || encode(&proof) != bytes {
        return 2;
    }
    #[cfg(target_os = "zkvm")]
    println!(
        "PROFILE after_checked_proof_decode {}",
        risc0_zkvm::guest::env::cycle_count()
    );
    match Groth16::<Bn254>::verify_proof(pvk, &proof, &public_inputs(&proxy::journal(intent))) {
        Ok(true) => 0,
        _ => 3,
    }
}
