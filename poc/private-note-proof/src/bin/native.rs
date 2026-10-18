//! Local actual Kaspa script execution. Synthetic UTXO/anchor, never a broadcast.
use kaspa_consensus_core::{hashing::sighash::SigHashReusedValuesUnsync, tx::*};
use kaspa_hashes::Hash;
use kaspa_txscript::{
    caches::Cache, covenants::CovenantsContext, engine_context::EngineContext,
    script_builder::ScriptBuilder, standard::pay_to_script_hash_script, EngineFlags,
    TxScriptEngine,
};
use kaspa_txscript_errors::TxScriptError;
use kpi_private_note_proof::*;
use risc0_zkvm::{
    sha::{Digestible, Sha256},
    Receipt,
};
use serde_json::json;
use std::{fs, path::Path};
use vprogs_zk_backend_risc0_covenant::{
    script::{succinct_consts, CommonPins, RedeemPins, SuccinctPins},
    Settlement, SettlementInput, SettlementWitness, SuccinctWitness,
};

const OLD_IMAGE: &str = "397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716";
const OLD_RECEIPT_SHA: &str = "9e68cda38325f673d00734433a1bd7b127fab20ac88f16aad948f2bec1492186";
const PRINCIPAL: u64 = 1_000_000_000;
struct Anchor {
    block: Hash,
    seq: Hash,
}
impl kaspa_txscript::seq_commit_accessor::SeqCommitAccessor for Anchor {
    fn is_chain_ancestor_from_pov(&self, b: Hash) -> Option<bool> {
        Some(b == self.block)
    }
    fn seq_commitment_within_depth(&self, b: Hash) -> Option<Hash> {
        (b == self.block).then_some(self.seq)
    }
}
fn parts(r: &Receipt) -> Result<(Vec<u8>, Vec<u8>, [u8; 32])> {
    let s = r.inner.succinct()?;
    Ok((
        s.seal.iter().flat_map(|w| w.to_le_bytes()).collect(),
        s.control_inclusion_proof
            .digests
            .iter()
            .flat_map(|d| <[u8; 32]>::from(*d))
            .collect(),
        s.claim.digest().into(),
    ))
}
/// Old real 167-byte receipt only qualifies join/control/precompile compatibility.
/// It is NOT a private-note receipt or a positive 352-byte covenant settlement.
fn raw_precompile(r: &Receipt, label: &str) -> Result<std::result::Result<(), TxScriptError>> {
    use kaspa_txscript::{
        opcodes::codes::{OpTrue, OpVerify, OpZkPrecompile},
        zk_precompiles::tags::ZkTag,
    };
    let (mut seal, mut inclusion, claim) = parts(r)?;
    let mut image: [u8; 32] = digest(OLD_IMAGE)?.into();
    let mut journal: [u8; 32] = (*risc0_zkvm::sha::Impl::hash_bytes(&r.journal.bytes)).into();
    let mut control: [u8; 32] = digest(JOIN)?.into();
    let mut index = r.inner.succinct()?.control_inclusion_proof.index;
    match label {
        "wrong-control" => control = succinct_consts::SUCCINCT_CONTROL_ID,
        "wrong-image" => image[0] ^= 1,
        "wrong-journal" => journal[0] ^= 1,
        "bad-seal" => seal[0] ^= 1,
        "bad-inclusion" => inclusion[0] ^= 1,
        "truncated-inclusion" => {
            inclusion.pop();
        }
        "wrong-control-index" => index ^= 1,
        "valid" => {}
        _ => return Err("unknown raw precompile case".into()),
    }
    let mut b = ScriptBuilder::new();
    for d in [
        &claim[..],
        &index.to_le_bytes(),
        &inclusion,
        &seal,
        &journal,
        &image,
        &control,
        &[1],
        &[ZkTag::R0Succinct as u8],
    ] {
        b.add_data(d)?;
    }
    b.add_ops(&[OpZkPrecompile, OpVerify, OpTrue])?;
    let script = b.drain();
    let cache = Cache::new(1);
    let reused = SigHashReusedValuesUnsync::new();
    let mut vm = TxScriptEngine::<PopulatedTransaction<'_>, _>::from_script(
        &script,
        &reused,
        &cache,
        EngineFlags::default(),
    );
    Ok(vm.execute())
}
fn fixture(r: &Receipt, label: &str) -> Result<std::result::Result<(), TxScriptError>> {
    let mut fields: [[u8; 32]; 11] =
        std::array::from_fn(|i| EXPECTED[i * 32..i * 32 + 32].try_into().unwrap());
    let mut image: [u8; 32] = digest(IMAGE)?.into();
    let (mut seal, mut inclusion, claim) = parts(r)?;
    let mut seq = fields[4];
    let mut endpoint = Hash::from_bytes([3; 32]);
    match label {
        "wrong-prior-root" => fields[0][0] ^= 1,
        "wrong-prior-tip" => fields[1][0] ^= 1,
        "wrong-new-root" => fields[2][0] ^= 1,
        "wrong-new-tip" => fields[3][0] ^= 1,
        "wrong-anchor" => seq[0] ^= 1,
        "wrong-endpoint" => endpoint = Hash::from_bytes([9; 32]),
        "wrong-covenant" => fields[5][0] ^= 1,
        "wrong-tx-relation" => fields[6][0] ^= 1,
        "wrong-batch-relation" => fields[7][0] ^= 1,
        "wrong-lane" => fields[10][0] ^= 1,
        "wrong-image" => image[0] ^= 1,
        "bad-seal" => seal[0] ^= 1,
        "bad-inclusion" => inclusion[0] ^= 1,
        "valid" | "wrong-control" | "divert-reserve" => {}
        _ => return Err("unknown native fixture case".into()),
    }
    let lane = Hash::from_bytes(fields[10]);
    let cov = Hash::from_bytes(fields[5]);
    let pins = SuccinctPins {
        common: CommonPins {
            program_id: &image,
            tx_image_id: &fields[6],
            batch_image_id: &fields[7],
            lane_key: &lane,
            permission_output_value: 50_000_000,
        },
    };
    let mut s = Settlement::build(&SettlementInput {
        covenant_id: cov,
        pins: if label == "wrong-control" {
            RedeemPins::Succinct(pins)
        } else {
            RedeemPins::SuccinctJoin(pins)
        },
        prev_state: &fields[0],
        prev_lane_tip: &Hash::from_bytes(fields[1]),
        new_state: &fields[2],
        new_lane_tip: &Hash::from_bytes(fields[3]),
        block_prove_to: endpoint,
        prev_outpoint: TransactionOutpoint::new(Hash::from_bytes([4; 32]), 0),
        value: PRINCIPAL,
        witness: SettlementWitness::Succinct(SuccinctWitness {
            seal: &seal,
            claim: &claim,
            control_index: r.inner.succinct()?.control_inclusion_proof.index,
            control_digests: &inclusion,
            deposit_spk_hash: &fields[9],
        }),
        permission_spk_hash: &fields[8],
    });
    assert_eq!(
        s.transaction.outputs.len(),
        1,
        "no exit or deposit permission in target"
    );
    assert_eq!(s.transaction.outputs[0].value, PRINCIPAL);
    if label == "divert-reserve" {
        s.transaction.outputs[0].value -= 1;
        s.transaction.finalize();
    }
    let utxo = UtxoEntry::new(
        PRINCIPAL,
        pay_to_script_hash_script(&s.prev_redeem),
        0,
        false,
        Some(cov),
    );
    let pop = PopulatedTransaction::new(&s.transaction, vec![utxo.clone()]);
    let ctx = CovenantsContext::from_tx(&pop)?;
    let cache = Cache::new(1);
    let reused = SigHashReusedValuesUnsync::new();
    let anchor = Anchor {
        block: Hash::from_bytes([3; 32]),
        seq: Hash::from_bytes(seq),
    };
    let ec = EngineContext::new(&cache)
        .with_reused(&reused)
        .with_seq_commit_accessor(&anchor)
        .with_covenants_ctx(&ctx);
    let mut vm = TxScriptEngine::from_transaction_input(
        &pop,
        &s.transaction.inputs[0],
        0,
        &utxo,
        ec,
        EngineFlags::default(),
    );
    Ok(vm.execute())
}
fn rejected(result: std::result::Result<(), TxScriptError>) -> Result<String> {
    let e = result
        .err()
        .ok_or("negative native control unexpectedly accepted")?;
    // Whitelist verifier/semantic failures. Resource errors, build failures and
    // panics must never become successful rejection evidence.
    match &e {
        TxScriptError::ZkIntegrity(_)
        | TxScriptError::VerifyError
        | TxScriptError::EvalFalse
        | TxScriptError::BlockNotSelected(_) => Ok(e.to_string()),
        _ => Err(format!("unexpected native failure, not attack evidence: {e:?}").into()),
    }
}
fn main() -> Result<()> {
    assert!(std::env::var_os("RISC0_DEV_MODE").is_none());
    let a: Vec<_> = std::env::args().collect();
    if a.len() != 4 {
        return Err("archived-join RECEIPT NEW_OUTPUT | verify-receipt RECEIPT NEW_OUTPUT".into());
    }
    let path = Path::new(&a[2]);
    let r = read_receipt(path)?;
    let mut results = serde_json::Map::new();
    let mut cpu_controls = serde_json::Value::Null;
    let scope = match a[1].as_str() {
        "archived-join" => {
            assert_eq!(
                sha(&fs::read(path)?),
                OLD_RECEIPT_SHA,
                "reviewed genuine PR43 receipt"
            );
            verify_claim(&r, digest(OLD_IMAGE)?, &r.journal.bytes, digest(JOIN)?)?;
            cpu_controls = crypto_negatives(&r, digest(OLD_IMAGE)?)?;
            raw_precompile(&r, "valid")??;
            for label in [
                "wrong-control",
                "wrong-image",
                "wrong-journal",
                "bad-seal",
                "bad-inclusion",
                "truncated-inclusion",
                "wrong-control-index",
            ] {
                results.insert(
                    label.into(),
                    json!({"rejected":true,"error":rejected(raw_precompile(&r,label)?)?}),
                );
            }
            "ARCHIVED_PR43_JOIN_PRECOMPILE_COMPATIBILITY_ONLY"
        }
        "verify-receipt" => {
            verify(&r)?;
            fixture(&r, "valid")??;
            for label in [
                "wrong-prior-root",
                "wrong-prior-tip",
                "wrong-new-root",
                "wrong-new-tip",
                "wrong-anchor",
                "wrong-endpoint",
                "wrong-covenant",
                "wrong-tx-relation",
                "wrong-batch-relation",
                "wrong-lane",
                "wrong-image",
                "wrong-control",
                "bad-seal",
                "bad-inclusion",
                "divert-reserve",
            ] {
                results.insert(
                    label.into(),
                    json!({"rejected":true,"error":rejected(fixture(&r,label)?)?}),
                );
            }
            "LOCAL_PRIVATE_NOTE_NATIVE_FIXTURE_NOT_CANONICAL_TN10_OR_PAYOUT"
        }
        _ => return Err("unsupported native command".into()),
    };
    let out = Path::new(&a[3]);
    fs::create_dir(out)?;
    save(
        out,
        "native-verification.json",
        &serde_json::to_vec_pretty(&json!({"scope":scope,"positiveNativeScriptAccepted":true,
        "receiptSha256":sha(&fs::read(path)?),"expectedControlId":JOIN,"developmentMode":false,
        "fixturePrincipalSompi":if a[1]=="verify-receipt" {Some(PRINCIPAL)} else {None},"principalExcludesRentAndSponsorFees":true,
        "actualTN10Broadcast":false,"newPrivateReceiptVerified":a[1]=="verify-receipt","negativeControls":results,"archivedCpuNegativeControls":cpu_controls}))?,
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn resource_failure_is_not_rejection_evidence() {
        assert!(rejected(Err(TxScriptError::ExceededCommittedScriptUnits {
            used: 2,
            limit: 1
        }))
        .is_err());
        assert!(rejected(Err(TxScriptError::EmptyStack)).is_err());
        assert!(rejected(Err(TxScriptError::ZkIntegrity("invalid seal".into()))).is_ok());
        assert!(rejected(Ok(())).is_err());
    }
    #[test]
    fn explicit_join_keeps_the_resolve_identity_separate() {
        let live = risc0_circuit_recursion::control_id::POSEIDON2_CONTROL_IDS
            .iter()
            .find(|(n, _)| *n == "resolve.zkr")
            .unwrap()
            .1;
        assert_eq!(succinct_consts::SUCCINCT_CONTROL_ID, <[u8; 32]>::from(live));
        assert_eq!(
            succinct_consts::JOIN_CONTROL_ID,
            <[u8; 32]>::from(digest(JOIN).unwrap())
        );
        assert_ne!(
            succinct_consts::SUCCINCT_CONTROL_ID,
            succinct_consts::JOIN_CONTROL_ID
        );
    }
}
