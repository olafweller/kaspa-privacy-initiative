//! One serial PUBLIC state resource. Reuses the PR32 action relation and vProgs ABI.
//! No MAX_SPAN check or lane accumulator: the reference batch/aggregate guests own those.
pub use kpi_native_common as app;
use serde::{Deserialize, Serialize};
use vprogs_core_codec::Writer;
use vprogs_core_smt::{
    proving::{Leaf, Membership},
    HashedNode,
};
use vprogs_zk_abi::{
    transaction_processor::{JournalEntries, OutputCommitment, OutputResourceCommitment},
    withdrawal::StandardSpk,
};
pub const RESOURCE: [u8; 32] = [0x71; 32];
#[derive(Clone, Serialize, Deserialize)]
pub struct Input {
    pub lane: [u8; 20],
    pub covenant: [u8; 32],
    pub context: [u8; 32],
    pub state: app::State,
    pub tx: app::lane::Tx,
}
pub fn root(state: &app::State) -> [u8; 32] {
    HashedNode::leaf::<vprogs_zk_backend_risc0_api::Sha256>(&RESOURCE, &state.hash()).hash
}
/// Reference SMT encoding for the single coarse app resource, present at depth zero.
pub fn proof(state: &app::State) -> Vec<u8> {
    let leaf = Leaf {
        depth: 0u16.into(),
        key_idx: 0u32.into(),
        value_hash: state.hash(),
    };
    let mut wire = vec![];
    wire.write_slice(&[RESOURCE]);
    wire.write_slice(&[leaf]);
    wire.write_slice::<HashedNode>(&[]);
    wire.write_slice::<u8>(&[]);
    wire.write_slice(&[Membership::Present(0u32.into())]);
    wire
}
pub fn execute(input: &Input) -> (app::State, Vec<u8>) {
    app::lane::check_rest(&input.tx.rest, &input.lane);
    assert!(
        input.lane[4..].iter().all(|x| *x == 0) && input.lane[1..4].iter().any(|x| *x != 0),
        "user lane"
    );
    let id = app::lane_id(&input.tx);
    let mut journal = vec![];
    journal.write(&1u16.to_le_bytes());
    journal.write(&id);
    journal.write(&input.tx.merge_idx.to_le_bytes());
    journal.write(&input.context);
    journal.write(&1u32.to_le_bytes());
    journal.write(&0u32.to_le_bytes());
    journal.write(&RESOURCE);
    journal.write(&input.state.hash());
    let state = match app::apply_transaction(&input.state, &input.covenant, &input.tx) {
        Ok((state, exits, deposit)) => {
            let mut sink = vec![];
            for exit in exits {
                StandardSpk::PubKey(&exit.recipient).encode(&mut sink);
                sink.write(&exit.amount.to_le_bytes());
            }
            journal.write(&[OutputCommitment::SUCCESS]);
            journal.write_blob(&sink);
            journal.write(&deposit);
            journal.write(&[OutputResourceCommitment::CHANGED]);
            journal.write(&state.hash());
            state
        }
        Err(error) => {
            journal.write(&[OutputCommitment::ERROR]);
            vprogs_zk_abi::Error::Decode(error).encode(&mut journal);
            input.state.clone()
        }
    };
    // Decode using the unchanged reference parser, also on the guest path.
    JournalEntries::decode(&journal).expect("canonical app journal");
    (state, journal)
}
