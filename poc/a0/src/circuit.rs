//! A0's deliberately narrow, terminal claim-authorization relation.
//!
//! The setup fixes the claim commitment and every byte of `context_prefix`.
//! The prefix must be constructed by the harness from the same immutable terms
//! that its covenant checks. This is not a note, nullifier, or privacy protocol.

use ark_bn254::Fr;
use ark_crypto_primitives::crh::sha256::constraints::Sha256Gadget;
use ark_ff::PrimeField;
use ark_r1cs_std::{
    alloc::AllocVar, boolean::Boolean, convert::ToBitsGadget, eq::EqGadget, fields::fp::FpVar,
    uint8::UInt8,
};
use ark_relations::gr1cs::{ConstraintSynthesizer, ConstraintSystemRef, SynthesisError};
use sha2::{Digest, Sha256};

/// Immutable circuit-specific authorization terms. A different value requires
/// a different setup/key; the reserve script must pin the intended key.
#[derive(Clone)]
pub struct ClaimConstants {
    pub context_prefix: Vec<u8>,
    pub claim: [u8; 32],
}

/// Public fields, in verifier order:
/// txid bytes [0..16] as LE128, txid [16..32] as LE128, index LE32,
/// tag [0..16] as LE128, tag [16..32] as LE128.
pub fn public_inputs(txid: &[u8; 32], index: u32, tag: &[u8; 32]) -> [Fr; 5] {
    [
        Fr::from_le_bytes_mod_order(&txid[..16]),
        Fr::from_le_bytes_mod_order(&txid[16..]),
        Fr::from(index),
        Fr::from_le_bytes_mod_order(&tag[..16]),
        Fr::from_le_bytes_mod_order(&tag[16..]),
    ]
}

pub fn claim_commitment(secret: &[u8; 32]) -> [u8; 32] {
    Sha256::digest(secret).into()
}

/// Prefix || secret32 || raw outpoint transaction-id32 || index LE32.
/// The fixed-width suffix and circuit-fixed prefix give unambiguous parsing.
pub fn compute_tag(prefix: &[u8], secret: &[u8; 32], txid: &[u8; 32], index: u32) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(prefix);
    hash.update(secret);
    hash.update(txid);
    hash.update(index.to_le_bytes());
    hash.finalize().into()
}

#[derive(Clone)]
pub struct ClaimCircuit {
    pub constants: ClaimConstants,
    pub secret: Option<[u8; 32]>,
    pub inputs: Option<[Fr; 5]>,
}

// Allocate a canonical public scalar, then require that every bit above the
// declared integer width is zero. Never truncate/reduce a 256-bit hash into Fr.
fn public_bytes(
    cs: ConstraintSystemRef<Fr>,
    value: Option<Fr>,
    byte_width: usize,
) -> Result<Vec<UInt8<Fr>>, SynthesisError> {
    let field = FpVar::new_input(cs, || value.ok_or(SynthesisError::AssignmentMissing))?;
    let bits = field.to_bits_le()?;
    for bit in &bits[byte_width * 8..] {
        bit.enforce_equal(&Boolean::FALSE)?;
    }
    Ok(bits[..byte_width * 8]
        .chunks_exact(8)
        .map(UInt8::from_bits_le)
        .collect())
}

impl ConstraintSynthesizer<Fr> for ClaimCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        let mut encoded = Vec::with_capacity(5);
        for (i, width) in [16, 16, 4, 16, 16].into_iter().enumerate() {
            encoded.push(public_bytes(
                cs.clone(),
                self.inputs.map(|inputs| inputs[i]),
                width,
            )?);
        }
        let secret = (0..32)
            .map(|i| {
                UInt8::new_witness(cs.clone(), || {
                    self.secret
                        .map(|s| s[i])
                        .ok_or(SynthesisError::AssignmentMissing)
                })
            })
            .collect::<Result<Vec<_>, _>>()?;
        let claim = Sha256Gadget::digest(&secret)?;
        claim
            .0
            .enforce_equal(&UInt8::constant_vec(&self.constants.claim))?;

        let mut message = UInt8::constant_vec(&self.constants.context_prefix);
        message.extend(secret);
        message.extend(encoded[0].iter().cloned());
        message.extend(encoded[1].iter().cloned());
        message.extend(encoded[2].iter().cloned());
        let tag = Sha256Gadget::digest(&message)?;
        let expected_tag = [encoded[3].as_slice(), encoded[4].as_slice()].concat();
        tag.0.enforce_equal(&expected_tag)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ark_relations::gr1cs::ConstraintSystem;

    // Explicitly synthetic, non-funding test witness.
    fn sample() -> ClaimCircuit {
        let secret = [0x42; 32];
        let constants = ClaimConstants {
            context_prefix: b"KPI-A0-CIRCUIT-TEST-v1".to_vec(),
            claim: claim_commitment(&secret),
        };
        let txid = [0xff; 32];
        let tag = compute_tag(&constants.context_prefix, &secret, &txid, u32::MAX);
        ClaimCircuit {
            constants,
            secret: Some(secret),
            inputs: Some(public_inputs(&txid, u32::MAX, &tag)),
        }
    }

    fn satisfied(circuit: ClaimCircuit) -> bool {
        let cs = ConstraintSystem::<Fr>::new_ref();
        circuit.generate_constraints(cs.clone()).unwrap();
        cs.is_satisfied().unwrap()
    }

    #[test]
    fn native_sha256_matches_circuit_at_integer_boundaries() {
        assert!(satisfied(sample()));
    }

    #[test]
    fn wrong_secret_fails_even_with_recomputed_tag() {
        let mut circuit = sample();
        let secret = [0x43; 32];
        let tag = compute_tag(
            &circuit.constants.context_prefix,
            &secret,
            &[0xff; 32],
            u32::MAX,
        );
        circuit.secret = Some(secret);
        circuit.inputs = Some(public_inputs(&[0xff; 32], u32::MAX, &tag));
        assert!(!satisfied(circuit));
    }

    #[test]
    fn high_public_limb_bits_cannot_be_silently_truncated() {
        let mut circuit = sample();
        // 2^128, outside the first txid limb's range but within Fr.
        let mut overflow = [0u8; 17];
        overflow[16] = 1;
        circuit.inputs.as_mut().unwrap()[0] = Fr::from_le_bytes_mod_order(&overflow);
        assert!(!satisfied(circuit));
    }

    #[test]
    fn wrong_outpoint_index_fails_and_index_overflow_fails() {
        let mut circuit = sample();
        circuit.inputs.as_mut().unwrap()[2] = Fr::from(0u32);
        assert!(!satisfied(circuit));
        let mut circuit = sample();
        circuit.inputs.as_mut().unwrap()[2] = Fr::from(u64::from(u32::MAX) + 1);
        assert!(!satisfied(circuit));
    }
}
