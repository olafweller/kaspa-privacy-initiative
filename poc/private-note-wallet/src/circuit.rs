use crate::protocol::*;
use ark_bn254::Fr;
use ark_crypto_primitives::crh::sha256::constraints::Sha256Gadget;
use ark_ff::PrimeField;
use ark_r1cs_std::{
    alloc::AllocVar, boolean::Boolean, convert::ToBitsGadget, eq::EqGadget, fields::fp::FpVar,
    select::CondSelectGadget, uint64::UInt64, uint8::UInt8,
};
use ark_relations::r1cs::{
    ConstraintSynthesizer, ConstraintSystem, ConstraintSystemRef, SynthesisError,
};

#[derive(Clone)]
pub struct Witness {
    pub secret: H,
    pub input: Note,
    pub outputs: [Note; 2],
    pub siblings: [H; DEPTH],
    pub directions: [bool; DEPTH],
}
#[derive(Clone)]
pub struct WalletCircuit {
    pub statement: Statement,
    pub witness: Witness,
}
fn digest(
    tag: &[u8],
    parts: &[&[UInt8<Fr>]],
) -> std::result::Result<Vec<UInt8<Fr>>, SynthesisError> {
    let mut b = UInt8::constant_vec(tag);
    b.extend(UInt8::constant_vec(&domain()));
    for p in parts {
        b.extend_from_slice(p)
    }
    Ok(Sha256Gadget::digest(&b)?.0)
}
fn u64_bytes(v: &UInt64<Fr>) -> std::result::Result<Vec<UInt8<Fr>>, SynthesisError> {
    v.to_bits_le()?
        .chunks(8)
        .map(|b| Ok(UInt8::from_bits_le(b)))
        .collect()
}
fn field(v: &UInt64<Fr>) -> std::result::Result<FpVar<Fr>, SynthesisError> {
    Boolean::le_bits_to_fp(&v.to_bits_le()?)
}
fn read64(bytes: &[UInt8<Fr>]) -> std::result::Result<FpVar<Fr>, SynthesisError> {
    let bits = bytes
        .iter()
        .flat_map(|b| b.to_bits_le().unwrap())
        .collect::<Vec<_>>();
    Boolean::le_bits_to_fp(&bits)
}
fn allocate_note(
    cs: ConstraintSystemRef<Fr>,
    n: &Note,
) -> std::result::Result<(Vec<UInt8<Fr>>, Vec<UInt8<Fr>>, UInt64<Fr>, Vec<UInt8<Fr>>), SynthesisError>
{
    Ok((
        UInt8::new_witness_vec(cs.clone(), &n.owner)?,
        UInt8::new_witness_vec(cs.clone(), &n.incoming)?,
        UInt64::new_witness(cs.clone(), || Ok(n.value))?,
        UInt8::new_witness_vec(cs, &n.rho)?,
    ))
}
impl WalletCircuit {
    pub fn check(&self) -> std::result::Result<(usize, bool), SynthesisError> {
        let cs = ConstraintSystem::<Fr>::new_ref();
        self.clone().generate_constraints(cs.clone())?;
        Ok((cs.num_constraints(), cs.is_satisfied()?))
    }
}
impl ConstraintSynthesizer<Fr> for WalletCircuit {
    fn generate_constraints(
        self,
        cs: ConstraintSystemRef<Fr>,
    ) -> std::result::Result<(), SynthesisError> {
        let bytes = self.statement.bytes();
        let public = UInt8::new_witness_vec(cs.clone(), &bytes)?;
        // Each public limb contains <=248 bits, strictly below Fr: no mod aliases.
        for (raw, vars) in bytes.chunks(31).zip(public.chunks(31)) {
            let p = FpVar::new_input(cs.clone(), || Ok(Fr::from_le_bytes_mod_order(raw)))?;
            let bits = vars
                .iter()
                .flat_map(|b| b.to_bits_le().unwrap())
                .collect::<Vec<_>>();
            Boolean::le_bits_to_fp(&bits)?.enforce_equal(&p)?;
        }
        public[0].enforce_equal(&UInt8::constant(1))?;
        public[2..34].enforce_equal(&UInt8::constant_vec(&domain()))?;
        let credit = public[1].is_eq(&UInt8::constant(CREDIT))?;
        let transfer = public[1].is_eq(&UInt8::constant(TRANSFER))?;
        let exit = public[1].is_eq(&UInt8::constant(EXIT))?;
        let recover = public[1].is_eq(&UInt8::constant(RECOVER))?;
        let spend = &transfer | &exit;
        let deposit = &credit | &recover;
        (&spend | &deposit).enforce_equal(&Boolean::TRUE)?;
        let z = UInt8::constant_vec(&[0; 32]);
        let secret = UInt8::new_witness_vec(cs.clone(), &self.witness.secret)?;
        let (input_owner, input_view, input_value, input_rho) =
            allocate_note(cs.clone(), &self.witness.input)?;
        let authority = digest(OWNER_TAG, &[&secret, &input_view])?;
        input_owner.enforce_equal(&authority)?;
        input_value
            .is_eq(&UInt64::constant(0))?
            .enforce_equal(&!&spend)?;
        let input_cm = digest(
            NOTE_TAG,
            &[
                &input_owner,
                &input_view,
                &u64_bytes(&input_value)?,
                &input_rho,
            ],
        )?;
        let mut root = input_cm.clone();
        for level in 0..DEPTH {
            let sib = UInt8::new_witness_vec(cs.clone(), &self.witness.siblings[level])?;
            let right = Boolean::new_witness(cs.clone(), || Ok(self.witness.directions[level]))?;
            let left = root
                .iter()
                .zip(&sib)
                .map(|(a, b)| UInt8::conditionally_select(&right, b, a))
                .collect::<std::result::Result<Vec<_>, _>>()?;
            let r = root
                .iter()
                .zip(&sib)
                .map(|(a, b)| UInt8::conditionally_select(&right, a, b))
                .collect::<std::result::Result<Vec<_>, _>>()?;
            root = digest(NODE_TAG, &[&left, &r])?;
        }
        root.as_slice()
            .conditional_enforce_equal(&public[66..98], &spend)?;
        // RFC2104 HMAC with a 32-byte key: ipad/opad are the standard 64-byte blocks.
        let mut padded = secret.clone();
        padded.extend(UInt8::constant_vec(&[0; 32]));
        let ipad = padded
            .iter()
            .map(|b| b ^ UInt8::constant(0x36))
            .collect::<Vec<_>>();
        let opad = padded
            .iter()
            .map(|b| b ^ UInt8::constant(0x5c))
            .collect::<Vec<_>>();
        let mut inner = ipad;
        inner.extend(UInt8::constant_vec(NF_TAG));
        inner.extend(UInt8::constant_vec(&domain()));
        inner.extend(input_cm);
        let mut outer = opad;
        outer.extend(Sha256Gadget::digest(&inner)?.0);
        let nf = Sha256Gadget::digest(&outer)?.0;
        nf.as_slice()
            .conditional_enforce_equal(&public[98..130], &spend)?;
        public[98..130].conditional_enforce_equal(&z, &!&spend)?;
        let flags = [&credit | &transfer, transfer.clone()];
        let mut values = vec![];
        for (i, note) in self.witness.outputs.iter().enumerate() {
            let (owner, view, value, rho) = allocate_note(cs.clone(), note)?;
            value
                .is_eq(&UInt64::constant(0))?
                .enforce_equal(&!&flags[i])?;
            let cm = digest(NOTE_TAG, &[&owner, &view, &u64_bytes(&value)?, &rho])?;
            cm.as_slice()
                .conditional_enforce_equal(&public[130 + 32 * i..162 + 32 * i], &flags[i])?;
            public[130 + 32 * i..162 + 32 * i].conditional_enforce_equal(&z, &!&flags[i])?;
            public[194 + 32 * i..226 + 32 * i].conditional_enforce_equal(&z, &!&flags[i])?;
            if i == 0 {
                owner
                    .as_slice()
                    .conditional_enforce_equal(&public[290..322], &credit)?;
                view.conditional_enforce_equal(&input_view, &credit)?;
            }
            values.push(field(&value)?);
        }
        public[130..162]
            .is_eq(&public[162..194])?
            .conditional_enforce_equal(&Boolean::FALSE, &transfer)?;
        public[258..290].conditional_enforce_equal(&z, &!&deposit)?;
        public[290..322].conditional_enforce_equal(&z, &!&deposit)?;
        public[322..330].conditional_enforce_equal(&UInt8::constant_vec(&[0; 8]), &!&deposit)?;
        authority
            .as_slice()
            .conditional_enforce_equal(&public[290..322], &deposit)?;
        public[258..290]
            .is_eq(&z)?
            .conditional_enforce_equal(&Boolean::FALSE, &deposit)?;
        public[322..330]
            .is_eq(&UInt8::constant_vec(&[0; 8]))?
            .conditional_enforce_equal(&Boolean::FALSE, &deposit)?;
        let withdrawing = &exit | &recover;
        public[330..362].conditional_enforce_equal(&z, &!&withdrawing)?;
        public[362..370]
            .conditional_enforce_equal(&UInt8::constant_vec(&[0; 8]), &!&withdrawing)?;
        public[330..362]
            .is_eq(&z)?
            .conditional_enforce_equal(&Boolean::FALSE, &withdrawing)?;
        public[362..370]
            .is_eq(&UInt8::constant_vec(&[0; 8]))?
            .conditional_enforce_equal(&Boolean::FALSE, &withdrawing)?;
        public[370..410].enforce_equal(&UInt8::constant_vec(&[0; 40]))?; // explicit zero app fees in v1
                                                                         // Five u64 limbs sum to <5*2^64 << Fr. Equality cannot hide overflow.
        (field(&input_value)? + read64(&public[322..330])?).enforce_equal(
            &(values[0].clone()
                + values[1].clone()
                + read64(&public[362..370])?
                + read64(&public[402..410])?),
        )?;
        Ok(())
    }
}
