//! Native relation checks. Receipt callbacks below check exact image/journal pairs;
//! they are test doubles, not cryptographic proofs or TN10 acceptance.
use kaspa_consensus_core::{
    hashing::tx::transaction_v1_rest_preimage, subnets::SubnetworkId, tx::*,
};
use kaspa_hashes::Hash;
use kaspa_seq_commit::{
    hashing::{lane_key, mergeset_context_hash},
    types::MergesetContext,
};
use kpi_takeover_common::{self as common, app};
use vprogs_core_codec::Writer;
use vprogs_zk_abi::transaction_processor::{JournalEntries, OutputCommitment};
use vprogs_zk_backend_risc0_api::build_delegate_entry_script;

#[allow(dead_code)]
#[path = "../../../native-value/host/src/actions.rs"]
mod actions;
const LANE: [u8; 20] = [4, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
const COV: [u8; 32] = [9; 32];
const IMAGE: [u8; 32] = [8; 32];
fn transaction(payload: Vec<u8>, outputs: Vec<TransactionOutput>) -> Transaction {
    Transaction::new(
        1,
        vec![TransactionInput::new(
            TransactionOutpoint::new(Hash::from_bytes([7; 32]), 0),
            vec![],
            0,
            1,
        )],
        outputs,
        0,
        SubnetworkId::from_bytes(LANE),
        0,
        payload,
    )
}
fn deposit(amount: u64) -> common::Input {
    let pk = app::runtime::genesis::GENESIS_SCHNORR_BYTES;
    let tx = transaction(
        actions::deposit_payload(&pk, 0),
        vec![TransactionOutput::new(
            amount,
            kaspa_txscript::standard::pay_to_script_hash_script(&build_delegate_entry_script(&COV)),
        )],
    );
    input(&tx)
}
fn input(tx: &Transaction) -> common::Input {
    common::Input {
        lane: LANE,
        covenant: COV,
        context: context(202),
        state: app::State::default(),
        tx: app::lane::Tx {
            payload: tx.payload.clone(),
            rest: transaction_v1_rest_preimage(tx),
            merge_idx: 1,
        },
    }
}
fn context(score: u64) -> [u8; 32] {
    mergeset_context_hash(&MergesetContext {
        timestamp: 11,
        daa_score: 303,
        blue_score: score,
    })
    .into()
}
fn batch(input: &common::Input, journals: &[Vec<u8>], score: u64) -> Vec<u8> {
    let mut w = vec![];
    w.write(&IMAGE);
    w.write(&COV);
    let deposit = journals
        .iter()
        .find_map(
            |j| match JournalEntries::decode(j).unwrap().output_commitment {
                OutputCommitment::Success {
                    deposit_spk_hash, ..
                } if *deposit_spk_hash != [0; 32] => Some(*deposit_spk_hash),
                _ => None,
            },
        )
        .unwrap_or([0; 32]);
    w.write(&deposit);
    w.write(lane_key(&LANE).as_slice());
    w.write_blob(&common::proof(&input.state));
    w.write(&score.to_le_bytes());
    w.write(&303u64.to_le_bytes());
    w.write(&11u64.to_le_bytes());
    w.write(&[6; 32]);
    w.write(&[5; 32]);
    w.write(&1u64.to_le_bytes());
    w.write(&[0]);
    let mut list = vec![];
    for j in journals {
        list.write_blob(j)
    }
    w.write_blob(&list);
    w
}
fn verified(w: &[u8], allowed: &[Vec<u8>]) -> Vec<u8> {
    let mut v = vprogs_zk_abi::batch_processor::Verifier::new(w, |image, j| {
        assert_eq!(image, &IMAGE);
        assert!(allowed.iter().any(|a| a == j), "missing/wrong receipt");
    });
    let (tip, score) = v.verify_batch();
    let mut j = vec![];
    v.commit_batch_transition::<vprogs_zk_backend_risc0_api::Sha256>(&mut j, &tip, score);
    j
}
fn rejects(f: impl FnOnce()) {
    assert!(std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)).is_err());
}
#[test]
fn native_id_lane_preimage_and_prior_state_binding() {
    let i = deposit(1_000_000_000);
    let (next, j) = common::execute(&i);
    let entries = JournalEntries::decode(&j).unwrap();
    assert_eq!(
        <[u8; 32]>::from(*entries.input_commitment.tx_id),
        app::lane_id(&i.tx)
    );
    let wire = batch(&i, &[j.clone()], 202);
    let out = verified(&wire, &[j.clone()]);
    assert_eq!(&out[..32], &common::root(&i.state));
    assert_eq!(&out[72..104], &common::root(&next));
    let mut wrong = i.clone();
    wrong.lane[0] ^= 1;
    rejects(|| {
        common::execute(&wrong);
    });
    let mut truncated = i.clone();
    truncated.tx.rest.pop();
    rejects(|| {
        common::execute(&truncated);
    });
    let mut trailing = i.clone();
    trailing.tx.rest.push(0);
    rejects(|| {
        common::execute(&trailing);
    });
    let mut changed = i.clone();
    changed.tx.payload.push(0);
    assert_ne!(app::lane_id(&i.tx), app::lane_id(&changed.tx));
    let mut wrong = i.clone();
    wrong.state = next;
    rejects(|| {
        verified(&batch(&wrong, &[j.clone()], 202), &[j]);
    });
}
#[test]
fn deposit_noops_and_replay_preserve_accounting() {
    let i = deposit(1_000_000_000);
    let (next, j) = common::execute(&i);
    assert_eq!(next.spendable(), 1_000_000_000);
    assert!(matches!(
        JournalEntries::decode(&j).unwrap().output_commitment,
        OutputCommitment::Success { .. }
    ));
    let mut replay = i.clone();
    replay.state = next.clone();
    let (s, j) = common::execute(&replay);
    assert_eq!(s, next);
    assert!(matches!(
        JournalEntries::decode(&j).unwrap().output_commitment,
        OutputCommitment::Error(_)
    ));
    let mut wrong = i.clone();
    wrong.covenant = [10; 32];
    let (s, j) = common::execute(&wrong);
    assert_eq!(s, i.state);
    assert!(matches!(
        JournalEntries::decode(&j).unwrap().output_commitment,
        OutputCommitment::Error(_)
    ));
    let mut malformed = i.clone();
    malformed.tx.payload = vec![0xff];
    let (s, j) = common::execute(&malformed);
    assert_eq!(s, i.state);
    let out = verified(&batch(&malformed, &[j.clone()], 202), &[j]);
    assert_eq!(out[..32], out[72..104]);
    let mut overflow = deposit(u64::MAX);
    overflow.state = next.clone();
    let (s, j) = common::execute(&overflow);
    assert_eq!(s, next);
    assert!(matches!(
        JournalEntries::decode(&j).unwrap().output_commitment,
        OutputCommitment::Error(_)
    ));
}
#[test]
fn batch_checks_context_order_image_and_receipt_and_allows_gap_over_100() {
    let i = deposit(1_000_000_000);
    let (_, j) = common::execute(&i);
    let wire = batch(&i, &[j.clone()], 202);
    // Previous touch is score 1; score 202 demonstrates the old 100-score adapter
    // cap is absent in this relation. This is a synthetic local check only.
    assert_eq!(
        u64::from_le_bytes(verified(&wire, &[j.clone()])[136..144].try_into().unwrap()),
        202
    );
    rejects(|| {
        verified(&wire, &[]);
    });
    let mut corrupt = j.clone();
    *corrupt.last_mut().unwrap() ^= 1;
    rejects(|| {
        verified(&wire, &[corrupt]);
    });
    let mut wrong_image = wire.clone();
    wrong_image[0] ^= 1;
    rejects(|| {
        verified(&wrong_image, &[j.clone()]);
    });
    rejects(|| {
        verified(&batch(&i, &[j.clone()], 203), &[j.clone()]);
    });
    let mut second = i.clone();
    second.state = common::execute(&i).0;
    let (_, j2) = common::execute(&second);
    rejects(|| {
        verified(&batch(&i, &[j.clone(), j2.clone()], 202), &[j.clone(), j2]);
    });
    // Strictly increasing merge index fixes order; the replay remains a no-op.
    second.tx.merge_idx = 2;
    let (_, j2) = common::execute(&second);
    let out = verified(&batch(&i, &[j.clone(), j2.clone()], 202), &[j, j2]);
    assert_eq!(out[72..104], common::root(&second.state));
}

#[test]
fn authorized_withdrawal_emits_exact_claim_and_replay_is_noop() {
    use vprogs_zk_abi::withdrawal::StandardSpk;
    let i = deposit(1_000_000_000);
    let (credited, _) = common::execute(&i);
    let owner = app::runtime::genesis::GENESIS_SCHNORR_BYTES;
    let previous = transaction(
        vec![],
        vec![TransactionOutput::new(
            200_000_000,
            ScriptPublicKey::new(
                0,
                StandardSpk::PubKey(&owner)
                    .to_script_bytes()
                    .as_slice()
                    .to_vec()
                    .into(),
            ),
        )],
    );
    let withdrawal = |amount, bad| {
        let (idx, _, entries) =
            actions::sorted_user_config_positions(actions::user_resource_id(&owner));
        let access = actions::encode_access_metadata(&entries);
        let acts = actions::encode_actions_section(&[actions::encode_withdraw_action(
            idx,
            amount,
            &StandardSpk::PubKey(&owner),
        )]);
        let rest = transaction_v1_rest_preimage(&previous);
        let probe =
            actions::encode_signers_section(&[actions::encode_witness_signer(idx, 0, 0, 0, 0)]);
        let offset = (access.len() + probe.len() + acts.len()) as u32;
        let signers = actions::encode_signers_section(&[actions::encode_witness_signer(
            idx,
            u8::from(bad),
            offset,
            rest.len() as u32,
            offset + rest.len() as u32,
        )]);
        let payload = [
            access,
            signers,
            acts,
            rest,
            vprogs_l1_utils::payload_digest_v1(&previous.payload).to_vec(),
        ]
        .concat();
        let mut tx = transaction(
            payload,
            vec![TransactionOutput::new(
                190_000_000,
                ScriptPublicKey::new(0, vec![0x51].into()),
            )],
        );
        tx.inputs[0].previous_outpoint = TransactionOutpoint::new(previous.id(), 0);
        tx.finalize();
        let mut i = input(&tx);
        i.state = credited.clone();
        i
    };
    for bad in [
        withdrawal(1_000_000_001, false),
        withdrawal(400_000_000, true),
    ] {
        let (s, j) = common::execute(&bad);
        assert_eq!(s, credited);
        assert!(matches!(
            JournalEntries::decode(&j).unwrap().output_commitment,
            OutputCommitment::Error(_)
        ));
    }
    let mut valid = withdrawal(400_000_000, false);
    let (next, j) = common::execute(&valid);
    assert_eq!(next.spendable(), 600_000_000);
    match JournalEntries::decode(&j).unwrap().output_commitment {
        OutputCommitment::Success {
            exits,
            deposit_spk_hash,
            ..
        } => {
            assert_eq!(*deposit_spk_hash, [0; 32]);
            let entries: Vec<_> = exits.iter().map(|e| e.unwrap()).collect();
            assert_eq!(entries.len(), 1);
            assert_eq!(entries[0].1, 400_000_000);
            assert!(matches!(entries[0].0,StandardSpk::PubKey(pk) if *pk==owner));
        }
        _ => panic!("authorized withdrawal rejected"),
    }
    let out = verified(&batch(&valid, &[j.clone()], 202), &[j]);
    assert_eq!(out[72..104], common::root(&next));
    valid.state = next.clone();
    let (s, j) = common::execute(&valid);
    assert_eq!(s, next);
    assert!(matches!(
        JournalEntries::decode(&j).unwrap().output_commitment,
        OutputCommitment::Error(_)
    ));
}

fn aggregate(journals: &[Vec<u8>], allowed: &[Vec<u8>]) -> Vec<u8> {
    // Use the retained native SMT path as public wire-format data. The endpoint
    // below is derived; no live-chain anchoring or settlement is asserted.
    let v: serde_json::Value = serde_json::from_str(include_str!(
        "../../../lane-completeness/evidence/cloud-tn10/kpi-input.json"
    ))
    .unwrap();
    let lane = if v["lane"].is_object() {
        &v["lane"]
    } else {
        &v
    };
    let anchor = &lane["end"];
    let a32 = |v: &serde_json::Value| serde_json::from_value::<[u8; 32]>(v.clone()).unwrap();
    let mut wire = vec![];
    wire.write(&IMAGE);
    for field in ["payload_ctx", "parent_seq", "shortcut"] {
        wire.write(&a32(&anchor[field]));
    }
    let mut smt = a32(&anchor["bitmap"]).to_vec();
    smt.push(1);
    smt.push(anchor["depth"].as_u64().unwrap() as u8);
    for h in anchor["siblings"].as_array().unwrap() {
        smt.write(&a32(h));
    }
    wire.write_blob(&smt);
    for j in journals {
        wire.write_blob(j);
    }
    let mut v = vprogs_zk_abi::batch_aggregator::Verifier::new(
        &wire,
        |image, j| {
            assert_eq!(image, &IMAGE);
            assert!(
                allowed.iter().any(|a| a == j),
                "missing/wrong batch receipt"
            );
        },
        vprogs_zk_backend_risc0_api::PermissionTreeAccumulator::new(),
    );
    let last = v.verify_batches();
    let mut out = vec![];
    v.commit_state_transition(&mut out, last);
    out
}
#[test]
fn aggregate_rejects_missing_receipts_and_broken_state_tip_lane_covenant_image_continuity() {
    let i = deposit(1_000_000_000);
    let (_, txj) = common::execute(&i);
    let first = verified(&batch(&i, &[txj.clone()], 202), &[txj]);
    let mut second = first.clone();
    second[..32].copy_from_slice(&first[72..104]);
    second[32..64].copy_from_slice(&first[104..136]);
    second[64..72].copy_from_slice(&first[136..144]);
    let journals = [first.clone(), second.clone()];
    let out = aggregate(&journals, &journals);
    assert_eq!(out.len(), 352);
    assert_eq!(out[..32], first[..32]);
    assert_eq!(out[64..96], second[72..104]);
    rejects(|| {
        aggregate(&journals, &[]);
    });
    // Mutations are allowed by the callback, so rejection must come from the
    // unchanged reference aggregator's continuity rules.
    for offset in [0, 32, 64, 144, 176, 208] {
        let mut bad = second.clone();
        bad[offset] ^= 1;
        let js = [first.clone(), bad];
        rejects(|| {
            aggregate(&js, &js);
        });
    }
}
