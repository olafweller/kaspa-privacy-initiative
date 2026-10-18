use kpi_private_note_proof::*;
use risc0_zkvm::{default_prover, ExecutorEnv, ProverOpts};
use serde_json::json;
use std::{fs, path::Path, time::Instant};
fn main() -> Result<()> {
    assert!(
        std::env::var_os("RISC0_DEV_MODE").is_none(),
        "development mode forbidden"
    );
    let a: Vec<_> = std::env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("check-target") if a.len() == 3 => {
            target(Path::new(&a[2]))?;
            println!(
                "{}",
                json!({"fixedTargetVerified":true,"image":IMAGE,"control":JOIN,"journalSha256":JOURNAL_SHA,"proofStarted":false})
            );
        }
        Some("prove") if a.len() == 4 => {
            let (p, i) = target(Path::new(&a[2]))?;
            let out = Path::new(&a[3]);
            fs::create_dir(out)?;
            save(
                out,
                "job-started.json",
                &serde_json::to_vec_pretty(&json!({"scope":"ONE_PRIVATE_NOTE_SUCCINCT_PROOF",
                "expectedProgramImage":IMAGE,"expectedControlId":JOIN,"cycleLimit":CYCLES,"wholeJobSecondsLimit":3600,
                "developmentMode":false,"assumptionsSupplied":0}))?,
            )?;
            let mut b = ExecutorEnv::builder();
            b.write_slice(&[u32::try_from(i.len())?])
                .write_slice(&i)
                .segment_limit_po2(20)
                .session_limit(Some(CYCLES));
            let start = Instant::now();
            let result = default_prover().prove_with_opts(b.build()?, &p, &ProverOpts::succinct());
            let info = match result {
                Ok(v) => v,
                Err(e) => {
                    save(
                        out,
                        "prover-error.json",
                        &serde_json::to_vec_pretty(
                            &json!({"error":format!("{e:#}"),"seconds":start.elapsed().as_secs_f64()}),
                        )?,
                    )?;
                    return Err(e.into());
                }
            };
            // Preserve the real returned artifact before any further assertion.
            let bytes = bincode::serialize(&info.receipt)?;
            save(out, "candidate-receipt.bin", &bytes)?;
            save(
                out,
                "proof-stats.json",
                &serde_json::to_vec_pretty(&info.stats)?,
            )?;
            verify(&info.receipt)?;
            assert!(info.stats.user_cycles <= CYCLES);
            assert!(start.elapsed().as_secs_f64() < 3600.0);
            save(out, "classifier-receipt.bin", &bytes)?;
            save(out, "classifier-journal.bin", &info.receipt.journal.bytes)?;
            save(
                out,
                "proof-complete.json",
                &serde_json::to_vec_pretty(&json!({"scope":"REAL_PRIVATE_NOTE_SUCCINCT_RECEIPT",
                "expectedProgramImage":IMAGE,"expectedControlId":JOIN,"receiptSha256":sha(&bytes),"receiptBytes":bytes.len(),
                "proofSeconds":start.elapsed().as_secs_f64(),"stats":info.stats,"developmentMode":false,
                "noUnresolvedAssumptions":true,"independentVerificationStillRequired":true}))?,
            )?;
        }
        _ => return Err("check-target PUBLIC_PACKAGE | prove PUBLIC_PACKAGE NEW_OUTPUT".into()),
    }
    Ok(())
}
