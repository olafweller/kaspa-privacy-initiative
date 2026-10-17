//! Local pinned-backend qualification. No network, funding or circuit setup.
use super::*;
use kpi_groth16_comparison::{self as reference, proxy};

const PRACTICAL: u64 = 32_000_000;
const CALIBRATION: u64 = 128_000_000;

fn reference_journal(input: &[u8], setup: &Path) -> Result<Vec<u8>> {
    let (pvk, key) = super::groth16_comparison::load_pvk(setup)?;
    let mut r = proxy::Reader(input);
    let root = r.take(32).map_err(|_| "root")?;
    let initial = r.take(8).map_err(|_| "balance")?;
    let mut balance = u64::from_le_bytes(initial.try_into()?);
    let count = r.u32().map_err(|_| "count")?;
    assert!(count > 0 && count as usize <= proxy::MAX_BATCH);
    let mut journal = root.to_vec();
    journal.extend(initial);
    journal.extend(count.to_le_bytes());
    let mut computed = [0; 32];
    let mut seen = vec![];
    for i in 0..count {
        let rest = r.blob(4096).map_err(|_| "rest")?;
        let op = r.blob(proxy::MAX_OPERATION).map_err(|_| "op")?;
        let tx = kpi_takeover_common::app::lane::Tx {
            rest: rest.to_vec(),
            payload: op.to_vec(),
            merge_idx: i,
        };
        let id = kpi_takeover_common::app::lane_id(&tx);
        computed = proxy::order_step(computed, i, id);
        let mut code = reference::classify(op, key, &pvk);
        if code == 0 {
            let intent = &op[..proxy::INTENT_LEN];
            let token = proxy::tagged(b"KPI-local-intent-v1", intent);
            let effect = u64::from_le_bytes(intent[202..210].try_into()?);
            if seen.contains(&token) || effect > balance {
                code = 4;
            } else {
                balance -= effect;
                seen.push(token);
            }
        }
        journal.extend(id);
        journal.push(code);
        journal.extend(balance.to_le_bytes());
    }
    assert!(r.0.is_empty());
    assert_eq!(computed, root);
    Ok(journal)
}
fn bounded_env(input: &[u8], budget: u64) -> Result<risc0_zkvm::ExecutorEnv<'static>> {
    assert!([PRACTICAL, CALIBRATION].contains(&budget));
    let mut b = ExecutorEnv::builder();
    b.write_slice(&[u32::try_from(input.len())?])
        .write_slice(input)
        .stdout(std::io::stdout())
        .segment_limit_po2(20)
        .session_limit(Some(budget));
    Ok(b.build()?)
}
fn expected_image(programs: &Path) -> Result<risc0_zkvm::sha::Digest> {
    let identity: Value = serde_json::from_slice(&fs::read(programs.join("identity.json"))?)?;
    let bytes = hex::decode(
        identity["expectedProgramImage"]
            .as_str()
            .ok_or("identity")?,
    )?;
    let image: risc0_zkvm::sha::Digest = bytes.as_slice().try_into()?;
    assert_eq!(
        compute_image_id(&fs::read(programs.join("classifier.program.bin"))?)?,
        image
    );
    Ok(image)
}
fn profile(a: &[String]) -> Result<()> {
    if a.len() != 9 {
        return Err("profile PROGRAMS FIXTURES SETUP NEW_OUTPUT CASE practical|calibration".into());
    }
    let programs = Path::new(&a[3]);
    let fixtures = Path::new(&a[4]);
    let setup = Path::new(&a[5]);
    let out = Path::new(&a[6]);
    let label = &a[7];
    let budget = match a[8].as_str() {
        "practical" => PRACTICAL,
        "calibration" if label == "valid-invalid-valid" => CALIBRATION,
        _ => return Err("undeclared profile".into()),
    };
    let image = expected_image(programs)?;
    let program = fs::read(programs.join("classifier.program.bin"))?;
    let input = fs::read(fixtures.join(format!("{label}.bin")))?;
    fs::create_dir(out)?;
    let auth = [
        "withheld",
        "substituted",
        "omitted",
        "reordered",
        "host-verdict",
    ]
    .contains(&label.as_str());
    let expected = if auth {
        None
    } else {
        Some(reference_journal(&input, setup)?)
    };
    if let Some(ref j) = expected {
        save(out, "expected-journal.bin", j)?;
    }
    let started = Instant::now();
    let result = default_executor().execute(bounded_env(&input, budget)?, &program);
    let mut report = json!({"scope":"EXECUTION_ONLY_NOT_PROOF","case":label,"profile":a[8],"cycleBudget":budget,
        "expectedProgramImage":image.to_string(),"seconds":started.elapsed().as_secs_f64()});
    match result {
        Ok(s) => {
            assert!(!auth, "authentication control unexpectedly completed");
            assert_eq!(&s.journal.bytes, expected.as_ref().unwrap());
            report["completed"] = json!(true);
            report["userCycles"] = json!(s.cycles());
            report["segments"] = json!(s.segments.iter().map(|s| s.po2).collect::<Vec<_>>());
            report["outcomes"] = json!(s.journal.bytes[44..]
                .chunks_exact(41)
                .map(|c| c[32])
                .collect::<Vec<_>>());
            report["balances"] = json!(s.journal.bytes[44..]
                .chunks_exact(41)
                .map(|c| u64::from_le_bytes(c[33..41].try_into().unwrap()))
                .collect::<Vec<_>>());
            save(out, "journal.bin", &s.journal.bytes)?;
        }
        Err(e) => {
            let message = format!("{e:#}");
            if auth && super::proof_classification::expected_authentication_abort(label, &message) {
                report["expectedAuthenticationFailureConfirmed"] = json!(true);
                report["authenticationAbort"] = json!(message);
            } else {
                report["completed"] = json!(false);
                report["unexpectedError"] = json!(message);
                save(out, "report.json", &serde_json::to_vec_pretty(&report)?)?;
                return Err(e.into());
            }
        }
    }
    save(out, "report.json", &serde_json::to_vec_pretty(&report)?)
}
fn reference_checks(a: &[String]) -> Result<()> {
    if a.len() != 6 {
        return Err("reference SETUP WALLETS NEW_OUTPUT".into());
    }
    let (pvk, id) = super::groth16_comparison::load_pvk(Path::new(&a[3]))?;
    let verifier = kpi_accelerated_bn254::Verifier::pinned();
    assert_eq!(id, verifier.id);
    let mut checks = vec![];
    for name in ["a", "c"] {
        let op = fs::read(Path::new(&a[4]).join(format!("wallet-{name}-operation.bin")))?;
        assert_eq!(verifier.classify(&op), 0);
        assert_eq!(reference::classify(&op, id, &pvk), 0);
        for offset in [
            8, 10, 42, 74, 106, 138, 170, 202, 210, 218, 250, 282, 314, 442,
        ] {
            let mut changed = op.clone();
            changed[offset] ^= 1;
            let expected = reference::classify(&changed, id, &pvk);
            assert_ne!(expected, 0);
            assert_eq!(verifier.classify(&changed), expected);
            checks.push(json!({"wallet":name,"offset":offset,"outcome":expected}));
        }
    }
    let out = Path::new(&a[5]);
    fs::create_dir(out)?;
    save(
        out,
        "report.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"HOST_DIFFERENTIAL_REFERENCE_NOT_GUEST_PROOF",
        "circuitId":hex::encode(id),"realProofsVerified":2,"mutations":checks,"setupRegenerated":false}),
        )?,
    )
}

pub(super) fn run(a: &[String]) -> Result<()> {
    match a.get(2).map(String::as_str) {
        Some("profile") => return profile(a),
        Some("reference") => return reference_checks(a),
        Some("pin") if a.len() == 4 => {
            let p = Path::new(&a[3]);
            let image = compute_image_id(&fs::read(p.join("classifier.program.bin"))?)?;
            return save(
                p,
                "identity.json",
                &serde_json::to_vec_pretty(
                    &json!({"expectedProgramImage":image.to_string(),"scope":"PRE_EXECUTION_EXPECTED_NEW_CLASSIFIER_IDENTITY","sdk":"3.0.3","backendCommit":"22108fe8c6ea1ebc1358fc4fd6854a6bf46e3509"}),
                )?,
            );
        }
        _ => {}
    }
    if a.len() != 5 || a[2] != "smoke" {
        return Err("accelerated-bn254 smoke PROGRAM NEW_OUTPUT_DIR".into());
    }
    let program = fs::read(&a[3])?;
    let out = Path::new(&a[4]);
    fs::create_dir(out)?;
    let image = compute_image_id(&program)?;
    save(out, "expected-image.txt", image.to_string().as_bytes())?;
    let mut b = ExecutorEnv::builder();
    b.write_slice(&[7u32])
        .stdout(std::io::stdout())
        .enable_profiler(out.join("accelerated-path.pprof"))
        .segment_limit_po2(20)
        .session_limit(Some(32_000_000));
    let started = Instant::now();
    let execution = default_executor().execute(b.build()?, &program);
    let mut report = json!({"scope":"EXECUTION_ONLY_BACKEND_SMOKE_NOT_WALLET_CLASSIFICATION",
        "expectedProgramImage":image.to_string(),"cycleBudget":32_000_000,
        "seconds":started.elapsed().as_secs_f64(),"developmentMode":false});
    match execution {
        Ok(s) => {
            assert_eq!(s.journal.bytes, b"KPI-BN254-SMOKE-OK");
            report["completed"] = json!(true);
            report["userCycles"] = json!(s.cycles());
            report["segmentPo2"] = json!(s.segments.iter().map(|s| s.po2).collect::<Vec<_>>());
            save(out, "journal.bin", &s.journal.bytes)?;
            save(out, "report.json", &serde_json::to_vec_pretty(&report)?)?;
            Ok(())
        }
        Err(e) => {
            report["completed"] = json!(false);
            report["executionError"] = json!(format!("{e:#}"));
            save(out, "report.json", &serde_json::to_vec_pretty(&report)?)?;
            Err(e.into())
        }
    }
}
