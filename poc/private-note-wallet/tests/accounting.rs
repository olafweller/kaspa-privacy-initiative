use kpi_private_note_wallet::{
    ledger::{Ledger, PendingExit},
    protocol::*,
};
#[test]
fn actual_payout_reference_cannot_settle_two_exits() {
    let mut l = Ledger::new([7; 32]);
    l.reserve = 8;
    for i in 0..2 {
        l.exits.insert(
            hash(&[i]),
            PendingExit {
                amount: 4,
                destination: [8; 32],
                paid: false,
            },
        );
    }
    l.invariant().unwrap();
    let first = hash(&[0]);
    let second = hash(&[1]);
    let native = hash(b"one native output");
    l.confirm_authenticated_fixture_payout(first, 4, [8; 32], native)
        .unwrap();
    let before = l.state_hash();
    assert!(l
        .confirm_authenticated_fixture_payout(second, 4, [8; 32], native)
        .is_err());
    assert_eq!(before, l.state_hash());
    assert!(l
        .confirm_authenticated_fixture_payout(second, 3, [8; 32], hash(b"second native output"))
        .is_err());
    assert_eq!(before, l.state_hash());
    assert!(l
        .confirm_authenticated_fixture_payout(second, 4, [9; 32], hash(b"second native output"))
        .is_err());
    assert_eq!(before, l.state_hash());
    l.confirm_authenticated_fixture_payout(second, 4, [8; 32], hash(b"second native output"))
        .unwrap();
    assert_eq!(l.reserve, 0);
    l.invariant().unwrap();
}
#[test]
fn pending_deposit_uniqueness_and_counter_overflow() {
    let mut l = Ledger::new([7; 32]);
    let id = hash(b"deposit");
    l.register_authenticated_fixture_deposit(id, u64::MAX, [8; 32])
        .unwrap();
    let before = l.state_hash();
    assert!(l
        .register_authenticated_fixture_deposit(id, 1, [8; 32])
        .is_err());
    assert_eq!(before, l.state_hash());
    assert!(l
        .register_authenticated_fixture_deposit(hash(b"another deposit"), 1, [8; 32])
        .is_err());
    assert_eq!(before, l.state_hash());
    l.batch = u64::MAX;
    assert!(l.next_batch().is_err());
}
