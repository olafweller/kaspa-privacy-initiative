//! Reuses the existing claim/control verifier; targets are compiled expectations.
//! No proof is run during local preparation. A future producer invocation must
//! be wrapped by the qualified process-group deadline and independent B guard.
use kpi_private_note_proof as trusted;
use risc0_zkvm::{default_prover, ExecutorEnv, ProverOpts};
use serde_json::{json, Value};
use std::{fs, path::Path, time::Instant};
type Result<T> = trusted::Result<T>;
use kpi_private_native::{self as app, chain, lane, wallet::protocol::*, State};
#[path = "../native.rs"]
mod native;

struct Anchor(kaspa_hashes::Hash, kaspa_hashes::Hash);
impl kaspa_txscript::seq_commit_accessor::SeqCommitAccessor for Anchor {
    fn is_chain_ancestor_from_pov(&self, b: kaspa_hashes::Hash) -> Option<bool> {
        Some(b == self.0)
    }
    fn seq_commitment_within_depth(&self, b: kaspa_hashes::Hash) -> Option<kaspa_hashes::Hash> {
        (b == self.0).then_some(self.1)
    }
}
fn native_exit(r: &risc0_zkvm::Receipt, out: &Path) -> Result<()> {
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
    verify("exit", r)?;
    let (t, _, j) = target("exit")?;
    let f: [[u8; 32]; 11] = std::array::from_fn(|n| j[n * 32..n * 32 + 32].try_into().unwrap());
    let image: H = hex::decode(t["expectedProgramImage"].as_str().unwrap())?
        .try_into()
        .unwrap();
    let lane = Hash::from_bytes(f[10]);
    let cov = Hash::from_bytes(f[5]);
    let s = r.inner.succinct()?;
    let seal: Vec<_> = s.seal.iter().flat_map(|x| x.to_le_bytes()).collect();
    let inclusion: Vec<u8> = s
        .control_inclusion_proof
        .digests
        .iter()
        .flat_map(|x| <[u8; 32]>::from(*x))
        .collect();
    let claim: H = s.claim.digest().into();
    let endpoint = Hash::from_bytes([3; 32]);
    let pins = RedeemPins::SuccinctJoin(SuccinctPins {
        common: CommonPins {
            program_id: &image,
            tx_image_id: &f[6],
            batch_image_id: &f[7],
            lane_key: &lane,
            permission_output_value: app::PERMISSION_RENT,
        },
    });
    let mut built = Settlement::build(&SettlementInput {
        covenant_id: cov,
        pins: RedeemPins::SuccinctJoin(SuccinctPins {
            common: CommonPins {
                program_id: &image,
                tx_image_id: &f[6],
                batch_image_id: &f[7],
                lane_key: &lane,
                permission_output_value: app::PERMISSION_RENT,
            },
        }),
        prev_state: &f[0],
        prev_lane_tip: &Hash::from_bytes(f[1]),
        new_state: &f[2],
        new_lane_tip: &Hash::from_bytes(f[3]),
        block_prove_to: endpoint,
        prev_outpoint: TransactionOutpoint::new(Hash::from_bytes([0x83; 32]), 0),
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
    let expected: app::Output =
        bincode::deserialize(include_bytes!("../../../evidence/exit.expected.bin"))?;
    let eid = *expected
        .state
        .ledger
        .exits
        .keys()
        .next()
        .ok_or("exit target")?;
    let skeleton = native::issuance(&expected.state, eid);
    built.transaction.inputs.push(skeleton.inputs[1].clone());
    built.transaction.subnetwork_id = skeleton.subnetwork_id;
    built.transaction.payload = skeleton.payload.clone();
    built.transaction.finalize();
    if built.transaction.id() != skeleton.id() {
        return Err(
            "receipt-bearing permission issuance differs from predeclared reconciliation input"
                .into(),
        );
    }
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
    let v = app::AcceleratedVerifier::checked(
        include_bytes!("../../../../private-note-chain/pins/vk.bin"),
        *include_bytes!("../../../../private-note-chain/pins/vk-id.bin"),
    )?;
    let registered = app::apply(&expected.state, &native::lane_tx(&built.transaction), &v)?.0;
    let payout = native::campaign(&registered, eid)?;
    fs::create_dir(out)?;
    trusted::save(
        out,
        "native-verification.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"GENUINE_EXIT_RECEIPT_LOCAL_NATIVE_ISSUANCE_AND_PAYOUT_NOT_TN10","permissionIssuanceReceiptVerified":true,"matchesFrozenReconciliationInput":true,"permissionTransactionId":built.transaction.id().to_string(),"stateCovenantContinuationSompi":app::STATE_RENT,"permissionRentSompi":app::PERMISSION_RENT,"issuanceSponsorFeeSompi":100_000,"issuanceInputScriptUnits":units,"payout":payout,"actualTN10Broadcast":false}),
        )?,
    )?;
    Ok(())
}

/// Qualify only the additive state-script restriction using PR #48's already
/// produced genuine receipt. This does NOT prove the new lifecycle or issuance.
fn qualify_state_guard(r: &risc0_zkvm::Receipt, out: &Path) -> Result<()> {
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
    trusted::verify(r)?;
    let f: [[u8; 32]; 11] =
        std::array::from_fn(|i| r.journal.bytes[i * 32..i * 32 + 32].try_into().unwrap());
    assert_eq!(f[8], [0; 32], "archived fixture has no permission");
    let image: H = trusted::digest(trusted::IMAGE)?.into();
    let lane = Hash::from_bytes(f[10]);
    let cov = Hash::from_bytes(f[5]);
    let endpoint = Hash::from_bytes([3; 32]);
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
    let seal: Vec<_> = s.seal.iter().flat_map(|w| w.to_le_bytes()).collect();
    let inclusion: Vec<_> = s
        .control_inclusion_proof
        .digests
        .iter()
        .flat_map(|d| <[u8; 32]>::from(*d))
        .collect();
    let claim: H = s.claim.digest().into();
    let mut built = Settlement::build(&SettlementInput {
        covenant_id: cov,
        pins,
        prev_state: &f[0],
        prev_lane_tip: &Hash::from_bytes(f[1]),
        new_state: &f[2],
        new_lane_tip: &Hash::from_bytes(f[3]),
        block_prove_to: endpoint,
        prev_outpoint: TransactionOutpoint::new(Hash::from_bytes([0x83; 32]), 0),
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
    let unrestricted_next = built.next_redeem.clone();
    native::restrict_settlement(
        &mut built,
        &f[0],
        &Hash::from_bytes(f[1]),
        &f[2],
        &Hash::from_bytes(f[3]),
        &pins,
    )?;
    let mut rows = vec![];
    for label in [
        "valid-private-lane",
        "default-lane",
        "removed-continuation-guard",
    ] {
        let mut tx = built.transaction.clone();
        tx.subnetwork_id = chain::LANE.into();
        if label == "default-lane" {
            tx.subnetwork_id = kaspa_consensus_core::subnets::SUBNETWORK_ID_NATIVE;
        }
        if label == "removed-continuation-guard" {
            tx.outputs[0].script_public_key = pay_to_script_hash_script(&unrestricted_next);
        }
        tx.finalize();
        let entries = vec![UtxoEntry::new(
            app::STATE_RENT,
            pay_to_script_hash_script(&built.prev_redeem),
            0,
            false,
            Some(cov),
        )];
        let pop = PopulatedTransaction::new(&tx, entries.clone());
        let ctx = CovenantsContext::from_tx(&pop)?;
        let cache = Cache::new(10);
        let reused = SigHashReusedValuesUnsync::new();
        let anchor = Anchor(endpoint, Hash::from_bytes(f[4]));
        let ec = EngineContext::new(&cache)
            .with_reused(&reused)
            .with_covenants_ctx(&ctx)
            .with_seq_commit_accessor(&anchor);
        let mut vm = TxScriptEngine::from_transaction_input(
            &pop,
            &tx.inputs[0],
            0,
            &entries[0],
            ec,
            EngineFlags::default(),
        );
        let result = vm.execute();
        if label == "valid-private-lane" {
            result.clone()?;
        } else {
            let error = result.clone().expect_err("native restriction must reject");
            if !matches!(
                error,
                kaspa_txscript_errors::TxScriptError::VerifyError
                    | kaspa_txscript_errors::TxScriptError::EvalFalse
            ) {
                return Err(error.into());
            }
        }
        rows.push(json!({"case":label,"accepted":result.is_ok(),"error":result.err().map(|e|e.to_string()),"scriptUnits":vm.used_script_units().0}));
    }
    fs::create_dir(out)?;
    trusted::save(
        out,
        "state-guard.json",
        &serde_json::to_vec_pretty(
            &json!({"scope":"ADDITIVE_STATE_SCRIPT_QUALIFICATION_WITH_ARCHIVED_PR48_RECEIPT_NOT_NEW_LIFECYCLE_PROOF","archivedReceiptSha256":trusted::sha(&bincode::serialize(r)?),"archivedProgramImage":trusted::IMAGE,"newLifecycleReceiptProduced":false,"nativeEngineCases":rows,"guardCopiedInContinuation":built.next_redeem[99..].starts_with(&app::restricted::lane_guard())}),
        )?,
    )?;
    Ok(())
}
fn target(case: &str) -> Result<(Value, Value, Vec<u8>)> {
    let t: Value = serde_json::from_str(include_str!("../../../evidence/targets.json"))?;
    let b = t["batches"]
        .get(case)
        .ok_or("unknown fixed proof batch")?
        .clone();
    let journal = hex::decode(b["expectedJournalHex"].as_str().ok_or("journal pin")?)?;
    if journal.len() != 352
        || trusted::sha(&journal) != b["expectedJournalSha256"].as_str().unwrap()
    {
        return Err("compiled journal pin mismatch".into());
    }
    Ok((t, b, journal))
}
fn verify(case: &str, r: &risc0_zkvm::Receipt) -> Result<()> {
    let (t, _, j) = target(case)?;
    trusted::verify_claim(
        r,
        trusted::digest(t["expectedProgramImage"].as_str().unwrap())?,
        &j,
        trusted::digest(t["expectedJoinControl"].as_str().unwrap())?,
    )
}
fn package(case: &str, dir: &Path) -> Result<(Vec<u8>, Vec<u8>, u32)> {
    let (t, b, j) = target(case)?;
    let program = fs::read(dir.join("guest.program.bin"))?;
    let input = fs::read(dir.join(format!("{case}.input.bin")))?;
    if trusted::sha(&program) != t["programSha256"].as_str().unwrap()
        || risc0_zkvm::compute_image_id(&program)?.to_string()
            != t["expectedProgramImage"].as_str().unwrap()
        || trusted::sha(&input) != b["inputSha256"].as_str().unwrap()
        || fs::read(dir.join(format!("{case}.journal.bin")))? != j
    {
        return Err("fixed public package mismatch".into());
    }
    Ok((program, input, b["segmentPo2"].as_u64().unwrap() as u32))
}
fn main() -> Result<()> {
    if std::env::var_os("RISC0_DEV_MODE").is_some() {
        return Err("development mode forbidden".into());
    }
    let a: Vec<_> = std::env::args().collect();
    match a.get(1).map(String::as_str){
        Some("check-target") if a.len()==4=>{package(&a[2],Path::new(&a[3]))?;println!("fixed public target verified; no proof started");},
        Some("verify-receipt") if a.len()==5=>{
            let r=trusted::read_receipt(Path::new(&a[3]))?;verify(&a[2],&r)?;let (t,_,_)=target(&a[2])?;
            let negatives=trusted::crypto_negatives(&r,trusted::digest(t["expectedProgramImage"].as_str().unwrap())?)?;
            let out=Path::new(&a[4]);fs::create_dir(out)?;trusted::save(out,"verification.json",&serde_json::to_vec_pretty(&json!({"scope":"INDEPENDENT_FROZEN_LIFECYCLE_RECEIPT_NOT_CANONICAL_TN10","case":a[2],"receiptSha256":trusted::sha(&fs::read(&a[3])?),"programImage":t["expectedProgramImage"],"exactJournalVerified":true,"noUnresolvedAssumptions":true,"developmentMode":false,"negativeControls":negatives}))?)?;
        },
        Some("verify-native-exit") if a.len()==4=>{let r=trusted::read_receipt(Path::new(&a[2]))?;native_exit(&r,Path::new(&a[3]))?;},
        Some("qualify-state-guard") if a.len()==4=>{let r=trusted::read_receipt(Path::new(&a[2]))?;qualify_state_guard(&r,Path::new(&a[3]))?;},
        Some("prove") if a.len()==5=>{
            let (program,input,po2)=package(&a[2],Path::new(&a[3]))?;let out=Path::new(&a[4]);fs::create_dir(out)?;
            trusted::save(out,"started.json",&serde_json::to_vec_pretty(&json!({"scope":"ONE_FIXED_FUTURE_LIFECYCLE_BATCH","case":a[2],"cycleLimit":160000000,"wholeJobProcessGroupLimitSeconds":3600,"segmentPo2":po2,"automaticRetries":false,"externalProcessGroupDeadlineRequired":true}))?)?;
            let mut env=ExecutorEnv::builder();env.write_slice(&[u32::try_from(input.len())?]).write_slice(&input).segment_limit_po2(po2).session_limit(Some(160_000_000));
            let start=Instant::now();let info=default_prover().prove_with_opts(env.build()?,&program,&ProverOpts::succinct())?;
            let bytes=bincode::serialize(&info.receipt)?;trusted::save(out,"candidate-receipt.bin",&bytes)?;trusted::save(out,"stats.json",&serde_json::to_vec_pretty(&info.stats)?)?;
            verify(&a[2],&info.receipt)?;assert!(info.stats.user_cycles<=160_000_000);assert!(start.elapsed().as_secs_f64()<3600.0);
            trusted::save(out,"receipt.bin",&bytes)?;trusted::save(out,"journal.bin",&info.receipt.journal.bytes)?;
            trusted::save(out,"complete.json",&serde_json::to_vec_pretty(&json!({"seconds":start.elapsed().as_secs_f64(),"receiptSha256":trusted::sha(&bytes),"independentVerificationStillRequired":true,"actualTN10Settlement":false}))?)?;
        },
        _=>return Err("check-target CASE PUBLIC_PACKAGE | verify-receipt CASE RECEIPT NEW_OUTPUT | prove CASE PUBLIC_PACKAGE NEW_OUTPUT".into())
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn frozen_local_targets_and_fake_rejection() {
        let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("../evidence");
        for c in ["deposit", "credit-transfer", "exit", "reconcile"] {
            package(c, &dir).unwrap();
            let (t, _, j) = target(c).unwrap();
            let r = risc0_zkvm::Receipt::new(
                risc0_zkvm::InnerReceipt::Fake(risc0_zkvm::FakeReceipt::new(
                    risc0_zkvm::ReceiptClaim::ok(
                        trusted::digest(t["expectedProgramImage"].as_str().unwrap()).unwrap(),
                        j.clone(),
                    ),
                )),
                j,
            );
            assert!(verify(c, &r).is_err());
        }
        assert!(target("arbitrary-remote-input").is_err());
    }
}
