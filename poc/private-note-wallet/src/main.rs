use kpi_private_note_wallet::{
    circuit::WalletCircuit,
    ledger::Ledger,
    protocol::*,
    wallet::{Engine, Verifier, Wallet},
    Result,
};
use serde_json::json;
use std::{fs, path::Path, time::Instant};
fn ensure(v: bool, label: &str) -> Result<()> {
    if v {
        Ok(())
    } else {
        Err(label.into())
    }
}
fn reject_atomic(l: &mut Ledger, e: &Verifier, op: &Operation, label: &str) -> Result<()> {
    let before = l.state_hash();
    ensure(l.apply(e, op).is_err(), label)?;
    ensure(l.state_hash() == before, "atomic rejection")
}
fn record(out: &Path, name: &str, op: &Operation) -> Result<()> {
    fs::write(out.join(name), serde_json::to_vec_pretty(op).unwrap()).map_err(|e| e.to_string())?;
    fs::write(out.join(name.replace(".json", ".bin")), op.wire_bytes()?).map_err(|e| e.to_string())
}
fn demo(out: &Path, inspect: bool) -> Result<()> {
    let started = Instant::now();
    let alice = Wallet::new();
    let bob = Wallet::new();
    let deposit = hash(b"authenticated-local-native-fixture-1");
    let initial = alice.note(1_000_000_000);
    let mut tree = Tree::default();
    tree.append(initial.commitment())?;
    let (path, bits) = tree.path(0)?;
    let pay_notes = [bob.note(400_000_000), alice.note(600_000_000)];
    let mut template = Statement::new(TRANSFER, [0; 32], tree.root());
    template.nullifier = alice.nf(&initial);
    let pay_delivery = [pay_notes[0].deliver()?, pay_notes[1].deliver()?];
    for i in 0..2 {
        template.outputs[i] = pay_delivery[i].commitment;
        template.delivery[i] = hash(&pay_delivery[i].ciphertext)
    }
    let circuit = WalletCircuit {
        statement: template.clone(),
        witness: alice.witness(initial.clone(), pay_notes.clone(), path, bits),
    };
    let (constraints, satisfied) = circuit.check().map_err(|e| e.to_string())?;
    ensure(satisfied, "valid transfer circuit")?;
    if inspect {
        println!(
            "{}",
            json!({"constraints":constraints,"publicFieldElements":14,"satisfied":satisfied,"seconds":started.elapsed().as_secs_f64()})
        );
        return Ok(());
    }
    fs::create_dir(out).map_err(|e| e.to_string())?;
    let setup_start = Instant::now();
    let engine = Engine::setup(circuit)?;
    let setup_seconds = setup_start.elapsed().as_secs_f64();
    fs::write(out.join("verifying-key.bin"), engine.vk_bytes()).map_err(|e| e.to_string())?;
    let verifier = engine.verifier();
    let mut state = Ledger::new(engine.id());
    state.register_authenticated_fixture_deposit(deposit, 1_000_000_000, alice.address.owner)?;
    let pending = state.clone();
    let mut times = vec![];
    let mut credit = Statement::new(CREDIT, engine.id(), state.tree.root());
    credit.deposit = deposit;
    credit.deposit_owner = alice.address.owner;
    credit.deposit_value = 1_000_000_000;
    let t = Instant::now();
    let credit = engine.prove(
        credit,
        alice.witness(
            alice.authority_note(),
            [initial.clone(), Note::dummy()],
            [[0; 32]; DEPTH],
            [false; DEPTH],
        ),
        [initial.deliver()?, Delivery::absent()],
    )?;
    times.push(json!({"operation":"credit","seconds":t.elapsed().as_secs_f64()}));
    state.apply(&verifier, &credit)?;
    reject_atomic(&mut state, &verifier, &credit, "double credit")?;
    state.next_batch()?;
    let t = Instant::now();
    let pay = engine.prove(
        template,
        alice.witness(initial.clone(), pay_notes, path, bits),
        pay_delivery,
    )?;
    times.push(json!({"operation":"transfer","seconds":t.elapsed().as_secs_f64()}));
    state.apply(&verifier, &pay)?;
    state.next_batch()?;
    let mut second = Statement::new(TRANSFER, engine.id(), tree.root());
    second.nullifier = alice.nf(&initial);
    let second_notes = [bob.note(300_000_000), alice.note(700_000_000)];
    let ds = [second_notes[0].deliver()?, second_notes[1].deliver()?];
    let t = Instant::now();
    let competing = engine.prove(
        second,
        alice.witness(initial.clone(), second_notes, path, bits),
        ds,
    )?;
    times.push(
        json!({"operation":"competing-old-root-transfer","seconds":t.elapsed().as_secs_f64()}),
    );
    engine.verify(&competing)?;
    ensure(
        competing.statement.id() != pay.statement.id(),
        "distinct intents",
    )?;
    ensure(
        competing.statement.nullifier == pay.statement.nullifier,
        "economic nullifier",
    )?;
    reject_atomic(
        &mut state,
        &verifier,
        &competing,
        "old-root competing valid spend",
    )?;
    reject_atomic(&mut state, &verifier, &pay, "replay across batches")?;
    // Bob uses only his wallet and public accepted records/tree/current nullifiers.
    let found = bob.discover(&state.deliveries, &state.tree, &state.nullifiers);
    ensure(
        found.len() == 1 && found[0].0.value == 400_000_000,
        "independent Bob discovery",
    )?;
    let (note, index) = found[0].clone();
    let (p, b) = state.tree.path(index)?;
    let t = Instant::now();
    let exit = bob.witness(note, [Note::dummy(), Note::dummy()], p, b);
    let exit = engine.prove(
        {
            let mut s = Statement::new(EXIT, engine.id(), state.tree.root());
            s.nullifier = nullifier(&exit.secret, &exit.input);
            s.exit_destination = hash(b"Bob native script fixture");
            s.exit_value = 400_000_000;
            s
        },
        exit,
        [Delivery::absent(), Delivery::absent()],
    )?;
    times.push(json!({"operation":"bob-exit","seconds":t.elapsed().as_secs_f64()}));
    state.apply(&verifier, &exit)?;
    state.next_batch()?;
    reject_atomic(&mut state, &verifier, &exit, "duplicate exit spend")?;
    ensure(
        state.reserve == 1_000_000_000
            && state.private_liability == 600_000_000
            && state.exits[&exit.statement.id()].amount == 400_000_000,
        "pending exit remains backed",
    )?;
    let before = state.state_hash();
    ensure(
        state
            .confirm_authenticated_fixture_payout(
                exit.statement.id(),
                399_999_999,
                exit.statement.exit_destination,
                hash(b"native payout output 1"),
            )
            .is_err(),
        "underpaid exit",
    )?;
    ensure(state.state_hash() == before, "payout atomic")?;
    ensure(
        state
            .confirm_authenticated_fixture_payout(
                exit.statement.id(),
                400_000_000,
                hash(b"wrong recipient"),
                hash(b"native payout output 1"),
            )
            .is_err(),
        "diverted payout",
    )?;
    state.confirm_authenticated_fixture_payout(
        exit.statement.id(),
        400_000_000,
        exit.statement.exit_destination,
        hash(b"native payout output 1"),
    )?;
    ensure(
        state
            .confirm_authenticated_fixture_payout(
                exit.statement.id(),
                400_000_000,
                exit.statement.exit_destination,
                hash(b"native payout output 1"),
            )
            .is_err(),
        "duplicate payout",
    )?;
    let alice_found = alice.discover(&state.deliveries, &state.tree, &state.nullifiers);
    ensure(
        alice_found.len() == 1 && alice_found[0].0.value == 600_000_000,
        "Alice discovers only spendable change",
    )?;
    ensure(
        bob.discover(&state.deliveries, &state.tree, &state.nullifiers)
            .is_empty(),
        "Bob spent note excluded",
    )?;
    let mut old_root_removed = pending.clone();
    old_root_removed.apply(&verifier, &credit)?;
    old_root_removed.anchors.remove(&pay.statement.anchor);
    reject_atomic(
        &mut old_root_removed,
        &verifier,
        &pay,
        "unpermitted historical root",
    )?;
    let mut full_tree = pending.clone();
    full_tree.apply(&verifier, &credit)?;
    for i in 0..3 {
        full_tree.tree.append(hash(&[i as u8, 99]))?;
    }
    reject_atomic(
        &mut full_tree,
        &verifier,
        &pay,
        "tree-capacity atomic rejection",
    )?;
    let mut recover = Statement::new(RECOVER, engine.id(), pending.tree.root());
    recover.deposit = deposit;
    recover.deposit_owner = alice.address.owner;
    recover.deposit_value = 1_000_000_000;
    recover.exit_value = 1_000_000_000;
    recover.exit_destination = hash(b"Alice recovery script fixture");
    let t = Instant::now();
    let recover = engine.prove(
        recover,
        alice.witness(
            alice.authority_note(),
            [Note::dummy(), Note::dummy()],
            [[0; 32]; DEPTH],
            [false; DEPTH],
        ),
        [Delivery::absent(), Delivery::absent()],
    )?;
    times.push(json!({"operation":"pending-deposit-recovery","seconds":t.elapsed().as_secs_f64()}));
    reject_atomic(
        &mut state,
        &verifier,
        &recover,
        "credited deposit cannot refund",
    )?;
    let mut recovering = pending.clone();
    recovering.apply(&verifier, &recover)?;
    reject_atomic(
        &mut recovering,
        &verifier,
        &credit,
        "refunded deposit cannot credit",
    )?;
    for mode in 0..8 {
        let mut changed = pay.clone();
        match mode {
            0 => changed.statement.domain[0] ^= 1,
            1 => changed.statement.verifier[0] ^= 1,
            2 => changed.statement.exit_destination[0] ^= 1,
            3 => changed.statement.fee = 1,
            4 => changed.statement.outputs[0][0] ^= 1,
            5 => changed.deliveries[0].ciphertext[50] ^= 1,
            6 => changed.proof[32] ^= 1,
            _ => changed.proof.push(0),
        }
        ensure(engine.verify(&changed).is_err(), "mutated operation")?;
        reject_atomic(&mut state, &verifier, &changed, "mutated operation atomic")?;
    }
    ensure(
        state.reserve == 600_000_000 && state.private_liability == 600_000_000,
        "final backing",
    )?;
    for (name, op) in [
        ("credit.json", &credit),
        ("transfer.json", &pay),
        ("competing.json", &competing),
        ("bob-exit.json", &exit),
        ("recovery.json", &recover),
    ] {
        record(out, name, op)?;
    }
    let report = json!({"scope":"REAL_LOCAL_PRIVATE_WALLET_PROOFS_AND_UNPROVED_APPLICATION_KERNEL_NOT_TN10","constraints":constraints,"publicFieldElements":14,"treeDepth":DEPTH,"capacity":1<<DEPTH,"setupSeconds":setup_seconds,"walletProofs":times,"proofBytes":pay.proof.len(),"publicStatementBytes":PUBLIC_LEN,"transferWireBytes":pay.wire_bytes()?.len(),"provingKeyCompressedBytes":engine.proving_key_bytes(),"verifyingKeyBytes":engine.vk_bytes().len(),"ciphertextBytesPerOutput":185,"vkId":hex::encode(engine.id()),"economicNullifierAcrossBatchesVerified":true,"twoDistinctValidOldRootProofsSameNullifierRejectedAtomically":true,"bobIndependentDiscoveryAndExitProof":true,"pendingExitBackedUntilFixturePayout":true,"depositCreditRecoverySingleConsumption":true,"negativeProofPayloadMutationsRejected":8,"finalReservedSompi":state.reserve,"finalPrivateLiabilitySompi":state.private_liability,"witnessesSerializedOrUploaded":false,"appFeesSompi":0,"nativeFacts":"explicit authenticated test fixtures; no real native payout","provedOuterStateTransition":false,"totalSeconds":started.elapsed().as_secs_f64()});
    fs::write(
        out.join("report.json"),
        serde_json::to_vec_pretty(&report).unwrap(),
    )
    .map_err(|e| e.to_string())?;
    println!("{}", serde_json::to_string_pretty(&report).unwrap());
    Ok(())
}
fn replay(out: &Path, expected: H) -> Result<()> {
    let verification_started = Instant::now();
    let verifier = Verifier::from_bytes(
        &fs::read(out.join("verifying-key.bin")).map_err(|e| e.to_string())?,
        expected,
    )?;
    let load = |name: &str| -> Result<Operation> {
        serde_json::from_slice(&fs::read(out.join(name)).map_err(|e| e.to_string())?)
            .map_err(|e| e.to_string())
    };
    let credit = load("credit.json")?;
    let pay = load("transfer.json")?;
    let competing = load("competing.json")?;
    let exit = load("bob-exit.json")?;
    let recovery = load("recovery.json")?;
    for op in [&credit, &pay, &competing, &exit, &recovery] {
        verifier.verify(op)?;
        let wire = op.wire_bytes()?;
        let parsed = Operation::parse_wire(&wire)?;
        verifier.verify(&parsed)?;
        let mut trailing = wire.clone();
        trailing.push(0);
        ensure(
            Operation::parse_wire(&trailing).is_err(),
            "wire trailing bytes",
        )?;
    }
    let mut unknown = serde_json::to_value(&pay).unwrap();
    unknown["host_verdict"] = json!(true);
    ensure(
        serde_json::from_value::<Operation>(unknown).is_err(),
        "unknown operation field",
    )?;
    let mut state = Ledger::new(expected);
    state.register_authenticated_fixture_deposit(
        credit.statement.deposit,
        credit.statement.deposit_value,
        credit.statement.deposit_owner,
    )?;
    let pending = state.clone();
    state.apply(&verifier, &credit)?;
    reject_atomic(&mut state, &verifier, &credit, "duplicate credit")?;
    state.next_batch()?;
    let mut invalid_then_valid = pay.clone();
    invalid_then_valid.proof[0] ^= 1;
    reject_atomic(
        &mut state,
        &verifier,
        &invalid_then_valid,
        "invalid-then-valid actual proof",
    )?;
    state.apply(&verifier, &pay)?;
    state.next_batch()?;
    reject_atomic(
        &mut state,
        &verifier,
        &competing,
        "competing old-root proof",
    )?;
    reject_atomic(&mut state, &verifier, &pay, "cross-batch replay")?;
    state.apply(&verifier, &exit)?;
    ensure(
        state.reserve == 1_000_000_000 && state.private_liability == 600_000_000,
        "pending backing",
    )?;
    reject_atomic(
        &mut state,
        &verifier,
        &recovery,
        "credited deposit recovery",
    )?;
    let mut other = pending.clone();
    other.apply(&verifier, &recovery)?;
    reject_atomic(&mut other, &verifier, &credit, "recovery and credit race")?;
    let before = state.state_hash();
    ensure(
        state
            .confirm_authenticated_fixture_payout(
                exit.statement.id(),
                399_999_999,
                exit.statement.exit_destination,
                hash(b"native-output"),
            )
            .is_err(),
        "underpayment",
    )?;
    ensure(before == state.state_hash(), "underpayment atomic")?;
    ensure(
        state
            .confirm_authenticated_fixture_payout(
                exit.statement.id(),
                400_000_000,
                hash(b"diverted"),
                hash(b"native-output"),
            )
            .is_err(),
        "diversion",
    )?;
    state.confirm_authenticated_fixture_payout(
        exit.statement.id(),
        400_000_000,
        exit.statement.exit_destination,
        hash(b"native-output"),
    )?;
    ensure(
        state.reserve == 600_000_000 && state.private_liability == 600_000_000,
        "settled fixture backing",
    )?;
    let mut wrong = Ledger::new(hash(b"different pinned VK"));
    let before = wrong.state_hash();
    ensure(
        wrong.apply(&verifier, &credit).is_err(),
        "wrong state verifier",
    )?;
    ensure(before == wrong.state_hash(), "wrong verifier atomic")?;
    let mut mutated_vk = expected;
    mutated_vk[0] ^= 1;
    ensure(
        Verifier::from_bytes(
            &fs::read(out.join("verifying-key.bin")).unwrap(),
            mutated_vk,
        )
        .is_err(),
        "wrong expected VK",
    )?;
    for mode in 0..8 {
        let mut changed = pay.clone();
        match mode {
            0 => changed.statement.domain[0] ^= 1,
            1 => changed.statement.verifier[0] ^= 1,
            2 => changed.statement.exit_destination[0] ^= 1,
            3 => changed.statement.fee = 1,
            4 => changed.statement.outputs[0][0] ^= 1,
            5 => changed.deliveries[0].ciphertext[50] ^= 1,
            6 => changed.proof[32] ^= 1,
            _ => changed.proof.push(0),
        }
        ensure(
            verifier.verify(&changed).is_err(),
            "mutated persisted operation",
        )?;
    }
    // These pass framing/shape/digest checks and must fail the Groth16 equation.
    let mut changed_exit = exit.clone();
    changed_exit.statement.exit_destination = hash(b"different nonzero Bob payout script");
    ensure(
        changed_exit.statement.exit_destination != exit.statement.exit_destination
            && changed_exit.statement.exit_destination != [0; 32],
        "different nonzero exit destination",
    )?;
    ensure(
        verifier.verify(&changed_exit) == Err("invalid proof".into()),
        "real exit destination proof binding",
    )?;
    let mut changed_delivery = pay.clone();
    changed_delivery.deliveries[0].ciphertext[50] ^= 1;
    changed_delivery.statement.delivery[0] = hash(&changed_delivery.deliveries[0].ciphertext);
    ensure(
        verifier.verify(&changed_delivery) == Err("invalid proof".into()),
        "rehashed ciphertext proof binding",
    )?;
    {
        use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
        let original =
            ark_groth16::Proof::<ark_bn254::Bn254>::deserialize_compressed(pay.proof.as_slice())
                .map_err(|e| e.to_string())?;
        let mut bad = original.clone();
        bad.c = -bad.c;
        let mut operation = pay.clone();
        operation.proof.clear();
        bad.serialize_compressed(&mut operation.proof).unwrap();
        ensure(
            verifier.verify(&operation).is_err(),
            "canonical subgroup point but false pairing",
        )?;
        let wrong_group = (0u64..100)
            .find_map(|n| {
                let x = ark_bn254::Fq2::new(ark_bn254::Fq::from(n), ark_bn254::Fq::from(1u64));
                ark_bn254::G2Affine::get_point_from_x_unchecked(x, false)
                    .filter(|p| !p.is_in_correct_subgroup_assuming_on_curve())
            })
            .ok_or("subgroup negative fixture")?;
        let mut bad = original.clone();
        bad.b = wrong_group;
        operation.proof.clear();
        bad.serialize_compressed(&mut operation.proof).unwrap();
        ensure(verifier.verify(&operation).is_err(), "wrong subgroup")?;
        let mut bad = original;
        bad.a = ark_bn254::G1Affine::identity();
        operation.proof.clear();
        bad.serialize_compressed(&mut operation.proof).unwrap();
        ensure(verifier.verify(&operation).is_err(), "identity proof")?;
    }
    let report = json!({"separateProcess":true,"verificationSeconds":verification_started.elapsed().as_secs_f64(),"actualProofsVerified":5,"expectedVkId":hex::encode(expected),"stateVerifierPinEnforced":true,"wrongExpectedVkRejected":true,"economicNullifiersAcrossBatches":true,"atomicRejections":true,"depositCreditRecoveryRaceRejected":true,"mutationsRejected":8,"exitDestinationCryptographicBinding":true,"rehashedCiphertextCryptographicBinding":true,"canonicalFalsePairingRejected":true,"wrongSubgroupRejected":true,"identityPointRejected":true,"invalidThenValidPreservesState":true,"canonicalWireRoundTrips":5,"unknownFieldsAndTrailingBytesRejected":true,"exactFixturePayoutAndBacking":true,"scope":"REAL_WALLET_PROOFS_LOCAL_KERNEL_NOT_NATIVE_SETTLEMENT"});
    fs::write(
        out.join("separate-verification.json"),
        serde_json::to_vec_pretty(&report).unwrap(),
    )
    .map_err(|e| e.to_string())?;
    println!("{}", report);
    Ok(())
}
fn main() {
    let args = std::env::args().collect::<Vec<_>>();
    let inspect = args.get(1).map(|s| s == "inspect").unwrap_or(false);
    let path = args
        .get(2)
        .map(Path::new)
        .unwrap_or(Path::new("private-note-demo-output"));
    let result = if args.get(1).map(|s| s == "verify").unwrap_or(false) {
        args.get(3)
            .ok_or_else(|| "expected VK id required".to_owned())
            .and_then(|s| hex::decode(s).map_err(|e| e.to_string()))
            .and_then(|b| b.try_into().map_err(|_| "VK id length".into()))
            .and_then(|id| replay(path, id))
    } else {
        demo(path, inspect)
    };
    if let Err(e) = result {
        eprintln!("{e}");
        std::process::exit(1)
    }
}
