//! Build and execute the *fully signed* layout offline. All UTXO values/scripts
//! are supplied from read-only chain snapshots; live rechecking remains required.
use super::*;
use kaspa_consensus_core::{
    hashing::sighash::SigHashReusedValuesUnsync,
    mass::{transaction_estimated_serialized_size, ComputeBudget, Mass, MassCalculator},
    sign::sign_input,
};
use kaspa_rpc_core::{RpcTransaction, RpcUtxosByAddressesEntry};
use kaspa_txscript::{
    caches::Cache, covenants::CovenantsContext, engine_context::EngineContext,
    script_builder::ScriptBuilder, standard::pay_to_script_hash_script, EngineFlags,
    TxScriptEngine,
};
use risc0_zkvm::sha::Digestible;
use std::str::FromStr;
use vprogs_l1_wallet::build::{commit_storage_mass, min_fee};
use vprogs_zk_backend_risc0_covenant::{
    script::*, Settlement, SettlementInput, SettlementWitness, SuccinctWitness,
};

pub struct Anchor(pub Hash, pub Hash);
impl kaspa_txscript::seq_commit_accessor::SeqCommitAccessor for Anchor {
    fn is_chain_ancestor_from_pov(&self, b: Hash) -> Option<bool> {
        Some(b == self.0)
    }
    fn seq_commitment_within_depth(&self, b: Hash) -> Option<Hash> {
        (b == self.0).then_some(self.1)
    }
}
pub fn execute(tx: &Transaction, entries: &[UtxoEntry], anchor: &Anchor) -> Result<Vec<u64>> {
    require(tx.inputs.len() == entries.len(), "populated input count")?;
    let pop = PopulatedTransaction::new(tx, entries.to_vec());
    let ctx = CovenantsContext::from_tx(&pop)?;
    let cache = Cache::new(100);
    let reused = SigHashReusedValuesUnsync::new();
    let mut units = vec![];
    for (i, e) in entries.iter().enumerate() {
        let ec = EngineContext::new(&cache)
            .with_reused(&reused)
            .with_covenants_ctx(&ctx)
            .with_seq_commit_accessor(anchor);
        let mut vm = TxScriptEngine::from_transaction_input(
            &pop,
            &tx.inputs[i],
            i,
            e,
            ec,
            EngineFlags::default(),
        );
        vm.execute()?;
        units.push(vm.used_script_units().0);
    }
    Ok(units)
}
pub fn check(tx: &Transaction, entries: &[UtxoEntry], anchor: &Anchor, rate: u64) -> Result<Value> {
    require(
        tx.version == 1 && tx.subnetwork_id.as_bytes() == &chain::LANE,
        "v1 reviewed private lane",
    )?;
    require(
        rate >= 100,
        "fee quote below documented default relay floor",
    )?;
    let units = execute(tx, entries, anchor)?;
    for (index, (u, i)) in units.iter().zip(&tx.inputs).enumerate() {
        let required = ComputeBudget::checked_covering_script_units(
            kaspa_consensus_core::mass::ScriptUnits(*u),
        )
        .ok_or("script budget overflow")?;
        require(
            i.compute_commit
                .compute_budget()
                .is_some_and(|b| b >= u16::from(required)),
            &format!("insufficient declared compute budget at input {index}: actual units {u}, required budget {}, declared {:?}",u16::from(required),i.compute_commit.compute_budget()),
        )?;
    }
    let calc = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS);
    let non = calc.calc_non_contextual_masses(tx);
    let ctx = calc
        .calc_contextual_masses(&PopulatedTransaction::new(tx, entries.to_vec()))
        .ok_or("storage mass overflow")?;
    let limits = TESTNET_PARAMS.block_mass_limits;
    require(
        non.compute_mass <= limits.compute
            && non.transient_mass <= limits.transient
            && ctx.storage_mass <= limits.storage,
        "full signed transaction exceeds native block mass limits",
    )?;
    require(
        tx.storage_mass() == ctx.storage_mass,
        "wrong committed storage mass",
    )?;
    let priority = Mass::new(non, ctx).normalized_max(&limits.cofactors());
    let ins = entries
        .iter()
        .try_fold(0u64, |a, e| a.checked_add(e.amount))
        .ok_or("input overflow")?;
    let outs = tx
        .outputs
        .iter()
        .try_fold(0u64, |a, e| a.checked_add(e.value))
        .ok_or("output overflow")?;
    require(tx.outputs.iter().all(|o| o.value > 0), "zero output")?;
    let fee = ins.checked_sub(outs).ok_or("negative fee")?;
    let required = rate
        .checked_mul(priority)
        .ok_or("fee overflow")?
        .max(min_fee(&TESTNET_PARAMS, tx));
    require(
        fee >= required,
        "fee below supplied quote / signed layout floor",
    )?;
    Ok(
        json!({"scope":"OFFLINE_SIGNED_NATIVE_CHECK_NOT_MEMPOOL_OR_SELECTED_CHAIN_ACCEPTANCE","transactionId":tx.id().to_string(),
        "estimatedSerializedBytes":transaction_estimated_serialized_size(tx),"rpcJsonBytes":serde_json::to_vec(&RpcTransaction::from(tx))?.len(),
        "computeMass":non.compute_mass,"transientMass":non.transient_mass,"storageMass":ctx.storage_mass,"priorityMass":priority,
        "inputScriptUnits":units,"inputComputeBudgets":tx.inputs.iter().map(|i|i.compute_commit.compute_budget()).collect::<Vec<_>>(),
        "feeSompi":fee,"requiredFeeSompi":required,"feeRateSompiPerGram":rate,"allInputScriptsExecuted":true,
        "liveUtxoAndAnchorRecheckRequired":true,"networkAcceptance":false}),
    )
}
fn utxo(v: &Value) -> Result<(TransactionOutpoint, UtxoEntry)> {
    let e: RpcUtxosByAddressesEntry = serde_json::from_value(v.clone())?;
    Ok((e.outpoint.into(), e.utxo_entry.into()))
}
fn push(data: &[u8]) -> Result<Vec<u8>> {
    Ok(ScriptBuilder::new().add_data(data)?.drain())
}
pub(crate) fn sign_fee_input(
    mut tx: Transaction,
    entries: &[UtxoEntry],
    key: secp256k1::Keypair,
) -> Transaction {
    // The broad native `sign()` helper resets EVERY input budget to the P2PK
    // default (10), including the 2500-unit proof input. Use the existing
    // single-input signer after budgets are fixed; it changes no commitments.
    let index = tx.inputs.len() - 1;
    let signature = sign_input(
        &PopulatedTransaction::new(&tx, entries.to_vec()),
        index,
        &key.secret_bytes(),
        kaspa_consensus_core::hashing::sighash_type::SIG_HASH_ALL,
    );
    tx.inputs[index].signature_script = signature;
    tx
}
pub fn build(trial_path: &Path, request_path: &Path, key_file: &Path, out: &Path) -> Result<()> {
    let trial = read(trial_path)?;
    let r = read(request_path)?;
    require(
        trial["schema"] == "KPI_TN10_PRIVATE_TRIAL_V1" && trial["lane"] == hex::encode(chain::LANE),
        "wrong trial",
    )?;
    require(
        r["server"]["networkId"] == "testnet-10" && r["server"]["isSynced"] == true,
        "wrong network / unsynced snapshot",
    )?;
    require(r["trial"] == trial["trial"], "cross-trial request")?;
    let rate = n(&r["feeRateSompiPerGram"])?;
    let key = secp256k1::SecretKey::from_str(std::str::from_utf8(&secret(key_file)?)?.trim())?;
    let kp = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &key);
    let pk = kp.x_only_public_key().0.serialize();
    require(
        hex::encode(pk) == trial["sponsorNative"]["pubkey"],
        "not this trial's sponsor",
    )?;
    let sponsor_spk = kaspa_txscript::pay_to_address_script(&kaspa_addresses::Address::new(
        kaspa_addresses::Prefix::Testnet,
        kaspa_addresses::Version::PubKey,
        &pk,
    ));
    let (fp, fe) = utxo(&r["sponsorUtxo"])?;
    require(
        fe.covenant_id.is_none() && fe.script_public_key == sponsor_spk,
        "foreign / bound fee input",
    )?;
    require(
        !fe.is_coinbase
            || fe
                .block_daa_score
                .checked_add(TESTNET_PARAMS.blockrate.coinbase_maturity)
                .is_some_and(|v| {
                    r["server"]["virtualDaaScore"]
                        .as_u64()
                        .is_some_and(|s| s >= v)
                }),
        "immature sponsor",
    )?;
    let mut inputs = vec![];
    let mut entries = vec![];
    let mut outputs = vec![];
    let mut scripts = vec![];
    let mut payload = vec![];
    let mut extra = json!({});
    let kind = r["kind"].as_str().ok_or("kind")?;
    let mut anchor = Anchor(Hash::from_bytes([0; 32]), Hash::from_bytes([0; 32]));
    match kind {
        "bootstrap" => {
            let seed = read(r["seedPath"].as_str().ok_or("seedPath")?)?;
            require(
                trusted::sha(&fs::read(r["seedPath"].as_str().unwrap())?) == r["seedSha256"],
                "trusted seed hash",
            )?;
            require(
                seed["scope"] == "VERIFIED_NATIVE_LANE_SEED" && seed["lane"] == trial["lane"],
                "native seed required",
            )?;
            let tip = h(&seed["tip"])?;
            let touch = n(&seed["lastTouch"])?;
            let (o, cov) = bootstrap::output(tip, touch, fp)?;
            outputs.push(o);
            let s = State::genesis(cov, verifier().id(), tip, touch);
            extra = json!({"covenantId":hex::encode(cov),"seed":seed,"genesisRoot":hex::encode(s.root()),"initializerRedeem":hex::encode(bootstrap::redeem(tip,touch)?),"stateRedeem":hex::encode(state_script(&s))});
        }
        "initialize" => {
            let b = read(r["bootstrapPath"].as_str().ok_or("bootstrapPath")?)?;
            require(
                b["trial"] == trial["trial"] && b["kind"] == "bootstrap",
                "bootstrap trial",
            )?;
            let (p, e) = utxo(&r["stateUtxo"])?;
            let cov = h(&b["details"]["covenantId"])?;
            let tip = h(&b["details"]["seed"]["tip"])?;
            let touch = n(&b["details"]["seed"]["lastTouch"])?;
            require(
                p.transaction_id.to_string() == b["transactionId"]
                    && p.index == 0
                    && e.amount == app::STATE_RENT
                    && e.covenant_id == Some(Hash::from_bytes(cov))
                    && e.script_public_key
                        == pay_to_script_hash_script(&bootstrap::redeem(tip, touch)?),
                "wrong bootstrap lineage",
            )?;
            scripts.push(push(&bootstrap::redeem(tip, touch)?)?);
            inputs.push(TransactionInput::new_with_compute_budget(
                p,
                scripts[0].clone(),
                0,
                1,
            ));
            entries.push(e);
            let s = State::genesis(cov, verifier().id(), tip, touch);
            outputs.push(TransactionOutput::with_covenant(
                app::STATE_RENT,
                pay_to_script_hash_script(&state_script(&s)),
                Some(CovenantBinding::new(0, Hash::from_bytes(cov))),
            ));
            extra = json!({"covenantId":hex::encode(cov),"stateHex":hex::encode(bincode::serialize(&s)?),"stateRoot":hex::encode(s.root()),"seed":b["details"]["seed"]});
        }
        "deposit" => {
            let cov = h(&r["covenantId"])?;
            let cp_path = Path::new(
                r["checkpointPath"]
                    .as_str()
                    .ok_or("accepted initialization checkpointPath")?,
            );
            let cp = read(cp_path)?;
            let genesis = state(
                cp_path
                    .parent()
                    .ok_or("checkpoint parent")?
                    .join("state.bin"),
            )?;
            require(
                cp["trial"] == trial["trial"]
                    && cp["completed"] == "initialize"
                    && cp["status"] == "CAPTURED_NATIVE_ACCEPTANCE_OFFLINE_RECHECK_REQUIRED"
                    && genesis.covenant == cov
                    && hex::encode(genesis.root()) == cp["stateRoot"],
                "deposit requires this trial's accepted initialized covenant",
            )?;
            let (sp, se) = utxo(&r["stateUtxo"])?;
            require(
                cp["stateOutpoint"]
                    == json!({"transactionId":sp.transaction_id.to_string(),"index":sp.index})
                    && se.amount == app::STATE_RENT
                    && se.covenant_id == Some(Hash::from_bytes(cov))
                    && se.script_public_key == pay_to_script_hash_script(&state_script(&genesis)),
                "initialized state no longer present / wrong deposit covenant",
            )?;
            outputs.push(TransactionOutput::new(
                1_000_000_000,
                ScriptPublicKey::new(0, app::delegate(&cov).into()),
            ));
            payload = chain::deposit_payload(h(&trial["alice"]["owner"])?, 0);
        }
        "activate" => {
            payload = [
                b"KPI-TN10-private-trial-activation-v1\0".as_slice(),
                &h(&trial["trial"])?,
            ]
            .concat();
        }
        "publish" => {
            payload = hex::decode(
                r["operationPayloadHex"]
                    .as_str()
                    .ok_or("public operation envelope")?,
            )?;
            require(
                payload.starts_with(chain::OP_TAG),
                "wallet operation envelope",
            )?;
        }
        "settlement" => {
            let target_path = Path::new(r["targetPath"].as_str().ok_or("targetPath")?);
            let t = batch::target(
                target_path,
                r["targetSha256"].as_str().ok_or("targetSha256")?,
            )?;
            require(t["trial"] == trial["trial"], "cross trial target")?;
            let receipt =
                trusted::read_receipt(Path::new(r["receiptPath"].as_str().ok_or("receiptPath")?))?;
            batch::verify_target(&t, &receipt)?;
            let j = hex::decode(t["journalHex"].as_str().unwrap())?;
            let f: [[u8; 32]; 11] =
                std::array::from_fn(|i| j[i * 32..i * 32 + 32].try_into().unwrap());
            let (p, e) = utxo(&r["stateUtxo"])?;
            let before = state(
                target_path
                    .parent()
                    .ok_or("target parent")?
                    .join("prior-state.bin"),
            )?;
            require(
                before.root() == f[0] && before.lane_tip == f[1] && before.covenant == f[5],
                "prior state journal",
            )?;
            require(
                e.amount == app::STATE_RENT
                    && e.covenant_id == Some(Hash::from_bytes(f[5]))
                    && e.script_public_key == pay_to_script_hash_script(&state_script(&before)),
                "actual state UTXO mismatch",
            )?;
            require(
                t["stateOutpoint"]
                    == json!({"transactionId":p.transaction_id.to_string(),"index":p.index}),
                "state lineage differs from frozen target",
            )?;
            anchor = Anchor(Hash::from_bytes(h(&t["endBlock"])?), Hash::from_bytes(f[4]));
            // Refresh eligibility after proving without rewriting the proven
            // endpoint. A newer anchor cannot stand in for this receipt's seq.
            let ab = &r["anchorBlock"]["block"];
            require(
                ab["header"]["hash"] == t["endBlock"]
                    && ab["verboseData"]["isChainBlock"] == true
                    && h(&ab["header"]["acceptedIdMerkleRoot"])? == f[4],
                "receipt endpoint no longer selected / wrong seq",
            )?;
            let high = n(&r["selectedParentBlock"]["block"]["header"]["blueScore"])?;
            let low = n(&ab["header"]["blueScore"])?;
            require(
                high >= low && high - low < TESTNET_PARAMS.finality_depth(),
                "receipt endpoint outside native seqcommit window",
            )?;
            let s = receipt.inner.succinct()?;
            let seal: Vec<_> = s.seal.iter().flat_map(|x| x.to_le_bytes()).collect();
            let inclusion: Vec<_> = s
                .control_inclusion_proof
                .digests
                .iter()
                .flat_map(|x| <[u8; 32]>::from(*x))
                .collect();
            let image = h(&json!(IMAGE))?;
            let key = Hash::from_bytes(f[10]);
            let pins = RedeemPins::SuccinctJoin(SuccinctPins {
                common: CommonPins {
                    program_id: &image,
                    tx_image_id: &f[6],
                    batch_image_id: &f[7],
                    lane_key: &key,
                    permission_output_value: app::PERMISSION_RENT,
                },
            });
            let claim = s.claim.digest().into();
            let mut built = Settlement::build(&SettlementInput {
                covenant_id: Hash::from_bytes(f[5]),
                pins,
                prev_state: &f[0],
                prev_lane_tip: &Hash::from_bytes(f[1]),
                new_state: &f[2],
                new_lane_tip: &Hash::from_bytes(f[3]),
                block_prove_to: anchor.0,
                prev_outpoint: p,
                value: app::STATE_RENT,
                witness: SettlementWitness::Succinct(SuccinctWitness {
                    seal: &seal,
                    claim: &claim,
                    control_index: s.control_inclusion_proof.index,
                    control_digests: &inclusion,
                    deposit_spk_hash: &f[9],
                }),
                permission_spk_hash: &f[8],
            });
            native::restrict_settlement(
                &mut built,
                &f[0],
                &Hash::from_bytes(f[1]),
                &f[2],
                &Hash::from_bytes(f[3]),
                &pins,
            )?;
            scripts.push(built.transaction.inputs[0].signature_script.clone());
            inputs = built.transaction.inputs;
            outputs = built.transaction.outputs;
            entries.push(e);
            if f[8] != [0; 32] {
                let after = state(target_path.parent().unwrap().join("state.bin"))?;
                require(after.root() == f[2], "permission post-state root")?;
                let pending: Vec<_> = after.ledger.exits.iter().filter(|(_, e)| !e.paid).collect();
                require(pending.len() == 1, "one open exit")?;
                payload = app::permission_payload(*pending[0].0);
            }
            extra = json!({"targetSha256":r["targetSha256"],"anchorBlock":t["endBlock"],"expectedSeq":hex::encode(f[4]),"nativeReceiptVerified":true});
        }
        "payout" => {
            let mut s = state(r["publicStatePath"].as_str().ok_or("publicStatePath")?)?;
            let eid = h(&r["exitId"])?;
            // Exit's post-state precedes its permission issuance. Derive the
            // public build-only intermediate state from that exact native tx.
            // The D batch still starts from the unmodified C checkpoint and
            // proves the complete lane including issuance and payout.
            if !s.permissions.contains_key(&eid) {
                let grant = read(
                    r["permissionTransactionPath"]
                        .as_str()
                        .ok_or("permissionTransactionPath")?,
                )?;
                let rpc: RpcTransaction = serde_json::from_value(grant["transaction"].clone())?;
                let tx: Transaction = rpc.try_into()?;
                require(
                    grant["kind"] == "settlement" && grant["trial"] == trial["trial"],
                    "permission issuance trial",
                )?;
                s = app::apply(&s, &native::lane_tx(&tx), &verifier())?.0;
            }
            let permission = s.permissions.get(&eid).ok_or("unregistered permission")?;
            let reserve = s
                .exit_reserves
                .get(&eid)
                .ok_or("missing selected reserve")?;
            let exit = &s.ledger.exits[&eid];
            require(
                !exit.paid && hex::encode(s.exit_keys[&eid]) == trial["bobNative"]["pubkey"],
                "unpaid Bob-authorized exit required",
            )?;
            for (value, expected, amount, spk) in [
                (
                    &r["permissionUtxo"],
                    &permission.outpoint,
                    permission.rent,
                    pay_to_script_hash_script(&app::restricted::permission_redeem(&s, eid)),
                ),
                (
                    &r["reserveUtxo"],
                    reserve,
                    s.reserves[reserve],
                    ScriptPublicKey::new(0, app::delegate(&s.covenant).into()),
                ),
            ] {
                let (p, e) = utxo(value)?;
                require(
                    p == native::op(expected) && e.amount == amount && e.script_public_key == spk,
                    "permission/reserve lineage",
                )?;
                require(
                    e.covenant_id
                        == if inputs.is_empty() {
                            Some(Hash::from_bytes(s.covenant))
                        } else {
                            None
                        },
                    "payout input covenant",
                )?;
                entries.push(e);
                inputs.push(TransactionInput::new_with_compute_budget(p, vec![], 0, 1));
            }
            let empty = vprogs_zk_backend_risc0_api::PermissionTreeAccumulator::hash_empty();
            let destination = vprogs_zk_abi::withdrawal::StandardSpk::PubKey(&s.exit_keys[&eid]);
            let mut b = ScriptBuilder::new();
            for _ in 0..2 {
                b.add_data(&empty)?.add_i64(0)?;
            }
            b.add_data(destination.to_script_bytes().as_slice())?
                .add_data(&exit.amount.to_le_bytes())?
                .add_i64(i64::try_from(exit.amount)?)?
                .add_data(&app::restricted::permission_redeem(&s, eid))?;
            scripts.push(b.drain());
            scripts.push(push(
                &vprogs_zk_backend_risc0_api::build_delegate_entry_script(&s.covenant),
            )?);
            for (i, sig) in scripts.iter().enumerate() {
                inputs[i].signature_script = sig.clone();
            }
            outputs.push(TransactionOutput::new(
                exit.amount
                    .checked_add(permission.rent)
                    .ok_or("rent overflow")?,
                ScriptPublicKey::new(0, destination.to_script_bytes().as_slice().to_vec().into()),
            ));
            outputs.push(TransactionOutput::new(
                s.reserves[reserve]
                    .checked_sub(exit.amount)
                    .ok_or("reserve deficit")?,
                ScriptPublicKey::new(0, app::delegate(&s.covenant).into()),
            ));
            payload = app::payout_payload(eid);
        }
        _ => return Err("unsupported preparation kind".into()),
    }
    require(
        !inputs.iter().any(|i| i.previous_outpoint == fp),
        "duplicate sponsor",
    )?;
    inputs.push(TransactionInput::new_with_compute_budget(fp, vec![], 0, 1));
    entries.push(fe);
    let input_total = entries
        .iter()
        .try_fold(0u64, |a, e| a.checked_add(e.amount))
        .ok_or("input overflow")?;
    let fixed = outputs
        .iter()
        .try_fold(0u64, |a, o| a.checked_add(o.value))
        .ok_or("output overflow")?;
    let mut fee = 100_000u64;
    let (tx, qualification) = loop {
        let mut outs = outputs.clone();
        let change = input_total
            .checked_sub(fixed)
            .and_then(|v| v.checked_sub(fee))
            .ok_or("insufficient sponsor funds")?;
        require(change > 0, "positive sponsor change required")?;
        outs.push(TransactionOutput::new(change, sponsor_spk.clone()));
        let mut tx = Transaction::new(
            1,
            inputs.clone(),
            outs,
            0,
            chain::LANE.into(),
            0,
            payload.clone(),
        );
        // First measure protocol scripts. Sponsor is signed only after all
        // compute commitments are final; restore protocol witnesses afterwards.
        for i in 0..scripts.len() {
            tx.inputs[i].compute_commit = ComputeBudget(u16::MAX).into();
        }
        let mut probe = tx.clone();
        probe.inputs.last_mut().unwrap().compute_commit = ComputeBudget(10).into();
        probe = sign_fee_input(probe, &entries, kp);
        for (i, sig) in scripts.iter().enumerate() {
            probe.inputs[i].signature_script = sig.clone();
        }
        let measured = execute(&probe, &entries, &anchor)?;
        for (i, u) in measured.iter().enumerate() {
            tx.inputs[i].compute_commit = ComputeBudget::checked_covering_script_units(
                kaspa_consensus_core::mass::ScriptUnits(*u),
            )
            .ok_or("compute limit")?
            .into();
        }
        tx = sign_fee_input(tx, &entries, kp);
        for (i, sig) in scripts.iter().enumerate() {
            tx.inputs[i].signature_script = sig.clone();
        }
        commit_storage_mass(&TESTNET_PARAMS, &tx, &entries);
        tx.finalize();
        let calc = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS);
        let m = calc
            .calc_contextual_masses(&PopulatedTransaction::new(&tx, entries.clone()))
            .ok_or("mass")?;
        let priority = Mass::new(calc.calc_non_contextual_masses(&tx), m)
            .normalized_max(&TESTNET_PARAMS.block_mass_limits.cofactors());
        let need = rate
            .checked_mul(priority)
            .ok_or("fee quote overflow")?
            .max(min_fee(&TESTNET_PARAMS, &tx));
        if need > fee {
            fee = need;
            continue;
        }
        let q = check(&tx, &entries, &anchor, rate)?;
        break (tx, q);
    };
    mkdir(out)?;
    report(
        &out.join("transaction.json"),
        &json!({"trial":trial["trial"],"kind":kind,"transactionId":tx.id().to_string(),"transaction":RpcTransaction::from(&tx),"details":extra,"qualification":qualification,"broadcast":false}),
    )?;
    report(&out.join("request.json"), &r)?;
    if kind == "initialize" {
        save(
            &out.join("state.bin"),
            &hex::decode(extra["stateHex"].as_str().unwrap())?,
        )?;
    }
    if kind == "payout" {
        let mut s = state(r["publicStatePath"].as_str().unwrap())?;
        if s.permissions.is_empty() {
            let grant = read(
                r["permissionTransactionPath"]
                    .as_str()
                    .ok_or("permissionTransactionPath")?,
            )?;
            let rpc: RpcTransaction = serde_json::from_value(grant["transaction"].clone())?;
            let grant: Transaction = rpc.try_into()?;
            s = app::apply(&s, &native::lane_tx(&grant), &verifier())?.0;
        }
        let (after, _, _) = app::apply(&s, &native::lane_tx(&tx), &verifier())?;
        report(
            &out.join("reconciliation-preview.json"),
            &json!({"scope":"LOCAL_PREVIEW_NOT_ACCEPTED_CHAIN","accounting":after.accounting()?}),
        )?;
    }
    Ok(())
}
