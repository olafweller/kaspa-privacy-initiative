//! Thin live-data adapter over Kaspa's existing transaction, lane and SMT code.
//! This executable checks captured commitments; it does NOT produce a zk proof.
use kaspa_consensus_core::{config::params::TESTNET_PARAMS, tx::Transaction};
use kaspa_hashes::{Hash, SeqCommitActiveNode};
use kaspa_rpc_core::{GetSeqCommitLaneProofResponse, RpcOptionalTransaction};
use kaspa_seq_commit::{hashing::*, types::*};
use kaspa_smt::proof::OwnedSmtProof;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{collections::HashSet, error::Error, fs, str::FromStr};

type Result<T> = std::result::Result<T, Box<dyn Error>>;
mod proofs;
const STATE_TAG: &[u8] = b"KPI-LANE-STATE-v1";
fn ensure(condition: bool, message: &str) -> Result<()> {
    if condition {
        Ok(())
    } else {
        Err(message.into())
    }
}
fn hash(value: &Value) -> Result<Hash> {
    Ok(Hash::from_str(value.as_str().ok_or("missing hash")?)?)
}
fn number(value: &Value) -> Result<u64> {
    value.as_u64().ok_or_else(|| "missing integer".into())
}
fn record(capture: &Value, name: &str) -> Result<Value> {
    let records = capture["records"].as_array().ok_or("missing records")?;
    let matches: Vec<_> = records.iter().filter(|r| r["label"] == name).collect();
    ensure(matches.len() == 1, "missing/duplicate RPC record")?;
    let wire: Value = serde_json::from_str(matches[0]["raw"].as_str().ok_or("missing raw")?)?;
    ensure(wire.get("error").is_none(), "RPC error in capture")?;
    Ok(wire["params"].clone())
}
fn seq_for_lane(
    proof: &GetSeqCommitLaneProofResponse,
    key: &Hash,
    lane: Option<(Hash, u64)>,
) -> Result<Hash> {
    let leaf = lane.map(|(tip, score)| {
        smt_leaf_hash(&SmtLeafInput {
            lane_tip: &tip,
            blue_score: score,
        })
    });
    let owned = OwnedSmtProof::from_bytes(&proof.smt_proof)?;
    let lanes_root = owned
        .as_proof()
        .compute_root::<SeqCommitActiveNode>(key, leaf)?;
    let activity_root = activity_root_hash(&proof.inactivity_shortcut, &lanes_root);
    let state_root = seq_state_root(&SeqState {
        activity_root: &activity_root,
        payload_and_ctx_digest: &proof.payload_and_ctx_digest,
    });
    Ok(seq_commit(&SeqCommitInput {
        parent_seq_commit: &proof.parent_seq_commit,
        state_root: &state_root,
    }))
}
fn proof_lane(p: &GetSeqCommitLaneProofResponse) -> Option<(Hash, u64)> {
    p.lane.as_ref().map(|l| (l.tip, l.blue_score))
}

fn verify(capture: &Value, subnet: &[u8; 20], attack: &str) -> Result<Value> {
    ensure(
        capture["kind"] == "TN10_NATIVE_JSON_RPC_CAPTURE_V1" && capture["failure"].is_null(),
        "incomplete capture",
    )?;
    for label in ["server-before", "server-after"] {
        let server = record(capture, label)?;
        ensure(
            server["networkId"] == "testnet-10" && server["isSynced"] == true,
            "wrong network or unsynchronized node",
        )?;
    }
    let key = lane_key(subnet);
    ensure(hash(&capture["laneKey"])? == key, "wrong lane key")?;
    let start = record(capture, "start-block")?["block"].clone();
    let end = record(capture, "end-block")?["block"].clone();
    ensure(
        start["verboseData"]["isChainBlock"] == true && end["verboseData"]["isChainBlock"] == true,
        "orphan endpoint",
    )?;
    let start_hash = hash(&start["header"]["hash"])?;
    let end_hash = hash(&end["header"]["hash"])?;
    let start_seq = hash(&start["header"]["acceptedIdMerkleRoot"])?;
    let end_seq = hash(&end["header"]["acceptedIdMerkleRoot"])?;
    let start_proof: GetSeqCommitLaneProofResponse =
        serde_json::from_value(record(capture, "start-proof")?)?;
    let end_proof: GetSeqCommitLaneProofResponse =
        serde_json::from_value(record(capture, "end-proof")?)?;
    ensure(
        seq_for_lane(&start_proof, &key, proof_lane(&start_proof))? == start_seq,
        "start witness mismatch",
    )?;
    ensure(
        seq_for_lane(&end_proof, &key, proof_lane(&end_proof))? == end_seq,
        "end witness mismatch",
    )?;
    // Pin proof requests to the exact selected-chain endpoints, not executor-chosen roots.
    for (label, block_hash) in [("start-proof", start_hash), ("end-proof", end_hash)] {
        let r = capture["records"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["label"] == label)
            .unwrap();
        ensure(
            hash(&r["request"]["blockHash"])? == block_hash
                && hash(&r["request"]["laneKey"])? == key,
            "proof request binding",
        )?;
    }
    let first = record(capture, "accepted")?;
    let second = record(capture, "accepted-recheck")?;
    ensure(
        first["removedChainBlockHashes"]
            .as_array()
            .ok_or("missing reorg list")?
            .is_empty()
            && second["removedChainBlockHashes"]
                .as_array()
                .ok_or("missing reorg list")?
                .is_empty(),
        "reorg capture",
    )?;
    let count = number(&capture["intervalBlocks"])? as usize;
    let chain = first["chainBlockAcceptedTransactions"]
        .as_array()
        .ok_or("missing accepted bodies")?;
    let check = second["chainBlockAcceptedTransactions"]
        .as_array()
        .ok_or("missing recheck")?;
    ensure(
        count > 0 && chain.len() >= count && check.len() >= count,
        "truncated interval",
    )?;
    ensure(chain[..count] == check[..count], "unstable interval")?;
    let added = first["addedChainBlockHashes"]
        .as_array()
        .ok_or("missing added chain")?;
    ensure(added.len() >= count, "missing selected-chain hashes")?;
    let mut lane = proof_lane(&start_proof);
    let mut parent_seq = start_seq;
    let mut parent_time = number(&start["header"]["timestamp"])?;
    let mut parent_score = number(&start["header"]["blueScore"])?;
    let mut state: [u8; 32] = Sha256::digest(STATE_TAG).into();
    let mut seen = HashSet::new();
    let mut operations = Vec::new();
    let mut activity_count = 0;
    let mut did_attack = false;
    let mut selected_ids = Vec::new();
    for (n, b) in chain[..count].iter().enumerate() {
        let header = &b["chainBlockHeader"];
        ensure(header["hash"] == added[n], "chain order mismatch")?;
        let score = number(&header["blueScore"])?;
        ensure(score > parent_score, "unordered chain scores")?;
        let mut transactions = b["acceptedTransactions"]
            .as_array()
            .ok_or("missing transactions")?
            .clone();
        if attack == "reorder"
            && transactions
                .iter()
                .filter(|t| t["subnetworkId"] == hex::encode(subnet))
                .count()
                >= 2
            && !did_attack
        {
            let indices: Vec<_> = transactions
                .iter()
                .enumerate()
                .filter(|(_, t)| t["subnetworkId"] == hex::encode(subnet))
                .map(|(i, _)| i)
                .collect();
            transactions.swap(indices[0], indices[1]);
            did_attack = true;
        }
        let mut activity = ActivityDigestBuilder::new();
        let mut nonempty = false;
        for (idx, raw) in transactions.iter().enumerate() {
            let rpc: RpcOptionalTransaction = serde_json::from_value(raw.clone())?;
            let tx: Transaction = rpc.try_into()?;
            let txid = tx.id();
            ensure(
                hash(&raw["verboseData"]["transactionId"])? == txid,
                "transaction/payload ID mismatch",
            )?;
            ensure(seen.insert(txid), "duplicate accepted transaction")?;
            if tx.subnetwork_id.as_bytes() != subnet {
                continue;
            }
            if attack == "omit" && !did_attack {
                did_attack = true;
                continue;
            }
            let mut id = txid;
            if attack == "substitute-id" && !did_attack {
                id = Hash::from_bytes([0x99; 32]);
                did_attack = true;
            }
            activity.add_leaf(activity_leaf(&id, tx.version, u32::try_from(idx)?));
            nonempty = true;
            activity_count += 1;
            selected_ids.push(txid.to_string());
            if tx.payload.len() == 15 && tx.payload.starts_with(b"KPI-LANE-v1") {
                operations.push(u32::from_le_bytes(tx.payload[11..].try_into()?));
                state = Sha256::digest([STATE_TAG, &state, &tx.payload].concat()).into();
            }
        }
        if nonempty {
            let previous = match lane {
                Some((tip, last_score)) => {
                    ensure(
                        score.saturating_sub(last_score) <= TESTNET_PARAMS.finality_depth(),
                        "unsupported lane reactivation",
                    )?;
                    tip
                }
                None => parent_seq, // Upstream first-touch rule, authenticated absence above.
            };
            let ctx = mergeset_context_hash(&MergesetContext {
                timestamp: parent_time,
                daa_score: number(&header["daaScore"])?,
                blue_score: score,
            });
            let tip = lane_tip_next(&LaneTipInput {
                parent_ref: &previous,
                lane_key: &key,
                activity_digest: &activity.finalize(),
                context_hash: &ctx,
            });
            lane = Some((tip, score));
        }
        parent_seq = hash(&header["acceptedIdMerkleRoot"])?;
        parent_time = number(&header["timestamp"])?;
        parent_score = score;
    }
    ensure(
        chain[count - 1]["chainBlockHeader"]["hash"] == end["header"]["hash"]
            && parent_seq == end_seq,
        "end block mismatch",
    )?;
    ensure(
        attack == "none" || did_attack,
        "negative control had no applicable activity",
    )?;
    ensure(
        seq_for_lane(&end_proof, &key, lane)? == end_seq,
        "derived lane does not match fixed TN10 end anchor",
    )?;
    ensure(
        lane == proof_lane(&end_proof),
        "derived lane entry mismatch",
    )?;
    Ok(
        json!({"scope":"LIVE_TN10_COMMITMENT_RECONSTRUCTION_NOT_ZK_OR_SETTLEMENT", "network":"testnet-10", "blocks":count,
        "start":start_hash.to_string(),"end":end_hash.to_string(),"lane":hex::encode(subnet),"lane_key":key.to_string(),
        "lane_tip":lane.map(|x|x.0.to_string()),"seq_commit":end_seq.to_string(),"accepted_lane_transactions":activity_count,
        "ordered_transaction_ids":selected_ids,"recognized_kpi_operations":operations,"state_from_initial_domain":hex::encode(state),
        "trust":"one owner-operated consensus-validating node; no second independent node", "zk_proof":false,"settlement":false}),
    )
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    if args.get(1).map(String::as_str) == Some("profile") {
        ensure(
            std::env::var("RISC0_DEV_MODE").is_err(),
            "development mode forbidden",
        )?;
        let input: kpi_lane_common::Input = serde_json::from_slice(&fs::read(&args[2])?)?;
        let program = fs::read(&args[3])?;
        let env = risc0_zkvm::ExecutorEnv::builder().write(&input)?.build()?;
        let execution = risc0_zkvm::default_executor().execute(env, &program)?;
        ensure(
            execution.journal.bytes
                == kpi_lane_common::journal(&input, &kpi_lane_common::execute(&input)),
            "profile journal mismatch",
        )?;
        println!(
            "{}",
            json!({"scope":"EXECUTION_ONLY_NO_CRYPTOGRAPHIC_PROOF", "segments":execution.segments.iter().map(|s|json!({"po2":s.po2,"cycles":s.cycles})).collect::<Vec<_>>()})
        );
        return Ok(());
    }
    if args.get(1).map(String::as_str) == Some("prove") {
        let input: kpi_lane_common::Input = serde_json::from_slice(&fs::read(&args[2])?)?;
        println!(
            "{}",
            proofs::prove(&input, std::path::Path::new(&args[3]), &fs::read(&args[4])?)
        );
        return Ok(());
    }
    let subnet: [u8; 20] = hex::decode(
        args.get(2)
            .ok_or("usage: kpi-tn10-integration key LANE | verify LANE CAPTURE")?,
    )?
    .try_into()
    .map_err(|_| "lane length")?;
    if args[1] == "key" {
        println!("{}", lane_key(&subnet));
        return Ok(());
    }
    if args[1] == "build" {
        return build_transaction(&args, &subnet);
    }
    if args[1] == "export" {
        let capture: Value = serde_json::from_slice(&fs::read(&args[3])?)?;
        verify(&capture, &subnet, "none")?;
        let covenant = Hash::from_str(&args[4])?;
        let input = export_input(&capture, subnet, covenant)?;
        println!("{}", serde_json::to_string_pretty(&input)?);
        return Ok(());
    }
    ensure(args[1] == "verify", "unknown command")?;
    let capture: Value = serde_json::from_slice(&fs::read(args.get(3).ok_or("missing capture")?)?)?;
    let result = verify(&capture, &subnet, "none")?;
    let mut negatives = serde_json::Map::new();
    for attack in ["omit", "reorder", "substitute-id"] {
        match verify(&capture, &subnet, attack) {
            Err(error) => {
                if error.to_string() == "negative control had no applicable activity" {
                    negatives.insert(
                        attack.into(),
                        json!({"exercised":false,"reason":error.to_string()}),
                    );
                    continue;
                }
                negatives.insert(
                    attack.into(),
                    json!({"rejected":true,"reason":error.to_string()}),
                );
            }
            Ok(_) => return Err(format!("negative control accepted: {attack}").into()),
        }
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({"valid":result,"negative_controls":negatives}))?
    );
    Ok(())
}

fn export_input(
    capture: &Value,
    subnet: [u8; 20],
    covenant: Hash,
) -> Result<kpi_lane_common::Input> {
    use kaspa_smt::proof::ProofTerminal;
    use kpi_lane_common::{Anchor, Block, Input, Tx};
    fn convert(p: GetSeqCommitLaneProofResponse) -> Result<Anchor> {
        let lane = p.lane.ok_or("original guest requires active lane")?;
        let proof = OwnedSmtProof::from_bytes(&p.smt_proof)?;
        let depth = match proof.terminal {
            ProofTerminal::Collapsed { depth } => depth,
            _ => return Err("original guest requires collapsed inclusion".into()),
        };
        Ok(Anchor {
            parent_seq: p.parent_seq_commit.into(),
            payload_ctx: p.payload_and_ctx_digest.into(),
            shortcut: p.inactivity_shortcut.into(),
            blue_score: lane.blue_score,
            bitmap: proof.bitmap,
            depth,
            siblings: proof.siblings.into_iter().map(Into::into).collect(),
        })
    }
    let start = record(capture, "start-block")?["block"].clone();
    let sp: GetSeqCommitLaneProofResponse =
        serde_json::from_value(record(capture, "start-proof")?)?;
    let ep: GetSeqCommitLaneProofResponse = serde_json::from_value(record(capture, "end-proof")?)?;
    let old_tip = sp.lane.as_ref().ok_or("inactive start")?.tip;
    let mut prev_time = number(&start["header"]["timestamp"])?;
    let mut blocks = Vec::new();
    let accepted = record(capture, "accepted")?;
    for b in accepted["chainBlockAcceptedTransactions"]
        .as_array()
        .ok_or("missing blocks")?
        .iter()
        .take(number(&capture["intervalBlocks"])? as usize)
    {
        let mut txs = Vec::new();
        for (index, raw) in b["acceptedTransactions"]
            .as_array()
            .ok_or("missing bodies")?
            .iter()
            .enumerate()
        {
            let rpc: RpcOptionalTransaction = serde_json::from_value(raw.clone())?;
            let tx: Transaction = rpc.try_into()?;
            if tx.subnetwork_id.as_bytes() != &subnet {
                continue;
            }
            ensure(tx.version == 1, "guest requires v1")?;
            txs.push(Tx {
                payload: tx.payload.clone(),
                rest: kaspa_consensus_core::hashing::tx::transaction_v1_rest_preimage(&tx),
                merge_idx: u32::try_from(index)?,
            });
        }
        let h = &b["chainBlockHeader"];
        blocks.push(Block {
            prev_timestamp: prev_time,
            daa_score: number(&h["daaScore"])?,
            blue_score: number(&h["blueScore"])?,
            txs,
        });
        prev_time = number(&h["timestamp"])?;
    }
    let input = Input {
        lane: subnet,
        covenant: covenant.into(),
        old_state: kpi_lane_common::initial_state(),
        old_tip: old_tip.into(),
        start: convert(sp)?,
        start_seq: hash(&start["header"]["acceptedIdMerkleRoot"])?.into(),
        blocks,
        end: convert(ep)?,
    };
    let output = kpi_lane_common::execute(&input);
    let end = record(capture, "end-block")?;
    ensure(
        Hash::from_bytes(output.seq) == hash(&end["block"]["header"]["acceptedIdMerkleRoot"])?,
        "guest endpoint differs from node",
    )?;
    Ok(input)
}

fn build_transaction(args: &[String], subnet: &[u8; 20]) -> Result<()> {
    use kaspa_addresses::{Address, Prefix, Version};
    use kaspa_consensus_core::{
        sign::sign,
        subnets::SubnetworkId,
        tx::{MutableTransaction, TransactionOutpoint, TransactionOutput, UtxoEntry},
    };
    use kaspa_rpc_core::{RpcTransaction, RpcUtxosByAddressesEntry};
    use std::io::Write;
    use vprogs_l1_wallet::build::*;
    ensure(
        subnet[4..].iter().all(|x| *x == 0) && subnet[1..4].iter().any(|x| *x != 0),
        "invalid user lane",
    )?;
    let request: Value = serde_json::from_slice(&fs::read(&args[4])?)?;
    ensure(
        request["server"]["networkId"] == "testnet-10" && request["server"]["isSynced"] == true,
        "wrong network or unsynchronized node",
    )?;
    let secret = secp256k1::SecretKey::from_str(fs::read_to_string(&args[3])?.trim())?;
    let keypair = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &secret);
    let address = Address::new(
        Prefix::Testnet,
        Version::PubKey,
        &keypair.x_only_public_key().0.serialize(),
    );
    let entries: Vec<RpcUtxosByAddressesEntry> =
        serde_json::from_value(request["utxos"]["entries"].clone())?;
    let current = number(&request["server"]["virtualDaaScore"])?;
    let mut candidates = Vec::new();
    for e in entries {
        ensure(
            e.address.as_ref() == Some(&address),
            "foreign funding address",
        )?;
        if e.utxo_entry.is_coinbase
            && e.utxo_entry.block_daa_score + TESTNET_PARAMS.blockrate.coinbase_maturity > current
        {
            continue;
        }
        let entry: UtxoEntry = e.utxo_entry.into();
        ensure(entry.covenant_id.is_none(), "reserve cannot fund fees")?;
        candidates.push((e.outpoint.into(), entry));
    }
    candidates.sort_by_key(|(_, e)| std::cmp::Reverse(e.amount));
    ensure(
        !candidates.is_empty(),
        "testwallet has no mature spendable UTXOs",
    )?;
    let rate = request["feeEstimate"]["normalBuckets"]
        .as_array()
        .and_then(|a| a.first())
        .and_then(|b| b["feerate"].as_f64())
        .unwrap_or(100.0);
    ensure(rate.is_finite() && rate > 0., "invalid fee rate")?;
    let policy = FeePolicy::TargetFeerate(rate * 1.25);
    let mut meta =
        json!({"network":"testnet-10","address":address.to_string(),"kind":request["kind"]});
    let tx = match request["kind"].as_str().ok_or("missing kind")? {
        "activity" => activity_transaction(ActivityTx {
            payload: kpi_lane_common::operation(u32::try_from(number(&request["number"])?)?),
            candidates: candidates.clone(),
            keypair,
            address: &address,
            subnetwork_id: SubnetworkId::from_bytes(*subnet),
            tx_version: 1,
            fee_policy: policy,
            params: &TESTNET_PARAMS,
        })?,
        "bootstrap" => {
            let tip = hash(&request["tip"])?;
            let program = fs::read(args.get(6).ok_or("program required")?)?;
            let redeem = proofs::initial_redeem(subnet, &tip, &program);
            let value = 100_000_000u64;
            let (outpoint, entry) = candidates[0].clone();
            // Reuse upstream genesis binding, add ordinary change before signing.
            let (template, covenant) = covenant_bootstrap_transaction(
                &redeem,
                value,
                outpoint,
                entry.clone(),
                keypair,
                &TESTNET_PARAMS,
            );
            let mut fee = 1_000_000u64;
            let signed = loop {
                let mut t = template.clone();
                let change = entry
                    .amount
                    .checked_sub(value)
                    .and_then(|n| n.checked_sub(fee))
                    .ok_or("insufficient bootstrap funds")?;
                t.outputs.push(TransactionOutput::new(
                    change,
                    kaspa_txscript::pay_to_address_script(&address),
                ));
                t = sign(
                    MutableTransaction::with_entries(t, vec![entry.clone()]),
                    keypair,
                )
                .tx;
                let required = min_fee(&TESTNET_PARAMS, &t)
                    .max((min_fee(&TESTNET_PARAMS, &t) as f64 * rate / 100. * 1.25).ceil() as u64);
                if required > fee {
                    fee = required;
                    continue;
                }
                commit_storage_mass(&TESTNET_PARAMS, &t, &[entry.clone()]);
                t.finalize();
                break t;
            };
            let spk = &signed.outputs[0].script_public_key;
            let covenant_address =
                kaspa_txscript::extract_script_pub_key_address(spk, Prefix::Testnet)?;
            meta["covenantId"] = json!(covenant.to_string());
            meta["initialTip"] = json!(tip.to_string());
            meta["redeemHex"] = json!(hex::encode(redeem));
            meta["covenantAddress"] = json!(covenant_address.to_string());
            signed
        }
        "settlement" => {
            let input: kpi_lane_common::Input = serde_json::from_value(request["input"].clone())?;
            ensure(input.lane == *subnet, "settlement lane mismatch")?;
            let mut output = kpi_lane_common::execute(&input);
            let receipt: risc0_zkvm::Receipt = bincode::deserialize(&fs::read(
                request["receiptPath"].as_str().ok_or("receipt path")?,
            )?)?;
            let program = fs::read(args.get(6).ok_or("program required")?)?;
            let end = hash(&request["end"])?;
            let ce: RpcUtxosByAddressesEntry =
                serde_json::from_value(request["covenantUtxo"].clone())?;
            ensure(
                ce.utxo_entry.covenant_id == Some(Hash::from_bytes(input.covenant)),
                "wrong covenant entry",
            )?;
            let covenant_entry: UtxoEntry = ce.utxo_entry.into();
            let outpoint: TransactionOutpoint = ce.outpoint.into();
            let valid = proofs::settlement(
                &input,
                &output,
                &program,
                &receipt,
                end,
                outpoint,
                covenant_entry.amount,
            );
            ensure(
                covenant_entry.script_public_key
                    == kaspa_txscript::standard::pay_to_script_hash_script(&valid.prev_redeem),
                "covenant state pin mismatch",
            )?;
            struct Anchor(Hash, Hash);
            impl kaspa_txscript::seq_commit_accessor::SeqCommitAccessor for Anchor {
                fn is_chain_ancestor_from_pov(&self, b: Hash) -> Option<bool> {
                    Some(b == self.0)
                }
                fn seq_commitment_within_depth(&self, b: Hash) -> Option<Hash> {
                    (b == self.0).then_some(self.1)
                }
            }
            let budget = valid.covenant_compute_budget(
                Hash::from_bytes(input.covenant),
                &Anchor(end, Hash::from_bytes(output.seq)),
            );
            meta["computeBudget"] = json!(u16::from(budget));
            let settlement = if request["invalidState"] == true {
                output.state[0] ^= 1;
                proofs::settlement(
                    &input,
                    &output,
                    &program,
                    &receipt,
                    end,
                    outpoint,
                    covenant_entry.amount,
                )
            } else {
                valid
            };
            meta["newState"] = json!(hex::encode(output.state));
            settlement_transaction(SettlementTx {
                settlement_tx: settlement.transaction,
                covenant_entry,
                covenant_compute_budget: budget,
                fee_candidates: candidates.clone(),
                keypair,
                address: &address,
                fee_policy: policy,
                params: &TESTNET_PARAMS,
            })?
        }
        _ => return Err("unknown transaction kind".into()),
    };
    let spent: HashSet<_> = tx.inputs.iter().map(|i| i.previous_outpoint).collect();
    let mut total = 0u64;
    for (outpoint, entry) in candidates {
        if spent.contains(&outpoint) {
            total = total
                .checked_add(entry.amount)
                .ok_or("input amount overflow")?;
        }
    }
    if request["kind"] == "settlement" {
        total = total
            .checked_add(number(&request["covenantUtxo"]["utxoEntry"]["amount"])?)
            .ok_or("covenant amount overflow")?;
    }
    let outputs = tx
        .outputs
        .iter()
        .try_fold(0u64, |a, o| a.checked_add(o.value))
        .ok_or("output amount overflow")?;
    let fee = total.checked_sub(outputs).ok_or("value creation")?;
    ensure(
        fee <= 100_000_000,
        "trial fee exceeds one test-KAS; inspect concrete transaction",
    )?;
    meta["feeSompi"] = json!(fee);
    if request["kind"] == "settlement" {
        meta["successorAddress"] = json!(kaspa_txscript::extract_script_pub_key_address(
            &tx.outputs[0].script_public_key,
            Prefix::Testnet
        )?
        .to_string());
    }
    meta["transactionId"] = json!(tx.id().to_string());
    meta["transaction"] = serde_json::to_value(RpcTransaction::from(&tx))?;
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&args[5])?;
    file.write_all(serde_json::to_string_pretty(&meta)?.as_bytes())?;
    println!(
        "{}",
        json!({"transactionId":tx.id().to_string(),"feeSompi":fee,"kind":request["kind"]})
    );
    Ok(())
}
