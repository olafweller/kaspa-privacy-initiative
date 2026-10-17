#![no_main]
#[path = "../../types.rs"]
mod types;
include!("../../wallet-image.rs");
risc0_zkvm::guest::entry!(main);
fn main() {
    let input: types::AdapterInput = risc0_zkvm::guest::env::read();
    assert!(
        !input.host_requests_skip,
        "host cannot declare the wallet operation invalid"
    );
    assert_eq!(input.wallet_journal.len(), 96);
    assert_eq!(
        &input.wallet_journal[..32],
        &kpi_takeover_common::app::lane_id(&input.native.tx)
    );
    risc0_zkvm::guest::env::verify(WALLET_IMAGE, &input.wallet_journal).unwrap();
    let (_, journal) = kpi_takeover_common::execute(&input.native);
    risc0_zkvm::guest::env::commit_slice(&journal);
}
