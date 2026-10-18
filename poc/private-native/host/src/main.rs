mod native;
use kpi_private_native::{
    self as app, chain, lane,
    wallet::{protocol::*, ProofVerifier},
    AcceleratedVerifier, Input, Output, State,
};
use serde_json::json;
use std::{fs, path::Path, time::Instant};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
fn save<T: serde::Serialize>(out: &Path, name: &str, value: &T) -> Result<()> {
    fs::write(out.join(name), bincode::serialize(value)?)?;
    Ok(())
}
fn report(out: &Path, name: &str, value: &serde_json::Value) -> Result<()> {
    fs::write(out.join(name), serde_json::to_vec_pretty(value)?)?;
    Ok(())
}
fn verifier() -> AcceleratedVerifier {
    AcceleratedVerifier::checked(
        include_bytes!("../../../private-note-chain/pins/vk.bin"),
        *include_bytes!("../../../private-note-chain/pins/vk-id.bin"),
    )
    .unwrap()
}
fn source() -> std::path::PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../private-note-chain/evidence/public")
}
fn old(name: &str) -> Result<chain::Input> {
    Ok(bincode::deserialize(&fs::read(
        source().join(format!("{name}.input.bin")),
    )?)?)
}
fn linked(state: State, mut txs: Vec<lane::Tx>, score: u64) -> Input {
    for (i, t) in txs.iter_mut().enumerate() {
        t.merge_idx = i as u32;
    }
    let start = lane::Anchor {
        parent_seq: hash(&score.to_le_bytes()),
        payload_ctx: [2; 32],
        shortcut: [3; 32],
        blue_score: state.last_touch,
        bitmap: [0; 32],
        depth: 0,
        siblings: vec![],
    };
    let mut end = start.clone();
    end.blue_score = score;
    let key = kaspa_seq_commit::hashing::lane_key(&chain::LANE);
    Input {
        lane: lane::Input {
            lane: chain::LANE,
            covenant: state.covenant,
            old_state: state.root(),
            old_tip: state.lane_tip,
            start_seq: lane::bytes(start.seq(key, lane::h(state.lane_tip))),
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
fn scenarios(exit_override: Option<&Path>) -> Result<Vec<(String, Input, Output)>> {
    let v = verifier();
    let d = old("deposit")?;
    let genesis = State::genesis(d.state.covenant, v.id(), [0; 32], 10);
    let a = linked(genesis, d.lane.blocks[0].txs.clone(), 11);
    let oa = app::execute(&a, &v);
    let b = linked(
        oa.state.clone(),
        [
            old("credit")?.lane.blocks[0].txs.clone(),
            old("transfer")?.lane.blocks[0].txs.clone(),
        ]
        .concat(),
        5000,
    );
    let ob = app::execute(&b, &v);
    let mut exit_txs = old("exit")?.lane.blocks[0].txs.clone();
    if let Some(path) = exit_override {
        let op: Operation = serde_json::from_slice(&fs::read(path)?)?;
        let key: H =
            hex::decode("79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798")?
                .try_into()
                .unwrap();
        exit_txs[0].payload = chain::operation_payload(&op, key)?;
    }
    let c = linked(ob.state.clone(), exit_txs, 10000);
    let oc = app::execute(&c, &v);
    let eid = *oc.state.ledger.exits.keys().next().ok_or("no exit")?;
    let grant = native::issuance(&oc.state, eid);
    let gt = native::lane_tx(&grant);
    let (registered, _, _) = app::apply(&oc.state, &gt, &v)?;
    let (payout, _) = native::payout(&registered, eid, "")?;
    let d = linked(oc.state.clone(), vec![gt, native::lane_tx(&payout)], 15000);
    let od = app::execute(&d, &v);
    Ok(vec![
        ("deposit".into(), a, oa),
        ("credit-transfer".into(), b, ob),
        ("exit".into(), c, oc),
        ("reconcile".into(), d, od),
    ])
}
fn prepare(out: &Path, exit_override: Option<&Path>) -> Result<()> {
    fs::create_dir(out)?;
    let cases = scenarios(exit_override)?;
    let mut rows = vec![];
    rows.push(json!({"stage":"zero","accounting":cases[0].1.state.accounting()?}));
    let v = verifier();
    let mut controls = vec![];
    for (name, input, expected) in &cases {
        assert!(expected.events.iter().all(|e| e.accepted), "{name}");
        save(out, &format!("{name}.input.bin"), input)?;
        save(out, &format!("{name}.expected.bin"), expected)?;
        save(out, &format!("{name}.state.bin"), &expected.state)?;
        fs::write(out.join(format!("{name}.journal.bin")), &expected.journal)?;
        let mut s = input.state.clone();
        for tx in &input.lane.blocks[0].txs {
            s = app::apply(&s, tx, &v)?.0;
            rows.push(json!({"stage":name,"nativeId":hex::encode(vprogs_l1_utils::tx_id_v1(&tx.payload,&tx.rest)),"accounting":s.accounting()?}));
        }
    }
    let dep = &cases[0].1;
    let mut duplicate = dep.lane.blocks[0].txs[0].clone();
    assert!(app::apply(&cases[0].2.state, &duplicate, &v).is_err());
    controls.push(json!({"case":"duplicate-deposit-outpoint","rejected":true,"layer":"guest native-output registration"}));
    duplicate.payload[chain::DEPOSIT_TAG.len() + 32..].copy_from_slice(&1u32.to_le_bytes());
    assert!(app::apply(&dep.state, &duplicate, &v).is_err());
    controls.push(json!({"case":"fabricated-deposit-output","rejected":true,"layer":"guest ID-bound native output"}));
    for (name, s, tx) in [
        (
            "old-root-double-spend",
            &cases[1].2.state,
            old("old-root-competing-next-batch")?.lane.blocks[0].txs[0].clone(),
        ),
        (
            "transfer-replay",
            &cases[1].2.state,
            old("transfer")?.lane.blocks[0].txs[0].clone(),
        ),
        (
            "wrong-exit-recipient",
            &cases[1].2.state,
            old("wrong-native-destination")?.lane.blocks[0].txs[0].clone(),
        ),
    ] {
        assert!(app::apply(s, &tx, &v).is_err(), "{name}");
        controls.push(json!({"case":name,"rejected":true,"layer":"guest current nullifier/actual wallet proof/destination"}));
    }
    let exit_state = &cases[2].2.state;
    let eid = *exit_state.ledger.exits.keys().next().unwrap();
    let grant = cases[3].1.lane.blocks[0].txs[0].clone();
    let registered = app::apply(exit_state, &grant, &v)?.0;
    let reserve = &registered.exit_reserves[&eid];
    report(
        out,
        "native-policy.json",
        &json!({
            "scope":"PUBLIC_UNFUNDED_RESTRICTED_POLICY_FOR_BUILDER_INTEGRATION",
            "covenantId":hex::encode(registered.covenant),
            "recipient":hex::encode(registered.exit_keys[&eid]),
            "amount":registered.ledger.exits[&eid].amount,
            "reserveTxid":hex::encode(reserve.id),"reserveIndex":reserve.index,
            "reserveValue":registered.reserves[reserve],
            "permissionRedeem":hex::encode(app::restricted::permission_redeem(&registered,eid)),
            "permissionRent":app::PERMISSION_RENT
        }),
    )?;
    report(
        out,
        "review-regressions.json",
        &native::scope_campaign(&registered, eid, &v)?,
    )?;
    let mut negative_cases: Vec<(&str, State, lane::Tx)> = vec![
        (
            "duplicate-deposit",
            cases[0].2.state.clone(),
            cases[0].1.lane.blocks[0].txs[0].clone(),
        ),
        ("fabricated-deposit", dep.state.clone(), duplicate.clone()),
        (
            "stale-double-spend",
            cases[1].2.state.clone(),
            old("old-root-competing-next-batch")?.lane.blocks[0].txs[0].clone(),
        ),
        (
            "transfer-replay",
            cases[1].2.state.clone(),
            old("transfer")?.lane.blocks[0].txs[0].clone(),
        ),
        (
            "wrong-exit-recipient",
            cases[1].2.state.clone(),
            old("wrong-native-destination")?.lane.blocks[0].txs[0].clone(),
        ),
    ];
    for attack in ["underpay", "reserve-diversion", "wrong-recipient"] {
        let (t, _) = native::payout(&registered, eid, attack)?;
        assert!(app::apply(&registered, &native::lane_tx(&t), &v).is_err());
        negative_cases.push((attack, registered.clone(), native::lane_tx(&t)));
        controls.push(
            json!({"case":attack,"rejected":true,"layer":"guest authenticated payout accounting"}),
        );
    }
    let paid = &cases[3].2.state;
    assert_eq!(paid.ledger.reserve, 600_000_000);
    assert_eq!(paid.ledger.private_liability, 600_000_000);
    assert_eq!(paid.accounting()?.unpaid_exits, 0);
    assert!(app::apply(paid, &cases[3].1.lane.blocks[0].txs[1], &v).is_err());
    negative_cases.push((
        "payout-replay",
        paid.clone(),
        cases[3].1.lane.blocks[0].txs[1].clone(),
    ));
    controls.push(json!({"case":"reconcile-payout-replay","rejected":true,"layer":"guest consumed permission and paid exit"}));
    let mut omitted = cases[3].1.clone();
    omitted.lane.blocks[0].txs.remove(1);
    let omit = app::execute(&omitted, &v);
    assert_ne!(&omit.journal[96..160], &cases[3].2.journal[96..160]);
    controls.push(json!({"case":"omitted-payout-changes-native-endpoint","rejected":true,"layer":"endpoint comparison only; not a newly proved omission"}));
    let mut negative_names = vec![];
    for (name, s, t) in negative_cases {
        let i = linked(s, vec![t], 20_000);
        if ["underpay", "reserve-diversion", "wrong-recipient"].contains(&name) {
            let case = format!("reject-{name}");
            save(out, &format!("{case}.input.bin"), &i)?;
            fs::write(
                out.join(format!("{case}.abort.txt")),
                "unreconciled accepted native consumption",
            )?;
            assert!(
                std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| app::execute(&i, &v)))
                    .is_err()
            );
            negative_names.push(case);
            continue;
        }
        let o = app::execute(&i, &v);
        assert_eq!(o.events.len(), 1);
        assert!(!o.events[0].accepted);
        assert_eq!(o.events[0].before, o.events[0].after);
        let name = format!("reject-{name}");
        save(out, &format!("{name}.input.bin"), &i)?;
        save(out, &format!("{name}.expected.bin"), &o)?;
        negative_names.push(name);
    }
    // A third party may use the public permission witness with any payload.
    // Native outpoint consumption still triggers mandatory reconciliation.
    let mut grant_without_tag = grant.clone();
    grant_without_tag.payload = vec![];
    let no_tag = app::apply(exit_state, &grant_without_tag, &v)?.0;
    let (mut paid_without_tag, mut entries) = native::payout(&no_tag, eid, "")?;
    paid_without_tag.payload = vec![];
    native::sign_sponsor(&mut paid_without_tag, &mut entries)?;
    assert!(native::scripts(&paid_without_tag, &entries)?.is_ok());
    let reconciled = app::apply(&no_tag, &native::lane_tx(&paid_without_tag), &v)?.0;
    assert_eq!(reconciled.accounting()?.unpaid_exits, 0);
    controls.push(json!({"case":"permission-and-payout-without-executor-tags","acceptedByActualNativeScriptsAndReconciled":true,"layer":"native outpoint and covenant-output detection"}));
    // Positive complete guest folds for the native-accepted counterexamples.
    let (topup, entries) = native::payout(&registered, eid, "top-up")?;
    assert!(native::scripts(&topup, &entries)?.is_ok());
    let (second, entries) = native::second_deposit(&registered)?;
    assert!(native::scripts(&second, &entries)?.is_ok());
    let second_state = app::apply(&registered, &native::lane_tx(&second), &v)?.0;
    let (payout, entries) = native::payout(&second_state, eid, "")?;
    assert!(native::scripts(&payout, &entries)?.is_ok());
    for (name, txs) in [
        ("accept-top-up", vec![native::lane_tx(&topup)]),
        (
            "accept-second-deposit",
            vec![native::lane_tx(&second), native::lane_tx(&payout)],
        ),
    ] {
        let i = linked(registered.clone(), txs, 21_000);
        let o = app::execute(&i, &v);
        assert!(o.events.iter().all(|e| e.accepted));
        assert_eq!(o.state.accounting()?.unpaid_exits, 0);
        save(out, &format!("{name}.input.bin"), &i)?;
        save(out, &format!("{name}.expected.bin"), &o)?;
        negative_names.push(name.to_owned());
    }
    let (t, entries) = native::payout(&registered, eid, "versioned-sponsor-output")?;
    assert!(native::scripts(&t, &entries)?.is_ok());
    let i = linked(registered.clone(), vec![native::lane_tx(&t)], 21_500);
    let o = app::execute(&i, &v);
    assert!(o.events[0].accepted);
    assert_eq!(o.state.accounting()?.unpaid_exits, 0);
    save(out, "accept-versioned-sponsor.input.bin", &i)?;
    save(out, "accept-versioned-sponsor.expected.bin", &o)?;
    negative_names.push("accept-versioned-sponsor".into());
    let i = linked(
        no_tag.clone(),
        vec![native::lane_tx(&paid_without_tag)],
        22_000,
    );
    let o = app::execute(&i, &v);
    assert!(o.events[0].accepted);
    assert_eq!(o.state.accounting()?.unpaid_exits, 0);
    save(out, "accept-tagless.input.bin", &i)?;
    save(out, "accept-tagless.expected.bin", &o)?;
    negative_names.push("accept-tagless".into());
    for name in ["prior-state", "prior-tip", "start-inclusion", "last-touch"] {
        let mut i = cases[1].1.clone();
        match name {
            "prior-state" => i.lane.old_state[0] ^= 1,
            "prior-tip" => i.lane.old_tip[0] ^= 1,
            "start-inclusion" => i.lane.start_seq[0] ^= 1,
            _ => i.lane.start.blue_score += 1,
        };
        let label = match name {
            "prior-state" => "prior state",
            "prior-tip" => "prior tip",
            "start-inclusion" => "start active inclusion",
            _ => "prior last touch",
        };
        let case = format!("auth-{name}");
        save(out, &format!("{case}.input.bin"), &i)?;
        fs::write(out.join(format!("{case}.abort.txt")), label)?;
        negative_names.push(case);
        assert!(
            std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| app::execute(&i, &v)))
                .is_err()
        );
        controls.push(json!({"case":name,"rejected":true,"layer":"native host invocation of guest authentication relation"}));
    }
    report(
        out,
        "native-payout.json",
        &native::campaign(&registered, eid)?,
    )?;
    report(
        out,
        "lifecycle.json",
        &json!({"scope":"LOCAL_REAL_WALLET_PROOFS_NATIVE_PAYOUT_SCRIPTS_SYNTHETIC_ACCEPTED_LANE_AND_PERMISSION_ISSUANCE","rows":rows,"controls":controls,"guestCycleLimitPerBatch":app::CYCLE_LIMIT,"wallLimitPerBatchSeconds":900,"campaignWallLimitSeconds":3600,"newOuterReceiptProduced":false,"permissionIssuanceReceiptVerified":false,"actualTN10Broadcast":false,"activeLaneGapScores":[4989,5000,5000],"stateCovenantContinuationValueSompi":app::STATE_RENT,"parameterSetupPerformed":false,"additionalExecutionCases":negative_names}),
    )?;
    Ok(())
}
fn profile(program: &Path, fixtures: &Path, name: &str, out: &Path) -> Result<()> {
    use risc0_zkvm::{compute_image_id, default_executor, ExecutorEnv};
    fs::create_dir(out)?;
    let bytes = fs::read(program)?;
    let id = compute_image_id(&bytes)?;
    assert_eq!(
        id.to_string(),
        fs::read_to_string(fixtures.join("expected-image.txt"))?.trim(),
        "declared image"
    );
    let raw = fs::read(fixtures.join(format!("{name}.input.bin")))?;
    let abort = fixtures.join(format!("{name}.abort.txt"));
    if abort.exists() {
        let label = fs::read_to_string(abort)?;
        assert!([
            "prior state",
            "prior tip",
            "start active inclusion",
            "prior last touch",
            "unreconciled accepted native consumption"
        ]
        .contains(&label.as_str()));
        let mut b = ExecutorEnv::builder();
        b.write_slice(&[raw.len() as u32])
            .write_slice(&raw)
            .segment_limit_po2(20)
            .session_limit(Some(app::CYCLE_LIMIT));
        let start = Instant::now();
        let error = default_executor()
            .execute(b.build()?, &bytes)
            .err()
            .ok_or("required guest abort unexpectedly completed")?;
        let message = format!("{error:#}");
        let matched = if label == "unreconciled accepted native consumption" {
            message.starts_with("Guest panicked: unreconciled accepted native consumption")
        } else {
            message.starts_with("Guest panicked: assertion `left == right` failed: ")
                && message.contains(&format!("failed: {label}\n"))
        };
        if !matched {
            return Err(error.into());
        }
        report(
            out,
            "report.json",
            &json!({"scope":"ACTUAL_GUEST_REQUIRED_ABORT_NOT_RESOURCE_FAILURE","case":name,"expectedImage":id.to_string(),"expectedAbortReason":label,"expectedAbortConfirmed":true,"error":message,"seconds":start.elapsed().as_secs_f64()}),
        )?;
        return Ok(());
    }
    let expected: Output =
        bincode::deserialize(&fs::read(fixtures.join(format!("{name}.expected.bin")))?)?;
    let mut b = ExecutorEnv::builder();
    b.write_slice(&[raw.len() as u32])
        .write_slice(&raw)
        .stdout(std::io::stdout())
        .segment_limit_po2(if ["deposit", "reconcile"].contains(&name) {
            16
        } else {
            20
        })
        .session_limit(Some(app::CYCLE_LIMIT));
    let start = Instant::now();
    let s = default_executor().execute(b.build()?, &bytes)?;
    assert_eq!(s.journal.bytes, expected.journal, "full expected journal");
    if ["deposit", "credit-transfer", "exit", "reconcile"].contains(&name) {
        assert!(
            s.segments.len() > 1,
            "declared join profile requires multiple segments"
        );
    }
    fs::write(out.join("journal.bin"), &s.journal.bytes)?;
    report(
        out,
        "report.json",
        &json!({"scope":"NEW_LIFECYCLE_EXECUTION_ONLY_NO_RECEIPT","expectedImage":id.to_string(),"userCycles":s.cycles(),"segments":s.segments.len(),"segmentPo2":if ["deposit","reconcile"].contains(&name){16}else{20},"seconds":start.elapsed().as_secs_f64(),"exactExpectedJournalMatched":true,"journalSha256":hex::encode(hash(&s.journal.bytes)),"cycleLimit":app::CYCLE_LIMIT,"case":name,"developmentMode":false}),
    )?;
    Ok(())
}
fn bob_exit(
    secret: &Path,
    public: &Path,
    parameters: &Path,
    out: &Path,
    recipient: Option<&str>,
) -> Result<()> {
    use app::wallet::wallet::{Engine, Wallet};
    use std::os::unix::fs::PermissionsExt;
    if fs::metadata(secret)?.permissions().mode() & 0o077 != 0 {
        return Err("Bob backup must be owner-only".into());
    }
    let expected_parameter_sha = "812b3bda0ec5f9b0c17fc1d530e49fc21defc9dcc5ea9c70a133ca62fec31e99";
    let raw = fs::read(parameters)?;
    if hex::encode(hash(&raw)) != expected_parameter_sha {
        return Err("independently expected public parameter hash".into());
    }
    let v = verifier();
    let engine = Engine::from_public_parameters(&raw, v.id())?;
    let bob = Wallet::restore_local(
        &fs::read(secret)?
            .try_into()
            .map_err(|_| "Bob backup length")?,
    );
    let state: State = bincode::deserialize(&fs::read(public)?)?;
    state.accounting()?;
    let found = bob.discover(
        &state.ledger.deliveries,
        &state.ledger.tree,
        &state.ledger.nullifiers,
    );
    if found.len() != 1 || found[0].0.value != 400_000_000 {
        return Err("independent Bob discovery/value".into());
    }
    let (note, index) = found[0].clone();
    let (path, bits) = state.ledger.tree.path(index)?;
    let key: H = hex::decode(
        recipient.unwrap_or("79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"),
    )?
    .try_into()
    .map_err(|_| "native recipient length")?;
    secp256k1::XOnlyPublicKey::from_slice(&key)?;
    let mut s = Statement::new(EXIT, v.id(), state.ledger.tree.root());
    s.nullifier = bob.nf(&note);
    s.exit_value = note.value;
    s.exit_destination = chain::destination(&key);
    let start = Instant::now();
    let op = engine.prove(
        s,
        bob.witness(note, [Note::dummy(), Note::dummy()], path, bits),
        [Delivery::absent(), Delivery::absent()],
    )?;
    let mut check = state.ledger.clone();
    check.apply(&v, &op)?;
    fs::create_dir(out)?;
    fs::write(out.join("bob-exit.json"), serde_json::to_vec_pretty(&op)?)?;
    report(
        out,
        "bob-recovery.json",
        &json!({"scope":"SEPARATE_LOCAL_BOB_PROCESS_OWN_SECRET_AND_PUBLIC_STATE_ONLY","publicParameterHashChecked":true,"publicParameterSha256":expected_parameter_sha,"walletVk":hex::encode(v.id()),"discoveredAndValidatedOwnNote":true,"newActualExitProofVerifiedAgainstCurrentState":true,"exitPrincipalSompi":400_000_000u64,"secretMaterialPublished":false,"seconds":start.elapsed().as_secs_f64()}),
    )?;
    Ok(())
}
fn prepare_capture(
    program: &Path,
    lane_file: &Path,
    state_file: &Path,
    case: &str,
    out: &Path,
) -> Result<()> {
    if case.is_empty()
        || case.len() > 64
        || !case
            .bytes()
            .all(|x| x.is_ascii_alphanumeric() || x == b'-' || x == b'_')
    {
        return Err("safe fixed case name required".into());
    }
    let raw_state = fs::read(state_file)?;
    let state: State = bincode::deserialize(&raw_state)?;
    if bincode::serialize(&state)? != raw_state {
        return Err("canonical prior state bytes required".into());
    }
    let lane: lane::Input = serde_json::from_slice(&fs::read(lane_file)?)?;
    let input = Input { state, lane };
    let output = app::execute(&input, &verifier());
    let program = fs::read(program)?;
    let image = risc0_zkvm::compute_image_id(&program)?.to_string();
    if image != include_str!("../../evidence/expected-image.txt").trim() {
        return Err("fixed lifecycle guest required".into());
    }
    fs::create_dir(out)?;
    save(out, &format!("{case}.input.bin"), &input)?;
    save(out, &format!("{case}.expected.bin"), &output)?;
    save(out, &format!("{case}.state.bin"), &output.state)?;
    fs::write(out.join(format!("{case}.journal.bin")), &output.journal)?;
    fs::write(out.join("expected-image.txt"), &image)?;
    report(
        out,
        "capture-target.json",
        &json!({"scope":"PREPARED_PUBLIC_CAPTURE_REQUIRES_INDEPENDENT_NATIVE_ACCEPTANCE_CHECK","case":case,"expectedProgramImage":image,"inputSha256":hex::encode(hash(&bincode::serialize(&input)?)),"journalSha256":hex::encode(hash(&output.journal)),"expectedJournalHex":hex::encode(&output.journal),"acceptedNativeEndpointMustBeIndependentlyChecked":true,"proofStarted":false,"broadcast":false}),
    )?;
    Ok(())
}
fn main() -> Result<()> {
    let a: Vec<_> = std::env::args().collect();
    match a.get(1).map(String::as_str){
        Some("prepare") if a.len()==3 || a.len()==4=>prepare(Path::new(&a[2]),a.get(3).map(Path::new)),
        Some("bob-public") if a.len()==3=>{let cases=scenarios(None)?;fs::write(&a[2],bincode::serialize(&cases[1].2.state)?)?;Ok(())},
        Some("bob-exit") if a.len()==6 || a.len()==7=>bob_exit(Path::new(&a[2]),Path::new(&a[3]),Path::new(&a[4]),Path::new(&a[5]),a.get(6).map(String::as_str)),
        Some("profile") if a.len()==6=>profile(Path::new(&a[2]),Path::new(&a[3]),&a[4],Path::new(&a[5])),
        Some("genesis") if a.len()==6=>{
            use std::io::Write;
            let covenant:H=hex::decode(&a[2])?.try_into().map_err(|_|"covenant length")?;let tip:H=hex::decode(&a[3])?.try_into().map_err(|_|"seed tip length")?;
            let state=State::genesis(covenant,verifier().id(),tip,a[4].parse()?);state.accounting()?;
            let mut file=fs::OpenOptions::new().write(true).create_new(true).open(&a[5])?;file.write_all(&bincode::serialize(&state)?)?;file.sync_all()?;Ok(())
        },
        Some("prepare-capture") if a.len()==7=>prepare_capture(Path::new(&a[2]),Path::new(&a[3]),Path::new(&a[4]),&a[5],Path::new(&a[6])),
        _=>Err("prepare NEW_OUTPUT [PUBLIC_BOB_EXIT] | bob-public NEW_FILE | bob-exit OWN_BACKUP PUBLIC_STATE PUBLIC_PARAMS NEW_OUTPUT | profile PROGRAM FIXTURES CASE NEW_OUTPUT".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn captured_lane_adapter_preserves_prior_state_and_exact_journal() {
        let cases = scenarios(None).unwrap();
        let input = &cases[1].1;
        let dir = std::env::temp_dir().join(format!(
            "kpi-native-capture-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&dir).unwrap();
        let lane = dir.join("lane.json");
        let state = dir.join("state.bin");
        fs::write(&lane, serde_json::to_vec(&input.lane).unwrap()).unwrap();
        fs::write(&state, bincode::serialize(&input.state).unwrap()).unwrap();
        let program = Path::new(env!("CARGO_MANIFEST_DIR")).join("../evidence/guest.program.bin");
        let out = dir.join("output");
        prepare_capture(&program, &lane, &state, "credit-transfer", &out).unwrap();
        assert_eq!(
            fs::read(out.join("credit-transfer.journal.bin")).unwrap(),
            cases[1].2.journal
        );
        let target: serde_json::Value =
            serde_json::from_slice(&fs::read(out.join("capture-target.json")).unwrap()).unwrap();
        assert_eq!(
            target["acceptedNativeEndpointMustBeIndependentlyChecked"],
            true
        );
        assert_eq!(target["broadcast"], false);
        assert!(prepare_capture(&program, &lane, &state, "../escape", &dir.join("bad")).is_err());
        fs::remove_dir_all(dir).unwrap();
    }
    #[test]
    fn native_permitted_forms_are_reconciled_or_rejected_before_spending() {
        let cases = scenarios(None).unwrap();
        let v = verifier();
        let eid = *cases[2].2.state.ledger.exits.keys().next().unwrap();
        let registered = app::apply(&cases[2].2.state, &cases[3].1.lane.blocks[0].txs[0], &v)
            .unwrap()
            .0;
        let result = native::scope_campaign(&registered, eid, &v).unwrap();
        assert_eq!(result["cases"].as_array().unwrap().len(), 9);
        // A newly registered reserve does not reselect the reserve already
        // committed by the admitted exit, even before permission issuance.
        let (d, entries) = native::second_deposit(&cases[2].2.state).unwrap();
        assert!(native::scripts(&d, &entries).unwrap().is_ok());
        let s = app::apply(&cases[2].2.state, &native::lane_tx(&d), &v)
            .unwrap()
            .0;
        let g = native::issuance(&s, eid);
        let s = app::apply(&s, &native::lane_tx(&g), &v).unwrap().0;
        let (p, entries) = native::payout(&s, eid, "").unwrap();
        assert!(native::scripts(&p, &entries).unwrap().is_ok());
        assert_eq!(
            app::apply(&s, &native::lane_tx(&p), &v)
                .unwrap()
                .0
                .ledger
                .reserve,
            1_600_000_000
        );
        let (bad, _) = native::payout(&registered, eid, "underpay").unwrap();
        let i = linked(registered, vec![native::lane_tx(&bad)], 21_000);
        assert!(
            std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| app::execute(&i, &v)))
                .is_err()
        );
    }
    #[test]
    fn real_wallet_proofs_preserve_liability_until_native_payout() {
        let cases = scenarios(None).unwrap();
        let rows: Vec<_> = cases
            .iter()
            .map(|(_, _, o)| o.state.accounting().unwrap())
            .collect();
        assert_eq!(
            rows.iter()
                .map(|a| (
                    a.reserve_principal,
                    a.private_liability,
                    a.pending_deposits,
                    a.unpaid_exits
                ))
                .collect::<Vec<_>>(),
            vec![
                (1_000_000_000, 0, 1_000_000_000, 0),
                (1_000_000_000, 1_000_000_000, 0, 0),
                (1_000_000_000, 600_000_000, 0, 400_000_000),
                (600_000_000, 600_000_000, 0, 0)
            ]
        );
        for a in rows {
            assert_eq!(a.state_covenant_rent_excluded, 100_000_000);
            assert_eq!(
                a.reserve_principal,
                a.private_liability + a.pending_deposits + a.unpaid_exits
            );
        }
        for w in cases.windows(2) {
            assert_eq!(w[0].2.state.root(), w[1].1.lane.old_state);
            assert_eq!(w[0].2.state.lane_tip, w[1].1.lane.old_tip);
            assert!(w[1].1.lane.blocks[0].blue_score - w[0].2.state.last_touch > lane::MAX_SPAN);
        }
    }
    #[test]
    fn native_payout_underpayment_diversion_recipient_and_distinct_replay() {
        let cases = scenarios(None).unwrap();
        let v = verifier();
        let s = &cases[2].2.state;
        let eid = *s.ledger.exits.keys().next().unwrap();
        let registered = app::apply(s, &cases[3].1.lane.blocks[0].txs[0], &v)
            .unwrap()
            .0;
        let r = native::campaign(&registered, eid).unwrap();
        assert_eq!(r["positiveNativeScriptsAccepted"], true);
        assert_eq!(r["permissionIssuanceReceiptVerified"], false);
        assert_eq!(r["recipientNativeOutputSompi"], 450_000_000u64);
        assert_eq!(r["nativeFeeSompi"], 100_000u64);
        assert_eq!(r["negativeControls"].as_array().unwrap().len(), 4);
    }
    #[test]
    fn canonical_v1_parser_matches_consensus_bytes_and_rejects_all_truncations() {
        let cases = scenarios(None).unwrap();
        let s = &cases[2].2.state;
        let eid = *s.ledger.exits.keys().next().unwrap();
        let t = native::issuance(s, eid);
        let wire = native::lane_tx(&t);
        let parsed = app::NativeTx::parse(&wire.rest).unwrap();
        assert_eq!(parsed.outputs[1].value, 50_000_000);
        assert_eq!(parsed.outputs[1].covenant, Some((0, s.covenant)));
        assert_eq!(
            vprogs_l1_utils::tx_id_v1(&wire.payload, &wire.rest),
            <[u8; 32]>::from(t.id())
        );
        for n in 0..wire.rest.len() {
            assert!(
                app::NativeTx::parse(&wire.rest[..n]).is_err(),
                "truncated offset {n}"
            );
        }
        let mut trailing = wire.rest.clone();
        trailing.push(0);
        assert!(app::NativeTx::parse(&trailing).is_err());
        let mut wrong = wire.rest.clone();
        wrong[2..10].copy_from_slice(&u64::MAX.to_le_bytes());
        assert!(app::NativeTx::parse(&wrong).is_err());
    }
    #[test]
    fn payout_cannot_be_disguised_as_new_deposit_or_hidden_by_missing_tags() {
        let cases = scenarios(None).unwrap();
        let v = verifier();
        let s = &cases[2].2.state;
        let eid = *s.ledger.exits.keys().next().unwrap();
        let mut grant = native::issuance(s, eid);
        grant.payload.clear();
        grant.finalize();
        let s = app::apply(s, &native::lane_tx(&grant), &v).unwrap().0;
        let (mut p, mut entries) = native::payout(&s, eid, "").unwrap();
        p.payload = chain::deposit_payload([4; 32], 1);
        native::sign_sponsor(&mut p, &mut entries).unwrap();
        assert!(native::scripts(&p, &entries).unwrap().is_ok());
        let paid = app::apply(&s, &native::lane_tx(&p), &v).unwrap().0;
        assert_eq!(paid.ledger.reserve, 600_000_000);
        assert_eq!(paid.accounting().unwrap().pending_deposits, 0);
        assert_eq!(paid.accounting().unwrap().unpaid_exits, 0);
        assert!(app::apply(&paid, &native::lane_tx(&p), &v).is_err());
    }
    #[test]
    fn immutable_permission_outpoint_and_covenant_rent_are_enforced() {
        let cases = scenarios(None).unwrap();
        let v = verifier();
        let s = &cases[2].2.state;
        let eid = *s.ledger.exits.keys().next().unwrap();
        let mut grant = native::issuance(s, eid);
        grant.outputs[0].value -= 1;
        grant.finalize();
        assert!(app::apply(s, &native::lane_tx(&grant), &v).is_err());
        let s = app::apply(s, &cases[3].1.lane.blocks[0].txs[0], &v)
            .unwrap()
            .0;
        let (mut p, _) = native::payout(&s, eid, "").unwrap();
        p.inputs[0].previous_outpoint.index += 1;
        p.finalize();
        assert!(app::apply(&s, &native::lane_tx(&p), &v).is_err());
    }
    #[test]
    fn checkpoint_state_and_last_touch_cannot_be_relabelled_for_a_gap() {
        let cases = scenarios(None).unwrap();
        let v = verifier();
        for n in 0..4 {
            let mut i = cases[1].1.clone();
            match n {
                0 => i.lane.old_state[0] ^= 1,
                1 => i.lane.old_tip[0] ^= 1,
                2 => i.lane.start.blue_score += 1,
                _ => i.lane.start_seq[0] ^= 1,
            };
            assert!(
                std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| app::execute(&i, &v)))
                    .is_err()
            );
        }
    }
}
