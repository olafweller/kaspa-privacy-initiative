use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use kpi_private_note_chain::{
    self as chain,
    wallet::{protocol::*, ProofVerifier},
    AcceleratedVerifier, Input, Output,
};
use std::{fs, path::PathBuf};
fn public() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../evidence/public")
}
fn verifier() -> AcceleratedVerifier {
    let raw = fs::read(public().join("vk.bin")).unwrap();
    let id = fs::read(public().join("vk-id.bin"))
        .unwrap()
        .try_into()
        .unwrap();
    assert_eq!(
        hex(id),
        "d3c179aae5c2c6c013b1de1da5ad4412e4b2c8bae7288c0b9d85e0c986b5a3ec"
    );
    AcceleratedVerifier::checked(&raw, id).unwrap()
}
fn hex(id: H) -> String {
    id.iter().map(|b| format!("{b:02x}")).collect()
}
#[test]
fn real_proof_state_native_output_and_replay_cases() {
    let v = verifier();
    let preparation: serde_json::Value =
        serde_json::from_slice(&fs::read(public().join("preparation.json")).unwrap()).unwrap();
    assert_eq!(
        preparation["nativeEndpointContinuityAcrossFourBatches"],
        true
    );
    let cases = preparation["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 18);
    for case in cases {
        let name = case["case"].as_str().unwrap();
        let input: Input =
            bincode::deserialize(&fs::read(public().join(format!("{name}.input.bin"))).unwrap())
                .unwrap();
        let expected: Output =
            bincode::deserialize(&fs::read(public().join(format!("{name}.expected.bin"))).unwrap())
                .unwrap();
        let actual = chain::execute(&input, &v);
        assert_eq!(
            bincode::serialize(&actual).unwrap(),
            bincode::serialize(&expected).unwrap(),
            "{name}"
        );
        assert_eq!(actual.aggregate_journal.len(), 352);
        for e in actual.events {
            if e.verdict != 0 {
                assert_eq!(e.before, e.after, "atomic rejection {name}");
            }
        }
    }
}
#[test]
fn all_fourteen_field_inputs_and_real_proof_mutations() {
    let v = verifier();
    let raw = fs::read(public().join("vk.bin")).unwrap();
    let vk = ark_groth16::VerifyingKey::<ark_bn254::Bn254>::deserialize_compressed(raw.as_slice())
        .unwrap();
    let reference = ark_groth16::prepare_verifying_key(&vk);
    let backend = kpi_accelerated_bn254::Verifier::from_validated_program_key(&vk, v.id());
    let mut op: Operation =
        serde_json::from_slice(&fs::read(public().join("transfer.json")).unwrap()).unwrap();
    v.verify(&op).unwrap();
    let proof = ark_groth16::Proof::<ark_bn254::Bn254>::deserialize_compressed(op.proof.as_slice())
        .unwrap();
    let fields = op.statement.inputs();
    assert_eq!(fields.len(), 14);
    for i in 0..14 {
        let mut f = fields.clone();
        f[i] += ark_bn254::Fr::from(1u64);
        assert!(
            !ark_groth16::Groth16::<ark_bn254::Bn254>::verify_proof(&reference, &proof, &f)
                .unwrap()
        );
        assert_eq!(backend.verify_inputs(&op.proof, &f), Err("invalid proof"));
    }
    op.deliveries[0].ciphertext[50] ^= 1;
    op.statement.delivery[0] = hash(&op.deliveries[0].ciphertext);
    assert_eq!(v.verify(&op), Err("invalid proof".into()));
    let mut exit: Operation =
        serde_json::from_slice(&fs::read(public().join("exit.json")).unwrap()).unwrap();
    exit.statement.exit_destination = hash(b"other nonzero destination");
    assert_eq!(v.verify(&exit), Err("invalid proof".into()));
    let mut bad = proof.clone();
    bad.c = -bad.c;
    op.proof.clear();
    bad.serialize_compressed(&mut op.proof).unwrap();
    op.statement.delivery[0] = hash(&op.deliveries[0].ciphertext);
    assert!(v.verify(&op).is_err());
    // Native checked parsing rejects an on-curve point outside the G2 subgroup.
    let point = (0u64..100)
        .find_map(|n| {
            ark_bn254::G2Affine::get_point_from_x_unchecked(
                ark_bn254::Fq2::new(ark_bn254::Fq::from(n), ark_bn254::Fq::from(1u64)),
                false,
            )
            .filter(|p| !p.is_in_correct_subgroup_assuming_on_curve())
        })
        .unwrap();
    let mut bad = proof.clone();
    bad.b = point;
    let mut encoded = vec![];
    bad.serialize_compressed(&mut encoded).unwrap();
    assert_eq!(
        backend.verify_inputs(&encoded, &fields),
        Err("malformed proof")
    );
    let mut bad = proof;
    bad.a = ark_bn254::G1Affine::identity();
    encoded.clear();
    bad.serialize_compressed(&mut encoded).unwrap();
    assert_eq!(
        backend.verify_inputs(&encoded, &fields),
        Err("proof encoding/identity")
    );
}
#[test]
fn prior_state_and_config_preimages_cannot_be_swapped() {
    let v = verifier();
    let i: Input =
        bincode::deserialize(&fs::read(public().join("deposit.input.bin")).unwrap()).unwrap();
    let mut changed = i.clone();
    changed.state.ledger.batch = 1;
    assert!(
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| chain::execute(
            &changed, &v
        )))
        .is_err()
    );
    let mut changed = i;
    changed.state.covenant[0] ^= 1;
    changed.lane.covenant = changed.state.covenant;
    assert!(
        std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| chain::execute(
            &changed, &v
        )))
        .is_err()
    );
}
#[test]
fn target_domain_is_derived_from_explicit_network_pool_descriptor() {
    let d: serde_json::Value = serde_json::from_slice(
        &fs::read(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../domain.json")).unwrap(),
    )
    .unwrap();
    fn bytes(s: &str) -> Vec<u8> {
        (0..s.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
            .collect()
    }
    let mut b = b"KPI/TN10/private-note-rehearsal-v1\0".to_vec();
    for f in ["genesis", "lane", "poolNonce"] {
        b.extend(bytes(d[f].as_str().unwrap()));
    }
    assert_eq!(hash(&b), domain());
    assert_eq!(d["economicDomain"], hex(domain()));
    assert_eq!(bytes(d["lane"].as_str().unwrap()), chain::LANE);
    assert_ne!(
        domain(),
        hash(b"KPI/LOCAL-NO-FUNDING/native-KAS/private-note-experiment-1")
    );
}
