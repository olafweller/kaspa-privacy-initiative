//! Additive native restrictions for this lifecycle, not changes to the pinned
//! upstream contracts. All withdrawal crypto/amount checks remain upstream.
use super::*;
use vprogs_zk_backend_risc0_api::{blake2b_script_hash, build_permission_redeem_script};

fn data(s: &mut Vec<u8>, v: &[u8]) {
    assert!(v.len() <= 75);
    s.push(v.len() as u8);
    s.extend_from_slice(v);
}
fn number(s: &mut Vec<u8>, n: u32) {
    match n {
        0 => s.push(0),
        1..=16 => s.push(0x50 + n as u8),
        _ => {
            let mut v = n.to_le_bytes().to_vec();
            while v.last() == Some(&0) {
                v.pop();
            }
            if v.last().unwrap() & 0x80 != 0 {
                v.push(0);
            }
            data(s, &v);
        }
    }
}
/// Stack-neutral OpTxSubnetId / literal lane / OpEqualVerify. Also inserted
/// after the state's 99-byte prefix, so copied continuation suffixes retain it.
pub fn lane_guard() -> Vec<u8> {
    let mut s = vec![0xb6];
    data(&mut s, &chain::LANE);
    s.push(0x88);
    s
}
pub fn permission_redeem(state: &State, eid: H) -> Vec<u8> {
    let e = &state.ledger.exits[&eid];
    let reserve = &state.exit_reserves[&eid];
    let key = &state.exit_keys[&eid];
    let delegate = delegate(&state.covenant);
    let mut s = lane_guard();
    // v1; permission at input 0; three inputs and three outputs.
    s.extend_from_slice(&[
        0xb2, 0x51, 0x88, 0xb9, 0x00, 0x88, 0xb3, 0x53, 0x88, 0xb4, 0x53, 0x88,
    ]);
    // Input 1 is the exact reserve selected when this exit was admitted.
    s.extend_from_slice(&[0x51, 0xba]);
    data(&mut s, &reserve.id);
    s.push(0x88);
    s.extend_from_slice(&[0x51, 0xbb]);
    number(&mut s, reserve.index);
    s.push(0x88);
    s.extend_from_slice(&[0x51, 0xbf]);
    data(&mut s, &[vec![0, 0], delegate.clone()].concat());
    s.push(0x88);
    // Sponsor is unbound and cannot masquerade as a second delegate.
    s.extend_from_slice(&[0x52, 0xcf]);
    data(&mut s, &[0; 32]);
    s.push(0x88);
    s.extend_from_slice(&[0x52, 0xbf]);
    data(&mut s, &[vec![0, 0], delegate.clone()].concat());
    s.extend_from_slice(&[0x87, 0x00, 0x88]);
    // Terminal only: no partial/permission continuation, no covenant outputs.
    for i in 0..3 {
        number(&mut s, i);
        s.extend_from_slice(&[0xd6, 0x4f, 0x88]);
    }
    // Reserve change must remain positive and output 2 cannot add an
    // untracked delegate. Upstream enforces the exact principal deduction.
    s.extend_from_slice(&[0x51, 0xc2, 0x00, 0xa0, 0x69, 0x52, 0xc3]);
    data(&mut s, &[vec![0, 0], delegate].concat());
    s.extend_from_slice(&[0x87, 0x00, 0x88]);
    let leaf = PermissionTreeAccumulator::hash_leaf(StandardSpk::PubKey(key), e.amount);
    let root =
        PermissionTreeAccumulator::hash_branch(&leaf, &PermissionTreeAccumulator::hash_empty());
    // Partial consumption is rejected before this unchanged verifier body;
    // its self-referential continuation path is intentionally unreachable.
    s.extend_from_slice(&build_permission_redeem_script(&root, 1, 1));
    s
}
pub fn permission_hash(state: &State, eid: H) -> H {
    blake2b_script_hash(&permission_redeem(state, eid))
}
