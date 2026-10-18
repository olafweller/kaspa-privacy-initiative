#![no_main]
use kpi_private_native::{execute, AcceleratedVerifier, Input};
risc0_zkvm::guest::entry!(main);
fn main() {
    let n: u32 = risc0_zkvm::guest::env::read();
    assert!(n <= 1024 * 1024);
    let mut raw = vec![0; n as usize];
    risc0_zkvm::guest::env::read_slice(&mut raw);
    let input: Input = bincode::deserialize(&raw).unwrap();
    assert_eq!(bincode::serialize(&input).unwrap(), raw, "canonical input");
    let out = execute(&input, &AcceleratedVerifier::pinned());
    risc0_zkvm::guest::env::commit_slice(&out.journal);
}
