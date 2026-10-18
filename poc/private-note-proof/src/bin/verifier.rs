//! Separate executable/process; does not accept GPU-selected expectations.
use kpi_private_note_proof::*;
use std::{fs, path::Path};
fn main() -> Result<()> {
    assert!(
        std::env::var_os("RISC0_DEV_MODE").is_none(),
        "development mode forbidden"
    );
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 4 || a[1] != "verify-receipt" {
        return Err("verify-receipt RECEIPT NEW_OUTPUT".into());
    }
    let path = Path::new(&a[2]);
    let r = read_receipt(path)?;
    verify(&r)?;
    let negatives = crypto_negatives(&r, digest(IMAGE)?)?;
    let out = Path::new(&a[3]);
    fs::create_dir(out)?;
    save(
        out,
        "verification.json",
        &serde_json::to_vec_pretty(&serde_json::json!({
        "scope":"INDEPENDENT_CPU_PRIVATE_NOTE_RECEIPT_NOT_TN10_SETTLEMENT", "expectedProgramImage":IMAGE,
        "expectedControlId":JOIN,"receiptSha256":sha(&fs::read(path)?),"journalSha256":JOURNAL_SHA,
        "journalBytes":352,"exactExpectedJournalVerified":true,"noUnresolvedAssumptions":true,
        "developmentMode":false,"negativeControls":negatives}))?,
    )?;
    Ok(())
}
