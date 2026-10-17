#![no_main]
risc0_zkvm::guest::entry!(main);
fn main() {
    let input: kpi_native_common::Input = risc0_zkvm::guest::env::read();
    let output = kpi_native_common::execute(&input);
    // Operational padding keeps short intervals on the historical fixed lift-20
    // verifier. cycle_count is host supplied: NEVER used for application validity.
    // The actual receipt control identity is still checked by the covenant.
    while risc0_zkvm::guest::env::cycle_count() < 600_000 {
        std::hint::black_box(1u32.wrapping_add(1));
    }
    risc0_zkvm::guest::env::commit_slice(&kpi_native_common::journal(&input, &output));
}
