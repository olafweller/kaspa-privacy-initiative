#![no_main]
risc0_zkvm::guest::entry!(main);
fn main() {
    let input: kpi_lane_common::Input = risc0_zkvm::guest::env::read();
    let result = kpi_lane_common::execute(&input);
    risc0_zkvm::guest::env::commit_slice(&kpi_lane_common::journal(&input, &result));
}
