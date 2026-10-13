//! Public-data research relation, with no value, notes, keys or exits.
//! No fixed operation count: completeness comes from the authenticated lane endpoint.
use kaspa_hashes::{Hash, SeqCommitActiveNode};
use kaspa_seq_commit::{hashing::*, types::*};
use kaspa_smt::proof::{ProofTerminal, SmtProof};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const OP_TAG: &[u8] = b"KPI-LANE-v1";
pub const STATE_TAG: &[u8] = b"KPI-LANE-STATE-v1";
// Identifies this monolithic relation; these are domain pins, not recursive guests.
pub const TX_DOMAIN: [u8; 32] = [0x41; 32];
pub const BATCH_DOMAIN: [u8; 32] = [0x42; 32];
pub const MAX_SPAN: u64 = 100; // only the continuously active short-interval experiment
pub fn h(b: [u8; 32]) -> Hash {
    Hash::from_bytes(b)
}
pub fn bytes(h: Hash) -> [u8; 32] {
    h.into()
}
pub fn initial_state() -> [u8; 32] {
    Sha256::digest(STATE_TAG).into()
}
pub fn operation(n: u32) -> Vec<u8> {
    [OP_TAG, &n.to_le_bytes()].concat()
}
pub fn apply(state: [u8; 32], payload: &[u8]) -> [u8; 32] {
    // Every lane tx affects the lane commitment. Unrecognized payloads are deterministic no-ops.
    if payload.len() != OP_TAG.len() + 4 || !payload.starts_with(OP_TAG) {
        return state;
    }
    Sha256::digest([STATE_TAG, &state, payload].concat()).into()
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Tx {
    pub payload: Vec<u8>,
    pub rest: Vec<u8>,
    pub merge_idx: u32,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Block {
    pub prev_timestamp: u64,
    pub daa_score: u64,
    pub blue_score: u64,
    pub txs: Vec<Tx>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Anchor {
    pub parent_seq: [u8; 32],
    pub payload_ctx: [u8; 32],
    pub shortcut: [u8; 32],
    pub blue_score: u64,
    pub bitmap: [u8; 32],
    pub depth: u8,
    pub siblings: Vec<[u8; 32]>,
}
impl Anchor {
    pub fn seq(&self, key: Hash, tip: Hash) -> Hash {
        let siblings: Vec<Hash> = self.siblings.iter().copied().map(h).collect();
        let proof = SmtProof {
            bitmap: &self.bitmap,
            terminal: ProofTerminal::Collapsed { depth: self.depth },
            siblings: &siblings,
        };
        let leaf = smt_leaf_hash(&SmtLeafInput {
            lane_tip: &tip,
            blue_score: self.blue_score,
        });
        let root = proof
            .compute_root::<SeqCommitActiveNode>(&key, Some(leaf))
            .expect("invalid SMT proof");
        let activity = activity_root_hash(&h(self.shortcut), &root);
        let sr = seq_state_root(&SeqState {
            activity_root: &activity,
            payload_and_ctx_digest: &h(self.payload_ctx),
        });
        seq_commit(&SeqCommitInput {
            parent_seq_commit: &h(self.parent_seq),
            state_root: &sr,
        })
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Input {
    pub lane: [u8; 20],
    pub covenant: [u8; 32],
    pub old_state: [u8; 32],
    pub old_tip: [u8; 32],
    pub start: Anchor,
    pub start_seq: [u8; 32],
    pub blocks: Vec<Block>,
    pub end: Anchor,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Output {
    pub state: [u8; 32],
    pub tip: [u8; 32],
    pub seq: [u8; 32],
    pub operations: usize,
}

struct Reader<'a>(&'a [u8]);
impl<'a> Reader<'a> {
    fn take(&mut self, n: usize) -> &'a [u8] {
        assert!(n <= self.0.len(), "truncated rest preimage");
        let (a, b) = self.0.split_at(n);
        self.0 = b;
        a
    }
    fn len(&mut self) -> usize {
        let n = u64::from_le_bytes(self.take(8).try_into().unwrap());
        usize::try_from(n).expect("length overflow")
    }
}
/// Strictly parse the v1 rest preimage; never trust a separate lane/version label.
pub fn check_rest(rest: &[u8], lane: &[u8; 20]) {
    let mut r = Reader(rest);
    assert_eq!(r.take(2), 1u16.to_le_bytes(), "only v1 supported");
    let n = r.len();
    assert!(n > 0 && n <= r.0.len() / 52, "input count");
    for _ in 0..n {
        r.take(36);
        assert_eq!(r.len(), 0, "signature excluded");
        r.take(8);
    }
    let n = r.len();
    assert!(n > 0 && n <= r.0.len() / 19, "output count");
    for _ in 0..n {
        r.take(10);
        let len = r.len();
        r.take(len);
        match r.take(1)[0] {
            0 => {}
            1 => {
                r.take(34);
            }
            _ => panic!("noncanonical covenant flag"),
        }
    }
    r.take(8);
    assert_eq!(r.take(20), lane, "wrong lane in transaction");
    r.take(8);
    assert_eq!(r.len(), 0, "payload excluded");
    assert!(r.0.is_empty(), "trailing preimage bytes");
}
pub fn execute(input: &Input) -> Output {
    assert!(
        input.lane[4..].iter().all(|x| *x == 0) && input.lane[1..4].iter().any(|x| *x != 0),
        "invalid user lane"
    );
    let key = lane_key(&input.lane);
    assert_eq!(
        bytes(input.start.seq(key, h(input.old_tip))),
        input.start_seq,
        "start inclusion"
    );
    assert!(!input.blocks.is_empty(), "empty interval");
    let mut state = input.old_state;
    let mut tip = h(input.old_tip);
    let mut score = input.start.blue_score;
    let mut operations = 0;
    for block in &input.blocks {
        assert!(
            block.blue_score > score && block.blue_score - input.start.blue_score <= MAX_SPAN,
            "unsupported expiry or unordered blocks"
        );
        score = block.blue_score;
        if block.txs.is_empty() {
            continue;
        }
        let context = mergeset_context_hash(&MergesetContext {
            timestamp: block.prev_timestamp,
            daa_score: block.daa_score,
            blue_score: block.blue_score,
        });
        let mut activity = ActivityDigestBuilder::new();
        let mut last = None;
        for tx in &block.txs {
            assert!(
                last.is_none_or(|prev| tx.merge_idx > prev),
                "nonascending merge_idx"
            );
            last = Some(tx.merge_idx);
            check_rest(&tx.rest, &input.lane);
            let id = h(vprogs_l1_utils::tx_id_v1(&tx.payload, &tx.rest));
            activity.add_leaf(activity_leaf(&id, 1, tx.merge_idx));
            let next = apply(state, &tx.payload);
            operations += usize::from(next != state);
            state = next;
        }
        tip = lane_tip_next(&LaneTipInput {
            parent_ref: &tip,
            lane_key: &key,
            activity_digest: &activity.finalize(),
            context_hash: &context,
        });
    }
    assert_eq!(
        input.end.blue_score,
        input
            .blocks
            .iter()
            .rev()
            .find(|b| !b.txs.is_empty())
            .expect("no activity")
            .blue_score,
        "last-touch score"
    );
    Output {
        state,
        tip: bytes(tip),
        seq: bytes(input.end.seq(key, tip)),
        operations,
    }
}
pub fn journal(input: &Input, output: &Output) -> Vec<u8> {
    // Exact production vProgs StateTransition ABI (352 bytes); monolithic guest, no recursive proofs.
    [
        input.old_state,
        input.old_tip,
        output.state,
        output.tip,
        output.seq,
        input.covenant,
        TX_DOMAIN,
        BATCH_DOMAIN,
        [0; 32],
        [0; 32],
        bytes(lane_key(&input.lane)),
    ]
    .concat()
}
