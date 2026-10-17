#![no_main]
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
#[derive(Serialize, Deserialize)]
struct WalletInput {
    native_id: [u8; 32],
    synthetic_secret: [u8; 32],
    amount: u64,
    pay: u64,
    change: u64,
    fee: u64,
}
risc0_zkvm::guest::entry!(main);
fn main() {
    let input: WalletInput = risc0_zkvm::guest::env::read();
    assert!(input.amount > 0);
    assert_eq!(
        input
            .pay
            .checked_add(input.change)
            .and_then(|n| n.checked_add(input.fee)),
        Some(input.amount)
    );
    risc0_zkvm::guest::env::commit_slice(&input.native_id);
    risc0_zkvm::guest::env::commit_slice(&Sha256::digest(input.synthetic_secret));
    // Only a representative private arithmetic/preimage relation. No note ownership,
    // membership, nullifier, ciphertext correctness or anonymity claim is made.
    let mut values = Vec::new();
    for n in [input.amount, input.pay, input.change, input.fee] {
        values.extend(n.to_le_bytes());
    }
    risc0_zkvm::guest::env::commit_slice(&Sha256::digest(values));
}
