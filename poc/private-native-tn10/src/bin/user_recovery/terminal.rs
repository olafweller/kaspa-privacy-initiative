//! Additive HOST-ONLY full-drain relation. Not used by the PR54 guest.
//! Incoming permission/payout facts require authenticated accepted L1 in a future
//! guest. Tests explicitly use synthetic UTXOs; no acceptance flag is a proof.
#![allow(dead_code)]
use super::*;
use kaspa_consensus_core::tx::Transaction;
use kaspa_txscript::script_builder::ScriptBuilder;
use vprogs_zk_abi::withdrawal::StandardSpk;
use vprogs_zk_backend_risc0_api::{build_permission_redeem_script, PermissionTreeAccumulator};

#[derive(Clone)]
pub struct Claim {
    pub prior: State,
    pub ledger: app::wallet::ledger::Ledger,
    pub reserve: app::Outpoint,
    pub eid: H,
    pub recipient: H,
}
impl Claim {
    pub fn admit(state: &State, op: &Operation, recipient: H) -> Result<Self> {
        state.accounting()?;
        require(
            state.permissions.is_empty() && state.ledger.exits.values().all(|e| e.paid),
            "one pending terminal exit",
        )?;
        require(
            op.statement.kind == EXIT
                && chain::destination(&recipient) == op.statement.exit_destination,
            "authorized terminal recipient",
        )?;
        secp256k1::XOnlyPublicKey::from_slice(&recipient)?;
        let mut ledger = state.ledger.clone();
        ledger.apply(&verifier(), op)?;
        let reserve = state
            .reserves
            .iter()
            .find(|(_, value)| **value == op.statement.exit_value)
            .map(|(p, _)| p.clone())
            .ok_or("one exact reserve required")?;
        // Native script numbers are signed. Reject instead of truncating.
        i64::try_from(
            op.statement
                .exit_value
                .checked_add(app::PERMISSION_RENT)
                .ok_or("rent overflow")?,
        )?;
        Ok(Self {
            prior: state.clone(),
            ledger,
            reserve,
            eid: op.statement.id(),
            recipient,
        })
    }
    pub fn amount(&self) -> u64 {
        self.ledger.exits[&self.eid].amount
    }
    pub fn commitment(&self) -> H {
        tagged(
            b"KPI-local-terminal-claim-v1\0",
            &[
                &self.prior.root(),
                &self.ledger.state_hash(),
                &self.eid,
                &self.recipient,
                &bincode::serialize(&self.reserve).unwrap(),
                &hash(&self.redeem().expect("admitted claim")),
            ],
        )
    }
    pub fn redeem(&self) -> Result<Vec<u8>> {
        let mut b = ScriptBuilder::new();
        b.add_ops(&app::restricted::lane_guard())?;
        // v1, permission index 0, exactly 3 inputs / 2 outputs.
        b.add_ops(&[
            0xb2, 0x51, 0x88, 0xb9, 0x00, 0x88, 0xb3, 0x53, 0x88, 0xb4, 0x52, 0x88,
        ])?;
        b.add_ops(&[0x51, 0xba])?
            .add_data(&self.reserve.id)?
            .add_op(0x88)?;
        b.add_ops(&[0x51, 0xbb])?
            .add_i64(self.reserve.index as i64)?
            .add_op(0x88)?;
        let delegate = [vec![0, 0], app::delegate(&self.prior.covenant)].concat();
        b.add_ops(&[0x51, 0xbf])?
            .add_data(&delegate)?
            .add_op(0x88)?;
        b.add_ops(&[0x51, 0xbe])?
            .add_i64(i64::try_from(self.amount())?)?
            .add_op(0x88)?;
        // Sponsor cannot be covenant-bound or a second tracked delegate.
        b.add_ops(&[0x52, 0xcf])?.add_data(&[0; 32])?.add_op(0x88)?;
        b.add_ops(&[0x52, 0xbf])?
            .add_data(&delegate)?
            .add_ops(&[0x87, 0x00, 0x88])?;
        for i in 0..2 {
            b.add_i64(i)?.add_ops(&[0xd6, 0x4f, 0x88])?; // no covenant output
            b.add_i64(i)?
                .add_op(0xc3)?
                .add_data(&delegate)?
                .add_ops(&[0x87, 0x00, 0x88])?;
        }
        let empty = PermissionTreeAccumulator::hash_empty();
        let leaf = PermissionTreeAccumulator::hash_leaf(
            StandardSpk::PubKey(&self.recipient),
            self.amount(),
        );
        let root = PermissionTreeAccumulator::hash_branch(&leaf, &empty);
        b.add_ops(&build_permission_redeem_script(&root, 1, 1))?;
        Ok(b.drain())
    }
    /// Call ONLY for ID-derived accepted lane bodies after permission issuance
    /// has authenticated this exact permission outpoint/script/covenant/rent.
    /// This function cannot establish native acceptance by itself.
    pub fn reconcile_accepted_body(
        &self,
        permission: &app::Outpoint,
        tx: &Transaction,
    ) -> Result<State> {
        use kaspa_consensus_core::hashing::tx::transaction_v1_rest_preimage;
        let body = app::NativeTx::parse(&transaction_v1_rest_preimage(tx))?;
        require(
            body.inputs.len() == 3
                && body.outputs.len() == 2
                && body.inputs[0] == *permission
                && body.inputs[1] == self.reserve,
            "terminal shape/lineage",
        )?;
        require(
            body.inputs[2] != *permission && !self.prior.reserves.contains_key(&body.inputs[2]),
            "separate sponsor input",
        )?;
        let paid = self
            .amount()
            .checked_add(app::PERMISSION_RENT)
            .ok_or("rent overflow")?;
        let destination = StandardSpk::PubKey(&self.recipient).to_script_bytes();
        require(
            body.outputs[0].value >= paid
                && body.outputs[0].version == 0
                && body.outputs[0].script == destination.as_slice(),
            "principal/rent/recipient",
        )?;
        require(
            body.outputs.iter().all(|o| {
                o.covenant.is_none()
                    && (o.version != 0 || o.script != app::delegate(&self.prior.covenant))
            }),
            "terminal no reserve/covenant outputs",
        )?;
        let id = vprogs_l1_utils::tx_id_v1(&tx.payload, &transaction_v1_rest_preimage(tx));
        let mut next = self.prior.clone();
        next.ledger = self.ledger.clone();
        next.ledger.confirm_authenticated_fixture_payout(
            self.eid,
            self.amount(),
            chain::destination(&self.recipient),
            chain::deposit_reference(id, 0),
        )?;
        require(
            next.reserves.remove(&self.reserve) == Some(self.amount()),
            "exact reserve removal",
        )?;
        next.exit_keys.insert(self.eid, self.recipient);
        next.exit_reserves.insert(self.eid, self.reserve.clone());
        next.accounting()?;
        Ok(next)
    }
}
