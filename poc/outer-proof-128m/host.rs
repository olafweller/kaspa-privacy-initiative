//! Approved real outer proof of the unchanged compact-wallet classifier.
use super::*;
use risc0_zkvm::{
    sha::{Digest, Sha256},
    VerifierContext,
};

const CYCLES: u64 = 128_000_000;
const IMAGE: &str = "397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716";
const CASES: &[&str] = &[
    "valid-invalid-valid",
    "replay",
    "changed-public-input",
    "empty",
    "truncated",
    "oversized",
    "unreduced",
    "identity",
    "wrong-subgroup",
    "trailing",
    "huge-length",
    "withheld",
    "substituted",
    "omitted",
    "reordered",
    "host-verdict",
    "malformed-only-empty",
    "malformed-only-truncated",
    "malformed-only-oversized",
    "malformed-only-unreduced",
    "malformed-only-identity",
    "malformed-only-wrong-subgroup",
    "malformed-only-trailing",
    "malformed-only-huge-length",
];
fn sha(bytes: &[u8]) -> String {
    risc0_zkvm::sha::Impl::hash_bytes(bytes).to_string()
}
fn image() -> Result<Digest> {
    Ok(hex::decode(IMAGE)?.as_slice().try_into()?)
}
pub(super) fn program(programs: &Path) -> Result<Vec<u8>> {
    assert_eq!(
        super::accelerated_bn254::expected_image(programs)?,
        image()?
    );
    Ok(fs::read(programs.join("classifier.program.bin"))?)
}
fn auth(label: &str) -> bool {
    [
        "withheld",
        "substituted",
        "omitted",
        "reordered",
        "host-verdict",
    ]
    .contains(&label)
}
fn expected_main(fixtures: &Path) -> Result<Vec<u8>> {
    let v: Value = serde_json::from_slice(&fs::read(fixtures.join("expected.json"))?)?;
    assert_eq!(v["outcomes"], json!([0, 3, 0]));
    assert_eq!(
        v["balances"],
        json!([600_000_000, 600_000_000, 500_000_000])
    );
    let mut out = hex::decode(v["orderedRoot"].as_str().ok_or("root")?)?;
    out.extend(1_000_000_000u64.to_le_bytes());
    out.extend(3u32.to_le_bytes());
    for i in 0..3 {
        out.extend(hex::decode(
            v["operations"][i]["nativeId"].as_str().ok_or("native ID")?,
        )?);
        out.push(v["outcomes"][i].as_u64().ok_or("outcome")? as u8);
        out.extend(v["balances"][i].as_u64().ok_or("balance")?.to_le_bytes());
    }
    assert_eq!(out.len(), 167);
    Ok(out)
}
fn expected_codes(label: &str) -> Vec<u8> {
    if label.starts_with("malformed-only-") {
        vec![2]
    } else {
        vec![
            0,
            match label {
                "valid-invalid-valid" | "changed-public-input" => 3,
                "replay" => 4,
                _ => 2,
            },
            0,
        ]
    }
}
fn prepare(a: &[String]) -> Result<()> {
    if a.len() != 7 {
        return Err("prepare PROGRAMS FIXTURES SETUP NEW_EXPECTATIONS".into());
    }
    let programs = Path::new(&a[3]);
    let fixtures = Path::new(&a[4]);
    let setup = Path::new(&a[5]);
    let out = Path::new(&a[6]);
    let program = program(programs)?;
    fs::create_dir(out)?;
    let main = expected_main(fixtures)?;
    let mut cases = vec![];
    for label in CASES {
        let input = fs::read(fixtures.join(format!("{label}.bin")))?;
        let mut item =
            json!({"case":label,"inputSha256":sha(&input),"authenticationControl":auth(label)});
        if !auth(label) {
            let expected = super::accelerated_bn254::reference_journal(&input, setup)?;
            assert_eq!(
                expected[44..]
                    .chunks_exact(41)
                    .map(|c| c[32])
                    .collect::<Vec<_>>(),
                expected_codes(label)
            );
            let balances = expected[44..]
                .chunks_exact(41)
                .map(|c| u64::from_le_bytes(c[33..41].try_into().unwrap()))
                .collect::<Vec<_>>();
            assert_eq!(
                balances,
                if label.starts_with("malformed-only-") {
                    vec![1_000_000_000]
                } else {
                    vec![600_000_000, 600_000_000, 500_000_000]
                }
            );
            if *label == "valid-invalid-valid" {
                assert_eq!(expected, main);
            }
            item["journalSha256"] = json!(sha(&expected));
            save(out, &format!("{label}-expected-journal.bin"), &expected)?;
        }
        cases.push(item);
    }
    save(out, "expected-journal.bin", &main)?;
    save(
        out,
        "expectations.json",
        &serde_json::to_vec_pretty(&json!({
        "scope":"INDEPENDENT_EXPECTATIONS_PREPARED_BEFORE_QUALIFICATION_AND_PROOF",
        "expectedProgramImage":IMAGE,"programSha256":sha(&program),"executionCycleLimit":CYCLES,
        "proofWholeJobSecondsLimit":3600,"mainJournalSha256":sha(&main),"cases":cases}))?,
    )
}
pub(super) fn gate(
    programs: &Path,
    fixtures: &Path,
    expected: &Path,
    qualification: &Path,
) -> Result<Vec<u8>> {
    let p = program(programs)?;
    let e: Value = serde_json::from_slice(&fs::read(expected.join("expectations.json"))?)?;
    assert_eq!(e["expectedProgramImage"], IMAGE);
    assert_eq!(e["programSha256"], sha(&p));
    assert_eq!(e["cases"].as_array().ok_or("cases")?.len(), CASES.len());
    let q: Value = serde_json::from_slice(&fs::read(qualification.join("qualification.json"))?)?;
    assert_eq!(q["passed"], true);
    assert_eq!(
        q["cases"].as_array().ok_or("qualified cases")?.len(),
        CASES.len()
    );
    for (i, label) in CASES.iter().enumerate() {
        assert_eq!(e["cases"][i]["case"], *label);
        assert_eq!(
            e["cases"][i]["inputSha256"],
            sha(&fs::read(fixtures.join(format!("{label}.bin")))?)
        );
        let r: Value = serde_json::from_slice(&fs::read(
            qualification.join(format!("result-{label}/report.json")),
        )?)?;
        assert_eq!(r["case"], *label);
        assert_eq!(r["profile"], "approved-128m");
        assert_eq!(r["cycleBudget"], CYCLES);
        assert_eq!(r["expectedProgramImage"], IMAGE);
        if auth(label) {
            assert_eq!(r["expectedAuthenticationFailureConfirmed"], true);
            assert!(super::proof_classification::expected_authentication_abort(
                label,
                r["authenticationAbort"].as_str().ok_or("specific abort")?
            ));
        } else {
            assert_eq!(r["completed"], true);
            assert!(r["userCycles"].as_u64().ok_or("cycles")? <= CYCLES);
            let j = fs::read(qualification.join(format!("result-{label}/journal.bin")))?;
            assert_eq!(
                j,
                fs::read(expected.join(format!("{label}-expected-journal.bin")))?
            );
            assert_eq!(e["cases"][i]["journalSha256"], sha(&j));
        }
        let resource: Value = serde_json::from_slice(&fs::read(
            qualification.join(format!("measure-{label}.resources.json")),
        )?)?;
        assert_eq!(resource["exitCode"], 0);
        assert!(resource["limitExceeded"].is_null());
    }
    let main = fs::read(expected.join("expected-journal.bin"))?;
    assert_eq!(main, expected_main(fixtures)?);
    assert_eq!(e["mainJournalSha256"], sha(&main));
    Ok(main)
}
fn verify_receipt(r: &Receipt, expected: &[u8]) -> Result<()> {
    // Require a genuine succinct seal; Fake/Composite alternatives do not pass
    // as the requested artifact. verify_with_context binds successful exit,
    // expected program, journal digest and the empty assumptions claim.
    r.inner.succinct()?;
    r.verify_with_context(&VerifierContext::default().with_dev_mode(false), image()?)?;
    let claim = r.claim()?.value()?;
    let output = claim.output.value()?.ok_or("missing output")?;
    assert!(
        output.assumptions.is_empty(),
        "unresolved assumptions forbidden"
    );
    assert_eq!(r.journal.bytes, expected);
    Ok(())
}
fn produce(a: &[String]) -> Result<()> {
    if a.len() != 8 {
        return Err("prove PROGRAMS FIXTURES EXPECTATIONS QUALIFICATION NEW_OUTPUT".into());
    }
    let programs = Path::new(&a[3]);
    let fixtures = Path::new(&a[4]);
    let expected = Path::new(&a[5]);
    let qualification = Path::new(&a[6]);
    let out = Path::new(&a[7]);
    fs::create_dir(out)?;
    save(
        out,
        "job-started.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"ONE_REAL_OUTER_PROOF_ATTEMPT","expectedProgramImage":IMAGE,"executionCycleLimit":CYCLES,"proofWholeJobSecondsLimit":3600,"developmentMode":false}),
        )?,
    )?;
    let expected = gate(programs, fixtures, expected, qualification)?;
    let p = program(programs)?;
    let input = fs::read(fixtures.join("valid-invalid-valid.bin"))?;
    let start = Instant::now();
    let profile =
        default_executor().execute(super::accelerated_bn254::bounded_env(&input, CYCLES)?, &p)?;
    assert_eq!(profile.journal.bytes, expected);
    save(
        out,
        "profile-complete.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"EXECUTION_ONLY_BEFORE_REAL_PROVING","userCycles":profile.cycles(),"segmentCount":profile.segments.len(),"segmentPo2":profile.segments.iter().map(|s|s.po2).collect::<Vec<_>>(),"seconds":start.elapsed().as_secs_f64()}),
        )?,
    )?;
    save(
        out,
        "prover-started.json",
        &serde_json::to_vec_pretty(
            &json!({"stage":"REAL_PROVING_WITH_SUCCINCT_COMPRESSION_REQUESTED","assumptionsSupplied":0,"expectedProgramImage":IMAGE}),
        )?,
    )?;
    let started = Instant::now();
    let result = default_prover().prove_with_opts(
        super::accelerated_bn254::bounded_env(&input, CYCLES)?,
        &p,
        &ProverOpts::succinct(),
    );
    let info = match result {
        Ok(info) => info,
        Err(e) => {
            save(
                out,
                "prover-error.json",
                &serde_json::to_vec_pretty(
                    &json!({"stage":"PROVE_WITH_SUCCINCT_OPTS_FAILED","seconds":started.elapsed().as_secs_f64(),"error":format!("{e:#}")}),
                )?,
            )?;
            return Err(e.into());
        }
    };
    save(
        out,
        "candidate-receipt.bin",
        &bincode::serialize(&info.receipt)?,
    )?;
    save(
        out,
        "proof-stats.json",
        &serde_json::to_vec_pretty(&info.stats)?,
    )?;
    verify_receipt(&info.receipt, &expected)?;
    assert_eq!(info.stats.user_cycles, profile.cycles());
    let receipt = bincode::serialize(&info.receipt)?;
    save(out, "classifier-receipt.bin", &receipt)?;
    save(out, "classifier-journal.bin", &info.receipt.journal.bytes)?;
    save(
        out,
        "proof-complete.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"REAL_SUCCINCT_CLASSIFIER_RECEIPT","expectedProgramImage":IMAGE,"proofSeconds":started.elapsed().as_secs_f64(),"stats":info.stats,"receiptBytes":receipt.len(),"receiptSha256":sha(&receipt),"noUnresolvedAssumptions":true,"developmentMode":false,"hostVerified":true}),
        )?,
    )
}
fn verify(a: &[String]) -> Result<()> {
    if a.len() != 6 {
        return Err("verify EXPECTATIONS PROOF_OUTPUT NEW_VERIFICATION_OUTPUT".into());
    }
    let expectations = Path::new(&a[3]);
    let proof = Path::new(&a[4]);
    let out = Path::new(&a[5]);
    let e: Value = serde_json::from_slice(&fs::read(expectations.join("expectations.json"))?)?;
    assert_eq!(e["expectedProgramImage"], IMAGE);
    let expected = fs::read(expectations.join("expected-journal.bin"))?;
    assert_eq!(e["mainJournalSha256"], sha(&expected));
    let bytes = fs::read(proof.join("classifier-receipt.bin"))?;
    let r: Receipt = bincode::deserialize(&bytes)?;
    verify_receipt(&r, &expected)?;
    let ctx = VerifierContext::default().with_dev_mode(false);
    let mut wrong: [u8; 32] = image()?.into();
    wrong[0] ^= 1;
    assert!(r.verify_with_context(&ctx, Digest::from(wrong)).is_err());
    // Root, initial balance, native ID, outcome and final balance must all be
    // cryptographically bound by the actual seal, not just a JSON comparison.
    for offset in [0, 32, 44, 76, 166] {
        let mut tampered = r.clone();
        tampered.journal.bytes[offset] ^= 1;
        assert!(tampered.verify_with_context(&ctx, image()?).is_err());
    }
    fs::create_dir(out)?;
    save(
        out,
        "verification.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"SEPARATE_PROCESS_CRYPTOGRAPHIC_RECEIPT_VERIFICATION_NOT_TN10_SETTLEMENT","expectedProgramImage":IMAGE,"receiptSha256":sha(&bytes),"exactExpectedJournalVerified":true,"wrongExpectedImageCryptographicallyRejected":true,"tamperedJournalOffsetsCryptographicallyRejected":[0,32,44,76,166],"noUnresolvedAssumptions":true,"developmentMode":false}),
        )?,
    )
}
pub(super) fn run(a: &[String]) -> Result<()> {
    match a.get(2).map(String::as_str) {
        Some("prepare") => prepare(a),
        Some("prove") => produce(a),
        Some("verify") => verify(a),
        _ => Err("outer-proof-128m prepare|prove|verify ...".into()),
    }
}
