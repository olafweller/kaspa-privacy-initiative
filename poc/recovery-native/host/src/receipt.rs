//! Fixed new-program/journal receipt verification. No proof-production entrypoint.
use super::*;
use kpi_private_note_proof as trusted;
use risc0_zkvm::Receipt;
pub fn target(stage: &str) -> Result<Vec<u8>> {
    let t: serde_json::Value = serde_json::from_str(include_str!("../../evidence/targets.json"))?;
    if t["expectedProgramImage"] != include_str!("../../evidence/expected-image.txt").trim() {
        return Err("compiled program pin".into());
    }
    let b = t["batches"].get(stage).ok_or("unknown fixed stage")?;
    let j = hex::decode(b["expectedJournalHex"].as_str().ok_or("journal pin")?)?;
    if j.len() != 352 || hex::encode(hash(&j)) != b["expectedJournalSha256"].as_str().unwrap() {
        return Err("compiled journal hash".into());
    }
    Ok(j)
}
pub fn verify(stage: &str, r: &Receipt) -> Result<()> {
    trusted::verify_claim(
        r,
        trusted::digest(include_str!("../../evidence/expected-image.txt").trim())?,
        &target(stage)?,
        trusted::digest(trusted::JOIN)?,
    )
}
pub fn verify_file(stage: &str, path: &Path) -> Result<()> {
    let r = trusted::read_receipt(path)?;
    verify(stage, &r)?;
    println!(
        "{}",
        json!({"stage":stage,"receiptSha256":hex::encode(hash(&fs::read(path)?)),"newProgramVerified":true,"exactJournalVerified":true,"developmentMode":false,"noUnresolvedAssumptions":true})
    );
    Ok(())
}
struct Anchor(kaspa_hashes::Hash, kaspa_hashes::Hash);
impl kaspa_txscript::seq_commit_accessor::SeqCommitAccessor for Anchor {
    fn is_chain_ancestor_from_pov(&self, b: kaspa_hashes::Hash) -> Option<bool> {
        Some(b == self.0)
    }
    fn seq_commitment_within_depth(&self, b: kaspa_hashes::Hash) -> Option<kaspa_hashes::Hash> {
        (b == self.0).then_some(self.1)
    }
}
/// Requires a GENUINE NEW receipt. No accepted=true flag or fake seal is supplied.
/// The only chain accessor is an explicit local fixture; this is not TN10 acceptance.
pub fn issuance(stage: &str, path: &Path, out: &Path) -> Result<()> {
    use kaspa_consensus_core::{hashing::sighash::SigHashReusedValuesUnsync, tx::*};
    use kaspa_hashes::Hash;
    use kaspa_txscript::{
        caches::Cache, covenants::CovenantsContext, engine_context::EngineContext,
        standard::pay_to_script_hash_script, EngineFlags, TxScriptEngine,
    };
    use risc0_zkvm::sha::Digestible;
    use vprogs_zk_backend_risc0_covenant::{
        script::{CommonPins, RedeemPins, SuccinctPins},
        Settlement, SettlementInput, SettlementWitness, SuccinctWitness,
    };
    let index = match stage {
        "bob-exit" => 2,
        "alice-exit" => 4,
        _ => return Err("exit stage required".into()),
    };
    let r = trusted::read_receipt(path)?;
    verify(stage, &r)?;
    let p = fixtures::scenarios()?;
    let (_, input, output) = &p.cases[index];
    let j = target(stage)?;
    assert_eq!(output.journal, j, "independent regenerated journal");
    let f: [[u8; 32]; 11] = std::array::from_fn(|n| j[n * 32..n * 32 + 32].try_into().unwrap());
    let image: H = hex::decode(include_str!("../../evidence/expected-image.txt").trim())?
        .try_into()
        .unwrap();
    let lane = Hash::from_bytes(f[10]);
    let cov = Hash::from_bytes(f[5]);
    let endpoint = Hash::from_bytes([0x79; 32]);
    let pins = RedeemPins::SuccinctJoin(SuccinctPins {
        common: CommonPins {
            program_id: &image,
            tx_image_id: &f[6],
            batch_image_id: &f[7],
            lane_key: &lane,
            permission_output_value: app::PERMISSION_RENT,
        },
    });
    let s = r.inner.succinct()?;
    let seal: Vec<_> = s.seal.iter().flat_map(|x| x.to_le_bytes()).collect();
    let inclusion: Vec<_> = s
        .control_inclusion_proof
        .digests
        .iter()
        .flat_map(|x| <[u8; 32]>::from(*x))
        .collect();
    let claim: H = s.claim.digest().into();
    let template = &p.templates[index];
    let mut built = Settlement::build(&SettlementInput {
        covenant_id: cov,
        pins,
        prev_state: &f[0],
        prev_lane_tip: &Hash::from_bytes(f[1]),
        new_state: &f[2],
        new_lane_tip: &Hash::from_bytes(f[3]),
        block_prove_to: endpoint,
        prev_outpoint: template.inputs[0].previous_outpoint,
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
    built.transaction.inputs.push(template.inputs[1].clone());
    built.transaction.subnetwork_id = template.subnetwork_id.clone();
    built.transaction.payload = template.payload.clone();
    built.transaction.finalize();
    assert_eq!(
        built.transaction.id(),
        template.id(),
        "receipt issuance / frozen reconciliation ID"
    );
    let entries = vec![
        UtxoEntry::new(
            app::STATE_RENT,
            pay_to_script_hash_script(&built.prev_redeem),
            0,
            false,
            Some(cov),
        ),
        UtxoEntry::new(
            app::PERMISSION_RENT + 100_000,
            ScriptPublicKey::new(0, vec![0x51].into()),
            0,
            false,
            None,
        ),
    ];
    let pop = PopulatedTransaction::new(&built.transaction, entries.clone());
    let ctx = CovenantsContext::from_tx(&pop)?;
    let cache = Cache::new(10);
    let reused = SigHashReusedValuesUnsync::new();
    let anchor = Anchor(endpoint, Hash::from_bytes(f[4]));
    let mut units = vec![];
    for (i, e) in entries.iter().enumerate() {
        let ec = EngineContext::new(&cache)
            .with_reused(&reused)
            .with_covenants_ctx(&ctx)
            .with_seq_commit_accessor(&anchor);
        let mut vm = TxScriptEngine::from_transaction_input(
            &pop,
            &built.transaction.inputs[i],
            i,
            e,
            ec,
            EngineFlags::default(),
        );
        vm.execute()?;
        units.push(vm.used_script_units().0);
    }
    assert_eq!(input.state.root(), f[0]);
    let registered = app::apply(
        &output.state,
        &native::lane_tx(&built.transaction),
        &verifier(),
    )?
    .0;
    let eid = *registered
        .permissions
        .keys()
        .next()
        .ok_or("permission registration")?;
    let (payout, entries) = native::payout(&registered, eid, "")?;
    let payout_units = native::scripts(&payout, &entries)??;
    let reconciled = app::apply(&registered, &native::lane_tx(&payout), &verifier())?.0;
    assert_eq!(
        payout.id(),
        vprogs_l1_utils::tx_id_v1(
            &p.cases[index + 1].1.lane.blocks[0].txs[1].payload,
            &p.cases[index + 1].1.lane.blocks[0].txs[1].rest
        )
        .into()
    );
    assert_eq!(
        reconciled.ledger.state_hash(),
        p.cases[index + 1].2.state.ledger.state_hash()
    );
    fs::create_dir(out)?;
    report(
        out,
        "native-issuance.json",
        &json!({"scope":"GENUINE_NEW_RECEIPT_NATIVE_ISSUANCE_AND_PAYOUT_LOCAL_CONTEXT_NOT_TN10","stage":stage,"receiptSha256":trusted::sha(&fs::read(path)?),"newReceiptVerified":true,"frozenPermissionIdMatched":true,"issuanceScriptUnits":units,"payoutScriptUnits":payout_units,"accounting":reconciled.accounting()?,"nativeBroadcast":false}),
    )
}
