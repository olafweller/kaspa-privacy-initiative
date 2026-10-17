#![no_main]
use substrate_bn::{pairing_batch, Fr, Group, Gt, G1, G2};
risc0_zkvm::guest::entry!(main);
fn main() {
    // Runtime input prevents constant folding. Exercise target-specific field
    // arithmetic and the library's real pairing path; this is not a wallet test.
    let n: u32 = risc0_zkvm::guest::env::read();
    assert_eq!(n, 7);
    let x = Fr::from_str(&n.to_string()).unwrap();
    let p = G1::one() * x;
    let q = G2::one() * x;
    let start = risc0_zkvm::guest::env::cycle_count();
    assert!(pairing_batch(&[(p, q), (-p, q)]) == Gt::one());
    let cycles = risc0_zkvm::guest::env::cycle_count() - start;
    println!("SMOKE pairing cycles {cycles}");
    risc0_zkvm::guest::env::commit_slice(b"KPI-BN254-SMOKE-OK");
}
