//! Local integration relation. Lane endpoints require native consensus anchoring;
//! no host success flag can register native principal or discharge an exit.
pub use kpi_private_note_chain::{self as chain, lane, wallet, AcceleratedVerifier};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use vprogs_core_smt::HashedNode;
use vprogs_zk_abi::withdrawal::StandardSpk;
use vprogs_zk_backend_risc0_api::{delegate_entry_spk_hash, PermissionTreeAccumulator};
use wallet::{ledger::Ledger, protocol::*, ProofVerifier, Result};
pub mod restricted;

pub const RESOURCE: H = [0x75; 32];
pub const STATE_RENT: u64 = 100_000_000;
pub const PERMISSION_RENT: u64 = 50_000_000;
pub const PERMISSION_TAG: &[u8] = b"KPI-native-permission-v1\0";
pub const PAYOUT_TAG: &[u8] = b"KPI-native-payout-v1\0";
pub const CYCLE_LIMIT: u64 = 160_000_000;

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Outpoint {
    pub id: H,
    pub index: u32,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeOutput {
    pub value: u64,
    pub version: u16,
    pub script: Vec<u8>,
    pub covenant: Option<(u16, H)>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct NativeTx {
    pub inputs: Vec<Outpoint>,
    pub outputs: Vec<NativeOutput>,
}
struct Reader<'a>(&'a [u8]);
impl<'a> Reader<'a> {
    fn take(&mut self, n: usize) -> Result<&'a [u8]> {
        if n > self.0.len() {
            return Err("truncated v1 preimage".into());
        }
        let (a, b) = self.0.split_at(n);
        self.0 = b;
        Ok(a)
    }
    fn count(&mut self) -> Result<usize> {
        usize::try_from(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
            .map_err(|_| "native length".into())
    }
}
impl NativeTx {
    /// Full canonical parse, including covenant flags/tail. Signatures and mass
    /// are excluded by the consensus v1 ID format; accepted L1 validates them.
    pub fn parse(rest: &[u8]) -> Result<Self> {
        let mut r = Reader(rest);
        if r.take(2)? != 1u16.to_le_bytes() {
            return Err("only native v1".into());
        }
        let n = r.count()?;
        if n == 0 || n > r.0.len() / 52 {
            return Err("input count".into());
        }
        let mut inputs = vec![];
        let mut seen = BTreeSet::new();
        for _ in 0..n {
            let o = Outpoint {
                id: r.take(32)?.try_into().unwrap(),
                index: u32::from_le_bytes(r.take(4)?.try_into().unwrap()),
            };
            if !seen.insert(o.clone()) || r.count()? != 0 {
                return Err("duplicate input or noncanonical signature".into());
            }
            r.take(8)?;
            inputs.push(o);
        }
        let n = r.count()?;
        if n == 0 || n > r.0.len() / 19 {
            return Err("output count".into());
        }
        let mut outputs = vec![];
        for _ in 0..n {
            let value = u64::from_le_bytes(r.take(8)?.try_into().unwrap());
            let version = u16::from_le_bytes(r.take(2)?.try_into().unwrap());
            let len = r.count()?;
            let script = r.take(len)?.to_vec();
            let covenant = match r.take(1)?[0] {
                0 => None,
                1 => Some((
                    u16::from_le_bytes(r.take(2)?.try_into().unwrap()),
                    r.take(32)?.try_into().unwrap(),
                )),
                _ => return Err("covenant flag".into()),
            };
            if covenant
                .as_ref()
                .is_some_and(|(i, _)| *i as usize >= inputs.len())
            {
                return Err("covenant auth index".into());
            }
            outputs.push(NativeOutput {
                value,
                version,
                script,
                covenant,
            });
        }
        r.take(8)?;
        if r.take(20)? != chain::LANE {
            return Err("native lane".into());
        }
        r.take(8)?;
        if r.count()? != 0 || !r.0.is_empty() {
            return Err("native trailing/payload bytes".into());
        }
        Ok(Self { inputs, outputs })
    }
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Permission {
    pub outpoint: Outpoint,
    pub rent: u64,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct State {
    pub covenant: H,
    pub ledger: Ledger,
    pub reserves: BTreeMap<Outpoint, u64>,
    pub exit_keys: BTreeMap<H, H>,
    pub exit_reserves: BTreeMap<H, Outpoint>,
    pub permissions: BTreeMap<H, Permission>,
    pub lane_tip: H,
    pub last_touch: u64,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Accounting {
    pub reserve_principal: u64,
    pub private_liability: u64,
    pub pending_deposits: u64,
    pub unpaid_exits: u64,
    pub state_covenant_rent_excluded: u64,
    pub outstanding_permission_rent_excluded: u64,
}
impl State {
    pub fn genesis(covenant: H, verifier: H, seed_tip: H, seed_touch: u64) -> Self {
        Self {
            covenant,
            ledger: Ledger::new(verifier),
            reserves: BTreeMap::new(),
            exit_keys: BTreeMap::new(),
            exit_reserves: BTreeMap::new(),
            permissions: BTreeMap::new(),
            lane_tip: seed_tip,
            last_touch: seed_touch,
        }
    }
    pub fn hash(&self) -> H {
        tagged(
            b"KPI-private-native-state-v2\0",
            &[&bincode::serialize(self).unwrap()],
        )
    }
    pub fn root(&self) -> H {
        HashedNode::leaf::<vprogs_zk_backend_risc0_api::Sha256>(&RESOURCE, &self.hash()).hash
    }
    pub fn accounting(&self) -> Result<Accounting> {
        self.ledger.invariant()?;
        let sum = |v: Vec<u64>| -> Result<u64> {
            v.into_iter().try_fold(0u64, |s, x| {
                s.checked_add(x).ok_or("accounting overflow".into())
            })
        };
        if sum(self.reserves.values().copied().collect())? != self.ledger.reserve {
            return Err("tracked reserve/principal mismatch".into());
        }
        for (id, e) in self.ledger.exits.iter().filter(|(_, e)| !e.paid) {
            let o = self
                .exit_reserves
                .get(id)
                .ok_or("exit has no pinned reserve")?;
            if self.reserves.get(o).is_none_or(|value| *value <= e.amount) {
                return Err("exit pinned reserve unavailable/insufficient".into());
            }
        }
        for (id, p) in &self.permissions {
            let e = self.ledger.exits.get(id).ok_or("permission without exit")?;
            if e.paid || p.rent != PERMISSION_RENT {
                return Err("permission paid/rent".into());
            }
        }
        Ok(Accounting {
            reserve_principal: self.ledger.reserve,
            private_liability: self.ledger.private_liability,
            pending_deposits: sum(self
                .ledger
                .deposits
                .values()
                .filter(|d| d.status == 0)
                .map(|d| d.amount)
                .collect())?,
            unpaid_exits: sum(self
                .ledger
                .exits
                .values()
                .filter(|e| !e.paid)
                .map(|e| e.amount)
                .collect())?,
            state_covenant_rent_excluded: STATE_RENT,
            outstanding_permission_rent_excluded: sum(self
                .permissions
                .values()
                .map(|p| p.rent)
                .collect())?,
        })
    }
}
pub fn delegate(covenant: &H) -> Vec<u8> {
    StandardSpk::ScriptHash(&delegate_entry_spk_hash(covenant))
        .to_script_bytes()
        .as_slice()
        .to_vec()
}
pub use restricted::permission_hash;
fn matches(o: &NativeOutput, value: u64, script: &[u8], cov: Option<(u16, H)>) -> bool {
    o.value == value && o.version == 0 && o.script == script && o.covenant == cov
}
pub fn permission_payload(exit: H) -> Vec<u8> {
    [PERMISSION_TAG, &exit].concat()
}
pub fn payout_payload(exit: H) -> Vec<u8> {
    [PAYOUT_TAG, &exit].concat()
}
fn suffix(payload: &[u8], tag: &[u8]) -> Result<H> {
    payload
        .strip_prefix(tag)
        .and_then(|x| x.try_into().ok())
        .ok_or("native event descriptor".into())
}

fn reconcile_native_payout(state: &State, body: &NativeTx, id: H, eid: H) -> Result<State> {
    let mut next = state.clone();
    let p = state
        .permissions
        .get(&eid)
        .ok_or("unknown/spent permission")?;
    let e = state.ledger.exits.get(&eid).ok_or("unknown exit")?;
    let key = state.exit_keys.get(&eid).ok_or("missing exit key")?;
    if body.inputs.len() != 3
        || body.outputs.len() != 3
        || body.inputs[0] != p.outpoint
        || state.exit_reserves.get(&eid) != body.inputs.get(1)
    {
        return Err("payout input/permission/scope".into());
    }
    let value = *state
        .reserves
        .get(&body.inputs[1])
        .ok_or("foreign/spent reserve")?;
    let change = value.checked_sub(e.amount).ok_or("reserve underpayment")?;
    let paid = e.amount.checked_add(p.rent).ok_or("payout overflow")?;
    if change == 0
        || !matches(
            &body.outputs[0],
            body.outputs[0].value,
            StandardSpk::PubKey(key).to_script_bytes().as_slice(),
            None,
        )
        || body.outputs[0].value < paid
        || !matches(&body.outputs[1], change, &delegate(&state.covenant), None)
    {
        return Err("payout amount/destination/reserve change".into());
    }
    if body.outputs[2].covenant.is_some()
        || (body.outputs[2].version == 0 && body.outputs[2].script == delegate(&state.covenant))
    {
        return Err("sponsor output must be separate".into());
    }
    next.ledger.confirm_authenticated_fixture_payout(
        eid,
        e.amount,
        e.destination,
        chain::deposit_reference(id, 0),
    )?;
    next.permissions.remove(&eid);
    next.reserves.remove(&body.inputs[1]);
    next.reserves.insert(Outpoint { id, index: 1 }, change);

    next.accounting()?;
    Ok(next)
}

fn register_native_permission(state: &State, body: &NativeTx, id: H, eid: H) -> Result<State> {
    let mut next = state.clone();
    let e = state
        .ledger
        .exits
        .get(&eid)
        .ok_or("unknown permission exit")?;
    state.exit_keys.get(&eid).ok_or("missing exit key")?;
    if e.paid || state.permissions.contains_key(&eid) || body.outputs.len() < 2 {
        return Err("permission duplicate/paid/shape".into());
    }
    // Accepted-L1 covenant binding is load-bearing: it requires the actual
    // covenant input's receipt verifier, not a caller-created UTXO record.
    if body.outputs[0].value != STATE_RENT || body.outputs[0].covenant != Some((0, state.covenant))
    {
        return Err("state covenant continuation/rent".into());
    }
    let spk = StandardSpk::ScriptHash(&permission_hash(state, eid)).to_script_bytes();
    if !matches(
        &body.outputs[1],
        PERMISSION_RENT,
        spk.as_slice(),
        Some((0, state.covenant)),
    ) {
        return Err("permission binding/value/destination".into());
    }
    next.permissions.insert(
        eid,
        Permission {
            outpoint: Outpoint { id, index: 1 },
            rent: PERMISSION_RENT,
        },
    );

    next.accounting()?;
    Ok(next)
}

/// Reached only for ID-derived transactions in the authenticated lane fold.
/// Clone-before-apply ensures any malformed/rejected operation is atomic.
pub fn apply<V: ProofVerifier>(
    state: &State,
    tx: &lane::Tx,
    v: &V,
) -> Result<(State, Option<(H, u64)>, bool)> {
    state.accounting()?;
    let body = NativeTx::parse(&tx.rest)?;
    let id = vprogs_l1_utils::tx_id_v1(&tx.payload, &tx.rest);
    let mut next = state.clone();
    let mut exit = None;
    let mut deposit = false;
    let spends_tracked = body.inputs.iter().any(|o| {
        state.reserves.contains_key(o) || state.permissions.values().any(|p| &p.outpoint == o)
    });
    if spends_tracked {
        // Native permission scripts do not require an honest payload tag. Any
        // accepted spend of tracked principal must be reconciled by outpoint,
        // including a third-party payout with an unrelated/empty payload.
        let eid = state
            .permissions
            .iter()
            .find(|(_, p)| body.inputs.first() == Some(&p.outpoint))
            .map(|(id, _)| *id)
            .ok_or("tracked spend without known permission")?;
        return Ok((reconcile_native_payout(state, &body, id, eid)?, None, false));
    }
    // Detect covenant-authorized permission outputs by their actual bytes,
    // not by an executor's tag or success assertion.
    if let Some(o) = body.outputs.get(1) {
        if o.covenant == Some((0, state.covenant)) {
            for eid in state.exit_keys.keys() {
                if let Some(e) = state.ledger.exits.get(eid) {
                    let spk =
                        StandardSpk::ScriptHash(&permission_hash(state, *eid)).to_script_bytes();
                    if !e.paid && !state.permissions.contains_key(eid) && o.script == spk.as_slice()
                    {
                        return Ok((
                            register_native_permission(state, &body, id, *eid)?,
                            None,
                            false,
                        ));
                    }
                }
            }
        }
    }
    if tx.payload.starts_with(chain::DEPOSIT_TAG) {
        let p = &tx.payload[chain::DEPOSIT_TAG.len()..];
        if p.len() != 36 {
            return Err("deposit descriptor".into());
        }
        let owner: H = p[..32].try_into().unwrap();
        let index = u32::from_le_bytes(p[32..].try_into().unwrap());
        let o = body
            .outputs
            .get(index as usize)
            .ok_or("deposit missing output")?;
        if o.value == 0 || !matches(o, o.value, &delegate(&state.covenant), None) {
            return Err("deposit script/value/binding".into());
        }
        let outpoint = Outpoint { id, index };
        if next.reserves.contains_key(&outpoint) {
            return Err("duplicate reserve deposit".into());
        }
        next.ledger.register_authenticated_fixture_deposit(
            chain::deposit_reference(id, index),
            o.value,
            owner,
        )?;
        next.reserves.insert(outpoint, o.value);
        deposit = true;
    } else if tx.payload.starts_with(chain::OP_TAG) {
        let mut r = Reader(&tx.payload[chain::OP_TAG.len()..]);
        let n = u32::from_le_bytes(r.take(4)?.try_into().unwrap()) as usize;
        if n > 1024 {
            return Err("operation size".into());
        }
        let op = Operation::parse_wire(r.take(n)?)?;
        let key: H = r.take(32)?.try_into().unwrap();
        if !r.0.is_empty() {
            return Err("operation trailing bytes".into());
        }
        if [EXIT, RECOVER].contains(&op.statement.kind) {
            if key == [0; 32] || chain::destination(&key) != op.statement.exit_destination {
                return Err("native exit recipient".into());
            }
            if state.ledger.exits.values().any(|e| !e.paid) {
                return Err("one pending exit scope".into());
            }
            let reserve = state
                .reserves
                .iter()
                .find(|(_, value)| **value > op.statement.exit_value)
                .map(|(outpoint, _)| outpoint.clone())
                .ok_or("exit requires one sufficient tracked reserve with positive change")?;
            next.exit_reserves.insert(op.statement.id(), reserve);
            next.exit_keys.insert(op.statement.id(), key);
            exit = Some((key, op.statement.exit_value));
        } else if key != [0; 32] {
            return Err("inactive native recipient".into());
        }
        next.ledger.apply(v, &op)?;
    } else if tx.payload.starts_with(PERMISSION_TAG) {
        let eid = suffix(&tx.payload, PERMISSION_TAG)?;
        next = register_native_permission(state, &body, id, eid)?;
    } else if tx.payload.starts_with(PAYOUT_TAG) {
        return Err("payout has no tracked native spend".into());
    } else {
        return Err("unrecognized lane operation".into());
    }
    next.accounting()?;
    Ok((next, exit, deposit))
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Input {
    pub state: State,
    pub lane: lane::Input,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Event {
    pub id: H,
    pub accepted: bool,
    pub before: H,
    pub after: H,
    pub error: Option<String>,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Output {
    pub state: State,
    pub journal: Vec<u8>,
    pub events: Vec<Event>,
}

pub fn execute<V: ProofVerifier>(input: &Input, v: &V) -> Output {
    use kaspa_seq_commit::{hashing::*, types::*};
    let i = &input.lane;
    assert_eq!(i.lane, chain::LANE, "fixed lane");
    assert_eq!(i.covenant, input.state.covenant, "covenant");
    assert_eq!(i.old_state, input.state.root(), "prior state");
    assert_eq!(i.old_tip, input.state.lane_tip, "prior tip");
    assert_eq!(
        i.start.blue_score, input.state.last_touch,
        "prior last touch"
    );
    assert_eq!(v.id(), input.state.ledger.verifier, "wallet verifier");
    let key = lane_key(&i.lane);
    assert_eq!(
        lane::bytes(i.start.seq(key, lane::h(i.old_tip))),
        i.start_seq,
        "start active inclusion"
    );
    let mut state = input.state.clone();
    state.accounting().unwrap();
    let mut events = vec![];
    let mut tip = lane::h(i.old_tip);
    let mut score = input.state.last_touch;
    let mut last_block_score = score;
    let mut permission = [0; 32];
    let mut deposit = [0; 32];
    assert!(!i.blocks.is_empty(), "empty interval");
    for block in &i.blocks {
        assert!(block.blue_score > last_block_score, "unordered block");
        last_block_score = block.blue_score;
        // Unlike the old 100-score fixture, active continuity is authenticated
        // by the unchanged old leaf and final native endpoint. Expiry reset
        // cannot match this carried tip; no invented reset path is accepted.
        if block.txs.is_empty() {
            continue;
        }
        score = block.blue_score;
        let context = mergeset_context_hash(&MergesetContext {
            timestamp: block.prev_timestamp,
            daa_score: block.daa_score,
            blue_score: block.blue_score,
        });
        let mut activity = ActivityDigestBuilder::new();
        let mut last = None;
        for tx in &block.txs {
            assert!(last.is_none_or(|x| tx.merge_idx > x), "merge order");
            last = Some(tx.merge_idx);
            lane::check_rest(&tx.rest, &chain::LANE);
            let id = vprogs_l1_utils::tx_id_v1(&tx.payload, &tx.rest);
            activity.add_leaf(activity_leaf(&lane::h(id), 1, tx.merge_idx));
            let before = state.hash();
            let error = match apply(&state, tx, v) {
                Ok((s, exit, d)) => {
                    state = s;
                    if exit.is_some() {
                        assert_eq!(permission, [0; 32], "one permission per batch");
                        let eid = *state.ledger.exits.iter().find(|(_, e)| !e.paid).unwrap().0;
                        permission = permission_hash(&state, eid);
                    }
                    if d {
                        deposit = delegate_entry_spk_hash(&state.covenant);
                    }
                    None
                }
                Err(e) => {
                    // Accepted native consumption has already moved money. It
                    // cannot be committed as an ordinary rejected wallet op.
                    let body = NativeTx::parse(&tx.rest).expect("accepted canonical native body");
                    assert!(
                        !body.inputs.iter().any(|o| state.reserves.contains_key(o)
                            || state.permissions.values().any(|p| &p.outpoint == o)),
                        "unreconciled accepted native consumption"
                    );
                    Some(e)
                }
            };
            events.push(Event {
                id,
                accepted: error.is_none(),
                before,
                after: state.hash(),
                error,
            });
        }
        tip = lane_tip_next(&LaneTipInput {
            parent_ref: &tip,
            lane_key: &key,
            activity_digest: &activity.finalize(),
            context_hash: &context,
        });
    }
    assert!(!events.is_empty(), "no activity");
    assert_eq!(i.end.blue_score, score, "end last touch");
    state.lane_tip = lane::bytes(tip);
    state.last_touch = score;
    state.accounting().unwrap();
    let journal = [
        i.old_state,
        i.old_tip,
        state.root(),
        state.lane_tip,
        lane::bytes(i.end.seq(key, tip)),
        i.covenant,
        hash(b"KPI-private-native-tx-domain-v1"),
        hash(b"KPI-private-native-batch-domain-v1"),
        permission,
        deposit,
        lane::bytes(key),
    ]
    .concat();
    Output {
        state,
        journal,
        events,
    }
}
