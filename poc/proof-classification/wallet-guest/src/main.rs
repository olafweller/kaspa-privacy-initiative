#![no_main]
#[path = "../../protocol.rs"]
#[allow(dead_code)]
mod protocol;
risc0_zkvm::guest::entry!(main);
fn main() {
    let input: protocol::WalletInput = risc0_zkvm::guest::env::read();
    assert_eq!(input.intent.len(), protocol::INTENT_LEN);
    let v = input.values;
    assert!(v[0] > 0);
    assert_eq!(
        v[1].checked_add(v[2]).and_then(|n| n.checked_add(v[3])),
        Some(v[0])
    );
    assert_eq!(protocol::hash(&input.secret), input.intent[138..170]);
    assert_eq!(protocol::values_hash(&v), input.intent[170..202]);
    assert_eq!(v[1].to_le_bytes(), input.intent[202..210]);
    assert_eq!(v[3].to_le_bytes(), input.intent[210..218]);
    risc0_zkvm::guest::env::commit_slice(&protocol::journal(&input.intent));
}
