//! A1 reuses A0's two SHA256 relations with branch-specific fixed contexts.
//!
//! Reuse pins: Arkworks 0.6.0; SHA256 gadget at
//! ba00127bf673d93d73a3e8bf969cb9eeced20d12, inspected at
//! crypto-primitives/src/crh/sha256/constraints.rs. The gadget implements the
//! established SHA256 byte/padding relation. No mature-protocol note/nullifier
//! code is imported: this remains one public claim consumed by native outpoints.
//! Fixed monetary consistency belongs to the model/checker BEFORE setup; this
//! circuit does not prove variable monetary arithmetic, output script execution,
//! chain acceptance, or availability. An opaque VK cannot attest its own origin.

use std::collections::BTreeMap;
use std::ops::Range;

use ark_bn254::Fr;
use ark_crypto_primitives::crh::sha256::constraints::Sha256Gadget;
use ark_ff::{PrimeField, Zero};
use ark_r1cs_std::{
    alloc::AllocVar, boolean::Boolean, convert::ToBitsGadget, eq::EqGadget, fields::fp::FpVar,
    uint8::UInt8,
};
use ark_relations::gr1cs::{
    ConstraintSynthesizer, ConstraintSystem, ConstraintSystemRef, OptimizationGoal,
    R1CS_PREDICATE_LABEL, SynthesisError, SynthesisMode,
};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize, SerializationError};
use sha2::{Digest, Sha256};

pub const RELATION_ID: &str = "sha256-preimage-and-outpoint-tag/v1";
pub const R1CS_MAGIC: &[u8] = b"KPI-A1/R1CS/v1\0";
pub const PUBLIC_NAMES: [&str; 5] = [
    "txid_lo128",
    "txid_hi128",
    "index_u32",
    "tag_lo128",
    "tag_hi128",
];
pub const PUBLIC_BITS: [usize; 5] = [128, 128, 32, 128, 128];

#[derive(Clone)]
pub struct ClaimConstants {
    pub context_prefix: Vec<u8>,
    pub claim: [u8; 32],
}

#[derive(Clone)]
pub struct ClaimCircuit {
    pub constants: ClaimConstants,
    pub secret: Option<[u8; 32]>,
    pub inputs: Option<[Fr; 5]>,
}

/// Fr limbs are below the modulus by construction; no complete digest reduction.
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

pub fn compute_tag(prefix: &[u8], secret: &[u8; 32], txid: &[u8; 32], index: u32) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(prefix);
    hash.update(secret);
    hash.update(txid);
    hash.update(index.to_le_bytes());
    hash.finalize().into()
}

/// Validated compressed parsing with explicit trailing-byte rejection. Native
/// proof/VK parsing is also required; this helper is not a substitute for it.
pub fn parse_compressed<T: CanonicalDeserialize>(bytes: &[u8]) -> Result<T, SerializationError> {
    let mut remaining = bytes;
    let value = T::deserialize_compressed(&mut remaining)?;
    if !remaining.is_empty() {
        return Err(SerializationError::InvalidData);
    }
    Ok(value)
}

pub fn compressed<T: CanonicalSerialize>(value: &T) -> Result<Vec<u8>, SerializationError> {
    let mut bytes = Vec::new();
    value.serialize_compressed(&mut bytes)?;
    Ok(bytes)
}

pub fn public_scalar_bytes(inputs: &[Fr; 5]) -> [[u8; 32]; 5] {
    inputs.map(|value| {
        let bytes = compressed(&value).expect("serialization of a canonical field cannot fail");
        bytes
            .try_into()
            .expect("BN254 Fr canonical encoding is 32 bytes")
    })
}

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
        self.generate_with_layout(cs).map(|_| ())
    }
}

/// Half-open normalized R1CS row regions from reviewed source phases. Public
/// inputs remain variables 1..5; no extra public variables are allocated.
/// Every context byte offset [0,context_bytes) is a constant in the tag region.
/// Constant propagation can fold full SHA blocks; this is deliberately not a
/// fictitious one-constraint-per-byte map.
#[derive(Debug, Clone)]
pub struct RelationLayout {
    pub context_bytes: usize,
    pub public_range_constraints: [Range<usize>; 5],
    pub secret_byte_constraints: Range<usize>,
    pub claim_hash_constraints: Range<usize>,
    pub claim_equality_constraints: Range<usize>,
    pub context_tag_hash_constraints: Range<usize>,
    pub tag_equality_constraints: Range<usize>,
}

impl ClaimCircuit {
    fn generate_with_layout(
        self,
        cs: ConstraintSystemRef<Fr>,
    ) -> Result<RelationLayout, SynthesisError> {
        let mut encoded = Vec::with_capacity(5);
        let mut public_ranges: [Range<usize>; 5] = std::array::from_fn(|_| 0..0);
        for (i, width) in [16, 16, 4, 16, 16].into_iter().enumerate() {
            let start = cs.num_constraints();
            encoded.push(public_bytes(
                cs.clone(),
                self.inputs.map(|inputs| inputs[i]),
                width,
            )?);
            public_ranges[i] = start..cs.num_constraints();
        }
        let secret_start = cs.num_constraints();
        let secret = (0..32)
            .map(|i| {
                UInt8::new_witness(cs.clone(), || {
                    self.secret
                        .map(|s| s[i])
                        .ok_or(SynthesisError::AssignmentMissing)
                })
            })
            .collect::<Result<Vec<_>, _>>()?;
        let claim_start = cs.num_constraints();
        let claim = Sha256Gadget::digest(&secret)?;
        let claim_equality_start = cs.num_constraints();
        claim
            .0
            .enforce_equal(&UInt8::constant_vec(&self.constants.claim))?;
        let context_start = cs.num_constraints();

        // UInt8::constant_vec fixes every context byte, including any full
        // SHA256 blocks folded by constant propagation. They are not witnesses.
        let mut message = UInt8::constant_vec(&self.constants.context_prefix);
        message.extend(secret);
        message.extend(encoded[0].iter().cloned());
        message.extend(encoded[1].iter().cloned());
        message.extend(encoded[2].iter().cloned());
        let tag = Sha256Gadget::digest(&message)?;
        let tag_equality_start = cs.num_constraints();
        let expected_tag = [encoded[3].as_slice(), encoded[4].as_slice()].concat();
        tag.0.enforce_equal(&expected_tag)?;
        Ok(RelationLayout {
            context_bytes: self.constants.context_prefix.len(),
            public_range_constraints: public_ranges,
            secret_byte_constraints: secret_start..claim_start,
            claim_hash_constraints: claim_start..claim_equality_start,
            claim_equality_constraints: claim_equality_start..context_start,
            context_tag_hash_constraints: context_start..tag_equality_start,
            tag_equality_constraints: tag_equality_start..cs.num_constraints(),
        })
    }
}

pub fn inspect_layout(constants: &ClaimConstants) -> Result<RelationLayout, SynthesisError> {
    let cs = ConstraintSystem::<Fr>::new_ref();
    cs.set_optimization_goal(OptimizationGoal::Constraints);
    cs.set_mode(SynthesisMode::Setup);
    let layout = ClaimCircuit {
        constants: constants.clone(),
        secret: None,
        inputs: None,
    }
    .generate_with_layout(cs.clone())?;
    cs.finalize();
    if layout.tag_equality_constraints.end != cs.num_constraints() {
        return Err(SynthesisError::Unsatisfiable);
    }
    Ok(layout)
}

/// Exact reviewed setup synthesis settings from Arkworks Groth16 generator.rs:
/// OptimizationGoal::Constraints, Setup, generate_constraints, finalize.
/// No setup randomness, witness assignments, PK or VK are produced here.
pub fn normalized_r1cs(constants: &ClaimConstants) -> Result<NormalizedR1cs, SynthesisError> {
    let cs = ConstraintSystem::<Fr>::new_ref();
    cs.set_optimization_goal(OptimizationGoal::Constraints);
    cs.set_mode(SynthesisMode::Setup);
    ClaimCircuit {
        constants: constants.clone(),
        secret: None,
        inputs: None,
    }
    .generate_constraints(cs.clone())?;
    cs.finalize();
    normalized_from_cs(&cs)
}

pub struct NormalizedR1cs {
    pub bytes: Vec<u8>,
    pub sha256: [u8; 32],
    /// Excludes constant-one variable 0.
    pub public_count: u32,
    /// Includes constant-one variable 0, all five public inputs and witnesses.
    pub variable_count: u64,
    pub constraint_count: u64,
}

/// Useful for comparing an assigned synthesis to the setup synthesis without
/// ever embedding secret assignments in the public artifact.
pub fn normalized_from_cs(cs: &ConstraintSystemRef<Fr>) -> Result<NormalizedR1cs, SynthesisError> {
    let matrices = cs.to_matrices()?;
    if cs.num_instance_variables() != 6 || matrices.len() != 1 {
        return Err(SynthesisError::Unsatisfiable);
    }
    let abc = matrices
        .get(R1CS_PREDICATE_LABEL)
        .ok_or(SynthesisError::Unsatisfiable)?;
    let constraints = cs.num_constraints();
    if abc.len() != 3 || abc.iter().any(|matrix| matrix.len() != constraints) {
        return Err(SynthesisError::Unsatisfiable);
    }
    let variables = cs
        .num_instance_variables()
        .checked_add(cs.num_witness_variables())
        .ok_or(SynthesisError::Unsatisfiable)?;
    let variable_count = u64::try_from(variables).map_err(|_| SynthesisError::Unsatisfiable)?;
    let constraint_count = u64::try_from(constraints).map_err(|_| SynthesisError::Unsatisfiable)?;
    let mut bytes = R1CS_MAGIC.to_vec();
    bytes.extend(5u32.to_le_bytes());
    bytes.extend(variable_count.to_le_bytes());
    bytes.extend(constraint_count.to_le_bytes());
    for row in 0..constraints {
        for matrix in abc {
            encode_row(&mut bytes, &matrix[row], variables)?;
        }
    }
    Ok(NormalizedR1cs {
        sha256: Sha256::digest(&bytes).into(),
        bytes,
        public_count: 5,
        variable_count,
        constraint_count,
    })
}

fn encode_row(
    bytes: &mut Vec<u8>,
    row: &[(Fr, usize)],
    variables: usize,
) -> Result<(), SynthesisError> {
    let mut terms = BTreeMap::<usize, Fr>::new();
    for &(coefficient, index) in row {
        if index >= variables {
            return Err(SynthesisError::Unsatisfiable);
        }
        *terms.entry(index).or_insert(Fr::zero()) += coefficient;
    }
    terms.retain(|_, coefficient| !coefficient.is_zero());
    bytes.extend(
        u64::try_from(terms.len())
            .map_err(|_| SynthesisError::Unsatisfiable)?
            .to_le_bytes(),
    );
    for (index, coefficient) in terms {
        bytes.extend(
            u64::try_from(index)
                .map_err(|_| SynthesisError::Unsatisfiable)?
                .to_le_bytes(),
        );
        let coefficient_bytes =
            compressed(&coefficient).map_err(|_| SynthesisError::Unsatisfiable)?;
        if coefficient_bytes.len() != 32 {
            return Err(SynthesisError::Unsatisfiable);
        }
        bytes.extend(coefficient_bytes);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // Explicitly public synthetic witness; cannot control experimental funds.
    fn sample() -> ClaimCircuit {
        let secret = [0x42; 32];
        let constants = ClaimConstants {
            context_prefix: b"KPI-A1-CIRCUIT-TEST-v1".to_vec(),
            claim: claim_commitment(&secret),
        };
        let tag = compute_tag(&constants.context_prefix, &secret, &[0xff; 32], u32::MAX);
        ClaimCircuit {
            constants,
            secret: Some(secret),
            inputs: Some(public_inputs(&[0xff; 32], u32::MAX, &tag)),
        }
    }

    fn assigned(circuit: ClaimCircuit) -> ConstraintSystemRef<Fr> {
        let cs = ConstraintSystem::<Fr>::new_ref();
        cs.set_optimization_goal(OptimizationGoal::Constraints);
        circuit.generate_constraints(cs.clone()).unwrap();
        cs.finalize();
        cs
    }

    // Literal independently calculated G0 bytes from ADR-0003; deliberately no
    // import of the A1 production codec and no locally generated expectations.
    fn unhex(input: &str) -> Vec<u8> {
        assert!(input.len().is_multiple_of(2));
        (0..input.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&input[i..i + 2], 16).unwrap())
            .collect()
    }

    fn golden_continue() -> ClaimCircuit {
        let prefix = unhex(concat!(
            "4b50492d41312f544e31302f66696e6974652f763100",
            "f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370",
            "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f0000",
            "72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084",
            "00512e3f0000000000ca9a3b000000000087930300000000002d310100000000",
            "00a02526000000000046c32300000000005a62020000000002",
            "00a0252600000000250000000000aa20",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa8700",
            "0084d7170000000024000000000020",
            "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac00",
        ));
        assert_eq!(prefix.len(), 276);
        let secret = std::array::from_fn(|i| 0x20 + u8::try_from(i).unwrap());
        let txid = std::array::from_fn(|i| 0x40 + u8::try_from(i).unwrap());
        let claim: [u8; 32] =
            unhex("72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084")
                .try_into()
                .unwrap();
        let tag: [u8; 32] =
            unhex("a552c701f0f1a1c25622cb95ea966c8c4331dae1d419f006d37bac1a4e5894df")
                .try_into()
                .unwrap();
        assert_eq!(claim_commitment(&secret), claim);
        assert_eq!(compute_tag(&prefix, &secret, &txid, 7), tag);
        ClaimCircuit {
            constants: ClaimConstants {
                context_prefix: prefix,
                claim,
            },
            secret: Some(secret),
            inputs: Some(public_inputs(&txid, 7, &tag)),
        }
    }

    #[test]
    fn adr_golden_positive_and_original_relation_negative_vectors() {
        let original = golden_continue();
        assert!(assigned(original.clone()).is_satisfied().unwrap());
        let txid = std::array::from_fn(|i| 0x40 + u8::try_from(i).unwrap());
        for (offset, replacement, expected) in [
            (
                87,
                2,
                "ebe7a11139890da093c561b8eacb29aa5afcbc8a64a0845fa6bddc39f0280b84",
            ),
            (
                86,
                1,
                "05299d3cbc51595cca3b85309546a7382598ff058f43c1120c19daaf68fa8640",
            ),
            (
                190,
                1,
                "0fab892f5af61ff60b33adc119772d9d3b279952386d1c306088d7d340673c8d",
            ),
            (
                226,
                1,
                "910bfe668bef282e6aaa02064e1d2c81de1882e0c9a22e2a13b19e8026c8b11a",
            ),
            (
                242,
                0x78,
                "729a917d85a7946600734e1ea684b695f27ce754f12f3b712c9a8cc14bac9557",
            ),
        ] {
            let mut changed_prefix = original.constants.context_prefix.clone();
            changed_prefix[offset] = replacement;
            let reference_tag: [u8; 32] = unhex(expected).try_into().unwrap();
            assert_eq!(
                compute_tag(&changed_prefix, &original.secret.unwrap(), &txid, 7),
                reference_tag
            );
            let mut changed = original.clone();
            changed.inputs = Some(public_inputs(&txid, 7, &reference_tag));
            assert!(
                !assigned(changed).is_satisfied().unwrap(),
                "G0 negative offset {offset}"
            );
        }
        // Every fixed field, including bytes in fully constant SHA blocks and
        // both ordered output records, affects the original relation. These
        // additional tags are native SHA calculations, not independent G0 goldens.
        for offset in [
            0, 22, 54, 88, 120, 128, 136, 144, 152, 160, 168, 176, 177, 185, 189, 227, 235, 239,
            275,
        ] {
            let mut changed_prefix = original.constants.context_prefix.clone();
            changed_prefix[offset] ^= 1;
            let reference_tag = compute_tag(&changed_prefix, &original.secret.unwrap(), &txid, 7);
            let mut changed = original.clone();
            changed.inputs = Some(public_inputs(&txid, 7, &reference_tag));
            assert!(
                !assigned(changed).is_satisfied().unwrap(),
                "field offset {offset}"
            );
        }
    }

    #[test]
    fn original_constants_reject_changed_context_tag_without_foreign_setup() {
        let original = sample();
        assert!(assigned(original.clone()).is_satisfied().unwrap());
        for offset in 0..original.constants.context_prefix.len() {
            let mut foreign_prefix = original.constants.context_prefix.clone();
            foreign_prefix[offset] ^= 1;
            let mut changed = original.clone();
            let tag = compute_tag(
                &foreign_prefix,
                &changed.secret.unwrap(),
                &[0xff; 32],
                u32::MAX,
            );
            changed.inputs = Some(public_inputs(&[0xff; 32], u32::MAX, &tag));
            assert!(
                !assigned(changed).is_satisfied().unwrap(),
                "context byte {offset}"
            );
        }
    }

    #[test]
    fn secret_and_outpoint_are_bound() {
        let original = sample();
        let mut changed = original.clone();
        let secret = [0x43; 32];
        let tag = compute_tag(
            &changed.constants.context_prefix,
            &secret,
            &[0xff; 32],
            u32::MAX,
        );
        changed.secret = Some(secret);
        changed.inputs = Some(public_inputs(&[0xff; 32], u32::MAX, &tag));
        assert!(!assigned(changed).is_satisfied().unwrap());
        for offset in [0, 1, 2] {
            let mut changed = original.clone();
            changed.inputs.as_mut().unwrap()[offset] = Fr::zero();
            assert!(!assigned(changed).is_satisfied().unwrap());
        }
    }

    #[test]
    fn every_public_width_is_enforced_without_truncation() {
        for (index, bits) in PUBLIC_BITS.into_iter().enumerate() {
            let mut circuit = sample();
            let mut overflow = vec![0u8; bits / 8 + 1];
            overflow[bits / 8] = 1;
            circuit.inputs.as_mut().unwrap()[index] = Fr::from_le_bytes_mod_order(&overflow);
            assert!(!assigned(circuit).is_satisfied().unwrap());
        }
    }

    #[test]
    fn zero_and_maximum_outpoint_integer_boundaries_satisfy() {
        for (txid, index) in [([0; 32], 0), ([0xff; 32], u32::MAX)] {
            let mut circuit = sample();
            let tag = compute_tag(
                &circuit.constants.context_prefix,
                &circuit.secret.unwrap(),
                &txid,
                index,
            );
            circuit.inputs = Some(public_inputs(&txid, index, &tag));
            assert!(assigned(circuit).is_satisfied().unwrap());
        }
    }

    #[test]
    fn canonical_scalar_parsing_rejects_modulus_wrong_sizes_and_trailing_data() {
        let bytes = compressed(&Fr::from(7u32)).unwrap();
        assert_eq!(parse_compressed::<Fr>(&bytes).unwrap(), Fr::from(7u32));
        assert!(parse_compressed::<Fr>(&bytes[..31]).is_err());
        let mut extra = bytes.clone();
        extra.push(0);
        assert!(parse_compressed::<Fr>(&extra).is_err());
        use ark_ff::BigInteger;
        assert!(parse_compressed::<Fr>(&Fr::MODULUS.to_bytes_le()).is_err());
    }

    #[test]
    fn normalized_row_sorts_sums_duplicates_and_omits_zeros() {
        let mut bytes = Vec::new();
        encode_row(
            &mut bytes,
            &[
                (Fr::from(3), 4),
                (Fr::from(7), 0),
                (-Fr::from(3), 4),
                (Fr::from(2), 2),
            ],
            5,
        )
        .unwrap();
        let mut expected = 2u64.to_le_bytes().to_vec();
        expected.extend(0u64.to_le_bytes());
        expected.extend(compressed(&Fr::from(7)).unwrap());
        expected.extend(2u64.to_le_bytes());
        expected.extend(compressed(&Fr::from(2)).unwrap());
        assert_eq!(bytes, expected);
        assert!(encode_row(&mut Vec::new(), &[(Fr::from(1), 5)], 5).is_err());
    }

    #[test]
    fn setup_and_assigned_normalized_exports_agree_and_change_with_constants() {
        let circuit = sample();
        let setup = normalized_r1cs(&circuit.constants).unwrap();
        let proving = normalized_from_cs(&assigned(circuit.clone())).unwrap();
        assert_eq!(setup.bytes, proving.bytes);
        assert_eq!(setup.public_count, 5);
        assert_eq!(&setup.bytes[..R1CS_MAGIC.len()], R1CS_MAGIC);
        let layout = inspect_layout(&circuit.constants).unwrap();
        assert_eq!(layout.context_bytes, circuit.constants.context_prefix.len());
        assert_eq!(layout.public_range_constraints[0].start, 0);
        assert_eq!(
            layout.tag_equality_constraints.end as u64,
            setup.constraint_count
        );
        assert_eq!(layout.secret_byte_constraints.len(), 256);
        let mut changed = circuit.constants.clone();
        changed.context_prefix[0] ^= 1;
        assert_ne!(setup.sha256, normalized_r1cs(&changed).unwrap().sha256);
        let mut changed = circuit.constants;
        changed.claim[0] ^= 1;
        assert_ne!(proving.sha256, normalized_r1cs(&changed).unwrap().sha256);
    }
}
