//! Read-only SDK re-verification of archived receipts. No executor, prover or RPC.
use risc0_zkvm::{compute_image_id, Receipt};
use serde_json::json;
use std::{error::Error, fs, path::Path};

fn main() -> Result<(), Box<dyn Error>> {
    assert!(
        std::env::var("RISC0_DEV_MODE").is_err(),
        "development mode forbidden"
    );
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 3 {
        return Err("PROGRAM_DIR PROOF_DIR".into());
    }
    let programs = Path::new(&args[1]);
    let proofs = Path::new(&args[2]);
    let mut receipts = Vec::new();
    let mut files = fs::read_dir(proofs)?.collect::<Result<Vec<_>, _>>()?;
    files.sort_by_key(|entry| entry.file_name());
    for entry in files {
        let name = entry.file_name();
        let name = name.to_str().ok_or("non-UTF8 filename")?;
        let Some(stem) = name.strip_suffix("-receipt.bin") else {
            continue;
        };
        let kind = if stem == "aggregate" {
            "aggregate"
        } else if stem.contains("-t") {
            "transaction"
        } else {
            "batch"
        };
        let image = compute_image_id(&fs::read(programs.join(format!("{kind}.program.bin")))?)?;
        let receipt: Receipt = bincode::deserialize(&fs::read(entry.path())?)?;
        receipt.inner.succinct()?; // Reject fake/development and non-succinct receipts.
        receipt.verify(image)?; // Includes the default verifier's empty-assumptions check.
        assert_eq!(
            receipt.journal.bytes,
            fs::read(proofs.join(format!("{stem}-journal.bin")))?
        );
        let mut changed = receipt.clone();
        let first = changed.journal.bytes.first_mut().ok_or("empty journal")?;
        *first ^= 1;
        assert!(changed.verify(image).is_err(), "changed journal accepted");
        let wrong = compute_image_id(&fs::read(programs.join(format!(
            "{}.program.bin",
            if kind == "transaction" {
                "batch"
            } else {
                "transaction"
            }
        )))?)?;
        assert!(receipt.verify(wrong).is_err(), "wrong program accepted");
        receipts.push(json!({"file":name,"kind":kind,"image":image.to_string(),
            "journalBytes":receipt.journal.bytes.len(),"changedJournalRejected":true,
            "wrongProgramRejected":true}));
    }
    if receipts.is_empty() {
        return Err("no receipts found".into());
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "scope":"OFFLINE_SDK_RECEIPT_REVERIFICATION_NOT_NEW_CHAIN_OBSERVATION",
            "developmentMode":false,"receipts":receipts
        }))?
    );
    Ok(())
}
