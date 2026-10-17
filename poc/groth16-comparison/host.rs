//! Bounded specialized wallet circuit, not receipt compression or a privacy protocol.
use super::*;
use ark_bn254::Bn254;
use ark_groth16::{
    prepare_verifying_key, Groth16, PreparedVerifyingKey, Proof, ProvingKey, VerifyingKey,
};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use kpi_groth16_comparison::{self as g16, circuit::WalletCircuit, proxy};
use std::io::{BufReader, BufWriter};

fn load_pvk(setup: &Path) -> Result<(PreparedVerifyingKey<Bn254>, [u8; 32])> {
    let vk_bytes = fs::read(setup.join("vk.bin"))?;
    let vk = VerifyingKey::<Bn254>::deserialize_compressed(&vk_bytes[..])?;
    let pvk = PreparedVerifyingKey::<Bn254>::deserialize_compressed(
        &fs::read(setup.join("pvk.bin"))?[..],
    )?;
    assert_eq!(g16::encode(&prepare_verifying_key(&vk)), g16::encode(&pvk));
    let static_path = setup.join("pvk-uncompressed.bin");
    if static_path.exists() {
        let mut checked = vec![];
        pvk.serialize_uncompressed(&mut checked)?;
        assert_eq!(
            fs::read(static_path)?,
            checked,
            "compiled static parameters differ from checked prepared VK"
        );
    }
    Ok((pvk, g16::key_id(&vk_bytes)))
}
fn setup(out: &Path) -> Result<()> {
    fs::create_dir(out)?;
    let values = [1_000_000_000, 400_000_000, 600_000_000, 0];
    let input = proxy::WalletInput {
        intent: proxy::intent([0; 32], 1, [1; 32], values),
        secret: [1; 32],
        values,
    };
    let circuit = WalletCircuit::new(input);
    let (constraints, satisfied) = circuit.check()?;
    assert!(satisfied);
    let start = Instant::now();
    let pk = Groth16::<Bn254>::generate_random_parameters_with_reduction(
        circuit,
        &mut rand::rngs::OsRng,
    )?;
    let setup_seconds = start.elapsed().as_secs_f64();
    let f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(out.join("public-proving-parameters.bin"))?;
    pk.serialize_compressed(BufWriter::new(f))?;
    let vk = g16::encode(&pk.vk);
    let pvk = g16::encode(&prepare_verifying_key(&pk.vk));
    save(out, "vk.bin", &vk)?;
    save(out, "pvk.bin", &pvk)?;
    save(
        out,
        "setup.json",
        &serde_json::to_vec_pretty(&json!({
            "scope":"LOCAL_SINGLE_PARTY_CIRCUIT_SPECIFIC_SETUP_NOT_PRODUCTION_CEREMONY",
            "randomness":"fresh OS entropy; no seed or scalar trapdoor serialized",
            "constraints":constraints,"publicFieldInputs":4,"seconds":setup_seconds,
            "circuitId":hex::encode(g16::key_id(&vk)),"vkBytes":vk.len(),"preparedVkBytes":pvk.len(),
            "publicProvingParametersBytes":fs::metadata(out.join("public-proving-parameters.bin"))?.len(),
            "risc0ReceiptWrapping":false,"outerCycleBudget":g16::CLASSIFIER_CYCLE_BUDGET,"outerProofSecondsBudget":3600,
        }))?,
    )
}
fn wallet(setup: &Path, out: &Path) -> Result<()> {
    fs::create_dir(out)?;
    let (pvk, id) = load_pvk(setup)?;
    let pk = ProvingKey::<Bn254>::deserialize_compressed(BufReader::new(fs::File::open(
        setup.join("public-proving-parameters.bin"),
    )?))?;
    assert_eq!(g16::encode(&pk.vk), g16::encode(&pvk.vk));
    for (name, nonce, pay) in [("a", 1, 400_000_000u64), ("c", 3, 100_000_000)] {
        let values = [1_000_000_000, pay, 1_000_000_000 - pay, 0];
        let intent = proxy::intent(id, nonce, [nonce; 32], values);
        let input = proxy::WalletInput {
            intent: intent.clone(),
            secret: [nonce; 32],
            values,
        };
        let circuit = WalletCircuit::new(input.clone());
        let (_, ok) = circuit.check()?;
        assert!(ok);
        let statement = circuit.inputs();
        let start = Instant::now();
        let proof = Groth16::<Bn254>::create_random_proof_with_reduction(
            circuit,
            &pk,
            &mut rand::rngs::OsRng,
        )?;
        let seconds = start.elapsed().as_secs_f64();
        assert!(Groth16::<Bn254>::verify_proof(&pvk, &proof, &statement)?);
        let bytes = g16::encode(&proof);
        assert_eq!(bytes.len(), g16::PROOF_BYTES);
        let op = proxy::operation(&intent, &bytes);
        assert_eq!(g16::classify(&op, id, &pvk), 0);
        save(out, &format!("wallet-{name}-proof.bin"), &bytes)?;
        save(out, &format!("wallet-{name}-operation.bin"), &op)?;
        save(
            out,
            &format!("wallet-{name}-public-test-witness.json"),
            &serde_json::to_vec_pretty(&input)?,
        )?;
        save(
            out,
            &format!("wallet-{name}-report.json"),
            &serde_json::to_vec_pretty(&json!({
                "scope":"REAL_SPECIALIZED_BN254_GROTH16_WALLET_PROOF_SAME_PROXY_STATEMENT",
                "seconds":seconds,"proofBytes":bytes.len(),"operationBytes":op.len(),"publicFieldInputs":statement.len(),
                "sdkVerified":true,"circuitId":hex::encode(id),"statementJournal":hex::encode(proxy::journal(&intent)),
            }))?,
        )?;
    }
    Ok(())
}
fn fixtures(setup: &Path, wallets: &Path, out: &Path) -> Result<()> {
    fs::create_dir(out)?;
    let (pvk, id) = load_pvk(setup)?;
    let a = fs::read(wallets.join("wallet-a-operation.bin"))?;
    let c = fs::read(wallets.join("wallet-c-operation.bin"))?;
    for op in [&a, &c] {
        assert_eq!(g16::classify(op, id, &pvk), 0);
    }
    let mut proof = Proof::<Bn254>::deserialize_compressed(&c[proxy::INTENT_LEN + 4..])?;
    proof.c = -proof.c; // Canonical on-curve subgroup point, incorrect pairing equation.
    let bad = proxy::operation(&c[..proxy::INTENT_LEN], &g16::encode(&proof));
    assert_eq!(g16::classify(&bad, id, &pvk), 3);
    let ops = [a.clone(), bad.clone(), c.clone()];
    let (input, root) = super::proof_classification::batch(&ops, None);
    save(out, "valid-invalid-valid.bin", &input)?;
    let mut public_mutations = vec![];
    for offset in [
        8, 10, 42, 74, 106, 138, 170, 202, 210, 218, 250, 282, 314, 442,
    ] {
        let mut op = c.clone();
        op[offset] ^= 1;
        let code = g16::classify(&op, id, &pvk);
        assert_ne!(code, 0);
        public_mutations.push(json!({"offset":offset,"outcome":code}));
    }
    let mut cases = vec![];
    for (name, bytes) in [
        ("empty", vec![]),
        ("truncated", vec![0; 127]),
        ("oversized", vec![0; 129]),
        ("unreduced", vec![0xff; 128]),
        ("identity", vec![0; 128]),
    ] {
        let op = proxy::operation(&c[..proxy::INTENT_LEN], &bytes);
        let code = g16::classify(&op, id, &pvk);
        assert_ne!(code, 0);
        save(
            out,
            &format!("malformed-only-{name}.bin"),
            &super::proof_classification::batch(&[op.clone()], None).0,
        )?;
        save(
            out,
            &format!("{name}.bin"),
            &super::proof_classification::batch(&[a.clone(), op, c.clone()], None).0,
        )?;
        cases.push(json!({"case":name,"expectedOutcome":code}));
    }
    let mut changed = c.clone();
    changed[314] ^= 1;
    assert_eq!(g16::classify(&changed, id, &pvk), 3);
    save(
        out,
        "changed-public-input.bin",
        &super::proof_classification::batch(&[a.clone(), changed, c.clone()], None).0,
    )?;
    // BN254 G1 has cofactor one, but an on-curve G2 point can be outside the
    // prime-order subgroup. Checked proof decoding must reject that case too.
    let wrong_subgroup = (0u64..100)
        .find_map(|n| {
            let x = ark_bn254::Fq2::new(ark_bn254::Fq::from(n), ark_bn254::Fq::from(1u64));
            ark_bn254::G2Affine::get_point_from_x_unchecked(x, false)
                .filter(|p| !p.is_in_correct_subgroup_assuming_on_curve())
        })
        .ok_or("could not construct subgroup negative fixture")?;
    let mut bad_group = Proof::<Bn254>::deserialize_compressed(&c[proxy::INTENT_LEN + 4..])?;
    bad_group.b = wrong_subgroup;
    let bad_group_op = proxy::operation(&c[..proxy::INTENT_LEN], &g16::encode(&bad_group));
    assert_eq!(g16::classify(&bad_group_op, id, &pvk), 2);
    save(
        out,
        "malformed-only-wrong-subgroup.bin",
        &super::proof_classification::batch(&[bad_group_op.clone()], None).0,
    )?;
    save(
        out,
        "wrong-subgroup.bin",
        &super::proof_classification::batch(&[a.clone(), bad_group_op, c.clone()], None).0,
    )?;
    let mut trailing = c.clone();
    trailing.push(0);
    assert_eq!(g16::classify(&trailing, id, &pvk), 2);
    save(
        out,
        "malformed-only-trailing.bin",
        &super::proof_classification::batch(&[trailing.clone()], None).0,
    )?;
    save(
        out,
        "trailing.bin",
        &super::proof_classification::batch(&[a.clone(), trailing, c.clone()], None).0,
    )?;
    let mut huge = c.clone();
    huge[proxy::INTENT_LEN..proxy::INTENT_LEN + 4].copy_from_slice(&u32::MAX.to_le_bytes());
    assert_eq!(g16::classify(&huge, id, &pvk), 2);
    save(
        out,
        "malformed-only-huge-length.bin",
        &super::proof_classification::batch(&[huge.clone()], None).0,
    )?;
    save(
        out,
        "huge-length.bin",
        &super::proof_classification::batch(&[a.clone(), huge, c.clone()], None).0,
    )?;
    save(
        out,
        "replay.bin",
        &super::proof_classification::batch(&[a.clone(), a.clone(), c.clone()], None).0,
    )?;
    for (name, changed) in [
        (
            "withheld",
            vec![
                a.clone(),
                proxy::operation(&c[..proxy::INTENT_LEN], &[]),
                c.clone(),
            ],
        ),
        ("substituted", vec![a.clone(), c.clone(), c.clone()]),
        ("omitted", vec![a.clone(), c.clone()]),
        ("reordered", vec![c.clone(), bad.clone(), a.clone()]),
    ] {
        save(
            out,
            &format!("{name}.bin"),
            &super::proof_classification::batch(&changed, Some(root)).0,
        )?;
    }
    let mut verdict = input.clone();
    verdict.push(1);
    save(out, "host-verdict.bin", &verdict)?;
    use kaspa_consensus_core::{
        config::params::TESTNET_PARAMS,
        mass::{transaction_estimated_serialized_size, MassCalculator},
    };
    let calc = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS);
    let operations:Vec<_>=ops.into_iter().enumerate().map(|(i,op)|{
        let tx=super::proof_classification::tx(op.clone(),i as u32);let m=calc.calc_non_contextual_masses(&tx);
        json!({"nativeId":tx.id().to_string(),"operationBytes":op.len(),"nativeEstimatedBytes":transaction_estimated_serialized_size(&tx),"computeMass":m.compute_mass,"transientMass":m.transient_mass})
    }).collect();
    save(
        out,
        "expected.json",
        &serde_json::to_vec_pretty(&json!({
            "scope":"LOCAL_FIXED_ORDER_NOT_ACTUAL_TN10_ACCEPTANCE","orderedRoot":hex::encode(root),
            "operations":operations,"outcomes":[0,3,0],"balances":[600_000_000,600_000_000,500_000_000],
            "malformedCases":cases,"publicInputMutations":public_mutations,"nativeBlockLimits":{"compute":500000,"transient":1000000},
        }))?,
    )
}
fn execute(program: &[u8], input: &[u8]) -> Result<risc0_zkvm::SessionInfo> {
    let mut b = ExecutorEnv::builder();
    b.write_slice(&[u32::try_from(input.len())?])
        .write_slice(input)
        .stdout(std::io::stdout())
        .segment_limit_po2(20)
        .session_limit(Some(g16::CLASSIFIER_CYCLE_BUDGET));
    Ok(default_executor().execute(b.build()?, program)?)
}
fn expected_journal(expected: &Value) -> Result<Vec<u8>> {
    let mut j = hex::decode(expected["orderedRoot"].as_str().ok_or("root")?)?;
    j.extend(1_000_000_000u64.to_le_bytes());
    j.extend(3u32.to_le_bytes());
    for i in 0..3 {
        j.extend(hex::decode(
            expected["operations"][i]["nativeId"].as_str().ok_or("id")?,
        )?);
        j.push(u8::try_from(
            expected["outcomes"][i].as_u64().ok_or("outcome")?,
        )?);
        j.extend(
            expected["balances"][i]
                .as_u64()
                .ok_or("balance")?
                .to_le_bytes(),
        );
    }
    Ok(j)
}
fn profile(programs: &Path, fixture: &Path, out: &Path, label: &str) -> Result<()> {
    fs::create_dir(out)?;
    let p = fs::read(programs.join("classifier.program.bin"))?;
    let input = fs::read(fixture.join(format!("{label}.bin")))?;
    let start = Instant::now();
    let result = execute(&p, &input);
    let mut r = json!({"scope":"EXECUTION_ONLY_NOT_PROOF","case":label,"seconds":start.elapsed().as_secs_f64(),"cycleBudget":g16::CLASSIFIER_CYCLE_BUDGET});
    match result {
        Ok(s) => {
            if label == "valid-invalid-valid" {
                let expected: Value =
                    serde_json::from_slice(&fs::read(fixture.join("expected.json"))?)?;
                assert_eq!(s.journal.bytes, expected_journal(&expected)?);
            } else if label.starts_with("malformed-only-") {
                assert_eq!(s.journal.bytes.len(), 85);
                assert_eq!(&s.journal.bytes[..32], &input[..32]);
                assert_eq!(s.journal.bytes[76], 2);
                assert_eq!(
                    u64::from_le_bytes(s.journal.bytes[77..85].try_into().unwrap()),
                    1_000_000_000
                );
                r["outcomes"] = json!([2]);
                r["balances"] = json!([1_000_000_000]);
            } else {
                let codes: Vec<_> = s.journal.bytes[44..]
                    .chunks_exact(41)
                    .map(|v| v[32])
                    .collect();
                let expected_code = match label {
                    "replay" => 4,
                    "changed-public-input" => 3,
                    "empty" | "truncated" | "oversized" | "unreduced" | "identity"
                    | "wrong-subgroup" | "trailing" | "huge-length" => 2,
                    _ => return Err("unknown expected profile outcome".into()),
                };
                assert_eq!(codes, [0, expected_code, 0]);
                let balances: Vec<_> = s.journal.bytes[44..]
                    .chunks_exact(41)
                    .map(|v| u64::from_le_bytes(v[33..41].try_into().unwrap()))
                    .collect();
                assert_eq!(balances, [600_000_000, 600_000_000, 500_000_000]);
                r["outcomes"] = json!(codes);
            }
            r["userCycles"] = json!(s.cycles());
            r["segments"] = json!(s.segments.iter().map(|v| v.po2).collect::<Vec<_>>());
            save(out, "journal.bin", &s.journal.bytes)?;
        }
        Err(e) => {
            let message = format!("{e:#}");
            if super::proof_classification::expected_authentication_abort(label, &message) {
                r["expectedAuthenticationFailureConfirmed"] = json!(true);
                r["authenticationAbort"] = json!(message);
            } else {
                r["unexpectedError"] = json!(message);
                save(out, "report.json", &serde_json::to_vec_pretty(&r)?)?;
                return Err(e);
            }
        }
    }
    save(out, "report.json", &serde_json::to_vec_pretty(&r)?)
}
pub(super) fn run(a: &[String]) -> Result<()> {
    if a.len() < 3 {
        return Err("groth16 setup|wallet|fixtures|profile|prove|verify ...".into());
    }
    match a[2].as_str() {
        "validate-key" if a.len() == 4 => {
            let (_, id) = load_pvk(Path::new(&a[3]))?;
            println!(
                "{}",
                json!({"circuitId":hex::encode(id),"preparedAndStaticParametersRecomputed":true})
            );
            Ok(())
        }
        "verify-wallets" if a.len() == 5 => {
            let (pvk, id) = load_pvk(Path::new(&a[3]))?;
            let mut checked = vec![];
            for name in ["a", "c"] {
                let op = fs::read(Path::new(&a[4]).join(format!("wallet-{name}-operation.bin")))?;
                assert_eq!(g16::classify(&op, id, &pvk), 0);
                let mut changed = op.clone();
                changed[314] ^= 1;
                assert_eq!(g16::classify(&changed, id, &pvk), 3);
                checked.push(name);
            }
            println!(
                "{}",
                json!({"scope":"SEPARATE_PROCESS_WALLET_PROOF_REVERIFICATION_NO_PROVING_KEY_READ",
                "walletProofs":checked,"circuitId":hex::encode(id),"preparedParametersRecomputed":true,"changedIntentRejected":true})
            );
            Ok(())
        }
        "export-key" if a.len() == 5 => {
            let (pvk, _) = load_pvk(Path::new(&a[3]))?;
            let file = fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&a[4])?;
            pvk.serialize_uncompressed(BufWriter::new(file))?;
            Ok(())
        }
        "setup" if a.len() == 4 => setup(Path::new(&a[3])),
        "wallet" if a.len() == 5 => wallet(Path::new(&a[3]), Path::new(&a[4])),
        "fixtures" if a.len() == 6 => {
            fixtures(Path::new(&a[3]), Path::new(&a[4]), Path::new(&a[5]))
        }
        "profile" if a.len() == 7 => {
            profile(Path::new(&a[3]), Path::new(&a[4]), Path::new(&a[5]), &a[6])
        }
        "prove" if a.len() == 6 => {
            let p = Path::new(&a[3]);
            let f = Path::new(&a[4]);
            let out = Path::new(&a[5]);
            fs::create_dir(out)?;
            let program = fs::read(p.join("classifier.program.bin"))?;
            let input = fs::read(f.join("valid-invalid-valid.bin"))?;
            let s = execute(&program, &input)?;
            assert!(s.cycles() <= g16::CLASSIFIER_CYCLE_BUDGET);
            let expected: Value = serde_json::from_slice(&fs::read(f.join("expected.json"))?)?;
            assert_eq!(s.journal.bytes, expected_journal(&expected)?);
            let receipt = prove(out, "classifier", &input, &program, &[], true, false)?;
            assert_eq!(receipt.journal.bytes, expected_journal(&expected)?);
            Ok(())
        }
        "verify" if a.len() == 6 => {
            let p = Path::new(&a[3]);
            let f = Path::new(&a[4]);
            let proofs = Path::new(&a[5]);
            let r: Receipt =
                bincode::deserialize(&fs::read(proofs.join("classifier-receipt.bin"))?)?;
            let image = compute_image_id(&fs::read(p.join("classifier.program.bin"))?)?;
            r.verify_with_context(
                &risc0_zkvm::VerifierContext::default().with_dev_mode(false),
                image,
            )?;
            let expected: Value = serde_json::from_slice(&fs::read(f.join("expected.json"))?)?;
            assert_eq!(r.journal.bytes, expected_journal(&expected)?);
            let mut wrong = r.clone();
            wrong.journal.bytes[76] ^= 1;
            assert!(wrong.verify(image).is_err());
            println!(
                "{}",
                json!({"scope":"INDEPENDENT_PROCESS_VERIFICATION_OF_REAL_OUTER_RECEIPT_NOT_TN10_SETTLEMENT",
                "expectedRoot":expected["orderedRoot"],"outcomes":expected["outcomes"],"balances":expected["balances"],"tamperedOutcomeRejected":true,"developmentMode":false})
            );
            Ok(())
        }
        _ => Err("wrong groth16 command arguments".into()),
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_sha_relation_and_integer_boundaries() {
        for (values, expected) in [
            ([10, 4, 6, 0], true),
            ([u64::MAX, u64::MAX, 0, 0], true),
            ([0, 0, 0, 0], false),
            ([10, 5, 6, 0], false),
            ([u64::MAX, u64::MAX, 1, 0], false),
        ] {
            let input = proxy::WalletInput {
                intent: proxy::intent([7; 32], 1, [1; 32], values),
                secret: [1; 32],
                values,
            };
            assert_eq!(WalletCircuit::new(input).check().unwrap().1, expected);
        }
    }
    #[test]
    fn secret_and_complete_intent_cannot_be_substituted() {
        let values = [10, 4, 6, 0];
        let input = proxy::WalletInput {
            intent: proxy::intent([7; 32], 1, [1; 32], values),
            secret: [1; 32],
            values,
        };
        let good = WalletCircuit::new(input.clone());
        assert!(good.check().unwrap().1);
        let mut bad = good.clone();
        bad.input.secret[0] ^= 1;
        assert!(!bad.check().unwrap().1);
        let mut bad = good;
        bad.input.intent[314] ^= 1;
        assert!(!bad.check().unwrap().1);
    }
}
