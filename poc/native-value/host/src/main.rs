use app::{lane, runtime};
use kaspa_addresses::{Address, Prefix, Version};
use kaspa_consensus_core::{
    config::params::TESTNET_PARAMS, hashing::tx::transaction_v1_rest_preimage, sign::sign,
    subnets::SubnetworkId, tx::*,
};
use kaspa_hashes::Hash;
use kaspa_rpc_core::{RpcTransaction, RpcUtxosByAddressesEntry};
use kpi_native_common::{self as app, Input, Output, State};
use risc0_zkvm::sha::Digestible;
use risc0_zkvm::{
    compute_image_id, default_executor, default_prover, ExecutorEnv, ProverOpts, Receipt,
};
use serde_json::{json, Value};
use std::{error::Error, fs, path::Path, str::FromStr};
use vprogs_l1_wallet::build::*;
use vprogs_zk_abi::withdrawal::StandardSpk;
use vprogs_zk_backend_risc0_api::{
    build_delegate_entry_script, build_permission_redeem_script, PermissionTreeAccumulator,
};
use vprogs_zk_backend_risc0_covenant::{
    script::{build_redeem_script, redeem_script_len, CommonPins, RedeemPins, SuccinctPins},
    Settlement, SettlementInput, SettlementWitness, SuccinctWitness,
};
#[allow(dead_code)]
mod actions;
type Result<T> = std::result::Result<T, Box<dyn Error>>;
fn read(p: &str) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(p)?)?)
}
fn save(p: &str, v: &Value) -> Result<()> {
    use std::io::Write;
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)?;
    f.write_all(&serde_json::to_vec_pretty(v)?)?;
    Ok(())
}
fn hash(v: &Value) -> Result<Hash> {
    Ok(Hash::from_str(v.as_str().ok_or("hash")?)?)
}
fn num(v: &Value) -> Result<u64> {
    v.as_u64().ok_or_else(|| "missing exact u64".into())
}
fn require(ok: bool, msg: &str) -> Result<()> {
    if ok {
        Ok(())
    } else {
        Err(msg.into())
    }
}
fn pins<'a>(image: &'a [u8; 32], key: &'a Hash) -> RedeemPins<'a> {
    RedeemPins::Succinct(SuccinctPins {
        common: CommonPins {
            program_id: image,
            tx_image_id: &app::TX_DOMAIN,
            batch_image_id: &app::BATCH_DOMAIN,
            lane_key: key,
            permission_output_value: app::PERMISSION_RENT,
        },
    })
}
fn initial(lane: &[u8; 20], tip: &Hash, program: &[u8]) -> Vec<u8> {
    let image = compute_image_id(program).unwrap().into();
    let key = kaspa_seq_commit::hashing::lane_key(lane);
    let pins = pins(&image, &key);
    let state = State::default().hash();
    build_redeem_script(&state, tip, redeem_script_len(&state, &pins), &pins)
}
struct Anchor(Hash, Hash);
impl kaspa_txscript::seq_commit_accessor::SeqCommitAccessor for Anchor {
    fn is_chain_ancestor_from_pov(&self, b: Hash) -> Option<bool> {
        Some(b == self.0)
    }
    fn seq_commitment_within_depth(&self, b: Hash) -> Option<Hash> {
        (b == self.0).then_some(self.1)
    }
}
fn settlement(
    input: &Input,
    out: &Output,
    program: &[u8],
    receipt: &Receipt,
    end: Hash,
    point: TransactionOutpoint,
    value: u64,
) -> Result<Settlement> {
    let image = compute_image_id(program)?;
    receipt.verify(image)?;
    require(
        receipt.journal.bytes == app::journal(input, &app::execute(input)),
        "receipt journal mismatch",
    )?;
    let s = receipt.inner.succinct()?;
    let seal: Vec<u8> = s.seal.iter().flat_map(|x| x.to_le_bytes()).collect();
    let claim = s.claim.digest().into();
    let control: Vec<u8> = s
        .control_inclusion_proof
        .digests
        .iter()
        .flat_map(|d| <[u8; 32]>::from(*d))
        .collect();
    let image = image.into();
    let key = kaspa_seq_commit::hashing::lane_key(&input.lane.lane);
    Ok(Settlement::build(&SettlementInput {
        covenant_id: Hash::from_bytes(input.lane.covenant),
        pins: pins(&image, &key),
        prev_state: &input.lane.old_state,
        prev_lane_tip: &Hash::from_bytes(input.lane.old_tip),
        new_state: &out.state.hash(),
        new_lane_tip: &Hash::from_bytes(out.lane.tip),
        block_prove_to: end,
        prev_outpoint: point,
        value,
        witness: SettlementWitness::Succinct(SuccinctWitness {
            seal: &seal,
            claim: &claim,
            control_index: s.control_inclusion_proof.index,
            control_digests: &control,
            deposit_spk_hash: &out.deposit_hash,
        }),
        permission_spk_hash: &out.permission_hash,
    }))
}
fn main() -> Result<()> {
    require(
        std::env::var("RISC0_DEV_MODE").is_err(),
        "development mode forbidden",
    )?;
    let a: Vec<_> = std::env::args().collect();
    match a.get(1).map(String::as_str){
 Some("wrap")=>{let raw=fs::read(&a[2])?;let p=risc0_binfmt::ProgramBinary::new(&raw,risc0_zkos_v1compat::V1COMPAT_ELF).encode();fs::write(&a[3],&p)?;println!("{}",compute_image_id(&p)?);},
 Some("prepare")=>{let mut lane:lane::Input=serde_json::from_value(read(&a[2])?)?;let state=if a[3]=="empty"{State::default()}else{serde_json::from_value(read(&a[3])?)?};lane.old_state=state.hash();lane.covenant=hash(&json!(a[4]))?.into();let input=Input{lane,state};save(&a[5],&serde_json::to_value(input)?)?;},
 Some("execute")|Some("profile")|Some("prove")=>{
  let input:Input=serde_json::from_value(read(&a[2])?)?;let out=app::execute(&input);let journal=app::journal(&input,&out);
  if a[1]=="execute"{println!("{}",serde_json::to_string_pretty(&out)?);return Ok(())}
  let program=fs::read(&a[3])?;let image=compute_image_id(&program)?;
  let env=ExecutorEnv::builder().write(&input)?.segment_limit_po2(20).build()?;
  if a[1]=="profile"{let session=default_executor().execute(env,&program)?;require(session.journal.bytes==journal,"profile journal mismatch")?;println!("{}",json!({"scope":"EXECUTION_ONLY_NO_PROOF","image":image.to_string(),"segments":session.segments.iter().map(|s|s.po2).collect::<Vec<_>>(),"cycles":session.segments.iter().map(|s|u64::from(s.cycles)).sum::<u64>(),"output":out}));}
  else{require(std::env::var("RISC0_PROVER").as_deref()==Ok("ipc"),"IPC real prover required")?;fs::create_dir(&a[4])?;let start=std::time::Instant::now();let info=default_prover().prove_with_opts(env,&program,&ProverOpts::succinct())?;info.receipt.verify(image)?;require(info.receipt.inner.succinct().is_ok(),"real succinct receipt required")?;require(info.receipt.journal.bytes==journal,"proven journal mismatch")?;let receipt=bincode::serialize(&info.receipt)?;fs::write(Path::new(&a[4]).join("receipt.bin"),&receipt)?;fs::write(Path::new(&a[4]).join("journal.bin"),&journal)?;save(&format!("{}/report.json",a[4]),&json!({"scope":"REAL_SUCCINCT_PROOF","developmentMode":false,"image":image.to_string(),"seconds":start.elapsed().as_secs_f64(),"bytes":receipt.len(),"stats":format!("{:?}",info.stats),"output":out}))?;}
 },
 Some("representative")=>{
  let mut lane:lane::Input=serde_json::from_value(read(&a[2])?)?;
  let pk=runtime::genesis::GENESIS_SCHNORR_BYTES;let covenant=[9u8;32];
  let outputs=vec![TransactionOutput::new(1_000_000_000,kaspa_txscript::standard::pay_to_script_hash_script(&build_delegate_entry_script(&covenant)))];
  let subnet=SubnetworkId::from_bytes(lane.lane);
  let dummy=|payload,outputs,point|Transaction::new(1,vec![TransactionInput::new(point,vec![],0,1)],outputs,0,subnet.clone(),0,payload);
  let point=TransactionOutpoint::new(Hash::from_bytes([7;32]),0);
  let deposit=dummy(actions::deposit_payload(&pk,0),outputs,point);
  let prev=dummy(vec![],vec![TransactionOutput::new(200_000_000,ScriptPublicKey::new(0,StandardSpk::PubKey(&pk).to_script_bytes().as_slice().to_vec().into()))],point);
  let withdrawal=dummy(witness_payload(&pk,400_000_000,&pk,&prev,false),vec![TransactionOutput::new(190_000_000,ScriptPublicKey::new(0,vec![0x51].into()))],TransactionOutpoint::new(prev.id(),0));
  let mut txs=vec![deposit];if a.get(4).is_some_and(|s|s=="full"){txs.push(withdrawal);}
  let first=lane.blocks.iter_mut().find(|b|!b.txs.is_empty()).ok_or("fixture has no txs")?;
  first.txs=txs.iter().enumerate().map(|(i,t)|lane::Tx{payload:t.payload.clone(),rest:transaction_v1_rest_preimage(t),merge_idx:i as u32+1}).collect();
  let mut seen=false;for b in &mut lane.blocks{if !b.txs.is_empty(){if seen{b.txs.clear()}else{seen=true}}}
  lane.end.blue_score=lane.blocks.iter().find(|b|!b.txs.is_empty()).unwrap().blue_score;
  lane.covenant=covenant;let state=State::default();lane.old_state=state.hash();
  save(&a[3],&serde_json::to_value(Input{lane,state})?)?;
 },
 Some("mutate-recipient")=>{
  let mut record=read(&a[2])?;
  let rpc:RpcTransaction=serde_json::from_value(record["transaction"].clone())?;
  let mut tx:Transaction=rpc.try_into()?;
  let payload=vprogs_zk_abi::transaction_processor::Payload::decode(&tx.payload)?;
  let ix=runtime::ix::decode_ix(payload.ix_data,payload.access_metadata.len())?;
  let mut offsets=vec![];
  for action in ix.actions {if let runtime::ix::ActionBody::Withdraw{dest:StandardSpk::PubKey(pk),..}=action.body{offsets.push(pk.as_ptr() as usize-tx.payload.as_ptr() as usize);}}
  require(offsets.len()==1,"one withdrawal recipient required")?;
  let replacement=hex::decode(&a[3])?;require(replacement.len()==32,"recipient length")?;
  let off=offsets[0];tx.payload[off..off+32].copy_from_slice(&replacement);tx.finalize();
  record["transactionId"]=json!(tx.id().to_string());record["transaction"]=serde_json::to_value(RpcTransaction::from(&tx))?;
  record["attack"]=json!("recipient changed without replacing owner's existing L1 signature");save(&a[4],&record)?;
 },
 Some("build")=>build(&a)?,
 _=>return Err("wrap RAW PROGRAM | prepare LANE STATE COV OUTPUT | execute INPUT | profile INPUT PROGRAM | prove INPUT PROGRAM NEWDIR | build KEY REQUEST OUTPUT PROGRAM".into())
 }
    Ok(())
}
fn witness_payload(
    owner: &[u8; 32],
    amount: u64,
    recipient: &[u8; 32],
    prev: &Transaction,
    unauthorized: bool,
) -> Vec<u8> {
    let (idx, _, entries) = actions::sorted_user_config_positions(actions::user_resource_id(owner));
    let access = actions::encode_access_metadata(&entries);
    let action = actions::encode_withdraw_action(idx, amount, &StandardSpk::PubKey(recipient));
    let acts = actions::encode_actions_section(&[action]);
    let rest = transaction_v1_rest_preimage(prev);
    let digest = vprogs_l1_utils::payload_digest_v1(&prev.payload);
    let probe = actions::encode_signers_section(&[actions::encode_witness_signer(idx, 0, 0, 0, 0)]);
    let offset = (access.len() + probe.len() + acts.len()) as u32;
    let sig = actions::encode_signers_section(&[actions::encode_witness_signer(
        idx,
        if unauthorized { 1 } else { 0 },
        offset,
        rest.len() as u32,
        offset + rest.len() as u32,
    )]);
    [access, sig, acts, rest, digest.to_vec()].concat()
}
// A one-funding-input builder, retaining the upstream signing/mass helpers.
// More complex settlement funding reuses settlement_transaction below.
fn ordinary(
    point: TransactionOutpoint,
    entry: UtxoEntry,
    key: secp256k1::Keypair,
    address: &Address,
    lane: SubnetworkId,
    payload: Vec<u8>,
    outputs: Vec<TransactionOutput>,
) -> Result<Transaction> {
    let fixed = outputs
        .iter()
        .try_fold(0u64, |a, o| a.checked_add(o.value))
        .ok_or("output overflow")?;
    let mut fee = 100_000u64;
    loop {
        let mut outs = outputs.clone();
        outs.push(TransactionOutput::new(
            entry
                .amount
                .checked_sub(fixed)
                .and_then(|n| n.checked_sub(fee))
                .ok_or("insufficient sponsor funds")?,
            kaspa_txscript::pay_to_address_script(address),
        ));
        let t = Transaction::new(
            1,
            vec![TransactionInput::new(point, vec![], 0, 1)],
            outs,
            0,
            lane.clone(),
            0,
            payload.clone(),
        );
        let mut t = sign(
            MutableTransaction::with_entries(t, vec![entry.clone()]),
            key,
        )
        .tx;
        let required = min_fee(&TESTNET_PARAMS, &t)
            .checked_mul(2)
            .ok_or("fee overflow")?;
        if required > fee {
            fee = required;
            continue;
        }
        commit_storage_mass(&TESTNET_PARAMS, &t, &[entry]);
        t.finalize();
        return Ok(t);
    }
}
fn build(a: &[String]) -> Result<()> {
    let req = read(&a[3])?;
    require(
        req["server"]["networkId"] == "testnet-10" && req["server"]["isSynced"] == true,
        "wrong network/unsynced",
    )?;
    let secret = secp256k1::SecretKey::from_str(fs::read_to_string(&a[2])?.trim())?;
    let key = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &secret);
    let owner = key.x_only_public_key().0.serialize();
    let address = Address::new(Prefix::Testnet, Version::PubKey, &owner);
    let es: Vec<RpcUtxosByAddressesEntry> =
        serde_json::from_value(req["utxos"]["entries"].clone())?;
    let mut candidates = vec![];
    for e in es {
        require(e.address.as_ref() == Some(&address), "foreign fee address")?;
        let entry: UtxoEntry = e.utxo_entry.into();
        require(
            entry.covenant_id.is_none(),
            "protocol covenant cannot fund fees",
        )?;
        if !entry.is_coinbase
            || entry.block_daa_score + TESTNET_PARAMS.blockrate.coinbase_maturity
                <= num(&req["server"]["virtualDaaScore"])?
        {
            candidates.push((e.outpoint.into(), entry));
        }
    }
    candidates.sort_by_key(|(_, e)| std::cmp::Reverse(e.amount));
    require(!candidates.is_empty(), "no funding")?;
    let (point, entry) = candidates[0].clone();
    let subnet: [u8; 20] = hex::decode(req["lane"].as_str().ok_or("lane")?)?
        .try_into()
        .map_err(|_| "lane length")?;
    let network = SubnetworkId::from_bytes(subnet);
    let mut meta = json!({"network":"testnet-10","address":address.to_string(),"kind":req["kind"]});
    let mut extra = vec![];
    let tx = match req["kind"].as_str().ok_or("kind")? {
        "replay" => ordinary(
            point,
            entry.clone(),
            key,
            &address,
            network,
            hex::decode(req["payload"].as_str().ok_or("replay payload")?)?,
            vec![],
        )?,
        "activity" => ordinary(
            point,
            entry.clone(),
            key,
            &address,
            network,
            b"KPI-NATIVE-SEED".to_vec(),
            vec![],
        )?,
        "fund-user" => {
            let pk: [u8; 32] = hex::decode(req["recipient"].as_str().ok_or("recipient")?)?
                .try_into()
                .map_err(|_| "pubkey")?;
            let spk = StandardSpk::PubKey(&pk).to_script_bytes();
            ordinary(
                point,
                entry.clone(),
                key,
                &address,
                network,
                vec![],
                vec![TransactionOutput::new(
                    num(&req["amount"])?,
                    ScriptPublicKey::new(0, spk.as_slice().to_vec().into()),
                )],
            )?
        }
        "deposit" | "bad-deposit" | "double-deposit" => {
            let covenant: [u8; 32] = hash(&req["covenantId"])?.into();
            let pk: [u8; 32] = hex::decode(req["owner"].as_str().ok_or("owner")?)?
                .try_into()
                .map_err(|_| "owner")?;
            let mut payload = actions::deposit_payload(&pk, 0);
            if req["kind"] == "double-deposit" {
                let (idx, _, entries) =
                    actions::sorted_user_config_positions(actions::user_resource_id(&pk));
                let lock =
                    runtime::lock::LockEnum::Schnorr(runtime::lock_variants::SchnorrLockView {
                        pubkey: &pk,
                    });
                let action = actions::encode_deposit_action(idx, 0, &lock);
                payload = [
                    actions::encode_access_metadata(&entries),
                    actions::encode_signers_section(&[]),
                    actions::encode_actions_section(&[action.clone(), action]),
                ]
                .concat();
            }
            let spk = if req["kind"] == "bad-deposit" {
                kaspa_txscript::pay_to_address_script(&address)
            } else {
                kaspa_txscript::standard::pay_to_script_hash_script(&build_delegate_entry_script(
                    &covenant,
                ))
            };
            ordinary(
                point,
                entry.clone(),
                key,
                &address,
                network,
                payload,
                vec![TransactionOutput::new(num(&req["amount"])?, spk)],
            )?
        }
        "withdraw" => {
            let pk: [u8; 32] = hex::decode(req["owner"].as_str().ok_or("owner")?)?
                .try_into()
                .map_err(|_| "owner")?;
            let recipient: [u8; 32] = hex::decode(req["recipient"].as_str().ok_or("recipient")?)?
                .try_into()
                .map_err(|_| "recipient")?;
            let prev_rpc: RpcTransaction =
                serde_json::from_value(req["previousTransaction"].clone())?;
            let prev: Transaction = prev_rpc.try_into()?;
            let required = TransactionOutpoint::new(prev.id(), num(&req["previousIndex"])? as u32);
            let (point, entry) = candidates
                .iter()
                .find(|(p, _)| *p == required)
                .cloned()
                .ok_or("witness funding output not unspent")?;
            let payload = witness_payload(
                &pk,
                num(&req["amount"])?,
                &recipient,
                &prev,
                req["badWitness"] == true,
            );
            ordinary(point, entry, key, &address, network, payload, vec![])?
        }
        "bootstrap" => {
            let program = fs::read(&a[5])?;
            let redeem = initial(&subnet, &hash(&req["tip"])?, &program);
            let (template, covenant) = covenant_bootstrap_transaction(
                &redeem,
                100_000_000,
                point,
                entry.clone(),
                key,
                &TESTNET_PARAMS,
            );
            let mut fee = 100_000;
            let tx = loop {
                let mut t = template.clone();
                t.outputs.push(TransactionOutput::new(
                    entry
                        .amount
                        .checked_sub(100_000_000 + fee)
                        .ok_or("bootstrap funding")?,
                    kaspa_txscript::pay_to_address_script(&address),
                ));
                t = sign(
                    MutableTransaction::with_entries(t, vec![entry.clone()]),
                    key,
                )
                .tx;
                let required = min_fee(&TESTNET_PARAMS, &t) * 2;
                if required > fee {
                    fee = required;
                    continue;
                }
                commit_storage_mass(&TESTNET_PARAMS, &t, &[entry.clone()]);
                t.finalize();
                break t;
            };
            meta["covenantId"] = json!(covenant.to_string());
            meta["covenantAddress"] = json!(kaspa_txscript::extract_script_pub_key_address(
                &tx.outputs[0].script_public_key,
                Prefix::Testnet
            )?
            .to_string());
            meta["depositAddress"] = json!(kaspa_txscript::extract_script_pub_key_address(
                &kaspa_txscript::standard::pay_to_script_hash_script(&build_delegate_entry_script(
                    &covenant.into()
                )),
                Prefix::Testnet
            )?
            .to_string());
            tx
        }
        "settlement" => {
            let input: Input = serde_json::from_value(req["input"].clone())?;
            require(input.lane.lane == subnet, "lane mismatch")?;
            let out = app::execute(&input);
            let program = fs::read(&a[5])?;
            let receipt: Receipt =
                bincode::deserialize(&fs::read(req["receiptPath"].as_str().ok_or("receipt")?)?)?;
            let end = hash(&req["end"])?;
            let cov: RpcUtxosByAddressesEntry =
                serde_json::from_value(req["covenantUtxo"].clone())?;
            require(
                cov.utxo_entry.covenant_id == Some(Hash::from_bytes(input.lane.covenant)),
                "wrong covenant",
            )?;
            let cov_entry: UtxoEntry = cov.utxo_entry.into();
            let cov_point: TransactionOutpoint = cov.outpoint.into();
            let s = settlement(
                &input,
                &out,
                &program,
                &receipt,
                end,
                cov_point,
                cov_entry.amount,
            )?;
            require(
                cov_entry.script_public_key
                    == kaspa_txscript::standard::pay_to_script_hash_script(&s.prev_redeem),
                "prior state/covenant mismatch",
            )?;
            // Omission receipts are valid computations against a fabricated commitment.
            // Derive their budget locally; the real TN10 accessor supplies the authentic end.
            let budget = s.covenant_compute_budget(
                Hash::from_bytes(input.lane.covenant),
                &Anchor(end, Hash::from_bytes(out.lane.seq)),
            );
            meta["state"] = serde_json::to_value(&out.state)?;
            meta["output"] = serde_json::to_value(&out)?;
            meta["permissionHash"] = json!(hex::encode(out.permission_hash));
            meta["computeBudget"] = json!(u16::from(budget));
            extra.push((cov_point, cov_entry.clone()));
            settlement_transaction(SettlementTx {
                settlement_tx: s.transaction,
                covenant_entry: cov_entry,
                covenant_compute_budget: budget,
                fee_candidates: candidates.clone(),
                keypair: key,
                address: &address,
                fee_policy: FeePolicy::TargetFeerate(200.0),
                params: &TESTNET_PARAMS,
            })?
        }
        "payout" => payout(&req, &candidates, key, &address, &mut extra)?,
        _ => return Err("unknown builder kind".into()),
    };
    let total = tx
        .inputs
        .iter()
        .try_fold(0u64, |n, i| {
            let entry = candidates
                .iter()
                .chain(extra.iter())
                .find(|(p, _)| *p == i.previous_outpoint)
                .ok_or("unknown transaction input")?;
            n.checked_add(entry.1.amount).ok_or("input overflow")
        })
        .map_err(|s: &str| s.to_string())?;
    let sum = tx
        .outputs
        .iter()
        .try_fold(0u64, |n, o| n.checked_add(o.value))
        .ok_or("output sum overflow")?;
    let fee = total.checked_sub(sum).ok_or("value creation")?;
    require(fee <= 200_000_000, "unexpected fee >2 test-KAS")?;
    meta["feeSompi"] = json!(fee);
    meta["transactionId"] = json!(tx.id().to_string());
    meta["transaction"] = serde_json::to_value(RpcTransaction::from(&tx))?;
    meta["outputAddresses"] = json!(tx
        .outputs
        .iter()
        .map(|o| kaspa_txscript::extract_script_pub_key_address(
            &o.script_public_key,
            Prefix::Testnet
        )
        .map(|a| a.to_string()))
        .collect::<std::result::Result<Vec<_>, _>>()?);
    save(&a[4], &meta)
}
fn payout(
    req: &Value,
    candidates: &[(TransactionOutpoint, UtxoEntry)],
    key: secp256k1::Keypair,
    address: &Address,
    extra: &mut Vec<(TransactionOutpoint, UtxoEntry)>,
) -> Result<Transaction> {
    use kaspa_consensus_core::{
        hashing::sighash::SigHashReusedValuesUnsync, mass::units::ComputeBudget,
        subnets::SUBNETWORK_ID_NATIVE,
    };
    use kaspa_txscript::{
        caches::Cache, covenants::CovenantsContext, engine_context::EngineContext,
        script_builder::ScriptBuilder, standard::pay_to_script_hash_script, EngineFlags,
        TxScriptEngine,
    };
    let permission: RpcUtxosByAddressesEntry =
        serde_json::from_value(req["permissionUtxo"].clone())?;
    let delegate: RpcUtxosByAddressesEntry = serde_json::from_value(req["delegateUtxo"].clone())?;
    let cov = hash(&req["covenantId"])?;
    require(
        permission.utxo_entry.covenant_id == Some(cov),
        "permission wrong covenant",
    )?;
    require(
        delegate.utxo_entry.covenant_id.is_none(),
        "delegate must be unbound",
    )?;
    let pe: UtxoEntry = permission.utxo_entry.into();
    let de: UtxoEntry = delegate.utxo_entry.into();
    let pp: TransactionOutpoint = permission.outpoint.into();
    let dp: TransactionOutpoint = delegate.outpoint.into();
    let pk: [u8; 32] = hex::decode(req["recipient"].as_str().ok_or("recipient")?)?
        .try_into()
        .map_err(|_| "recipient")?;
    let amount = num(&req["amount"])?;
    require(amount > 0 && amount <= de.amount, "payout exceeds delegate")?;
    let dest = StandardSpk::PubKey(&pk);
    let leaf = PermissionTreeAccumulator::hash_leaf(dest, amount);
    let empty = PermissionTreeAccumulator::hash_empty();
    let root = PermissionTreeAccumulator::hash_branch(&leaf, &empty);
    let redeem = build_permission_redeem_script(&root, 1, 1);
    require(
        pe.script_public_key == pay_to_script_hash_script(&redeem),
        "claim amount/recipient mismatch",
    )?;
    let delegate_redeem = build_delegate_entry_script(&cov.into());
    let delegate_spk = pay_to_script_hash_script(&delegate_redeem);
    require(
        de.script_public_key == delegate_spk,
        "foreign delegate input",
    )?;
    let mut b = ScriptBuilder::new();
    for _ in 0..2 {
        b.add_data(&empty)?.add_i64(0)?;
    }
    b.add_data(dest.to_script_bytes().as_slice())?
        .add_data(&amount.to_le_bytes())?
        .add_i64(i64::try_from(amount)?)?
        .add_data(&redeem)?;
    let perm_sig = b.drain();
    let delegate_sig = ScriptBuilder::new().add_data(&delegate_redeem)?.drain();
    let (fp, fe) = candidates[0].clone();
    let outputs = vec![
        TransactionOutput::new(
            amount.checked_add(pe.amount).ok_or("rent overflow")?,
            ScriptPublicKey::new(0, dest.to_script_bytes().as_slice().to_vec().into()),
        ),
        TransactionOutput::new(de.amount - amount, delegate_spk),
    ];
    require(de.amount > amount, "this trial retains nonzero backing")?;
    let mut fee = 100_000u64;
    let tx = loop {
        let mut outs = outputs.clone();
        outs.push(TransactionOutput::new(
            fe.amount.checked_sub(fee).ok_or("fee funds")?,
            kaspa_txscript::pay_to_address_script(address),
        ));
        // Balanced negative attacks use the same valid permission witness; freed reserve/payout
        // goes into sponsor change so a script rejection, rather than imbalance, is exercised.
        let attack = req["attack"].as_str().unwrap_or("");
        if attack == "underpay" {
            outs[0].value -= 1;
            outs[2].value += 1;
        }
        if attack == "reserve" {
            outs[1].value -= 1;
            outs[2].value += 1;
        }
        if attack == "recipient" {
            outs[0].script_public_key = kaspa_txscript::pay_to_address_script(address);
        }
        let mut t = Transaction::new(
            1,
            vec![
                TransactionInput::new(pp, perm_sig.clone(), 0, 1),
                TransactionInput::new(dp, delegate_sig.clone(), 0, 1),
                TransactionInput::new(fp, vec![], 0, 1),
            ],
            outs,
            0,
            SUBNETWORK_ID_NATIVE,
            0,
            vec![],
        );
        let entries = vec![pe.clone(), de.clone(), fe.clone()];
        // Measure both bridge inputs on the valid shape, then retain those budgets on negatives.
        let mut honest = t.clone();
        if attack == "underpay" {
            honest.outputs[0].value += 1;
            honest.outputs[2].value -= 1;
        }
        if attack == "reserve" {
            honest.outputs[1].value += 1;
            honest.outputs[2].value -= 1;
        }
        if attack == "recipient" {
            honest.outputs[0].script_public_key =
                ScriptPublicKey::new(0, dest.to_script_bytes().as_slice().to_vec().into());
        }
        let pop = PopulatedTransaction::new(&honest, entries.clone());
        let ctx = CovenantsContext::from_tx(&pop)?;
        let cache = Cache::new(1000);
        let reused = SigHashReusedValuesUnsync::new();
        let accessor = Anchor(Hash::from_bytes([0; 32]), Hash::from_bytes([0; 32]));
        for i in 0..2 {
            let ec = EngineContext::new(&cache)
                .with_reused(&reused)
                .with_seq_commit_accessor(&accessor)
                .with_covenants_ctx(&ctx);
            let mut vm = TxScriptEngine::from_transaction_input(
                &pop,
                &honest.inputs[i],
                i,
                &entries[i],
                ec,
                EngineFlags::default(),
            );
            vm.execute()?;
            let budget = ComputeBudget::checked_covering_script_units(vm.used_script_units())
                .ok_or("bridge budget")?;
            t.inputs[i].compute_commit = budget.into();
        }
        t = sign(MutableTransaction::with_entries(t, entries.clone()), key).tx;
        t.inputs[0].signature_script = perm_sig.clone();
        t.inputs[1].signature_script = delegate_sig.clone();
        let required = min_fee(&TESTNET_PARAMS, &t) * 2;
        if required > fee {
            fee = required;
            continue;
        }
        commit_storage_mass(&TESTNET_PARAMS, &t, &entries);
        t.finalize();
        break t;
    };
    extra.extend([(pp, pe), (dp, de)]);
    Ok(tx)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn tx(
        payload: Vec<u8>,
        outputs: Vec<TransactionOutput>,
        prev: Option<&Transaction>,
    ) -> Transaction {
        let point = prev
            .map(|p| TransactionOutpoint::new(p.id(), 0))
            .unwrap_or(TransactionOutpoint::new(Hash::from_bytes([7; 32]), 0));
        Transaction::new(
            1,
            vec![TransactionInput::new(point, vec![], 0, 1)],
            outputs,
            0,
            SubnetworkId::from_bytes([4; 20]),
            0,
            payload,
        )
    }
    fn as_lane(t: &Transaction) -> lane::Tx {
        lane::Tx {
            payload: t.payload.clone(),
            rest: transaction_v1_rest_preimage(t),
            merge_idx: 1,
        }
    }
    pub fn vectors() -> (Transaction, Transaction, [u8; 32], [u8; 32]) {
        let pk = runtime::genesis::GENESIS_SCHNORR_BYTES;
        let covenant = [9; 32];
        let deposit = tx(
            actions::deposit_payload(&pk, 0),
            vec![TransactionOutput::new(
                1_000_000_000,
                kaspa_txscript::standard::pay_to_script_hash_script(&build_delegate_entry_script(
                    &covenant,
                )),
            )],
            None,
        );
        let prev = tx(
            vec![],
            vec![TransactionOutput::new(
                200_000_000,
                ScriptPublicKey::new(
                    0,
                    StandardSpk::PubKey(&pk)
                        .to_script_bytes()
                        .as_slice()
                        .to_vec()
                        .into(),
                ),
            )],
            None,
        );
        (deposit, prev, pk, covenant)
    }
    #[test]
    fn public_cycle_and_application_rejections() {
        let (deposit, prev, pk, cov) = vectors();
        let empty = State::default();
        let d = as_lane(&deposit);
        let (credited, exits, dh) = app::apply_transaction(&empty, &cov, &d).unwrap();
        assert_eq!(empty.spendable(), 0);
        assert_eq!(credited.spendable(), 1_000_000_000);
        assert!(exits.is_empty());
        assert_eq!(
            dh,
            vprogs_zk_backend_risc0_api::delegate_entry_spk_hash(&cov)
        );
        assert!(app::apply_transaction(&credited, &cov, &d)
            .unwrap_err()
            .contains("already credited"));
        let mut bad = deposit.clone();
        bad.outputs[0].script_public_key = ScriptPublicKey::new(0, vec![0x51].into());
        assert!(app::apply_transaction(&empty, &cov, &as_lane(&bad)).is_err());
        let mut wrong_user = deposit.clone();
        let payload =
            vprogs_zk_abi::transaction_processor::Payload::decode(&wrong_user.payload).unwrap();
        let ix = runtime::ix::decode_ix(payload.ix_data, payload.access_metadata.len()).unwrap();
        let offset = match &ix.actions[0].body {
            runtime::ix::ActionBody::Deposit {
                initial_lock: runtime::lock::LockEnum::Schnorr(lock),
                ..
            } => lock.pubkey.as_ptr() as usize - wrong_user.payload.as_ptr() as usize,
            _ => unreachable!(),
        };
        wrong_user.payload[offset..offset + 32].copy_from_slice(&[0x55; 32]);
        assert!(app::apply_transaction(&empty, &cov, &as_lane(&wrong_user)).is_err());
        let mut foreign = deposit.clone();
        foreign.outputs[0].covenant = Some(CovenantBinding::new(0, Hash::from_bytes([8; 32])));
        assert!(app::apply_transaction(&empty, &cov, &as_lane(&foreign)).is_err());
        let withdraw = |amount, recipient, bad| {
            as_lane(&tx(
                witness_payload(&pk, amount, recipient, &prev, bad),
                vec![TransactionOutput::new(
                    190_000_000,
                    ScriptPublicKey::new(0, vec![0x51].into()),
                )],
                Some(&prev),
            ))
        };
        assert!(
            app::apply_transaction(&credited, &cov, &withdraw(1_000_000_001, &pk, false))
                .unwrap_err()
                .contains("insufficient balance")
        );
        assert!(
            app::apply_transaction(&credited, &cov, &withdraw(400_000_000, &pk, true)).is_err()
        );
        let w = withdraw(400_000_000, &pk, false);
        let (next, exits, dh) = app::apply_transaction(&credited, &cov, &w).unwrap();
        assert_eq!(next.spendable(), 600_000_000);
        assert_eq!(exits.len(), 1);
        assert_eq!(exits[0].amount, 400_000_000);
        assert_eq!(exits[0].recipient, pk);
        assert_eq!(dh, [0; 32]);
        assert!(app::apply_transaction(&next, &cov, &w)
            .unwrap_err()
            .contains("already applied"));
        // Replacing the recipient changes the accepted L1 transaction identity. Native signature
        // validation must reject retaining the original owner input signature on that body.
        let altered = withdraw(400_000_000, &[0x88; 32], false);
        assert_ne!(app::lane_id(&w), app::lane_id(&altered));
        // Exact integer arithmetic and overflow: no wraparound credit.
        let mut huge = deposit.clone();
        huge.outputs[0].value = u64::MAX;
        assert!(app::apply_transaction(&credited, &cov, &as_lane(&huge))
            .unwrap_err()
            .contains("overflow"));
        let (idx, _, entries) =
            actions::sorted_user_config_positions(actions::user_resource_id(&pk));
        let lock = runtime::lock::LockEnum::Schnorr(runtime::lock_variants::SchnorrLockView {
            pubkey: &pk,
        });
        let a = actions::encode_deposit_action(idx, 0, &lock);
        let mut double = deposit.clone();
        double.payload = [
            actions::encode_access_metadata(&entries),
            actions::encode_signers_section(&[]),
            actions::encode_actions_section(&[a.clone(), a]),
        ]
        .concat();
        assert!(app::apply_transaction(&empty, &cov, &as_lane(&double))
            .unwrap_err()
            .contains("output already consumed"));
        assert!(app::apply_transaction(&empty, &[8; 32], &d).is_err());
        let encoded = serde_json::to_value(&next).unwrap();
        let decoded: State = serde_json::from_value(encoded).unwrap();
        assert_eq!(next, decoded);
    }
}

#[cfg(test)]
mod bridge_tests {
    use super::*;
    use kaspa_consensus_core::hashing::sighash::SigHashReusedValuesUnsync;
    use kaspa_txscript::{
        caches::Cache, covenants::CovenantsContext, engine_context::EngineContext,
        standard::pay_to_script_hash_script, EngineFlags, TxScriptEngine,
    };
    fn rpc_entry(point: TransactionOutpoint, entry: UtxoEntry) -> Value {
        serde_json::to_value(RpcUtxosByAddressesEntry {
            address: None,
            outpoint: point.into(),
            utxo_entry: entry.into(),
        })
        .unwrap()
    }
    #[test]
    fn permission_payout_and_balanced_mutations() {
        let secret = secp256k1::SecretKey::from_slice(&[3u8; 32]).unwrap();
        let key = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &secret);
        let address = Address::new(
            Prefix::Testnet,
            Version::PubKey,
            &key.x_only_public_key().0.serialize(),
        );
        let recipient = [0x55; 32];
        let cov = Hash::from_bytes([9; 32]);
        let amount = 400_000_000;
        let leaf = PermissionTreeAccumulator::hash_leaf(StandardSpk::PubKey(&recipient), amount);
        let root =
            PermissionTreeAccumulator::hash_branch(&leaf, &PermissionTreeAccumulator::hash_empty());
        let permission = UtxoEntry::new(
            app::PERMISSION_RENT,
            pay_to_script_hash_script(&build_permission_redeem_script(&root, 1, 1)),
            0,
            false,
            Some(cov),
        );
        let delegate = UtxoEntry::new(
            1_000_000_000,
            pay_to_script_hash_script(&build_delegate_entry_script(&cov.into())),
            0,
            false,
            None,
        );
        let fee = UtxoEntry::new(
            200_000_000,
            kaspa_txscript::pay_to_address_script(&address),
            0,
            false,
            None,
        );
        let pp = TransactionOutpoint::new(Hash::from_bytes([1; 32]), 0);
        let dp = TransactionOutpoint::new(Hash::from_bytes([2; 32]), 0);
        let fp = TransactionOutpoint::new(Hash::from_bytes([3; 32]), 0);
        let entries = vec![permission.clone(), delegate.clone(), fee.clone()];
        for attack in ["", "underpay", "reserve", "recipient"] {
            let req = json!({"permissionUtxo":rpc_entry(pp,permission.clone()),"delegateUtxo":rpc_entry(dp,delegate.clone()),"covenantId":cov.to_string(),"recipient":hex::encode(recipient),"amount":amount,"attack":attack});
            let t = payout(&req, &[(fp, fee.clone())], key, &address, &mut vec![]).unwrap();
            let pop = PopulatedTransaction::new(&t, entries.clone());
            let ctx = CovenantsContext::from_tx(&pop).unwrap();
            let cache = Cache::new(100);
            let reused = SigHashReusedValuesUnsync::new();
            let anchor = Anchor(Hash::from_bytes([0; 32]), Hash::from_bytes([0; 32]));
            let ec = EngineContext::new(&cache)
                .with_reused(&reused)
                .with_seq_commit_accessor(&anchor)
                .with_covenants_ctx(&ctx);
            let mut vm = TxScriptEngine::from_transaction_input(
                &pop,
                &t.inputs[0],
                0,
                &entries[0],
                ec,
                EngineFlags::default(),
            );
            let result = vm.execute();
            assert_eq!(result.is_ok(), attack.is_empty(), "{attack}: {result:?}");
            eprintln!("permission attack={attack:?} result={result:?}");
            if attack.is_empty() {
                assert_eq!(t.outputs[0].value, 450_000_000);
                assert_eq!(t.outputs[1].value, 600_000_000);
            }
        }
    }
    #[test]
    fn native_owner_signature_binds_payload_recipient() {
        let secret = secp256k1::SecretKey::from_slice(&[3u8; 32]).unwrap();
        let key = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &secret);
        let pk = key.x_only_public_key().0.serialize();
        let address = Address::new(Prefix::Testnet, Version::PubKey, &pk);
        let entry = UtxoEntry::new(
            200_000_000,
            kaspa_txscript::pay_to_address_script(&address),
            0,
            false,
            None,
        );
        let p = TransactionOutpoint::new(Hash::from_bytes([1; 32]), 0);
        let payload = actions::withdraw_presig(&pk, 100_000_000, &StandardSpk::PubKey(&pk));
        let valid = ordinary(
            p,
            entry.clone(),
            key,
            &address,
            SubnetworkId::from_bytes([4; 20]),
            payload,
            vec![],
        )
        .unwrap();
        for altered in [false, true] {
            let mut t = valid.clone();
            if altered {
                *t.payload.last_mut().unwrap() ^= 1;
                t.finalize();
            }
            let pop = PopulatedTransaction::new(&t, vec![entry.clone()]);
            let ctx = CovenantsContext::from_tx(&pop).unwrap();
            let cache = Cache::new(100);
            let reused = SigHashReusedValuesUnsync::new();
            let anchor = Anchor(Hash::from_bytes([0; 32]), Hash::from_bytes([0; 32]));
            let ec = EngineContext::new(&cache)
                .with_reused(&reused)
                .with_seq_commit_accessor(&anchor)
                .with_covenants_ctx(&ctx);
            let mut vm = TxScriptEngine::from_transaction_input(
                &pop,
                &t.inputs[0],
                0,
                &entry,
                ec,
                EngineFlags::default(),
            );
            let result = vm.execute();
            assert_eq!(result.is_ok(), !altered, "{result:?}");
            eprintln!("native payload altered={altered}: {result:?}");
        }
    }
}
