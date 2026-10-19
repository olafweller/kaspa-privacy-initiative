//! Public negative fixture: retain genuine proof points; change the bound nullifier.
use kpi_private_native::{chain, wallet::protocol::Operation};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a: Vec<_> = std::env::args().collect();
    let mut op: Operation = serde_json::from_slice(&std::fs::read(&a[1])?)?;
    op.statement.nullifier[0] ^= 1;
    let payload = chain::operation_payload(&op, [0; 32])?;
    println!(
        "{}",
        serde_json::json!({"operationId":hex::encode(op.statement.id()),"operationPayloadHex":hex::encode(payload),"mutation":"one nullifier bit, unchanged genuine proof points"})
    );
    Ok(())
}
