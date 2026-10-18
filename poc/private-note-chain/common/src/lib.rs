//! Experimental private state transition. Native acceptance must authenticate the
//! lane endpoint externally; local execution alone is not a settlement proof.
use ark_bn254::Bn254;
use ark_serialize::CanonicalDeserialize;
#[cfg(target_os = "zkvm")]
use ark_serialize::CanonicalSerialize;
pub use kpi_lane_common as lane;
pub use kpi_private_note_wallet as wallet;
use serde::{Deserialize, Serialize};
use vprogs_core_codec::Writer;
use vprogs_core_smt::HashedNode;
use vprogs_zk_abi::{
    transaction_processor::{JournalEntries, OutputCommitment, OutputResourceCommitment},
    withdrawal::StandardSpk,
};
use vprogs_zk_backend_risc0_api::{delegate_entry_spk_hash, PermissionTreeAccumulator};
use wallet::{ledger::Ledger, protocol::*, ProofVerifier, Result};
pub const LANE: [u8; 20] = [
    0, 0x44, 0x45, 0x46, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
];
pub const RESOURCE: H = [0x74; 32];
pub const DEPOSIT_TAG: &[u8] = b"KPI-private-deposit-v1\0";
pub const OP_TAG: &[u8] = b"KPI-private-operation-v1\0";

pub struct AcceleratedVerifier {
    inner: kpi_accelerated_bn254::Verifier,
}
impl AcceleratedVerifier {
    pub fn checked(raw: &[u8], expected: H) -> Result<Self> {
        if hash(raw) != expected {
            return Err("unexpected VK".into());
        }
        let mut input = raw;
        let vk = ark_groth16::VerifyingKey::<Bn254>::deserialize_compressed(&mut input)
            .map_err(|_| "bad VK")?;
        if !input.is_empty() || vk.gamma_abc_g1.len() != 15 {
            return Err("VK arity/encoding".into());
        }
        Ok(Self {
            inner: kpi_accelerated_bn254::Verifier::from_validated_program_key(&vk, expected),
        })
    }
    #[cfg(target_os = "zkvm")]
    pub fn pinned() -> Self {
        let bytes = include_bytes!("../../pins/vk-uncompressed.bin");
        // Checked and canonically re-encoded by the native generator before build.
        // The guest identity binds these immutable bytes; submitted proofs are checked.
        let vk = ark_groth16::VerifyingKey::<Bn254>::deserialize_uncompressed_unchecked(&bytes[..])
            .unwrap();
        let mut raw = vec![];
        vk.serialize_compressed(&mut raw).unwrap();
        let expected = include_bytes!("../../pins/vk-id.bin");
        assert_eq!(hash(&raw), *expected);
        assert_eq!(vk.gamma_abc_g1.len(), 15);
        Self {
            inner: kpi_accelerated_bn254::Verifier::from_validated_program_key(&vk, *expected),
        }
    }
}
impl ProofVerifier for AcceleratedVerifier {
    fn id(&self) -> H {
        self.inner.id
    }
    fn verify(&self, op: &Operation) -> Result<()> {
        op.check_public(self.id())?;
        self.inner
            .verify_inputs(&op.proof, &op.statement.inputs())
            .map_err(str::to_owned)
    }
}
#[derive(Clone, Serialize, Deserialize)]
pub struct State {
    pub covenant: H,
    pub ledger: Ledger,
}
impl State {
    pub fn hash(&self) -> H {
        tagged(
            b"KPI-private-config-state-v1\0",
            &[&self.covenant, &self.ledger.state_hash()],
        )
    }
    pub fn root(&self) -> H {
        HashedNode::leaf::<vprogs_zk_backend_risc0_api::Sha256>(&RESOURCE, &self.hash()).hash
    }
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Input {
    pub state: State,
    pub lane: lane::Input,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Event {
    pub native_id: H,
    pub verdict: u8,
    pub before: H,
    pub after: H,
    pub error: Option<String>,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Output {
    pub state: State,
    pub events: Vec<Event>,
    pub transaction_journals: Vec<Vec<u8>>,
    pub aggregate_journal: Vec<u8>,
    pub exit_principals: Vec<u64>,
}
pub fn deposit_reference(id: H, index: u32) -> H {
    tagged(
        b"KPI-native-deposit-outpoint-v1\0",
        &[&id, &index.to_le_bytes()],
    )
}
pub fn destination(key: &H) -> H {
    let mut b = vec![];
    StandardSpk::PubKey(key).encode(&mut b);
    hash(&b)
}
pub fn operation_payload(op: &Operation, key: H) -> Result<Vec<u8>> {
    let mut p = OP_TAG.to_vec();
    let b = op.wire_bytes()?;
    p.extend((b.len() as u32).to_le_bytes());
    p.extend(b);
    p.extend(key);
    Ok(p)
}
pub fn deposit_payload(owner: H, index: u32) -> Vec<u8> {
    let mut b = DEPOSIT_TAG.to_vec();
    b.extend(owner);
    b.extend(index.to_le_bytes());
    b
}

struct Reader<'a>(&'a [u8]);
impl<'a> Reader<'a> {
    fn take(&mut self, n: usize) -> Result<&'a [u8]> {
        if n > self.0.len() {
            return Err("truncated native rest".into());
        }
        let (a, b) = self.0.split_at(n);
        self.0 = b;
        Ok(a)
    }
    fn n(&mut self) -> Result<usize> {
        usize::try_from(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
            .map_err(|_| "length".into())
    }
}
fn deposit_amount(rest: &[u8], index: u32, covenant: &H) -> Result<u64> {
    let mut r = Reader(rest);
    r.take(2)?;
    let n = r.n()?;
    if n > r.0.len() / 52 {
        return Err("inputs".into());
    }
    for _ in 0..n {
        r.take(36)?;
        let l = r.n()?;
        r.take(l)?;
        r.take(8)?;
    }
    let n = r.n()?;
    if n > r.0.len() / 19 {
        return Err("outputs".into());
    }
    let expected = StandardSpk::ScriptHash(&delegate_entry_spk_hash(covenant)).to_script_bytes();
    for i in 0..n {
        let value = u64::from_le_bytes(r.take(8)?.try_into().unwrap());
        let version = r.take(2)?;
        let l = r.n()?;
        let script = r.take(l)?;
        let flag = r.take(1)?[0];
        if i == index as usize {
            if version != [0, 0] || script != expected.as_slice() || flag != 0 || value == 0 {
                return Err("deposit script/value/covenant flag".into());
            }
            return Ok(value);
        }
        match flag {
            0 => (),
            1 => {
                r.take(34)?;
            }
            _ => return Err("covenant flag".into()),
        }
    }
    Err("missing deposit output".into())
}
fn apply<V: ProofVerifier>(
    state: &State,
    tx: &lane::Tx,
    v: &V,
) -> Result<(State, Vec<(H, u64)>, H)> {
    let mut next = state.clone();
    let id = vprogs_l1_utils::tx_id_v1(&tx.payload, &tx.rest);
    if tx.payload.starts_with(DEPOSIT_TAG) {
        let p = &tx.payload[DEPOSIT_TAG.len()..];
        if p.len() != 36 {
            return Err("deposit descriptor".into());
        }
        let owner: H = p[..32].try_into().unwrap();
        let index = u32::from_le_bytes(p[32..].try_into().unwrap());
        let value = deposit_amount(&tx.rest, index, &state.covenant)?;
        next.ledger.register_authenticated_fixture_deposit(
            deposit_reference(id, index),
            value,
            owner,
        )?;
        // The fixture-named ledger API is reached only after actual native output checks here.
        return Ok((next, vec![], delegate_entry_spk_hash(&state.covenant)));
    }
    if !tx.payload.starts_with(OP_TAG) {
        return Err("unrecognized private operation".into());
    }
    let mut r = Reader(&tx.payload[OP_TAG.len()..]);
    let n = u32::from_le_bytes(r.take(4)?.try_into().unwrap()) as usize;
    if n > 1024 {
        return Err("operation length".into());
    }
    let op = Operation::parse_wire(r.take(n)?)?;
    let key: H = r.take(32)?.try_into().unwrap();
    if !r.0.is_empty() {
        return Err("trailing envelope".into());
    }
    let withdrawing = [EXIT, RECOVER].contains(&op.statement.kind);
    if withdrawing {
        if key == [0; 32] || destination(&key) != op.statement.exit_destination {
            return Err("native destination binding".into());
        }
    } else if key != [0; 32] {
        return Err("inactive destination".into());
    }
    next.ledger
        .apply(v, &op)
        .map_err(|_| "private operation rejected".to_owned())?;
    let exits = if withdrawing {
        vec![(key, op.statement.exit_value)]
    } else {
        vec![]
    };
    Ok((next, exits, [0; 32]))
}
pub fn execute<V: ProofVerifier>(input: &Input, v: &V) -> Output {
    assert_eq!(input.lane.lane, LANE, "wrong fixed lane");
    assert_eq!(input.lane.covenant, input.state.covenant, "config covenant");
    assert_eq!(input.state.ledger.verifier, v.id(), "fixed wallet verifier");
    assert_eq!(
        input.lane.old_state,
        input.state.root(),
        "authenticated prior private state"
    );
    input.state.ledger.invariant().unwrap();
    let lane_output = lane::execute(&input.lane); // derive every native ID and complete endpoint
    let mut state = input.state.clone();
    let mut events = vec![];
    let mut journals = vec![];
    let mut all_exits = vec![];
    let mut deposits = [0; 32];
    for block in &input.lane.blocks {
        let context = lane::bytes(kaspa_seq_commit::hashing::mergeset_context_hash(
            &kaspa_seq_commit::types::MergesetContext {
                timestamp: block.prev_timestamp,
                daa_score: block.daa_score,
                blue_score: block.blue_score,
            },
        ));
        for tx in &block.txs {
            let id = vprogs_l1_utils::tx_id_v1(&tx.payload, &tx.rest);
            let before = state.hash();
            let mut j = vec![];
            j.write(&1u16.to_le_bytes());
            j.write(&id);
            j.write(&tx.merge_idx.to_le_bytes());
            // Context is supplied by the authenticated batch, not a wallet intent.
            j.write(&context);
            j.write(&1u32.to_le_bytes());
            j.write(&0u32.to_le_bytes());
            j.write(&RESOURCE);
            j.write(&before);
            let (verdict, error) = match apply(&state, tx, v) {
                Ok((next, exits, deposit)) => {
                    let mut sink = vec![];
                    for (key, amount) in &exits {
                        StandardSpk::PubKey(key).encode(&mut sink);
                        sink.write(&amount.to_le_bytes());
                    }
                    j.write(&[OutputCommitment::SUCCESS]);
                    j.write_blob(&sink);
                    j.write(&deposit);
                    j.write(&[OutputResourceCommitment::CHANGED]);
                    j.write(&next.hash());
                    all_exits.extend(exits);
                    if deposit != [0; 32] {
                        deposits = deposit
                    }
                    state = next;
                    (0, None)
                }
                Err(e) => {
                    j.write(&[OutputCommitment::ERROR]);
                    vprogs_zk_abi::Error::Decode(e.clone()).encode(&mut j);
                    (1, Some(e))
                }
            };
            JournalEntries::decode(&j).expect("reference transaction ABI");
            events.push(Event {
                native_id: id,
                verdict,
                before,
                after: state.hash(),
                error,
            });
            journals.push(j);
        }
    }
    let mut permissions = PermissionTreeAccumulator::new();
    for (key, amount) in &all_exits {
        permissions.add_exit(StandardSpk::PubKey(key), *amount);
    }
    let mut aggregate = lane::journal(&input.lane, &lane_output);
    aggregate[64..96].copy_from_slice(&state.root());
    // Monolithic calibration relation pins; future recursive program IDs replace these.
    aggregate[192..224].copy_from_slice(&hash(b"KPI-private-transaction-domain-v1"));
    aggregate[224..256].copy_from_slice(&hash(b"KPI-private-batch-domain-v1"));
    aggregate[256..288].copy_from_slice(&permissions.finalize());
    aggregate[288..320].copy_from_slice(&deposits);
    assert_eq!(aggregate.len(), 352);
    Output {
        state,
        events,
        transaction_journals: journals,
        aggregate_journal: aggregate,
        exit_principals: all_exits.iter().map(|x| x.1).collect(),
    }
}
