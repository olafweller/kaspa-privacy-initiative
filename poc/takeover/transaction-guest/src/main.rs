#![no_main]
risc0_zkvm::guest::entry!(main);
fn main() {
    let input:kpi_takeover_common::Input=risc0_zkvm::guest::env::read();
    let (_,journal)=kpi_takeover_common::execute(&input);
    risc0_zkvm::guest::env::commit_slice(&journal);
}
