//! Same SHA-256/u64/preimage and full-intent relation as the PR36 wallet guest.
use super::{proxy, public_inputs};
use ark_bn254::Fr;
use ark_crypto_primitives::crh::sha256::constraints::Sha256Gadget;
use ark_r1cs_std::{
    alloc::AllocVar,
    boolean::Boolean,
    convert::{ToBitsGadget, ToBytesGadget},
    eq::EqGadget,
    uint64::UInt64,
    uint8::UInt8,
};
use ark_relations::r1cs::{
    ConstraintSynthesizer, ConstraintSystem, ConstraintSystemRef, SynthesisError,
};

#[derive(Clone)]
pub struct WalletCircuit {
    pub input: proxy::WalletInput,
    pub journal: Vec<u8>,
}
impl WalletCircuit {
    pub fn new(input: proxy::WalletInput) -> Self {
        Self {
            journal: proxy::journal(&input.intent),
            input,
        }
    }
    pub fn inputs(&self) -> Vec<Fr> {
        public_inputs(&self.journal)
    }
    pub fn check(&self) -> Result<(usize, bool), SynthesisError> {
        let cs = ConstraintSystem::<Fr>::new_ref();
        self.clone().generate_constraints(cs.clone())?;
        Ok((cs.num_constraints(), cs.is_satisfied()?))
    }
}
impl ConstraintSynthesizer<Fr> for WalletCircuit {
    fn generate_constraints(self, cs: ConstraintSystemRef<Fr>) -> Result<(), SynthesisError> {
        if self.input.intent.len() != proxy::INTENT_LEN || self.journal.len() != 96 {
            return Err(SynthesisError::Unsatisfiable);
        }
        let intent = UInt8::new_witness_vec(cs.clone(), &self.input.intent)?;
        let secret = UInt8::new_witness_vec(cs.clone(), &self.input.secret)?;
        let public = UInt8::new_input_vec(cs.clone(), &self.journal)?;
        let values = self
            .input
            .values
            .into_iter()
            .map(|n| UInt64::new_witness(cs.clone(), || Ok(n)))
            .collect::<Result<Vec<_>, _>>()?;
        values[0]
            .is_eq(&UInt64::constant(0))?
            .enforce_equal(&Boolean::FALSE)?;
        // Each limb is 64-bit. Their sum is below 3*2^64, far below Fr modulus;
        // equality with the 64-bit input enforces no integer carry/field wrap.
        let fields = values
            .iter()
            .map(|v| Boolean::le_bits_to_fp(&v.to_bits_le()?))
            .collect::<Result<Vec<_>, SynthesisError>>()?;
        fields[0].enforce_equal(&(&fields[1] + &fields[2] + &fields[3]))?;
        let bytes = values
            .iter()
            .map(|v| v.to_bytes_le())
            .collect::<Result<Vec<_>, _>>()?;
        bytes[1].as_slice().enforce_equal(&intent[202..210])?;
        bytes[3].as_slice().enforce_equal(&intent[210..218])?;
        Sha256Gadget::digest(&secret)?
            .0
            .as_slice()
            .enforce_equal(&intent[138..170])?;
        let all_bytes: Vec<_> = bytes.into_iter().flatten().collect();
        Sha256Gadget::digest(&all_bytes)?
            .0
            .as_slice()
            .enforce_equal(&intent[170..202])?;
        let mut full = UInt8::constant_vec(b"KPI-local-intent-v1");
        full.extend(intent.iter().cloned());
        Sha256Gadget::digest(&full)?
            .0
            .as_slice()
            .enforce_equal(&public[..32])?;
        intent[138..202].enforce_equal(&public[32..96])?;
        Ok(())
    }
}
