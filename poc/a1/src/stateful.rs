//! Isolated native consensus/storage/virtual-processor tests. No RPC or networking.
//! The genesis is synthetic (fixture reserve imported with its real MuHash), and
//! proof-of-work is skipped. These are NOT public TN10 acceptance results.
use kaspa_consensus::consensus::test_consensus::TestConsensus;
use kaspa_consensus_core::{
    api::{ConsensusApi, args::TransactionValidationArgs},
    config::{ConfigBuilder, params::TESTNET_PARAMS},
    header::Header,
    muhash::MuHashExtensions,
    tx::{MutableTransaction, Transaction, TransactionOutpoint, UtxoEntry},
};
use kaspa_hashes::Hash;
use kaspa_muhash::MuHash;
use serde_json::{Value, json};
use std::{sync::Arc, thread::JoinHandle};

struct Harness {
    consensus: TestConsensus,
    threads: Vec<JoinHandle<()>>,
    serial: u64,
}
impl Drop for Harness {
    fn drop(&mut self) {
        self.consensus.shutdown(std::mem::take(&mut self.threads));
    }
}
impl Harness {
    fn new(outpoint: TransactionOutpoint, entry: &UtxoEntry) -> Result<Self, String> {
        let mut multiset = MuHash::new();
        multiset.add_utxo(&outpoint, entry);
        let mut params = TESTNET_PARAMS;
        params.genesis.utxo_commitment = multiset.finalize();
        params.genesis.hash = Header::from(&params.genesis).hash;
        let config = ConfigBuilder::new(params)
            .skip_proof_of_work()
            .set_archival()
            .build();
        let consensus = TestConsensus::new(&config);
        let threads = consensus.init();
        let result = Self {
            consensus,
            threads,
            serial: 0,
        };
        let mut imported = MuHash::new();
        result
            .consensus
            .append_imported_pruning_point_utxos(&[(outpoint, entry.clone())], &mut imported);
        result
            .consensus
            .import_pruning_point_utxo_set(result.consensus.params().genesis.hash, imported)
            .map_err(|e| format!("native fixture import: {e:?}"))?;
        if !result.has(outpoint) {
            return Err("fixture missing after native import".into());
        }
        Ok(result)
    }
    fn has(&self, outpoint: TransactionOutpoint) -> bool {
        self.consensus
            .get_virtual_utxos(Some(outpoint), 1, false)
            .first()
            .is_some_and(|(op, _)| *op == outpoint)
    }
    fn entry(&self, outpoint: TransactionOutpoint) -> Option<UtxoEntry> {
        self.consensus
            .get_virtual_utxos(Some(outpoint), 1, false)
            .into_iter()
            .next()
            .and_then(|(op, entry)| (op == outpoint).then_some(entry))
    }
    fn spend(&self, tx: &Transaction) -> Result<(), String> {
        let mut mutable = MutableTransaction::new(Arc::new(tx.clone()));
        self.consensus
            .validate_mempool_transaction(&mut mutable, &TransactionValidationArgs::default())
            .map_err(|e| format!("native virtual UTXO: {e:?}"))
    }
    fn block(&mut self, parents: Vec<Hash>, txs: Vec<Transaction>) -> Result<Hash, String> {
        self.serial += 1;
        let mut bytes = [0x5a; 32];
        bytes[..8].copy_from_slice(&self.serial.to_le_bytes());
        let hash = Hash::from_bytes(bytes);
        let future = self
            .consensus
            .add_utxo_valid_block_with_parents(hash, parents, txs);
        futures_executor::block_on(future).map_err(|e| format!("native block: {e:?}"))?;
        Ok(hash)
    }
}

/// Native archive receipts, not an RPC simulation: body indexes are supplied by
/// actual acceptance data and bodies are read back from native block storage.
fn accepted_group(h: &Harness, accepting: Hash) -> Result<Value, String> {
    let data = h
        .consensus
        .get_block_acceptance_data(accepting)
        .map_err(|e| format!("native receipt acceptance: {e:?}"))?;
    let mut bodies = vec![];
    for mb in data.iter() {
        for accepted in &mb.accepted_transactions {
            let stored = h
                .consensus
                .get_block_transactions(mb.block_hash, Some(vec![accepted.index_within_block]))
                .map_err(|e| format!("native receipt body retrieval: {e:?}"))?;
            let tx = stored.first().ok_or("native receipt missing body")?;
            if tx.id() != accepted.transaction_id {
                return Err("native receipt body ID mismatch".into());
            }
            bodies.push(json!({"source_block":mb.block_hash.to_string(),"index_within_block":accepted.index_within_block,
                "txid":tx.id().to_string(),"full_hash":kaspa_consensus_core::hashing::tx::hash(tx).to_string(),"transaction":tx}));
        }
    }
    Ok(
        json!({"accepting_block":accepting.to_string(),"acceptance_data":data.as_ref(),"accepted_bodies":bodies}),
    )
}

/// Accept an exact fixture path using actual native virtual UTXOs at each step,
/// and export bodies retrieved from native block storage with acceptance data.
/// This is a synthetic chain/archive fixture, not a live/indexed TN10 source.
pub fn accept_path(steps: &[Transaction], initial: &UtxoEntry) -> Result<Value, String> {
    let first = steps.first().ok_or("empty native path")?;
    if first.inputs.len() != 1 {
        return Err("native path initial input count".into());
    }
    let mut h = Harness::new(first.inputs[0].previous_outpoint, initial)?;
    let genesis = h.consensus.params().genesis.hash;
    let mut parent = genesis;
    let mut receipts = vec![];
    for tx in steps {
        if tx.inputs.len() != 1 {
            return Err("native path single input".into());
        }
        let input_entry = h
            .entry(tx.inputs[0].previous_outpoint)
            .ok_or("native path current input unavailable")?;
        h.spend(tx)?;
        let block = h.block(vec![parent], vec![tx.clone()])?;
        let accepting = h.block(vec![block], vec![])?;
        if h.has(tx.inputs[0].previous_outpoint) {
            return Err("native path input not consumed".into());
        }
        for (index, output) in tx.outputs.iter().enumerate() {
            let native = h
                .entry(TransactionOutpoint::new(tx.id(), index as u32))
                .ok_or("native path output missing")?;
            if native.amount != output.value
                || native.script_public_key != output.script_public_key
                || native.covenant_id.is_some()
            {
                return Err("native path output terms mismatch".into());
            }
        }
        let acceptance = h
            .consensus
            .get_block_acceptance_data(accepting)
            .map_err(|e| format!("native path acceptance: {e:?}"))?;
        let accepted = acceptance
            .iter()
            .flat_map(|m| m.accepted_transactions.iter())
            .any(|a| a.transaction_id == tx.id());
        if !accepted {
            return Err("native path transaction missing from acceptance data".into());
        }
        let bodies = h
            .consensus
            .get_block_transactions(block, Some(vec![1]))
            .map_err(|e| format!("native path body: {e:?}"))?;
        let body = bodies.first().ok_or("native path body retrieval empty")?;
        if body.id() != tx.id() {
            return Err("native path stored body ID mismatch".into());
        }
        receipts.push(
            json!({"block":block.to_string(),"accepting_block":accepting.to_string(),
            "acceptance_data":acceptance.as_ref(),"transaction":body,"input_entry":input_entry}),
        );
        parent = accepting;
    }
    Ok(json!({"backend":"native TestConsensus + temporary RocksDB",
        "network":"isolated synthetic TN10-parameter chain; no public TN10 acceptance",
        "synthetic_genesis_hash":genesis.to_string(),"accepted_path":receipts,
        "current_virtual_utxos":h.consensus.get_virtual_utxos(None, 1000, false)}))
}

#[cfg(test)]
mod tests {
    use super::*;
    use kaspa_consensus_core::tx::{ScriptPublicKey, TransactionInput, TransactionOutput};

    /// Harness qualification only: trivially spendable *synthetic* UTXO, never
    /// an A1 script/proof positive. Real A1 fixtures must separately call the suite.
    #[test]
    fn native_storage_competing_spends_and_rollback() {
        let original = TransactionOutpoint::new(Hash::from_bytes([0x91; 32]), 7);
        let entry = UtxoEntry::new(
            1_060_000_000,
            ScriptPublicKey::from_vec(0, vec![0x51]),
            0,
            false,
            None,
        );
        let mut tx = Transaction::new(
            1,
            vec![TransactionInput::new_with_compute_budget(
                original,
                vec![],
                u64::MAX,
                2000,
            )],
            vec![TransactionOutput::new(
                1_040_000_000,
                ScriptPublicKey::from_vec(0, vec![0x51]),
            )],
            0,
            Default::default(),
            0,
            vec![],
        );
        crate::validator::set_mass(&tx, &entry).unwrap();
        let mut other = tx.clone();
        other.inputs[0].sequence -= 1;
        other.finalize();
        crate::validator::set_mass(&other, &entry).unwrap();
        // One-bit replay modification in suite must differ from loser too.
        tx.inputs[0].sequence -= 2;
        tx.finalize();
        crate::validator::set_mass(&tx, &entry).unwrap();
        competing_and_reorg(&tx, &other, &entry).unwrap();
    }
}

/// Each competitor must already be a genuine proof-valid spend of the same S0.
/// Caller may provide continuation/continuation (different sequence/ID) or
/// continuation/terminal. We exercise a real conflicting sibling DAG and then
/// a longer conflicting fork to force native rollback/reapplication. In Kaspa's
/// DAG an empty fork need not remove a nonconflicting known spend: it can still
/// enter a mergeset. Therefore the final original outpoint remains spent by the
/// alternative, while every old winner output must disappear atomically.
pub fn competing_and_reorg(
    first: &Transaction,
    second: &Transaction,
    entry: &UtxoEntry,
) -> Result<Value, String> {
    if first.inputs.len() != 1
        || second.inputs.len() != 1
        || first.id() == second.id()
        || first.inputs[0].previous_outpoint != second.inputs[0].previous_outpoint
    {
        return Err("competitors need distinct IDs and same single input".into());
    }
    let tv = crate::validator::validator();
    crate::validator::validate(&tv, first, entry)?;
    crate::validator::validate(&tv, second, entry)?;
    let original = first.inputs[0].previous_outpoint;
    let mut h = Harness::new(original, entry)?;
    h.spend(first)?;
    h.spend(second)?;
    let genesis = h.consensus.params().genesis.hash;
    let a = h.block(vec![genesis], vec![first.clone()])?;
    let b = h.block(vec![genesis], vec![second.clone()])?;
    let merged = h.block(vec![a, b], vec![])?;
    let accepted = h.block(vec![merged], vec![])?;
    let first_present = h.has(TransactionOutpoint::new(first.id(), 0));
    let second_present = h.has(TransactionOutpoint::new(second.id(), 0));
    if first_present == second_present || h.has(original) {
        return Err("native competitors did not produce exactly one winner".into());
    }
    let (winner, loser) = if first_present {
        (first, second)
    } else {
        (second, first)
    };
    for (index, output) in winner.outputs.iter().enumerate() {
        let native = h
            .entry(TransactionOutpoint::new(winner.id(), index as u32))
            .ok_or("winner output missing from native UTXO set")?;
        if native.amount != output.value
            || native.script_public_key != output.script_public_key
            || native.covenant_id.is_some()
        {
            return Err("native winner output terms mismatch".into());
        }
    }
    for index in 0..loser.outputs.len() {
        if h.has(TransactionOutpoint::new(loser.id(), index as u32)) {
            return Err("loser payout/successor exists".into());
        }
    }
    let loser_result = h.spend(loser);
    if loser_result.is_ok() {
        return Err("spent-input competitor accepted".into());
    }
    let exact_replay_result = h.spend(winner);
    if exact_replay_result.is_ok() {
        return Err("exact replay accepted as new virtual-UTXO spend".into());
    }
    let mut replay = winner.clone();
    replay.inputs[0].sequence ^= 1; // Still relative-lock-disabled; outpoint proof remains valid.
    replay.finalize();
    crate::validator::set_mass(&replay, entry)?;
    if replay.id() == winner.id() {
        return Err("replay ID unchanged".into());
    }
    crate::validator::validate(&tv, &replay, entry)?;
    let replay_result = h.spend(&replay);
    if replay_result.is_ok() {
        return Err("native spent-input replay accepted".into());
    }
    let initial_acceptance = h
        .consensus
        .get_block_acceptance_data(merged)
        .map_err(|e| format!("native initial acceptance data: {e:?}"))?;
    let initial_ids = initial_acceptance
        .iter()
        .flat_map(|mb| mb.accepted_transactions.iter())
        .map(|tx| tx.transaction_id)
        .collect::<Vec<_>>();
    if !initial_ids.contains(&winner.id()) || initial_ids.contains(&loser.id()) {
        return Err("native initial accepting block disagrees with virtual winner".into());
    }
    let mut accepted_body = None;
    for mb in initial_acceptance.iter() {
        for tx in &mb.accepted_transactions {
            if tx.transaction_id == winner.id() {
                let body = h
                    .consensus
                    .get_block_transactions(mb.block_hash, Some(vec![tx.index_within_block]))
                    .map_err(|e| format!("native accepted body retrieval: {e:?}"))?;
                accepted_body = body.into_iter().next();
            }
        }
    }
    let accepted_body = accepted_body.ok_or("native accepted body missing")?;
    if accepted_body.id() != winner.id() {
        return Err("native accepted body ID mismatch".into());
    }
    let initial_path = h
        .consensus
        .get_virtual_chain_from_block(genesis, None)
        .map_err(|e| format!("native initial chain path: {e:?}"))?;
    if !initial_path.removed.is_empty() {
        return Err("initial genesis path unexpectedly removes history".into());
    }
    let initial_groups = initial_path
        .added
        .iter()
        .map(|block| accepted_group(&h, *block))
        .collect::<Result<Vec<_>, _>>()?;
    let before_utxos = h.consensus.get_virtual_utxos(None, 1000, false);
    let mut fork = h.block(vec![genesis], vec![loser.clone()])?;
    // Move competing history outside k-cluster. Use current native k, not a lower
    // convenience parameter, and read actual virtual-chain removed blocks.
    let fork_blocks = u64::from(h.consensus.params().ghostdag_k()) + 12;
    for _ in 1..fork_blocks {
        fork = h.block(vec![fork], vec![])?;
    }
    let path = h
        .consensus
        .get_virtual_chain_from_block(accepted, None)
        .map_err(|e| format!("native reorg chain: {e:?}"))?;
    if path.removed.is_empty()
        || h.has(original)
        || h.has(TransactionOutpoint::new(winner.id(), 0))
        || !h.has(TransactionOutpoint::new(loser.id(), 0))
    {
        return Err(format!(
            "native reorg failed to remove old winner/install alternative: removed={}, original={}, first={}, second={}",
            path.removed.len(),
            h.has(original),
            h.has(TransactionOutpoint::new(first.id(), 0)),
            h.has(TransactionOutpoint::new(second.id(), 0))
        ));
    }
    for index in 0..winner.outputs.len() {
        if h.has(TransactionOutpoint::new(winner.id(), index as u32)) {
            return Err("payout output survived native rollback".into());
        }
    }
    for (index, output) in loser.outputs.iter().enumerate() {
        let native = h
            .entry(TransactionOutpoint::new(loser.id(), index as u32))
            .ok_or("alternate output missing after native reorg")?;
        if native.amount != output.value
            || native.script_public_key != output.script_public_key
            || native.covenant_id.is_some()
        {
            return Err("native reorg alternate output terms mismatch".into());
        }
    }
    let mut new_acceptance = vec![];
    let mut new_ids = vec![];
    for block in &path.added {
        let data = h
            .consensus
            .get_block_acceptance_data(*block)
            .map_err(|e| format!("native reorg acceptance data: {e:?}"))?;
        for mb in data.iter() {
            for tx in &mb.accepted_transactions {
                new_ids.push(tx.transaction_id);
            }
        }
        new_acceptance.push(accepted_group(&h, *block)?);
    }
    if !new_ids.contains(&loser.id()) || new_ids.contains(&winner.id()) {
        return Err("native new chain acceptance IDs inconsistent with restored outputs".into());
    }
    Ok(
        json!({"backend":"kaspa-consensus TestConsensus temporary RocksDB + native virtual processors",
        "network":"isolated synthetic genesis with TN10 parameters; no public-chain acceptance", "proof_of_work":"skipped",
        "both_standalone_valid":true,"both_initial_virtual_utxo_valid":true,"winner_txid":winner.id().to_string(),
        "loser_txid":loser.id().to_string(),"loser_rejection":loser_result.unwrap_err(),
        "exact_replay_behavior":"native virtual-UTXO validation rejects spent original input (no RPC/idempotent submission claim)",
        "exact_replay_rejection":exact_replay_result.unwrap_err(),
        "distinct_replay_standalone_valid":true,"distinct_replay_txid":replay.id().to_string(),"replay_rejection":replay_result.unwrap_err(),
        "fork_blocks":fork_blocks,"removed_chain_blocks":path.removed.iter().map(ToString::to_string).collect::<Vec<_>>(),
        "added_chain_blocks":path.added.iter().map(ToString::to_string).collect::<Vec<_>>(),
        "synthetic_genesis_hash":genesis.to_string(),"initial_accepting_block":merged.to_string(),
        "initial_acceptance_data":initial_acceptance.as_ref(),"initial_native_accepted_body":accepted_body,
        "receipt_schema":"kpi-a1-native-reorg/v1",
        "checkpoint_scope":"S0 imported into synthetic genesis; authenticated fixture checkpoint, NOT recovered funding lineage or live TN10 history",
        "original_outpoint":original,"original_input_entry":entry,
        "initial_chain_blocks":initial_path.added.iter().map(ToString::to_string).collect::<Vec<_>>(),
        "initial_chain_acceptance_data":initial_groups,
        "before_reorg_virtual_utxos":before_utxos,
        "after_reorg_virtual_utxos":h.consensus.get_virtual_utxos(None, 1000, false),
        "new_chain_acceptance_data":new_acceptance,
        "original_reserve_final_unspent":false,"original_reserve_spent_by_alternative":true,
        "all_old_winner_outputs_removed_on_reorg":true,"all_alternate_outputs_exact":true,
        "state_pointer_rollback":"old winner outpoints removed, alternative outpoints installed by native UTXO processor; original S0 stays spent after atomic replacement",
        "alternate_accepted_after_reorg":true}),
    )
}
