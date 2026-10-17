//! Temporary PUBLIC account state. No privacy or general vProgs runtime claim.
//! Upstream actions execute inside the same guest as authenticated lane processing.
pub use kpi_lane_common as lane;
use runtime::{
    config::{config_total_len, write_config},
    deposit_policy::ExampleDepositPolicy,
    ix::{decode_ix, ActionBody},
    lock::LockEnum,
    lock_variants::SchnorrLockView,
    resource_id::config_resource_id,
    user::UserView,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use vprogs_core_codec::{Reader, Writer};
use vprogs_zk_abi::transaction_processor::{
    process_transaction, JournalEntries, OutputCommitment, Payload,
};
use vprogs_zk_backend_risc0_api::{delegate_entry_spk_hash, PermissionTreeAccumulator};
pub use vprogs_zk_backend_risc0_runtime_processor as runtime;

pub const TX_DOMAIN: [u8; 32] = [0x61; 32];
pub const BATCH_DOMAIN: [u8; 32] = [0x62; 32];
pub const MIN_WITHDRAWAL: u64 = 1_000;
pub const PERMISSION_RENT: u64 = 50_000_000;
#[derive(Clone, Debug, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct State {
    #[serde(with = "resource_map")]
    pub users: BTreeMap<[u8; 32], Vec<u8>>,
    pub credited: Vec<([u8; 32], u32)>,
    pub requests: Vec<[u8; 32]>,
}
impl State {
    pub fn hash(&self) -> [u8; 32] {
        let mut v = b"KPI-PUBLIC-NATIVE-STATE-v1".to_vec();
        v.extend_from_slice(&(self.users.len() as u32).to_le_bytes());
        for (id, data) in &self.users {
            v.extend(id);
            v.write_blob(data);
        }
        v.extend_from_slice(&(self.credited.len() as u32).to_le_bytes());
        for (id, i) in &self.credited {
            v.extend(id);
            v.extend(i.to_le_bytes());
        }
        v.extend_from_slice(&(self.requests.len() as u32).to_le_bytes());
        for id in &self.requests {
            v.extend(id);
        }
        Sha256::digest(v).into()
    }
    pub fn spendable(&self) -> u64 {
        self.users
            .values()
            .try_fold(0u64, |n, v| {
                n.checked_add(UserView::from_bytes(v).expect("user bytes").balance())
            })
            .expect("balance sum overflow")
    }
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Input {
    pub lane: lane::Input,
    pub state: State,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Event {
    pub id: [u8; 32],
    pub accepted: bool,
    pub error: Option<String>,
    pub spendable: u64,
    pub emitted: u64,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Exit {
    pub recipient: [u8; 32],
    pub amount: u64,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Output {
    pub state: State,
    pub lane: lane::Output,
    pub events: Vec<Event>,
    pub exits: Vec<Exit>,
    pub deposit_hash: [u8; 32],
    pub permission_hash: [u8; 32],
}
struct MemoryHost {
    input: Vec<u8>,
    output: Vec<u8>,
}
impl vprogs_zk_abi::Read for MemoryHost {
    fn read_blob(&mut self) -> Vec<u8> {
        std::mem::take(&mut self.input)
    }
}
impl Writer for MemoryHost {
    fn write(&mut self, b: &[u8]) {
        self.output.extend_from_slice(b)
    }
}
fn config(covenant: &[u8; 32]) -> Vec<u8> {
    // Not operator supplied, not a funded genesis allocation. Update/Init are disabled.
    let lock = LockEnum::Schnorr(SchnorrLockView {
        pubkey: &runtime::genesis::GENESIS_SCHNORR_BYTES,
    });
    let mut data = vec![0; config_total_len(&lock)];
    write_config(&mut data, MIN_WITHDRAWAL, covenant, &lock).unwrap();
    data
}
pub fn apply_transaction(
    state: &State,
    covenant: &[u8; 32],
    tx: &lane::Tx,
) -> Result<(State, Vec<Exit>, [u8; 32]), String> {
    let payload = Payload::decode(&tx.payload).map_err(|e| format!("{e:?}"))?;
    let ix =
        decode_ix(payload.ix_data, payload.access_metadata.len()).map_err(|e| format!("{e:?}"))?;
    if ix.actions.is_empty() {
        return Err("empty app action".into());
    }
    let cfg = *config_resource_id();
    let mut previous = None;
    for a in payload.access_metadata {
        let id = *a.resource_id;
        if previous.is_some_and(|p| p >= id) {
            return Err("noncanonical/duplicate resource ids".into());
        }
        previous = Some(id);
        if id == cfg && u8::from(a.access_type) != 0 {
            return Err("immutable config requires read access".into());
        }
    }
    let mut credit_keys = vec![];
    let mut withdrawal = false;
    let id = lane_id(tx);
    for a in &ix.actions {
        match &a.body {
            ActionBody::Deposit { output_idx, .. } => {
                let key = (id, *output_idx);
                if state.credited.contains(&key) {
                    return Err("deposit already credited".into());
                }
                // L1 outputs bound to a different covenant are not usable reserve entries.
                ensure_unbound_output(&tx.rest, *output_idx)?;
                credit_keys.push(key);
            }
            ActionBody::Withdraw { dest, .. } => {
                if !matches!(dest, vprogs_zk_abi::withdrawal::StandardSpk::PubKey(_)) {
                    return Err("experiment requires P2PK recipient".into());
                }
                withdrawal = true;
            }
            _ => return Err("only Deposit/Withdraw enabled; no config/admin actions".into()),
        }
    }
    if withdrawal && state.requests.contains(&id) {
        return Err("withdrawal command already applied".into());
    }
    let mut wire = vec![];
    wire.extend(1u16.to_le_bytes());
    wire.extend(id);
    wire.extend(tx.merge_idx.to_le_bytes());
    wire.extend([0u8; 32]);
    let mut body = vec![];
    body.write_blob(&tx.payload);
    body.write_blob(&tx.rest);
    wire.write_blob(&body);
    for (i, a) in payload.access_metadata.iter().enumerate() {
        wire.extend((i as u32).to_le_bytes());
        if *a.resource_id == cfg {
            wire.write_blob(&config(covenant));
        } else {
            wire.write_blob(
                state
                    .users
                    .get(&*a.resource_id)
                    .map(Vec::as_slice)
                    .unwrap_or(&[]),
            );
        }
    }
    let mut host = MemoryHost {
        input: wire,
        output: vec![],
    };
    let mut journal = vec![];
    let mut changed = BTreeMap::new();
    process_transaction::<vprogs_zk_backend_risc0_api::Sha256>(
        &mut host,
        &mut journal,
        |t, _, _, resources, exits, deposit| {
            runtime::runtime::run(t, resources, exits, deposit, &ExampleDepositPolicy)?;
            for r in resources {
                if **r.id() == cfg {
                    continue;
                }
                if u8::from(r.access_type()) == 0 && r.is_dirty() {
                    return Err(vprogs_zk_abi::Error::Decode(
                        "read resource modified".into(),
                    ));
                }
                if !r.data().is_empty() {
                    UserView::from_bytes(r.data())
                        .map_err(|e| vprogs_zk_abi::Error::Decode(e.into()))?;
                }
                changed.insert(**r.id(), r.data().to_vec());
            }
            Ok(())
        },
    );
    let entries = JournalEntries::decode(&journal).map_err(|e| format!("{e:?}"))?;
    match entries.output_commitment {
        OutputCommitment::Error(e) => Err(format!("{e:?}")),
        OutputCommitment::Success {
            exits,
            deposit_spk_hash,
            ..
        } => {
            let mut state = state.clone();
            for (id, data) in changed {
                if data.is_empty() {
                    state.users.remove(&id);
                } else {
                    state.users.insert(id, data);
                }
            }
            state.credited.extend(credit_keys);
            if withdrawal {
                state.requests.push(id);
            }
            let exits = exits
                .iter()
                .map(|e| match e.unwrap() {
                    (vprogs_zk_abi::withdrawal::StandardSpk::PubKey(k), amount) => Exit {
                        recipient: *k,
                        amount,
                    },
                    _ => unreachable!(),
                })
                .collect();
            Ok((state, exits, *deposit_spk_hash))
        }
    }
}
pub fn lane_id(tx: &lane::Tx) -> [u8; 32] {
    // Uses the same native v1 hashing implementation as the retained lane relation.
    vprogs_l1_utils::tx_id_v1(&tx.payload, &tx.rest)
}
fn ensure_unbound_output(rest: &[u8], index: u32) -> Result<(), String> {
    let parse = || -> vprogs_core_codec::Result<bool> {
        let mut b = rest;
        b.skip(2, "version")?;
        let n = b.le_u64("ninputs")?;
        for _ in 0..n {
            b.skip(36, "outpoint")?;
            let n = b.le_u64("siglen")?;
            b.skip(n as usize, "sig")?;
            b.skip(8, "sequence")?;
        }
        let n = b.le_u64("noutputs")?;
        for i in 0..n {
            b.skip(10, "amount/version")?;
            let n = b.le_u64("spklen")?;
            b.skip(n as usize, "spk")?;
            let flag = b.byte("covflag")?;
            if i == index as u64 {
                return Ok(flag == 0);
            }
            if flag == 1 {
                b.skip(34, "covenant")?;
            }
        }
        Ok(false)
    };
    if parse().map_err(|e| format!("{e:?}"))? {
        Ok(())
    } else {
        Err("deposit output missing or covenant-bound".into())
    }
}
pub fn execute(input: &Input) -> Output {
    assert_eq!(
        input.state.hash(),
        input.lane.old_state,
        "authenticated prior user state"
    );
    // This computes EVERY lane ID, including deterministically rejected app commands.
    // Its seq is derived, not equated to the host's claimed endpoint in the guest:
    // a real omitted-input proof can be made, but cannot settle at the authentic anchor.
    let lane = lane::execute(&input.lane);
    let mut state = input.state.clone();
    let mut events = vec![];
    let mut exits = vec![];
    let mut deposit_hash = [0; 32];
    for tx in input.lane.blocks.iter().flat_map(|b| &b.txs) {
        let result = apply_transaction(&state, &input.lane.covenant, tx);
        let (accepted, error, emitted) = match result {
            Ok((next, emitted, deposit)) => {
                if deposit != [0; 32] {
                    assert_eq!(deposit, delegate_entry_spk_hash(&input.lane.covenant));
                    deposit_hash = deposit;
                }
                let amount = emitted
                    .iter()
                    .try_fold(0u64, |n, e| n.checked_add(e.amount))
                    .unwrap();
                state = next;
                exits.extend(emitted);
                (true, None, amount)
            }
            Err(e) => (false, Some(e), 0),
        };
        events.push(Event {
            id: lane_id(tx),
            accepted,
            error,
            spendable: state.spendable(),
            emitted,
        });
    }
    let mut tree = PermissionTreeAccumulator::new();
    for e in &exits {
        tree.add_exit(
            vprogs_zk_abi::withdrawal::StandardSpk::PubKey(&e.recipient),
            e.amount,
        );
    }
    Output {
        state,
        lane,
        events,
        exits,
        deposit_hash,
        permission_hash: tree.finalize(),
    }
}
pub fn journal(input: &Input, out: &Output) -> Vec<u8> {
    let mut j = lane::journal(&input.lane, &out.lane);
    j[64..96].copy_from_slice(&out.state.hash());
    j[192..224].copy_from_slice(&TX_DOMAIN);
    j[224..256].copy_from_slice(&BATCH_DOMAIN);
    j[256..288].copy_from_slice(&out.permission_hash);
    j[288..320].copy_from_slice(&out.deposit_hash);
    j
}

mod resource_map {
    use super::*;
    pub fn serialize<S: serde::Serializer>(
        map: &BTreeMap<[u8; 32], Vec<u8>>,
        s: S,
    ) -> Result<S::Ok, S::Error> {
        map.iter().collect::<Vec<_>>().serialize(s)
    }
    pub fn deserialize<'de, D: serde::Deserializer<'de>>(
        d: D,
    ) -> Result<BTreeMap<[u8; 32], Vec<u8>>, D::Error> {
        let entries = Vec::<([u8; 32], Vec<u8>)>::deserialize(d)?;
        if entries.windows(2).any(|w| w[0].0 >= w[1].0) {
            return Err(serde::de::Error::custom("noncanonical resource order"));
        }
        Ok(entries.into_iter().collect())
    }
}
