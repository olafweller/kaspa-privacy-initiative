#![no_main]
use kpi_accelerated_bn254::Verifier;
use kpi_groth16_comparison::proxy;
risc0_zkvm::guest::entry!(main);
fn main() {
    let n: u32 = risc0_zkvm::guest::env::read();
    assert!(n as usize <= proxy::MAX_INPUT);
    let mut input = vec![0u8; n as usize];
    risc0_zkvm::guest::env::read_slice(&mut input);
    let mut r = proxy::Reader(&input);
    let expected: [u8; 32] = r.take(32).unwrap().try_into().unwrap();
    let mut balance = u64::from_le_bytes(r.take(8).unwrap().try_into().unwrap());
    let count = r.u32().unwrap();
    assert!(count > 0 && count as usize <= proxy::MAX_BATCH);
    let mut records = vec![];
    let mut root = [0; 32];
    for i in 0..count {
        let rest = r.blob(4096).unwrap();
        let op = r.blob(proxy::MAX_OPERATION).unwrap();
        kpi_takeover_common::app::lane::check_rest(rest, &LANE);
        let tx = kpi_takeover_common::app::lane::Tx {
            payload: op.to_vec(),
            rest: rest.to_vec(),
            merge_idx: i,
        };
        let id = kpi_takeover_common::app::lane_id(&tx);
        root = proxy::order_step(root, i, id);
        records.push((id, op));
    }
    assert!(r.0.is_empty());
    assert_eq!(
        root, expected,
        "withheld/substituted/reordered published operation"
    );
    println!(
        "PROFILE authenticated_input {}",
        risc0_zkvm::guest::env::cycle_count()
    );
    let verifier = Verifier::pinned();
    println!(
        "PROFILE loaded_prepared_key {}",
        risc0_zkvm::guest::env::cycle_count()
    );
    let mut journal = root.to_vec();
    journal.extend(balance.to_le_bytes());
    journal.extend(count.to_le_bytes());
    let mut seen = vec![];
    for (native_id, op) in records {
        let mut code = verifier.classify(op);
        println!(
            "PROFILE classified {} {}",
            code,
            risc0_zkvm::guest::env::cycle_count()
        );
        if code == 0 {
            let intent = &op[..proxy::INTENT_LEN];
            let key = proxy::tagged(b"KPI-local-intent-v1", intent);
            let effect = u64::from_le_bytes(intent[202..210].try_into().unwrap());
            if seen.contains(&key) || effect > balance {
                code = 4;
            } else {
                balance -= effect;
                seen.push(key);
            }
        }
        journal.extend(native_id);
        journal.push(code);
        journal.extend(balance.to_le_bytes());
    }
    risc0_zkvm::guest::env::commit_slice(&journal);
}
const LANE: [u8; 20] = {
    let mut b = [0; 20];
    b[1] = 0x35;
    b[2] = 0x36;
    b[3] = 0x37;
    b
};
