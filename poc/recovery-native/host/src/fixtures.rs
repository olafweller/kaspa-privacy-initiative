use super::*;
use kaspa_consensus_core::tx::*;
use kaspa_hashes::Hash;
use std::path::PathBuf;
pub const STAGES: [&str; 6] = [
    "deposit",
    "credit-transfer",
    "bob-exit",
    "bob-reconcile",
    "alice-exit",
    "alice-reconcile",
];
pub type Case = (String, Input, Output);
fn old() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../user-recovery/evidence/review-fix/local")
}
fn linked(state: State, mut txs: Vec<lane::Tx>, score: u64) -> Input {
    for (i, t) in txs.iter_mut().enumerate() {
        t.merge_idx = i as u32;
    }
    let start = lane::Anchor {
        parent_seq: [1; 32],
        payload_ctx: [2; 32],
        shortcut: [3; 32],
        blue_score: state.last_touch,
        bitmap: [0; 32],
        depth: 0,
        siblings: vec![],
    };
    let mut end = start.clone();
    end.blue_score = score;
    Input {
        lane: lane::Input {
            lane: chain::LANE,
            covenant: state.covenant,
            old_state: state.root(),
            old_tip: state.lane_tip,
            start_seq: lane::bytes(start.seq(
                kaspa_seq_commit::hashing::lane_key(&chain::LANE),
                lane::h(state.lane_tip),
            )),
            start,
            blocks: vec![lane::Block {
                prev_timestamp: score * 1000,
                daa_score: score * 10,
                blue_score: score,
                txs,
            }],
            end,
        },
        state,
    }
}
fn operation(op: &Operation, key: H, n: u8) -> Result<lane::Tx> {
    Ok(native::lane_tx(&Transaction::new(
        1,
        vec![TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(Hash::from_bytes([n; 32]), 0),
            vec![],
            0,
            1,
        )],
        vec![TransactionOutput::new(
            1,
            ScriptPublicKey::new(0, vec![0x51].into()),
        )],
        0,
        chain::LANE.into(),
        0,
        chain::operation_payload(op, key)?,
    )))
}
fn step(name: &str, state: State, txs: Vec<lane::Tx>, score: u64) -> Case {
    let input = linked(state, txs, score);
    let output = app::execute(&input, &verifier());
    (name.into(), input, output)
}
#[derive(Clone)]
pub struct Prepared {
    pub cases: Vec<Case>,
    pub templates: Vec<Transaction>,
}
pub fn scenarios() -> Result<Prepared> {
    let prior: Input = bincode::deserialize(&fs::read(old().join("deposit.input.bin"))?)?;
    let genesis = State::genesis(
        prior.state.covenant,
        verifier().id(),
        prior.state.lane_tip,
        prior.state.last_touch,
    );
    let a = step(STAGES[0], genesis, prior.lane.blocks[0].txs.clone(), 11);
    assert!(a.2.events.iter().all(|e| e.accepted));
    let initial = TransactionOutpoint::new(Hash::from_bytes([0x7b; 32]), 0);
    let sponsor = |n: u8| TransactionOutpoint::new(Hash::from_bytes([n; 32]), 0);
    let ta = native::settlement_template(&a.2.state, None, initial, sponsor(0xa1));
    let old_b: Input = bincode::deserialize(&fs::read(old().join("credit-transfer.input.bin"))?)?;
    let mut invalid = old_b.lane.blocks[0].txs[1].clone();
    // Rejection by the private application does not unspend its L1 input.
    // v1 rest begins with version (u16), count (u64), then the first input ID.
    assert_eq!(app::NativeTx::parse(&invalid.rest)?.inputs.len(), 1);
    invalid.rest[10..42].copy_from_slice(&[0x93; 32]);
    // Preserve actual canonical curve points, but change a bound nullifier bit.
    let offset = chain::OP_TAG.len() + 4 + 2 + 32 + 32 + 32;
    invalid.payload[offset] ^= 1;
    let b = step(
        STAGES[1],
        a.2.state.clone(),
        vec![
            native::lane_tx(&ta),
            old_b.lane.blocks[0].txs[0].clone(),
            invalid,
            old_b.lane.blocks[0].txs[1].clone(),
        ],
        12,
    );
    assert_eq!(
        b.2.events.iter().map(|e| e.accepted).collect::<Vec<_>>(),
        [false, true, false, true]
    );
    assert_eq!(b.2.events[2].error.as_deref(), Some("invalid proof"));
    let tb = native::settlement_template(
        &b.2.state,
        None,
        TransactionOutpoint::new(ta.id(), 0),
        sponsor(0xa2),
    );
    let bob: Operation = serde_json::from_slice(include_bytes!("../../pins/bob-exit.json"))?;
    let bob_public: serde_json::Value =
        serde_json::from_slice(include_bytes!("../../pins/bob-exit-public.json"))?;
    let key: H = hex::decode(bob_public["nativePubkey"].as_str().unwrap())?
        .try_into()
        .unwrap();
    assert_eq!(chain::destination(&key), bob.statement.exit_destination);
    let c = step(
        STAGES[2],
        b.2.state.clone(),
        vec![native::lane_tx(&tb), operation(&bob, key, 0x91)?],
        13,
    );
    assert!(c.2.events[1].accepted);
    let tc = native::settlement_template(
        &c.2.state,
        Some(bob.statement.id()),
        TransactionOutpoint::new(tb.id(), 0),
        sponsor(0xa3),
    );
    let registered = app::apply(&c.2.state, &native::lane_tx(&tc), &verifier())?.0;
    let (payout, entries) = native::payout(&registered, bob.statement.id(), "")?;
    native::scripts(&payout, &entries)??;
    let d = step(
        STAGES[3],
        c.2.state.clone(),
        vec![native::lane_tx(&tc), native::lane_tx(&payout)],
        14,
    );
    assert!(d.2.events.iter().all(|e| e.accepted));
    let td = native::settlement_template(
        &d.2.state,
        None,
        TransactionOutpoint::new(tc.id(), 0),
        sponsor(0xa4),
    );
    let alice: Operation = serde_json::from_slice(&fs::read(old().join("alice-exit.json"))?)?;
    let terminal: serde_json::Value =
        serde_json::from_slice(&fs::read(old().join("terminal.json"))?)?;
    let key: H = hex::decode(terminal["recipient"].as_str().unwrap())?
        .try_into()
        .unwrap();
    let e = step(
        STAGES[4],
        d.2.state.clone(),
        vec![native::lane_tx(&td), operation(&alice, key, 0x92)?],
        15,
    );
    assert!(e.2.events[1].accepted);
    let te = native::settlement_template(
        &e.2.state,
        Some(alice.statement.id()),
        TransactionOutpoint::new(td.id(), 0),
        sponsor(0xa5),
    );
    let registered = app::apply(&e.2.state, &native::lane_tx(&te), &verifier())?.0;
    let (payout, entries) = native::payout(&registered, alice.statement.id(), "")?;
    native::scripts(&payout, &entries)??;
    let f = step(
        STAGES[5],
        e.2.state.clone(),
        vec![native::lane_tx(&te), native::lane_tx(&payout)],
        16,
    );
    assert!(f.2.events.iter().all(|e| e.accepted));
    let tf = native::settlement_template(
        &f.2.state,
        None,
        TransactionOutpoint::new(te.id(), 0),
        sponsor(0xa6),
    );
    assert_eq!(f.2.state.ledger.reserve, 0);
    assert_eq!(f.2.state.ledger.private_liability, 0);
    assert!(f.2.state.reserves.is_empty());
    assert!(f.2.state.permissions.is_empty());
    assert!(f.2.state.ledger.exits.values().all(|e| e.paid));
    let prepared = Prepared {
        cases: vec![a, b, c, d, e, f],
        templates: vec![ta, tb, tc, td, te, tf],
    };
    require_single_spend(&native_history(
        prepared
            .cases
            .iter()
            .map(|(name, input, _)| (name.as_str(), input)),
    )?)?;
    Ok(prepared)
}
/// Fixture qualification only: L1 enforces native spentness in a real trial.
/// Scan captured main-history inputs exactly once. Templates are already present
/// in later batches; alternatives/replays are separate histories, not appended.
pub fn native_history<'a>(
    inputs: impl IntoIterator<Item = (&'a str, &'a Input)>,
) -> Result<serde_json::Value> {
    let mut spent = std::collections::BTreeMap::new();
    let mut conflicts = vec![];
    let mut transactions = vec![];
    let mut input_count = 0;
    for (stage, input) in inputs {
        for (block, b) in input.lane.blocks.iter().enumerate() {
            for (index, tx) in b.txs.iter().enumerate() {
                let parsed = app::NativeTx::parse(&tx.rest)?;
                let location = json!({"stage":stage,"block":block,"transactionIndex":index});
                for outpoint in &parsed.inputs {
                    input_count += 1;
                    if let Some(first) = spent.get(outpoint) {
                        conflicts.push(json!({"outpoint":outpoint,"first":first,"again":location}));
                    } else {
                        spent.insert(outpoint.clone(), location.clone());
                    }
                }
                transactions.push(json!({"location":location,"inputs":parsed.inputs}));
            }
        }
    }
    Ok(
        json!({"scope":"MAIN_CAPTURED_NATIVE_HISTORY_INPUT_UNIQUENESS_NOT_CHAIN_ACCEPTANCE",
        "transactionCount":transactions.len(),"inputCount":input_count,
        "uniqueInputs":spent.len(),"conflicts":conflicts,"transactions":transactions,
        "templatesCountedSeparately":false,"adversarialAlternativesIncluded":false}),
    )
}
pub fn require_single_spend(history: &serde_json::Value) -> Result<()> {
    if !history["conflicts"]
        .as_array()
        .ok_or("history conflicts field")?
        .is_empty()
    {
        return Err("reused native input in main fixture history".into());
    }
    Ok(())
}
pub fn controls(p: &Prepared) -> Result<(Vec<Case>, Vec<(String, Input, String)>)> {
    let mut complete = vec![];
    let mut aborts = vec![];
    for (label, mut i) in [
        ("auth-root", p.cases[5].1.clone()),
        ("auth-tip", p.cases[5].1.clone()),
        ("auth-inclusion", p.cases[5].1.clone()),
        ("auth-last-touch", p.cases[5].1.clone()),
        ("auth-covenant", p.cases[5].1.clone()),
        ("auth-lane", p.cases[5].1.clone()),
    ] {
        let reason = match label {
            "auth-root" => {
                i.lane.old_state[0] ^= 1;
                "prior state"
            }
            "auth-tip" => {
                i.lane.old_tip[0] ^= 1;
                "prior tip"
            }
            "auth-inclusion" => {
                i.lane.start_seq[0] ^= 1;
                "start active inclusion"
            }
            "auth-last-touch" => {
                i.lane.start.blue_score += 1;
                "prior last touch"
            }
            "auth-covenant" => {
                i.lane.covenant[0] ^= 1;
                "covenant"
            }
            _ => {
                i.lane.lane[0] ^= 1;
                "fixed lane"
            }
        };
        aborts.push((label.into(), i, reason.into()));
    }
    let mut tx = p.cases[5].1.lane.blocks[0].txs[1].clone();
    let mut t: app::NativeTx = app::NativeTx::parse(&tx.rest)?;
    // The rest preimage's first output amount occurs after the inputs and output count.
    let offset = 2 + 8 + 3 * (32 + 4 + 8 + 8) + 8;
    t.outputs[0].value -= 1;
    tx.rest[offset..offset + 8].copy_from_slice(&t.outputs[0].value.to_le_bytes());
    let mut i = p.cases[5].1.clone();
    i.lane.blocks[0].txs[1] = tx;
    aborts.push((
        "unreconciled-payout".into(),
        i,
        "unreconciled accepted native consumption".into(),
    ));
    let i = linked(
        p.cases[4].2.state.clone(),
        vec![native::lane_tx(&p.templates[4])],
        16,
    );
    let out = app::execute(&i, &verifier());
    assert_eq!(out.state.accounting()?.unpaid_exits, 600_000_000);
    assert_eq!(out.state.ledger.reserve, 600_000_000);
    complete.push(("permission-only".into(), i, out));
    let i = linked(
        p.cases[5].2.state.clone(),
        vec![p.cases[4].1.lane.blocks[0].txs[1].clone()],
        17,
    );
    let out = app::execute(&i, &verifier());
    assert!(!out.events[0].accepted);
    complete.push(("wallet-replay".into(), i, out));
    Ok((complete, aborts))
}
pub fn prepare(out: &Path) -> Result<()> {
    fs::create_dir(out)?;
    let p = scenarios()?;
    report(
        out,
        "native-history.json",
        &native_history(
            p.cases
                .iter()
                .map(|(name, input, _)| (name.as_str(), input)),
        )?,
    )?;
    let (extra, aborts) = controls(&p)?;
    let mut targets = serde_json::Map::new();
    for (name, input, expected) in p.cases.iter().chain(extra.iter()) {
        save(out, &format!("{name}.input.bin"), input)?;
        save(out, &format!("{name}.expected.bin"), expected)?;
        save(out, &format!("{name}.state.bin"), &expected.state)?;
        fs::write(out.join(format!("{name}.journal.bin")), &expected.journal)?;
        if STAGES.contains(&name.as_str()) {
            targets.insert(name.clone(),json!({"inputSha256":hex::encode(hash(&bincode::serialize(input)?)),"expectedJournalHex":hex::encode(&expected.journal),"expectedJournalSha256":hex::encode(hash(&expected.journal)),"segmentPo2":if name=="deposit"||name.ends_with("reconcile"){16}else{20},"accounting":expected.state.accounting()?}));
        }
    }
    for (name, input, reason) in &aborts {
        save(out, &format!("{name}.input.bin"), input)?;
        fs::write(out.join(format!("{name}.abort.txt")), reason)?;
    }
    let mut accounting = vec![];
    let mut native_rows = vec![];
    for n in 0..6 {
        let (name, input, expected) = &p.cases[n];
        accounting.push(json!({"stage":name,"root":hex::encode(expected.state.root()),"tip":hex::encode(expected.state.lane_tip),"accounting":expected.state.accounting()?}));
        save(out, &format!("{name}.template.bin"), &p.templates[n])?;
        let prev = if n == 0 {
            None
        } else {
            Some(p.templates[n - 1].id().to_string())
        };
        assert!(
            n == 0
                || p.templates[n].inputs[0].previous_outpoint.transaction_id
                    == p.templates[n - 1].id()
        );
        if n == 2 || n == 4 {
            let eid = *expected
                .state
                .ledger
                .exits
                .iter()
                .find(|(_, e)| !e.paid)
                .unwrap()
                .0;
            let registered = app::apply(
                &expected.state,
                &native::lane_tx(&p.templates[n]),
                &verifier(),
            )?
            .0;
            let (tx, es) = native::payout(&registered, eid, "")?;
            let units = native::scripts(&tx, &es)??;
            native_rows.push(json!({"stage":name,"permissionTransactionId":p.templates[n].id().to_string(),"payoutTransactionId":tx.id().to_string(),"outputs":tx.outputs.len(),"scriptUnits":units,"syntheticPermissionUTXO":true,"genuineIssuanceProofAvailable":false}));
        }
        report(
            out,
            &format!("{name}.template.json"),
            &json!({"templateOnly":true,"broadcast":false,"id":p.templates[n].id().to_string(),"previousSettlement":prev,"previousRoot":hex::encode(input.state.root()),"nextRoot":hex::encode(expected.state.root())}),
        )?;
    }
    report(
        out,
        "targets.json",
        &json!({"scope":"NEW_GUEST_SIX_LOCAL_BATCHES_NO_OUTER_RECEIPTS_OR_CHAIN_ACCEPTANCE","expectedProgramImage":include_str!("../../evidence/expected-image.txt").trim(),"expectedJoinControl":kpi_private_note_proof::JOIN,"batches":targets}),
    )?;
    report(
        out,
        "lifecycle.json",
        &json!({"scope":"LOCAL_REAL_WALLET_PROOFS_NATIVE_PAYOUTS_AND_GUEST_EXPECTATIONS_NOT_OUTER_PROOFS","stages":STAGES,"accounting":accounting,"nativePayouts":native_rows,"additionalExecutionCases":extra.iter().map(|x|x.0.as_str()).chain(aborts.iter().map(|x|x.0.as_str())).collect::<Vec<_>>(),"stateRentSeparated":app::STATE_RENT,"newOuterReceipts":0,"nativePermissionIssuanceProven":false,"sourceWalletProofs":"PR55 public fixtures only; no role secrets","instance":"Unfunded synthetic native context; future TN10 must bootstrap a fresh covenant pinned to this program"}),
    )
}
