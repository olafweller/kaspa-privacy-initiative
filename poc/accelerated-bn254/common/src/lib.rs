//! Thin backend adapter. Arkworks validates all submitted points and encodings;
//! substrate-bn supplies established field/group/pairing arithmetic. No new
//! arithmetic or proof format. Static parameters are validated before pinning.
use ark_bn254::{Bn254, Fq, Fr, G1Affine, G2Affine};
use ark_ff::{BigInteger, PrimeField};
use ark_groth16::{PreparedVerifyingKey, Proof};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use kpi_groth16_comparison::{self as reference, proxy};
use substrate_bn::{pairing_batch, Group, Gt, G1, G2};

fn be<F: PrimeField>(f: F) -> Vec<u8> {
    let mut v = f.into_bigint().to_bytes_be();
    assert!(v.len() <= 32);
    if v.len() < 32 {
        let mut prefix = vec![0; 32 - v.len()];
        prefix.extend(v);
        v = prefix;
    }
    v
}
fn fq(f: Fq) -> substrate_bn::Fq {
    substrate_bn::Fq::from_slice(&be(f)).expect("checked canonical base field")
}
fn fr(f: Fr) -> substrate_bn::Fr {
    // Fr::from_slice reduces its input in this library. Use strict constructor
    // instead, after extracting an already canonical Arkworks scalar.
    substrate_bn::Fr::new(substrate_bn::arith::U256::from_slice(&be(f)).unwrap())
        .expect("checked canonical scalar")
}
// These private conversions accept only already validated submitted points or
// immutable program-pinned parameters. Constructing projective coordinates does
// not itself validate a point; no untrusted unchecked decoding enters here.
fn g1(p: &G1Affine) -> G1 {
    if p.infinity {
        G1::zero()
    } else {
        G1::new(fq(p.x), fq(p.y), substrate_bn::Fq::one())
    }
}
fn g2(p: &G2Affine) -> G2 {
    if p.infinity {
        G2::zero()
    } else {
        G2::new(
            substrate_bn::Fq2::new(fq(p.x.c0), fq(p.x.c1)),
            substrate_bn::Fq2::new(fq(p.y.c0), fq(p.y.c1)),
            substrate_bn::Fq2::one(),
        )
    }
}
fn stage(name: &str) {
    #[cfg(target_os = "zkvm")]
    println!("PROFILE {name} {}", risc0_zkvm::guest::env::cycle_count());
    #[cfg(not(target_os = "zkvm"))]
    let _ = name;
}
pub struct Verifier {
    alpha: G1,
    beta: G2,
    gamma: G2,
    delta: G2,
    ic: Vec<G1>,
    pub id: [u8; 32],
}
impl Verifier {
    pub fn pinned() -> Self {
        let raw = include_bytes!("../../../groth16-comparison/pins/pvk-uncompressed.bin");
        // Exact existing PR37 static bytes; checked on host by validate-key.
        // New program identity binds them and the new arithmetic implementation.
        let pvk =
            PreparedVerifyingKey::<Bn254>::deserialize_uncompressed_unchecked(&raw[..]).unwrap();
        let vk = &pvk.vk;
        let encoded = reference::encode(vk);
        assert_eq!(
            encoded,
            include_bytes!("../../../groth16-comparison/pins/vk.bin")
        );
        Self {
            alpha: g1(&vk.alpha_g1),
            beta: g2(&vk.beta_g2),
            gamma: g2(&vk.gamma_g2),
            delta: g2(&vk.delta_g2),
            ic: vk.gamma_abc_g1.iter().map(g1).collect(),
            id: reference::key_id(&encoded),
        }
    }
    /// Program-pinned key only: caller must validate and freeze the key before
    /// building the guest. Submitted proof points always use checked decoding.
    pub fn from_validated_program_key(vk: &ark_groth16::VerifyingKey<Bn254>, id: [u8; 32]) -> Self {
        Self {
            alpha: g1(&vk.alpha_g1),
            beta: g2(&vk.beta_g2),
            gamma: g2(&vk.gamma_g2),
            delta: g2(&vk.delta_g2),
            ic: vk.gamma_abc_g1.iter().map(g1).collect(),
            id,
        }
    }
    /// Same standard Groth16 equation, for an independently bound input vector.
    pub fn verify_inputs(&self, raw: &[u8], inputs: &[Fr]) -> Result<(), &'static str> {
        use ark_ec::AffineRepr;
        if raw.len() != 128 || self.ic.len() != inputs.len() + 1 {
            return Err("encoding/arity");
        }
        let mut rest = raw;
        let proof =
            Proof::<Bn254>::deserialize_compressed(&mut rest).map_err(|_| "malformed proof")?;
        let mut canonical = vec![];
        proof
            .serialize_compressed(&mut canonical)
            .map_err(|_| "proof encoding")?;
        if !rest.is_empty()
            || canonical != raw
            || proof.a.is_zero()
            || proof.b.is_zero()
            || proof.c.is_zero()
        {
            return Err("proof encoding/identity");
        }
        stage("after_checked_proof_decode");
        let mut acc = self.ic[0];
        for (base, value) in self.ic[1..].iter().zip(inputs) {
            acc = acc + *base * fr(*value);
        }
        let a = g1(&proof.a);
        let b = g2(&proof.b);
        let c = g1(&proof.c);
        stage("after_conversion_and_public_inputs");
        let ok = pairing_batch(&[
            (a, b),
            (-self.alpha, self.beta),
            (-acc, self.gamma),
            (-c, self.delta),
        ]) == Gt::one();
        stage("after_pairing");
        if ok {
            Ok(())
        } else {
            Err("invalid proof")
        }
    }
    pub fn classify(&self, op: &[u8]) -> u8 {
        if op.len() > proxy::MAX_OPERATION || op.len() < proxy::INTENT_LEN + 4 {
            return 1;
        }
        let intent = &op[..proxy::INTENT_LEN];
        if !proxy::intent_valid(intent, self.id) {
            return 1;
        }
        let mut r = proxy::Reader(&op[proxy::INTENT_LEN..]);
        let Ok(bytes) = r.blob(reference::PROOF_BYTES) else {
            return 2;
        };
        if bytes.len() != reference::PROOF_BYTES || !r.0.is_empty() {
            return 2;
        }
        let mut rest = bytes;
        let Ok(proof) = Proof::<Bn254>::deserialize_compressed(&mut rest) else {
            return 2;
        };
        if !rest.is_empty() || reference::encode(&proof) != bytes {
            return 2;
        }
        stage("after_checked_proof_decode");
        let inputs = reference::public_inputs(&proxy::journal(intent));
        assert_eq!(self.ic.len(), inputs.len() + 1);
        let mut acc = self.ic[0];
        for (base, input) in self.ic[1..].iter().zip(inputs) {
            acc = acc + *base * fr(input);
        }
        let a = g1(&proof.a);
        let b = g2(&proof.b);
        let c = g1(&proof.c);
        stage("after_conversion_and_public_inputs");
        // Standard Groth16 product equation. Uses the candidate's pairing,
        // group/scalar operations only, no bespoke cryptographic arithmetic.
        let ok = pairing_batch(&[
            (a, b),
            (-self.alpha, self.beta),
            (-acc, self.gamma),
            (-c, self.delta),
        ]) == Gt::one();
        stage("after_pairing");
        if ok {
            0
        } else {
            3
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ark_ec::{AffineRepr, CurveGroup};
    #[test]
    fn field_order_and_group_coordinates_match_reference() {
        assert!(g1(&G1Affine::generator()) == G1::one());
        assert!(g2(&G2Affine::generator()) == G2::one());
        for value in [
            Fr::from(0u64),
            Fr::from(1u64),
            Fr::from(u64::MAX),
            -Fr::from(1u64),
        ] {
            let expected = (G1Affine::generator() * value).into_affine();
            assert!(G1::one() * fr(value) == g1(&expected));
        }
    }
}
