//! Local execution/native preparation. No wallet secret, RPC or provider client.
use kpi_recovery_native::{
    self as app, chain, lane,
    wallet::{protocol::*, ProofVerifier},
    AcceleratedVerifier, Input, Output, State,
};
use serde_json::json;
use std::{fs, path::Path, time::Instant};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
mod fixtures;
#[allow(dead_code)]
mod native;
#[cfg(feature = "proof")]
mod receipt;
#[cfg(test)]
mod tests;
fn verifier() -> AcceleratedVerifier {
    AcceleratedVerifier::checked(
        include_bytes!("../../../private-note-chain/pins/vk.bin"),
        *include_bytes!("../../../private-note-chain/pins/vk-id.bin"),
    )
    .unwrap()
}
fn report(out: &Path, name: &str, v: &serde_json::Value) -> Result<()> {
    fs::write(out.join(name), serde_json::to_vec_pretty(v)?)?;
    Ok(())
}
fn save<T: serde::Serialize>(out: &Path, name: &str, v: &T) -> Result<()> {
    fs::write(out.join(name), bincode::serialize(v)?)?;
    Ok(())
}
fn profile(program: &Path, fixtures: &Path, name: &str, out: &Path) -> Result<()> {
    use risc0_zkvm::{compute_image_id, default_executor, ExecutorEnv};
    fs::create_dir(out)?;
    let bytes = fs::read(program)?;
    let id = compute_image_id(&bytes)?.to_string();
    assert_eq!(
        id,
        include_str!("../../evidence/expected-image.txt").trim(),
        "compiled program identity"
    );
    let raw = fs::read(fixtures.join(format!("{name}.input.bin")))?;
    let mut b = ExecutorEnv::builder();
    let small = !name.contains("credit-transfer")
        && !["bob-exit", "alice-exit", "wallet-replay"].contains(&name);
    let po2 = if small { 16 } else { 20 };
    b.write_slice(&[raw.len() as u32])
        .write_slice(&raw)
        .segment_limit_po2(po2)
        .session_limit(Some(app::CYCLE_LIMIT));
    let started = Instant::now();
    let result = default_executor().execute(b.build()?, &bytes);
    let abort = fixtures.join(format!("{name}.abort.txt"));
    if abort.exists() {
        let expected = fs::read_to_string(abort)?;
        let error = result.err().ok_or("required guest abort completed")?;
        let message = format!("{error:#}");
        if !message.starts_with("Guest panicked:") || !message.contains(expected.trim()) {
            return Err(error.into());
        }
        report(
            out,
            "report.json",
            &json!({"scope":"ACTUAL_GUEST_SEMANTIC_ABORT_NOT_RESOURCE_FAILURE","case":name,"expectedImage":id,"expectedAbortReason":expected.trim(),"expectedAbortConfirmed":true,"error":message,"seconds":started.elapsed().as_secs_f64()}),
        )?;
        return Ok(());
    }
    let session = result?;
    let expected: Output =
        bincode::deserialize(&fs::read(fixtures.join(format!("{name}.expected.bin")))?)?;
    if fixtures::STAGES.contains(&name) {
        #[cfg(feature = "proof")]
        assert_eq!(
            expected.journal,
            receipt::target(name)?,
            "compiled full journal"
        );
        let targets: serde_json::Value =
            serde_json::from_str(include_str!("../../evidence/targets.json"))?;
        assert_eq!(
            hex::encode(hash(&raw)),
            targets["batches"][name]["inputSha256"].as_str().unwrap(),
            "compiled input hash"
        );
    }
    assert_eq!(
        session.journal.bytes, expected.journal,
        "complete expected journal"
    );
    if fixtures::STAGES.contains(&name) {
        assert!(session.segments.len() > 1, "join receipt profile");
    }
    fs::write(out.join("journal.bin"), &session.journal.bytes)?;
    report(
        out,
        "report.json",
        &json!({"scope":"NEW_GUEST_EXECUTION_ONLY_NO_RECEIPT","case":name,"expectedImage":id,"userCycles":session.cycles(),"segments":session.segments.len(),"segmentPo2":po2,"seconds":started.elapsed().as_secs_f64(),"journalSha256":hex::encode(hash(&session.journal.bytes)),"exactExpectedJournalMatched":true,"cycleLimit":app::CYCLE_LIMIT,"developmentMode":false}),
    )
}
fn check_package(dir: &Path) -> Result<()> {
    let program = fs::read(dir.join("guest.program.bin"))?;
    assert_eq!(
        risc0_zkvm::compute_image_id(&program)?.to_string(),
        include_str!("../../evidence/expected-image.txt").trim()
    );
    let p = fixtures::scenarios()?;
    for (name, input, expected) in &p.cases {
        assert_eq!(
            fs::read(dir.join(format!("{name}.input.bin")))?,
            bincode::serialize(input)?
        );
        assert_eq!(
            fs::read(dir.join(format!("{name}.expected.bin")))?,
            bincode::serialize(expected)?
        );
        assert_eq!(
            fs::read(dir.join(format!("{name}.journal.bin")))?,
            expected.journal
        );
        #[cfg(feature = "proof")]
        assert_eq!(receipt::target(name)?, expected.journal);
    }
    let history = load_history(dir)?;
    fixtures::require_single_spend(&history)?;
    let retained: serde_json::Value =
        serde_json::from_slice(&fs::read(dir.join("native-history.json"))?)?;
    assert_eq!(
        history, retained,
        "retained native history / actual input bytes"
    );
    println!("Six fixed inputs, full journals, state/tip/native-template continuity and guest identity match; no new guest execution or proof.");
    Ok(())
}
fn load_history(dir: &Path) -> Result<serde_json::Value> {
    let inputs: Vec<(String, Input)> = fixtures::STAGES
        .iter()
        .map(|name| {
            Ok((
                name.to_string(),
                bincode::deserialize(&fs::read(dir.join(format!("{name}.input.bin")))?)?,
            ))
        })
        .collect::<Result<_>>()?;
    fixtures::native_history(inputs.iter().map(|(name, input)| (name.as_str(), input)))
}
fn check_history(dir: &Path) -> Result<()> {
    let history = load_history(dir)?;
    println!("{}", serde_json::to_string_pretty(&history)?);
    fixtures::require_single_spend(&history)
}
fn main() -> Result<()> {
    if std::env::var_os("RISC0_DEV_MODE").is_some() {
        return Err("development mode forbidden".into());
    }
    let args: Vec<_> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("prepare") if args.len()==3=>fixtures::prepare(Path::new(&args[2])),
        Some("check-package") if args.len()==3=>check_package(Path::new(&args[2])),
        Some("check-history") if args.len()==3=>check_history(Path::new(&args[2])),
        Some("profile") if args.len()==6=>profile(Path::new(&args[2]),Path::new(&args[3]),&args[4],Path::new(&args[5])),
        #[cfg(feature="proof")]
        Some("verify") if args.len()==4=>receipt::verify_file(&args[2],Path::new(&args[3])),
        #[cfg(feature="proof")]
        Some("native-issuance") if args.len()==5=>receipt::issuance(&args[2],Path::new(&args[3]),Path::new(&args[4])),
        _=>Err("usage: prepare NEW_OUT | profile PROGRAM FIXTURES CASE NEW_OUT | verify STAGE RECEIPT | native-issuance EXIT_STAGE RECEIPT NEW_OUT (no proving command)".into())
    }
}
