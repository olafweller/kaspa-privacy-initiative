#![no_main]
use kpi_private_note_chain::{execute, AcceleratedVerifier, Input};
risc0_zkvm::guest::entry!(main);
fn main() {
    let n: u32 = risc0_zkvm::guest::env::read();
    assert!(n <= 1024 * 1024);
    let mut raw = vec![0; n as usize];
    risc0_zkvm::guest::env::read_slice(&mut raw);
    let input: Input = bincode::deserialize(&raw).unwrap();
    assert_eq!(
        bincode::serialize(&input).unwrap(),
        raw,
        "canonical execution input"
    );
    println!(
        "PROFILE authenticated_input {}",
        risc0_zkvm::guest::env::cycle_count()
    );
    let verifier = AcceleratedVerifier::pinned();
    println!(
        "PROFILE loaded_key {}",
        risc0_zkvm::guest::env::cycle_count()
    );
    let out = execute(&input, &verifier);
    risc0_zkvm::guest::env::commit_slice(&out.aggregate_journal);
}
