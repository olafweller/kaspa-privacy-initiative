//! Bounded, fixed PR56 proof driver. No guest/relation/policy changes or RPC.
use kpi_private_note_proof as trusted;
use kpi_recovery_native::{
    self as app, chain, lane,
    wallet::{protocol::*, ProofVerifier},
    AcceleratedVerifier, Input, Output, State,
};
use risc0_zkvm::{default_prover, ExecutorEnv, ProverOpts};
use serde_json::{json, Value};
use std::{fs, path::Path, time::Instant};
type Result<T> = trusted::Result<T>;
mod fixtures;
#[allow(dead_code)]
#[path = "../../../recovery-native/host/src/native.rs"]
mod native;
#[cfg(test)]
#[path = "../../../recovery-native/host/src/tests.rs"]
mod native_tests;
#[allow(dead_code)]
#[path = "../../../recovery-native/host/src/receipt.rs"]
mod receipt;
#[allow(dead_code)]
#[path = "../../../recovery-native/host/src/fixtures.rs"]
mod reviewed_fixtures;

const IMAGE: &str = "095a2fb2f58c350ccd2688ae7f72748c915bd973c60fd4abaa8d87b282ad68b5";
const PROGRAM_SHA: &str = "6039c3ef645d620bdd7eef6384750e73f51bcc8f9182aae1b1ac3c963601e75b";
fn verifier() -> AcceleratedVerifier {
    AcceleratedVerifier::checked(
        include_bytes!("../../../private-note-chain/pins/vk.bin"),
        *include_bytes!("../../../private-note-chain/pins/vk-id.bin"),
    )
    .unwrap()
}
fn report(out: &Path, name: &str, value: &Value) -> Result<()> {
    trusted::save(out, name, &serde_json::to_vec_pretty(value)?)
}
#[allow(dead_code)]
fn save<T: serde::Serialize>(out: &Path, name: &str, value: &T) -> Result<()> {
    trusted::save(out, name, &bincode::serialize(value)?)
}
fn target(case: &str) -> Result<(Value, Vec<u8>, u32)> {
    if !fixtures::STAGES.contains(&case) {
        return Err("unknown fixed batch".into());
    }
    let targets: Value = serde_json::from_str(include_str!(
        "../../../recovery-native/evidence/targets.json"
    ))?;
    if targets["expectedProgramImage"] != IMAGE || targets["expectedJoinControl"] != trusted::JOIN {
        return Err("compiled proof identities".into());
    }
    let b = targets["batches"][case].clone();
    let po2 = if case == "deposit" || case.ends_with("reconcile") {
        16
    } else {
        20
    };
    if b["segmentPo2"] != po2 {
        return Err("fixed segment profile".into());
    }
    Ok((b, receipt::target(case)?, po2))
}
fn package(case: &str, dir: &Path) -> Result<(Vec<u8>, Vec<u8>, u32)> {
    let (b, journal, po2) = target(case)?;
    let program = fs::read(dir.join("guest.program.bin"))?;
    let input = fs::read(dir.join(format!("{case}.input.bin")))?;
    if trusted::sha(&program) != PROGRAM_SHA
        || risc0_zkvm::compute_image_id(&program)?.to_string() != IMAGE
        || trusted::sha(&input) != b["inputSha256"].as_str().ok_or("input pin")?
        || fs::read(dir.join(format!("{case}.journal.bin")))? != journal
    {
        return Err("fixed public package mismatch".into());
    }
    Ok((program, input, po2))
}
fn verify(case: &str, path: &Path, out: &Path) -> Result<()> {
    let r = trusted::read_receipt(path)?;
    receipt::verify(case, &r)?;
    let negatives = trusted::crypto_negatives(&r, trusted::digest(IMAGE)?)?;
    fs::create_dir(out)?;
    report(
        out,
        "verification.json",
        &json!({"scope":"SIX_BATCH_INDEPENDENT_PROCESS_CPU_VERIFICATION_NOT_TN10",
        "case":case,"programImage":IMAGE,"controlId":trusted::JOIN,
        "receiptSha256":trusted::sha(&fs::read(path)?),"exactJournalVerified":true,
        "developmentMode":false,"noUnresolvedAssumptions":true,"negativeControls":negatives}),
    )
}
fn native_exit(case: &str, path: &Path, out: &Path) -> Result<()> {
    // The reused entrypoint checks the real new receipt BEFORE touching native
    // state. Both issued IDs and payout IDs must match the corrected captures.
    receipt::issuance(case, path, out)?;
    let index = match case {
        "bob-exit" => 2,
        "alice-exit" => 4,
        _ => return Err("exit stage".into()),
    };
    let p = fixtures::scenarios()?;
    let registered = app::apply(
        &p.cases[index].2.state,
        &native::lane_tx(&p.templates[index]),
        &verifier(),
    )?
    .0;
    let eid = *registered.permissions.keys().next().ok_or("permission")?;
    let (payout, _) = native::payout(&registered, eid, "")?;
    let mut negatives = vec![];
    for attack in [
        "underpay",
        "wrong-recipient",
        "default-lane",
        "foreign-reserve",
        "extra-sponsor-input",
        "extra-sponsor-output",
        "partial",
        "partial-three-outputs",
    ] {
        let (tx, entries) = native::payout(&registered, eid, attack)?;
        let result = native::scripts(&tx, &entries)?;
        match result {
            Err(
                kaspa_txscript_errors::TxScriptError::VerifyError
                | kaspa_txscript_errors::TxScriptError::EvalFalse,
            ) => (),
            _ => {
                return Err(
                    format!("native semantic rejection required: {attack}: {result:?}").into(),
                )
            }
        }
        negatives.push(attack);
    }
    if case == "alice-exit" {
        use kaspa_consensus_core::tx::{ScriptPublicKey, TransactionOutput};
        let (mut tx, mut entries) = native::payout(&registered, eid, "")?;
        tx.outputs.insert(
            1,
            TransactionOutput::new(
                0,
                ScriptPublicKey::new(0, app::delegate(&registered.covenant).into()),
            ),
        );
        native::sign_sponsor(&mut tx, &mut entries)?;
        if !matches!(
            native::scripts(&tx, &entries)?,
            Err(kaspa_txscript_errors::TxScriptError::VerifyError
                | kaspa_txscript_errors::TxScriptError::EvalFalse)
        ) {
            return Err("zero reserve output must fail semantically".into());
        }
        negatives.push("zero-reserve-output");
    }
    report(
        out,
        "native-identities-and-negatives.json",
        &json!({"stage":case,
        "frozenPermissionTransactionId":p.templates[index].id().to_string(),
        "frozenPayoutTransactionId":payout.id().to_string(),"negativeVariants":negatives,
        "syntheticChainContext":true,"newReceiptRequired":true,"nativeBroadcast":false}),
    )
}
fn prove(case: &str, dir: &Path, out: &Path) -> Result<()> {
    let (program, input, po2) = package(case, dir)?;
    fs::create_dir(out)?;
    report(
        out,
        "started.json",
        &json!({"case":case,"segmentPo2":po2,
        "cycleLimit":160000000,"aggregateExternalProcessGroupDeadlineRequired":true,
        "automaticRetries":false}),
    )?;
    let mut env = ExecutorEnv::builder();
    env.write_slice(&[u32::try_from(input.len())?])
        .write_slice(&input)
        .segment_limit_po2(po2)
        .session_limit(Some(160_000_000));
    let start = Instant::now();
    let info = default_prover().prove_with_opts(env.build()?, &program, &ProverOpts::succinct())?;
    let bytes = bincode::serialize(&info.receipt)?;
    // Preserve a returned candidate before verification or stats can fail.
    trusted::save(out, "candidate-receipt.bin", &bytes)?;
    report(out, "stats.json", &serde_json::to_value(&info.stats)?)?;
    receipt::verify(case, &info.receipt)?;
    if info.stats.user_cycles > 160_000_000 || start.elapsed().as_secs_f64() >= 3600.0 {
        return Err("proof budget exceeded".into());
    }
    trusted::save(out, "receipt.bin", &bytes)?;
    trusted::save(out, "journal.bin", &info.receipt.journal.bytes)?;
    report(
        out,
        "complete.json",
        &json!({"seconds":start.elapsed().as_secs_f64(),
        "receiptSha256":trusted::sha(&bytes),"independentCPUVerificationStillRequired":true,
        "actualTN10Settlement":false}),
    )
}
fn main() -> Result<()> {
    if std::env::var_os("RISC0_DEV_MODE").is_some() {
        return Err("development mode forbidden".into());
    }
    let a: Vec<_> = std::env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("check-native-context") if a.len()==2 => {
            let p = fixtures::scenarios()?;
            let mut rows = vec![];
            for index in [2,4] {
                let registered=app::apply(&p.cases[index].2.state,&native::lane_tx(&p.templates[index]),&verifier())?.0;
                let eid=*registered.permissions.keys().next().ok_or("permission")?;
                let (tx,entries)=native::payout(&registered,eid,"")?;
                native::scripts(&tx,&entries)??;
                let captured=&p.cases[index+1].1.lane.blocks[0].txs[1];
                assert_eq!(tx.id().as_bytes(),vprogs_l1_utils::tx_id_v1(&captured.payload,&captured.rest));
                rows.push(json!({"stage":fixtures::STAGES[index],"permissionId":p.templates[index].id().to_string(),"payoutId":tx.id().to_string()}));
            }
            println!("{}",json!({"scope":"EMBEDDED_PUBLIC_SYNTHETIC_NATIVE_CONTEXT_ONLY_NO_ISSUANCE_PROOF","rows":rows,"runtimeCorpusFilesNeeded":false}));
            Ok(())
        },
        Some("check-target") if a.len()==4 => { package(&a[2],Path::new(&a[3]))?; println!("fixed public target verified; no proof started"); Ok(()) },
        Some("verify-receipt") if a.len()==5 => verify(&a[2],Path::new(&a[3]),Path::new(&a[4])),
        Some("verify-native-exit") if a.len()==5 => native_exit(&a[2],Path::new(&a[3]),Path::new(&a[4])),
        Some("prove") if a.len()==5 => prove(&a[2],Path::new(&a[3]),Path::new(&a[4])),
        _ => Err("check-target CASE INPUTS | verify-receipt CASE RECEIPT NEW_OUT | verify-native-exit EXIT_CASE RECEIPT NEW_OUT | prove CASE INPUTS NEW_OUT".into())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn fixed_six_targets_keep_segment_profiles_and_reject_fakes() {
        let embedded = fixtures::scenarios().unwrap();
        let regenerated = reviewed_fixtures::scenarios().unwrap();
        for (e, r) in embedded.cases.iter().zip(&regenerated.cases) {
            assert_eq!(
                bincode::serialize(&e.1).unwrap(),
                bincode::serialize(&r.1).unwrap()
            );
            assert_eq!(
                bincode::serialize(&e.2).unwrap(),
                bincode::serialize(&r.2).unwrap()
            );
        }
        assert_eq!(
            bincode::serialize(&embedded.templates).unwrap(),
            bincode::serialize(&regenerated.templates).unwrap()
        );
        let dir =
            Path::new(env!("CARGO_MANIFEST_DIR")).join("../../recovery-native/evidence/fixtures");
        for case in fixtures::STAGES {
            let (_, _, po2) = package(case, &dir).unwrap();
            assert_eq!(
                po2,
                if case == "deposit" || case.ends_with("reconcile") {
                    16
                } else {
                    20
                }
            );
            let fake = risc0_zkvm::Receipt::new(
                risc0_zkvm::InnerReceipt::Fake(risc0_zkvm::FakeReceipt::new(
                    risc0_zkvm::ReceiptClaim::ok(
                        trusted::digest(IMAGE).unwrap(),
                        receipt::target(case).unwrap(),
                    ),
                )),
                receipt::target(case).unwrap(),
            );
            assert!(receipt::verify(case, &fake).is_err());
        }
        assert!(target("old-exit").is_err());
    }
}
