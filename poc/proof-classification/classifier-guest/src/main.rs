#![no_main]
#[path = "../../protocol.rs"]
#[allow(dead_code)]
mod protocol;
include!("../../wallet-image.rs");
risc0_zkvm::guest::entry!(main);
fn main() {
    let n: u32 = risc0_zkvm::guest::env::read();
    assert!(n as usize <= protocol::MAX_INPUT);
    let mut input = vec![0u8; n as usize];
    risc0_zkvm::guest::env::read_slice(&mut input);
    let mut r = protocol::Reader(&input);
    let expected: [u8; 32] = r.take(32).unwrap().try_into().unwrap();
    let mut balance = u64::from_le_bytes(r.take(8).unwrap().try_into().unwrap());
    let count = r.u32().unwrap();
    assert!(count > 0 && count as usize <= protocol::MAX_BATCH);
    let mut records = Vec::new();
    let mut root = [0; 32];
    for i in 0..count {
        let rest = r.blob(4096).unwrap();
        let op = r.blob(protocol::MAX_OPERATION).unwrap();
        // Strict native v1 canonical preimage; authentication failure halts.
        kpi_takeover_common::app::lane::check_rest(rest, &LOCAL_LANE);
        let tx = kpi_takeover_common::app::lane::Tx {
            payload: op.to_vec(),
            rest: rest.to_vec(),
            merge_idx: i,
        };
        let id = kpi_takeover_common::app::lane_id(&tx);
        root = protocol::order_step(root, i, id);
        records.push((id, op));
    }
    assert!(r.0.is_empty());
    assert_eq!(
        root, expected,
        "withheld/substituted/reordered published operation"
    );
    let image: [u8; 32] = WALLET_IMAGE
        .into_iter()
        .flat_map(u32::to_le_bytes)
        .collect::<Vec<_>>()
        .try_into()
        .unwrap();
    let mut seen = Vec::new();
    let mut journal = root.to_vec();
    journal.extend(balance.to_le_bytes());
    journal.extend(count.to_le_bytes());
    for (id, op) in records {
        let mut outcome = protocol::classify(op, image);
        if outcome == 0 {
            let intent = &op[..protocol::INTENT_LEN];
            let digest = protocol::tagged(b"KPI-local-intent-v1", intent);
            let effect = u64::from_le_bytes(intent[202..210].try_into().unwrap());
            if seen.contains(&digest) || effect > balance {
                outcome = 4;
            } else {
                balance -= effect;
                seen.push(digest);
            }
        }
        journal.extend(id);
        journal.push(outcome);
        journal.extend(balance.to_le_bytes());
    }
    risc0_zkvm::guest::env::commit_slice(&journal);
}
// Dedicated unfunded lane, not the earlier funded lane/delegate.
const LOCAL_LANE: [u8; 20] = {
    let mut b = [0; 20];
    b[1] = 0x35;
    b[2] = 0x36;
    b[3] = 0x37;
    b
};
