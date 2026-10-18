//! Local real-proof transition kernel. Native facts are test interfaces, not a
//! chain oracle; no native key, signing, RPC or payout command exists here.
use crate::{protocol::*, wallet::Verifier, Result};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
#[derive(Clone, Serialize, Deserialize)]
pub struct Deposit {
    pub amount: u64,
    pub owner: H,
    pub status: u8,
} // pending=0, credited=1, refund=2
#[derive(Clone, Serialize, Deserialize)]
pub struct PendingExit {
    pub amount: u64,
    pub destination: H,
    pub paid: bool,
}
#[derive(Clone, Serialize, Deserialize)]
pub struct Ledger {
    pub verifier: H,
    pub tree: Tree,
    pub anchors: BTreeSet<H>,
    pub nullifiers: BTreeSet<H>,
    pub deposits: BTreeMap<H, Deposit>,
    pub exits: BTreeMap<H, PendingExit>,
    pub paid_native_outputs: BTreeSet<H>,
    pub deliveries: Vec<Delivery>,
    pub reserve: u64,
    pub private_liability: u64,
    pub batch: u64,
}
impl Ledger {
    pub fn new(verifier: H) -> Self {
        let tree = Tree::default();
        let anchors = BTreeSet::from([tree.root()]);
        Self {
            verifier,
            tree,
            anchors,
            nullifiers: BTreeSet::new(),
            deposits: BTreeMap::new(),
            exits: BTreeMap::new(),
            paid_native_outputs: BTreeSet::new(),
            deliveries: vec![],
            reserve: 0,
            private_liability: 0,
            batch: 0,
        }
    }
    pub fn state_hash(&self) -> H {
        let mut b = b"KPI-canonical-state-v1\0".to_vec();
        b.extend(domain());
        b.extend(self.verifier);
        b.extend((self.tree.leaves.len() as u32).to_le_bytes());
        for x in &self.tree.leaves {
            b.extend(x)
        }
        b.extend((self.anchors.len() as u32).to_le_bytes());
        for x in &self.anchors {
            b.extend(x)
        }
        b.extend((self.nullifiers.len() as u32).to_le_bytes());
        for x in &self.nullifiers {
            b.extend(x)
        }
        b.extend((self.deposits.len() as u32).to_le_bytes());
        for (id, d) in &self.deposits {
            b.extend(id);
            b.extend(d.amount.to_le_bytes());
            b.extend(d.owner);
            b.push(d.status)
        }
        b.extend((self.exits.len() as u32).to_le_bytes());
        for (id, e) in &self.exits {
            b.extend(id);
            b.extend(e.amount.to_le_bytes());
            b.extend(e.destination);
            b.push(e.paid as u8)
        }
        b.extend((self.paid_native_outputs.len() as u32).to_le_bytes());
        for id in &self.paid_native_outputs {
            b.extend(id)
        }
        b.extend((self.deliveries.len() as u32).to_le_bytes());
        for d in &self.deliveries {
            b.extend(d.commitment);
            b.extend(hash(&d.ciphertext))
        }
        b.extend(self.reserve.to_le_bytes());
        b.extend(self.private_liability.to_le_bytes());
        b.extend(self.batch.to_le_bytes());
        hash(&b)
    }
    pub fn register_authenticated_fixture_deposit(
        &mut self,
        id: H,
        amount: u64,
        owner: H,
    ) -> Result<()> {
        self.invariant()?;
        if amount == 0 || id == [0; 32] || owner == [0; 32] || self.deposits.contains_key(&id) {
            return Err("deposit duplicate/encoding".into());
        }
        let reserve = self.reserve.checked_add(amount).ok_or("reserve overflow")?;
        self.deposits.insert(
            id,
            Deposit {
                amount,
                owner,
                status: 0,
            },
        );
        self.reserve = reserve;
        self.invariant()
    }
    pub fn invariant(&self) -> Result<()> {
        let pending: u128 = self
            .deposits
            .values()
            .filter(|d| d.status == 0)
            .map(|d| d.amount as u128)
            .sum();
        let exits: u128 = self
            .exits
            .values()
            .filter(|e| !e.paid)
            .map(|e| e.amount as u128)
            .sum();
        if self.private_liability as u128 + pending + exits != self.reserve as u128 {
            return Err("backing mismatch".into());
        }
        Ok(())
    }
    pub fn apply(&mut self, engine: &Verifier, op: &Operation) -> Result<H> {
        self.invariant()?;
        if engine.id() != self.verifier {
            return Err("unconfigured verifier".into());
        }
        engine.verify(op)?;
        let s = &op.statement;
        let before = self.state_hash();
        if !self.anchors.contains(&s.anchor) {
            return Err("unpermitted anchor".into());
        }
        let mut next = self.clone();
        if [TRANSFER, EXIT].contains(&s.kind) {
            if s.nullifier == [0; 32] || next.nullifiers.contains(&s.nullifier) {
                return Err("current economic nullifier spent".into());
            }
            next.nullifiers.insert(s.nullifier);
        }
        if [CREDIT, RECOVER].contains(&s.kind) {
            let d = next.deposits.get_mut(&s.deposit).ok_or("unknown deposit")?;
            if d.status != 0 || d.amount != s.deposit_value || d.owner != s.deposit_owner {
                return Err("deposit owner/value/status".into());
            }
            d.status = if s.kind == CREDIT { 1 } else { 2 };
        }
        if s.kind == CREDIT {
            next.private_liability = next
                .private_liability
                .checked_add(s.deposit_value)
                .ok_or("liability overflow")?;
        }
        if s.kind == EXIT {
            next.private_liability = next
                .private_liability
                .checked_sub(s.exit_value)
                .ok_or("exit backing")?;
        }
        if [EXIT, RECOVER].contains(&s.kind) {
            let id = s.id();
            if next.exits.contains_key(&id) {
                return Err("duplicate exit".into());
            }
            next.exits.insert(
                id,
                PendingExit {
                    amount: s.exit_value,
                    destination: s.exit_destination,
                    paid: false,
                },
            );
        }
        for d in op.deliveries.iter().take(s.output_count()) {
            next.tree.append(d.commitment)?;
            next.deliveries.push(d.clone());
        }
        next.anchors.insert(next.tree.root());
        next.invariant()?;
        *self = next;
        Ok(tagged(
            b"KPI-transition-v1\0",
            &[&before, &self.state_hash(), &s.id()],
        ))
    }
    pub fn next_batch(&mut self) -> Result<()> {
        self.batch = self.batch.checked_add(1).ok_or("batch overflow")?;
        Ok(())
    }
    pub fn confirm_authenticated_fixture_payout(
        &mut self,
        id: H,
        amount: u64,
        destination: H,
        native_output: H,
    ) -> Result<()> {
        self.invariant()?;
        if native_output == [0; 32] || self.paid_native_outputs.contains(&native_output) {
            return Err("native payout output replay".into());
        }
        let e = self.exits.get(&id).ok_or("unknown exit")?;
        if e.paid || e.amount != amount || e.destination != destination {
            return Err("payout amount/destination/status".into());
        }
        let reserve = self
            .reserve
            .checked_sub(amount)
            .ok_or("reserve underflow")?;
        self.exits.get_mut(&id).unwrap().paid = true;
        self.paid_native_outputs.insert(native_output);
        self.reserve = reserve;
        self.invariant()
    }
}
