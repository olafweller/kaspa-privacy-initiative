//! Diagnostic partial proofs only; never a full-classifier receipt substitute.
use super::*;
use risc0_zkvm::{
    sha::{Digestible, Sha256},
    ApiClient, Asset, AssetRequest, ReceiptClaim, SegmentReceipt, SuccinctReceipt, VerifierContext,
};

const IMAGE: &str = "397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716";
const SELECTED: [usize; 2] = [24, 25];
fn sha(b: &[u8]) -> String {
    risc0_zkvm::sha::Impl::hash_bytes(b).to_string()
}
fn context() -> VerifierContext {
    VerifierContext::default().with_dev_mode(false)
}
fn json_save(out: &Path, name: &str, v: Value) -> Result<()> {
    save(out, name, &serde_json::to_vec_pretty(&v)?)
}
fn export(a: &[String]) -> Result<()> {
    if a.len() != 9 {
        return Err(
            "export PROGRAMS FIXTURES EXPECTATIONS QUALIFICATION NEW_OUTPUT OLD_TRACES".into(),
        );
    }
    let out = Path::new(&a[7]);
    let expected = super::outer_proof_128m::gate(
        Path::new(&a[3]),
        Path::new(&a[4]),
        Path::new(&a[5]),
        Path::new(&a[6]),
    )?;
    let program = super::outer_proof_128m::program(Path::new(&a[3]))?;
    let input = fs::read(Path::new(&a[4]).join("valid-invalid-valid.bin"))?;
    fs::create_dir(out)?;
    let segments = out.join("segments");
    fs::create_dir(&segments)?;
    save(out, "program.bin", &program)?;
    save(out, "input.bin", &input)?;
    save(out, "expected-journal.bin", &expected)?;
    let mut rows = vec![];
    let mut user_cycle = 0u64;
    let old = Path::new(&a[8]);
    let client = ApiClient::from_env()?;
    let start = Instant::now();
    let session = client.execute(
        &super::accelerated_bn254::bounded_env(&input, 128_000_000)?,
        Asset::Inline(program.clone().into()),
        AssetRequest::Path(segments.canonicalize()?),
        |info, asset| {
            let i = rows.len();
            let bytes = asset.as_bytes()?;
            // SDK export names are not FileSegmentRef's N.bincode names.
            // Normalize explicitly instead of assuming an SDK output filename.
            fs::write(segments.join(format!("{i}.bincode")), &bytes)?;
            let old_bytes = fs::read(old.join(format!("{i}.bincode"))).ok();
            rows.push(json!({"index":i,"po2":info.po2,"userCycles":info.cycles,
                "userCycleStart":user_cycle,"userCycleEnd":user_cycle+u64::from(info.cycles),
                "assetSha256":sha(&bytes),"assetBytes":bytes.len(),
                "oldTraceSha256":old_bytes.as_ref().map(|b|sha(b)),
                "oldTraceByteMatch":old_bytes.as_deref()==Some(bytes.as_ref())}));
            user_cycle += u64::from(info.cycles);
            Ok(())
        },
    )?;
    assert_eq!(session.journal.bytes, expected);
    assert_eq!(session.cycles(), 117_473_222);
    assert_eq!(rows.len(), 121);
    let image = hex::decode(IMAGE)?;
    let image: risc0_zkvm::sha::Digest = image.as_slice().try_into()?;
    let claim = session
        .receipt_claim
        .as_ref()
        .ok_or("missing session claim")?;
    assert_eq!(
        claim.digest(),
        ReceiptClaim::ok(image, expected.clone()).digest()
    );
    for i in SELECTED {
        assert_eq!(rows[i]["po2"], 20);
        assert!(rows[i]["userCycleStart"].as_u64().unwrap() > 16_090_400);
        assert!(rows[i]["userCycleEnd"].as_u64().unwrap() < 40_494_407);
    }
    save(out, "session-claim.bin", &bincode::serialize(&claim)?)?;
    json_save(
        out,
        "session.json",
        json!({
        "scope":"EXECUTION_ASSETS_NOT_PROOFS", "expectedProgramImage":IMAGE,
        "programSha256":sha(&program),"inputSha256":sha(&input),
        "journalSha256":sha(&expected),"sessionClaimDigest":claim.digest().to_string(),
        "userCycles":session.cycles(),"segments":rows,"selected":SELECTED,
        "seconds":start.elapsed().as_secs_f64(),"oldTraceDirectory":old,
        "partialProofBinding":"Trusted pinned SDK execution/export and asset hashes; no full-session proof"}),
    )
}
fn manifest(out: &Path) -> Result<Value> {
    let m: Value = serde_json::from_slice(&fs::read(out.join("session.json"))?)?;
    assert_eq!(m["expectedProgramImage"], IMAGE);
    assert_eq!(m["selected"], json!(SELECTED));
    let program = fs::read(out.join("program.bin"))?;
    assert_eq!(compute_image_id(&program)?.to_string(), IMAGE);
    assert_eq!(m["programSha256"], sha(&program));
    assert_eq!(m["inputSha256"], sha(&fs::read(out.join("input.bin"))?));
    assert_eq!(
        m["journalSha256"],
        sha(&fs::read(out.join("expected-journal.bin"))?)
    );
    Ok(m)
}
fn segment_check(r: &SegmentReceipt) -> Result<()> {
    r.verify_integrity_with_context(&context())?;
    let mut bad = r.clone();
    bad.seal[0] ^= 1;
    assert!(bad.verify_integrity_with_context(&context()).is_err());
    let mut bad = r.clone();
    bad.claim.pre = risc0_zkvm::MaybePruned::Pruned(risc0_zkvm::sha::Digest::ZERO);
    assert!(bad.verify_integrity_with_context(&context()).is_err());
    Ok(())
}
fn succinct_check(r: &SuccinctReceipt<ReceiptClaim>, expected: &ReceiptClaim) -> Result<()> {
    r.verify_integrity_with_context(&context())?;
    assert_eq!(r.claim.digest(), expected.digest());
    let mut bad = r.clone();
    bad.seal[0] ^= 1;
    assert!(bad.verify_integrity_with_context(&context()).is_err());
    let mut bad = r.clone();
    bad.claim = ReceiptClaim::ok(risc0_zkvm::sha::Digest::ZERO, vec![]).into();
    assert!(bad.verify_integrity_with_context(&context()).is_err());
    Ok(())
}
fn read_segment(out: &Path, i: usize) -> Result<SegmentReceipt> {
    let r: SegmentReceipt = bincode::deserialize(&fs::read(out.join(format!("segment-{i}.bin")))?)?;
    assert_eq!(r.index, i as u32);
    segment_check(&r)?;
    Ok(r)
}
fn read_lift(out: &Path, i: usize) -> Result<SuccinctReceipt<ReceiptClaim>> {
    let r = bincode::deserialize(&fs::read(out.join(format!("lift-{i}.bin")))?)?;
    succinct_check(&r, &read_segment(out, i)?.claim)?;
    Ok(r)
}
fn segment(out: &Path, i: usize) -> Result<()> {
    assert!(SELECTED.contains(&i));
    let m = manifest(out)?;
    let file = out.join(format!("segments/{i}.bincode"));
    assert_eq!(m["segments"][i]["assetSha256"], sha(&fs::read(&file)?));
    json_save(
        out,
        &format!("segment-{i}-started.json"),
        json!({"stage":"prove_segment","index":i,"assetSha256":m["segments"][i]["assetSha256"]}),
    )?;
    let t = Instant::now();
    let r = ApiClient::from_env()?.prove_segment(
        &ProverOpts::succinct(),
        Asset::Path(file.canonicalize()?),
        AssetRequest::Inline,
    )?;
    let api_seconds = t.elapsed().as_secs_f64();
    save(out, &format!("segment-{i}.bin"), &bincode::serialize(&r)?)?;
    assert_eq!(r.index, i as u32);
    segment_check(&r)?;
    json_save(
        out,
        &format!("segment-{i}-verified.json"),
        json!({
        "scope":"VERIFIED_PARTIAL_SEGMENT_ONLY", "index":i,"apiSeconds":api_seconds,
        "stageSecondsIncludingVerification":t.elapsed().as_secs_f64(),
        "claimDigest":r.claim.digest().to_string(),"claim":r.claim,
        "receiptSha256":sha(&bincode::serialize(&r)?),"sealBytes":r.seal_size(),
        "sealAndClaimMutationRejected":true}),
    )
}
fn lift(out: &Path, i: usize) -> Result<()> {
    assert!(SELECTED.contains(&i));
    manifest(out)?;
    let s = read_segment(out, i)?;
    json_save(
        out,
        &format!("lift-{i}-started.json"),
        json!({"stage":"lift","index":i,"claimDigest":s.claim.digest().to_string()}),
    )?;
    let t = Instant::now();
    let r = ApiClient::from_env()?.lift(
        &ProverOpts::succinct(),
        s.clone().try_into()?,
        AssetRequest::Inline,
    )?;
    let api_seconds = t.elapsed().as_secs_f64();
    save(out, &format!("lift-{i}.bin"), &bincode::serialize(&r)?)?;
    succinct_check(&r, &s.claim)?;
    json_save(
        out,
        &format!("lift-{i}-verified.json"),
        json!({
        "scope":"VERIFIED_LIFT_OF_PARTIAL_SEGMENT_ONLY","index":i,"apiSeconds":api_seconds,
        "stageSecondsIncludingVerification":t.elapsed().as_secs_f64(),
        "claimDigest":r.claim.digest().to_string(),"receiptSha256":sha(&bincode::serialize(&r)?),
        "sealAndClaimMutationRejected":true}),
    )
}
fn join(out: &Path) -> Result<()> {
    manifest(out)?;
    let left = read_lift(out, 24)?;
    let right = read_lift(out, 25)?;
    let l = left.claim.as_value()?;
    let r = right.claim.as_value()?;
    assert_eq!(l.post.digest(), r.pre.digest());
    assert_ne!(
        r.post.digest(),
        l.pre.digest(),
        "reversed inputs must fail continuity"
    );
    let expected = l.join(r);
    json_save(
        out,
        "join-started.json",
        json!({"stage":"join","indices":SELECTED,"expectedClaimDigest":expected.digest().to_string()}),
    )?;
    let t = Instant::now();
    let joined = ApiClient::from_env()?.join(
        &ProverOpts::succinct(),
        left.try_into()?,
        right.try_into()?,
        AssetRequest::Inline,
    )?;
    let api_seconds = t.elapsed().as_secs_f64();
    save(out, "join.bin", &bincode::serialize(&joined)?)?;
    succinct_check(&joined, &expected)?;
    json_save(
        out,
        "join-verified.json",
        json!({
        "scope":"VERIFIED_TWO_SEGMENT_SPAN_NOT_FULL_CLASSIFIER", "indices":SELECTED,
        "apiSeconds":api_seconds,"stageSecondsIncludingVerification":t.elapsed().as_secs_f64(),
        "claimDigest":joined.claim.digest().to_string(),"expectedClaim":expected,
        "receiptSha256":sha(&bincode::serialize(&joined)?),"sealAndClaimMutationRejected":true}),
    )
}
fn verify(out: &Path) -> Result<()> {
    let m = manifest(out)?;
    for i in SELECTED {
        assert_eq!(
            m["segments"][i]["assetSha256"],
            sha(&fs::read(out.join(format!("segments/{i}.bincode")))?)
        );
        read_lift(out, i)?;
    }
    let left = read_segment(out, 24)?.claim;
    let right = read_segment(out, 25)?.claim;
    assert_eq!(left.post.digest(), right.pre.digest());
    let joined = bincode::deserialize(&fs::read(out.join("join.bin"))?)?;
    succinct_check(&joined, &left.join(&right))?;
    json_save(
        out,
        "separate-verification.json",
        json!({"verified":true,
        "scope":"FIVE_PARTIAL_RECEIPTS_NOT_FULL_CLASSIFIER","devMode":false,
        "segmentIndices":SELECTED,"exactJournalCheckedDuringExecutionOnly":true}),
    )
}
pub(super) fn run(a: &[String]) -> Result<()> {
    assert!(std::env::var_os("RISC0_DEV_MODE").is_none());
    let command = a.get(2).ok_or("missing diagnostic command")?.as_str();
    if command == "export" {
        return export(a);
    }
    let out = Path::new(a.get(3).ok_or("missing output directory")?);
    match command {
        "segment" | "lift" if a.len() == 5 => {
            let i = a[4].parse()?;
            if command == "segment" {
                segment(out, i)
            } else {
                lift(out, i)
            }
        }
        "join" if a.len() == 4 => join(out),
        "verify" if a.len() == 4 => verify(out),
        _ => Err("phase-diagnostics export|segment|lift|join|verify ...".into()),
    }
}
