//! Offline receipt verification with public inputs only; no node, wallet or proving.
use kpi_native_common as app;
use risc0_zkvm::{compute_image_id, Receipt};
use serde_json::json;
use std::{error::Error, fs};
fn main() -> Result<(), Box<dyn Error>> {
    assert!(
        std::env::var("RISC0_DEV_MODE").is_err(),
        "development mode forbidden"
    );
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 4 {
        return Err("kpi-native-verify INPUT_JSON PROGRAM_BIN RECEIPT_BIN".into());
    }
    let input: app::Input = serde_json::from_slice(&fs::read(&a[1])?)?;
    let program = fs::read(&a[2])?;
    let receipt: Receipt = bincode::deserialize(&fs::read(&a[3])?)?;
    let image = compute_image_id(&program)?;
    receipt.verify(image)?;
    receipt.inner.succinct()?;
    let output = app::execute(&input);
    assert_eq!(receipt.journal.bytes, app::journal(&input, &output));
    println!(
        "{}",
        json!({"scope":"REAL_SDK_RECEIPT_AND_JOURNAL_REVERIFICATION",
        "image":image.to_string(),"journalBytes":receipt.journal.bytes.len(),
        "derivedSeq":hex::encode(output.lane.seq),"state":hex::encode(output.state.hash()),
        "permissionHash":hex::encode(output.permission_hash),"developmentMode":false,
        "nativeAnchorChecked":false})
    );
    Ok(())
}
