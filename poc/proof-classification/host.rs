//! Local fixtures only: no RPC, signing key, funded UTXO or broadcast path.
use super::*;
use kaspa_consensus_core::{
    config::params::TESTNET_PARAMS,
    hashing::tx::transaction_v1_rest_preimage,
    mass::{transaction_estimated_serialized_size, MassCalculator},
    subnets::SubnetworkId,
    tx::*,
};
#[path = "protocol.rs"]
#[allow(dead_code)]
mod protocol;
const LANE: [u8; 20] = {
    let mut b = [0; 20];
    b[1] = 0x35;
    b[2] = 0x36;
    b[3] = 0x37;
    b
};
fn wire<T: serde::Serialize>(v: &T) -> Result<Vec<u8>> {
    Ok(risc0_zkvm::serde::to_vec(v)?
        .into_iter()
        .flat_map(u32::to_le_bytes)
        .collect())
}
fn tx(op: Vec<u8>, i: u32) -> Transaction {
    Transaction::new(
        1,
        vec![TransactionInput::new_with_compute_budget(
            TransactionOutpoint::new(Hash::from_bytes([0x36; 32]), i),
            vec![0; 65],
            0,
            100,
        )],
        vec![TransactionOutput::new(
            100_000_000,
            ScriptPublicKey::new(0, [&[0x20][..], &[0x37; 32], &[0xac]].concat().into()),
        )],
        0,
        SubnetworkId::from_bytes(LANE),
        0,
        op,
    )
}
fn batch(ops: &[Vec<u8>], expected: Option<[u8; 32]>) -> (Vec<u8>, [u8; 32]) {
    let mut records = vec![];
    let mut root = [0; 32];
    for (i, op) in ops.iter().enumerate() {
        let t = tx(op.clone(), i as u32);
        let rest = transaction_v1_rest_preimage(&t);
        let id = vprogs_l1_utils::tx_id_v1(op, &rest);
        assert_eq!(id, <[u8; 32]>::from(t.id()));
        root = protocol::order_step(root, i as u32, id);
        protocol::blob(&mut records, &rest);
        protocol::blob(&mut records, op);
    }
    let mut b = expected.unwrap_or(root).to_vec();
    b.extend(1_000_000_000u64.to_le_bytes());
    b.extend((ops.len() as u32).to_le_bytes());
    b.extend(records);
    (b, root)
}
fn altered_proof(bytes: &[u8]) -> Result<Vec<u8>> {
    let mut r: Receipt = bincode::deserialize(bytes)?;
    let risc0_zkvm::InnerReceipt::Succinct(s) = &mut r.inner else {
        return Err("succinct required".into());
    };
    *s.seal.last_mut().ok_or("empty seal")? ^= 1;
    Ok(bincode::serialize(&r)?)
}
fn prepare(programs: &Path, out: &Path) -> Result<()> {
    fs::create_dir(out)?;
    let wp = fs::read(programs.join("wallet.program.bin"))?;
    let image: [u8; 32] = compute_image_id(&wp)?.into();
    let mut ops = vec![];
    for (label, nonce, pay) in [
        ("wallet-a", 1, 400_000_000u64),
        ("wallet-c", 3, 100_000_000),
    ] {
        let values = [1_000_000_000, pay, 1_000_000_000 - pay, 0];
        let intent = protocol::intent(image, nonce, [nonce; 32], values);
        let input = protocol::WalletInput {
            intent: intent.clone(),
            secret: [nonce; 32],
            values,
        };
        save(
            out,
            &format!("{label}-input.json"),
            &serde_json::to_vec_pretty(&input)?,
        )?;
        let receipt = prove(out, label, &wire(&input)?, &wp, &[], false, false)?;
        assert_eq!(receipt.journal.bytes, protocol::journal(&intent));
        let bytes = bincode::serialize(&receipt)?;
        let op = protocol::operation(&intent, &bytes);
        assert_eq!(protocol::classify(&op, image), 0);
        save(out, &format!("{label}-operation.bin"), &op)?;
        ops.push(op);
    }
    finish_fixture(&ops, out, image)
}
fn finish_fixture(ops: &[Vec<u8>], out: &Path, image: [u8; 32]) -> Result<()> {
    let a = ops[0].clone();
    let c = ops[1].clone();
    // Keep the authentic intent, corrupt the submitted seal. This is not missing
    // executor material. The bad operation itself is in the committed sequence.
    let bad = protocol::operation(
        &a[..protocol::INTENT_LEN],
        &altered_proof(&a[protocol::INTENT_LEN + 4..])?,
    );
    assert_eq!(protocol::classify(&bad, image), 3);
    let (input, root) = batch(&[a.clone(), bad.clone(), c.clone()], None);
    save(out, "valid-invalid-valid.bin", &input)?;
    let mut invalids = vec![];
    for (name, proof) in [
        ("empty", vec![]),
        (
            "truncated",
            a[protocol::INTENT_LEN + 4..protocol::INTENT_LEN + 44].to_vec(),
        ),
        ("fake-tag", 3u32.to_le_bytes().to_vec()),
        (
            "huge-seal-length",
            [&1u32.to_le_bytes()[..], &u64::MAX.to_le_bytes()].concat(),
        ),
        ("all-zero", vec![0; 1024]),
    ] {
        let op = protocol::operation(&a[..protocol::INTENT_LEN], &proof);
        let code = protocol::classify(&op, image);
        assert_ne!(code, 0);
        save(
            out,
            &format!("{name}.bin"),
            &batch(&[a.clone(), op, c.clone()], None).0,
        )?;
        invalids.push(json!({"case":name,"outcome":code}));
    }
    // A proof for another intent, network, pool, receiving record or image must fail.
    let mut binding = vec![];
    for offset in [
        8, 10, 42, 74, 106, 138, 170, 202, 210, 218, 250, 282, 314, 442,
    ] {
        let mut op = a.clone();
        op[offset] ^= 1;
        let code = protocol::classify(&op, image);
        assert_ne!(code, 0);
        binding.push(json!({"intentOffset":offset,"outcome":code}));
    }
    let mut trailing = a.clone();
    trailing.push(0);
    assert_ne!(protocol::classify(&trailing, image), 0);
    let mut huge = a.clone();
    huge[protocol::INTENT_LEN..protocol::INTENT_LEN + 4].copy_from_slice(&u32::MAX.to_le_bytes());
    assert_ne!(protocol::classify(&huge, image), 0);
    save(
        out,
        "replay.bin",
        &batch(&[a.clone(), a.clone(), c.clone()], None).0,
    )?;
    // Same verifier-checked endpoint, different supplied bytes: authentication abort.
    save(
        out,
        "withheld.bin",
        &batch(
            &[
                a.clone(),
                protocol::operation(&a[..protocol::INTENT_LEN], &[]),
                c.clone(),
            ],
            Some(root),
        )
        .0,
    )?;
    save(
        out,
        "substituted.bin",
        &batch(&[a.clone(), a.clone(), c.clone()], Some(root)).0,
    )?;
    save(
        out,
        "omitted.bin",
        &batch(&[a.clone(), c.clone()], Some(root)).0,
    )?;
    save(
        out,
        "reordered.bin",
        &batch(&[c.clone(), bad.clone(), a.clone()], Some(root)).0,
    )?;
    let mut verdict = input.clone();
    verdict.push(1);
    save(out, "host-verdict.bin", &verdict)?;
    let calc = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS);
    let mut sizes = vec![];
    for (i, op) in [a, bad, c].into_iter().enumerate() {
        let t = tx(op.clone(), i as u32);
        let m = calc.calc_non_contextual_masses(&t);
        sizes.push(json!({"index":i,"intentBytes":protocol::INTENT_LEN,"operationBytes":op.len(),
            "receiptBytes":op.len()-protocol::INTENT_LEN-4,"nativeEstimatedBytes":transaction_estimated_serialized_size(&t),
            "computeMass":m.compute_mass,"transientMass":m.transient_mass,"nativeId":t.id().to_string()}));
    }
    save(
        out,
        "fixture.json",
        &serde_json::to_vec_pretty(&json!({
            "scope":"LOCAL_UNFUNDED_SYNTHETIC_NATIVE_ORDER_NOT_NEW_TN10_ACCEPTANCE",
            "walletImage":hex::encode(image),"orderedRoot":hex::encode(root),"operations":sizes,
            "malformedProofs":invalids,"intentBindingMutations":binding,
            "nativeLimits":{"compute":TESTNET_PARAMS.block_mass_limits.compute,"transient":TESTNET_PARAMS.block_mass_limits.transient},
            "delivery":"two bound opaque synthetic 128-byte records, not actual shielded note encryption",
            "storageMass":"not measured: dummy nonexistent UTXO has no authenticated amount/age context",
        }))?,
    )?;
    Ok(())
}
fn execute(program: &[u8], input: &[u8]) -> Result<risc0_zkvm::SessionInfo> {
    let mut b = ExecutorEnv::builder();
    b.write_slice(&[u32::try_from(input.len())?])
        .write_slice(input)
        .segment_limit_po2(20)
        .session_limit(Some(4 * 1024 * 1024 * 1024));
    Ok(default_executor().execute(b.build()?, program)?)
}
fn check_fixture(fixture: &Path, out: &Path) -> Result<()> {
    fs::create_dir(out)?;
    let a = fs::read(fixture.join("wallet-a-operation.bin"))?;
    let c = fs::read(fixture.join("wallet-c-operation.bin"))?;
    let image: [u8; 32] = a[106..138].try_into()?;
    let body = &a[..protocol::INTENT_LEN];
    let bytes = &a[protocol::INTENT_LEN + 4..];
    let original: Receipt = bincode::deserialize(bytes)?;
    assert_eq!(protocol::classify(&a, image), 0);
    // Isolate cryptographic invalidity from replay: C is still unconsumed at
    // this middle operation, and its genuine proof must succeed afterwards.
    let bad_c = protocol::operation(
        &c[..protocol::INTENT_LEN],
        &altered_proof(&c[protocol::INTENT_LEN + 4..])?,
    );
    assert_eq!(protocol::classify(&bad_c, image), 3);
    save(
        out,
        "invalid-unspent.bin",
        &batch(&[a.clone(), bad_c, c.clone()], None).0,
    )?;
    let baseline: Vec<Vec<u8>> = [a.clone(), a.clone(), c.clone()]
        .into_iter()
        .map(|mut op| {
            op[protocol::INTENT_LEN + 4..protocol::INTENT_LEN + 8]
                .copy_from_slice(&3u32.to_le_bytes());
            op
        })
        .collect();
    save(out, "encoding-baseline.bin", &batch(&baseline, None).0)?;
    let mut results = vec![];
    for i in 0..64 {
        let mut r = original.clone();
        let risc0_zkvm::InnerReceipt::Succinct(s) = &mut r.inner else {
            unreachable!()
        };
        let index = i * (s.seal.len() - 1) / 63;
        s.seal[index] = (s.seal[index] + 1) % 2_013_265_921;
        let code = protocol::classify(&protocol::operation(body, &bincode::serialize(&r)?), image);
        assert_ne!(code, 0);
        results.push(json!({"sealWord":index,"outcome":code}));
    }
    for mode in [
        "field",
        "path",
        "index",
        "exponent",
        "truncated-seal",
        "wrong-journal",
    ] {
        let mut r = original.clone();
        let risc0_zkvm::InnerReceipt::Succinct(s) = &mut r.inner else {
            unreachable!()
        };
        match mode {
            "field" => s.seal[40] = u32::MAX,
            "path" => s.control_inclusion_proof.digests[0] = [u32::MAX; 8].into(),
            "index" => s.control_inclusion_proof.index = 256,
            "exponent" => s.seal[32] = 25,
            "truncated-seal" => s.seal.truncate(32),
            "wrong-journal" => r.journal.bytes[0] ^= 1,
            _ => unreachable!(),
        }
        let op = protocol::operation(body, &bincode::serialize(&r)?);
        let code = protocol::classify(&op, image);
        assert_eq!(code, 2);
        save(
            out,
            &format!("{mode}.bin"),
            &batch(&[a.clone(), op, c.clone()], None).0,
        )?;
        results.push(json!({"case":mode,"outcome":code}));
    }
    let oversized = protocol::operation(body, &vec![0; protocol::MAX_PROOF + 1]);
    assert_eq!(protocol::classify(&oversized, image), 2);
    save(
        out,
        "oversized-proof.bin",
        &batch(&[a.clone(), oversized, c.clone()], None).0,
    )?;
    for end in [0, 1, 4, 8, 12, 100, bytes.len() / 2, bytes.len() - 1] {
        assert_ne!(
            protocol::classify(&protocol::operation(body, &bytes[..end]), image),
            0
        );
    }
    save(
        out,
        "checks.json",
        &serde_json::to_vec_pretty(&json!({"scope":"HOST_TESTS_NOT_GUEST_PROOFS",
        "realReceiptMutations":results,"receiptPrefixTruncations":8,"oversizedProofRejected":true}))?,
    )
}
pub(crate) fn expected_authentication_abort(label: &str, message: &str) -> bool {
    match label {
        "host-verdict" => message == "Guest panicked: assertion failed: r.0.is_empty()",
        "withheld" | "substituted" | "omitted" | "reordered" => {
            message.starts_with("Guest panicked: assertion `left == right` failed: withheld/substituted/reordered published operation\n  left: [")
                && message.contains("\n right: [")
        }
        _ => false,
    }
}
#[cfg(test)]
mod abort_tests {
    use super::expected_authentication_abort;
    #[test]
    fn unrelated_runtime_failures_cannot_pass_authentication_controls() {
        let intended = "Guest panicked: assertion `left == right` failed: withheld/substituted/reordered published operation\n  left: [1]\n right: [2]";
        for label in ["withheld", "substituted", "omitted", "reordered"] {
            assert!(expected_authentication_abort(label, intended));
            for wrong in [
                "Session limit exceeded: 32000000 >= 32000000",
                "out of memory",
                "IPC connection failed",
                "Guest panicked: assertion failed: another check",
                "",
            ] {
                assert!(!expected_authentication_abort(label, wrong));
            }
        }
        let trailing = "Guest panicked: assertion failed: r.0.is_empty()";
        assert!(expected_authentication_abort("host-verdict", trailing));
        assert!(!expected_authentication_abort("host-verdict", intended));
        assert!(!expected_authentication_abort("withheld", trailing));
        assert!(!expected_authentication_abort(
            "valid-invalid-valid",
            intended
        ));
    }
}
fn profile(programs: &Path, fixture: &Path, out: &Path, label: &str) -> Result<()> {
    fs::create_dir(out)?;
    let program = fs::read(programs.join("classifier.program.bin"))?;
    let input = fs::read(fixture.join(format!("{label}.bin")))?;
    let start = Instant::now();
    let result = execute(&program, &input);
    let mut report = json!({"scope":"EXECUTION_ONLY_NOT_PROOF","case":label,"seconds":start.elapsed().as_secs_f64()});
    match result {
        Ok(s) => {
            let bytes = &s.journal.bytes;
            assert_eq!(&bytes[..32], &input[..32]);
            let codes: Vec<u8> = bytes[44..].chunks_exact(41).map(|r| r[32]).collect();
            let balances: Vec<u64> = bytes[44..]
                .chunks_exact(41)
                .map(|r| u64::from_le_bytes(r[33..41].try_into().unwrap()))
                .collect();
            let expected = if ["valid-invalid-valid", "invalid-unspent"].contains(&label) {
                vec![0, 3, 0]
            } else if label == "replay" {
                vec![0, 4, 0]
            } else if label == "encoding-baseline" {
                vec![2, 2, 2]
            } else {
                vec![0, 2, 0]
            };
            assert_eq!(codes, expected);
            assert_eq!(
                balances,
                if label == "encoding-baseline" {
                    vec![1_000_000_000; 3]
                } else {
                    vec![600_000_000, 600_000_000, 500_000_000]
                }
            );
            report["userCycles"] = json!(s.cycles());
            report["segments"] = json!(s.segments.iter().map(|s| s.po2).collect::<Vec<_>>());
            report["outcomes"] = json!(codes);
            report["balances"] = json!(balances);
            save(out, "journal.bin", bytes)?;
        }
        Err(e) => {
            let message = format!("{e:#}");
            if !expected_authentication_abort(label, &message) {
                return Err(e);
            }
            report["authenticationAbort"] = json!(message);
            report["expectedAuthenticationFailureConfirmed"] = json!(true);
        }
    }
    save(out, "report.json", &serde_json::to_vec_pretty(&report)?)
}
pub(super) fn run(a: &[String]) -> Result<()> {
    if a.len() < 3 {
        return Err("classifier prepare|profile|prove ...".into());
    }
    match a[2].as_str() {
        "reuse" if a.len()==6 => {
            let image: [u8;32] = compute_image_id(&fs::read(Path::new(&a[3]).join("wallet.program.bin"))?)?.into();
            let source=Path::new(&a[4]);let out=Path::new(&a[5]);fs::create_dir(out)?;
            for entry in fs::read_dir(source)? {
                let entry=entry?;
                if entry.file_name().to_string_lossy().starts_with("wallet-") { fs::copy(entry.path(),out.join(entry.file_name()))?; }
            }
            let ops=[fs::read(out.join("wallet-a-operation.bin"))?,fs::read(out.join("wallet-c-operation.bin"))?];
            for op in &ops { assert_eq!(protocol::classify(op,image),0); }
            finish_fixture(&ops,out,image)
        }
        "check" if a.len()==5 => check_fixture(Path::new(&a[3]),Path::new(&a[4])),
        "verify" if a.len()==6 => {
            let programs=Path::new(&a[3]);let fixture=Path::new(&a[4]);let proofs=Path::new(&a[5]);
            let expected: Value=serde_json::from_slice(&fs::read(fixture.join("fixture.json"))?)?;
            let receipt: Receipt=bincode::deserialize(&fs::read(proofs.join("classifier-receipt.bin"))?)?;
            receipt.verify_with_context(&risc0_zkvm::VerifierContext::default().with_dev_mode(false),
                compute_image_id(&fs::read(programs.join("classifier.program.bin"))?)?)?;
            let mut journal=hex::decode(expected["orderedRoot"].as_str().ok_or("root")?)?;
            journal.extend(1_000_000_000u64.to_le_bytes());journal.extend(3u32.to_le_bytes());
            for (i,(code,balance)) in [(0,600_000_000u64),(3,600_000_000),(0,500_000_000)].into_iter().enumerate() {
                journal.extend(hex::decode(expected["operations"][i]["nativeId"].as_str().ok_or("native ID")?)?);
                journal.push(code);journal.extend(balance.to_le_bytes());
            }
            assert_eq!(receipt.journal.bytes,journal);
            let mut changed=receipt.clone();changed.journal.bytes[76]^=1;
            assert!(changed.verify(compute_image_id(&fs::read(programs.join("classifier.program.bin"))?)?).is_err());
            println!("{}",json!({"scope":"SDK_REVERIFIED_LOCAL_PROXY_PROOF_NOT_L1_ACCEPTANCE",
                "expectedOrderedRoot":expected["orderedRoot"],"outcomes":[0,3,0],"balances":[600_000_000,600_000_000,500_000_000],
                "tamperedJournalRejected":true,"developmentMode":false}));
            Ok(())
        }
        "inspect" if a.len() == 4 || a.len() == 5 => {
            let receipt: Receipt = bincode::deserialize(&fs::read(&a[3])?)?;
            let inner = receipt.inner.succinct()?;
            println!("{}", json!({"hashfn":inner.hashfn,"pathDepth":inner.control_inclusion_proof.digests.len(),
                "pathIndex":inner.control_inclusion_proof.index,"po2Raw":inner.seal[32],
                "sealWords":inner.seal.len(),"journalBytes":receipt.journal.bytes.len()}));
            if a.len() == 5 {
                let input: protocol::WalletInput = serde_json::from_slice(&fs::read(&a[4])?)?;
                let image: [u8;32] = input.intent[106..138].try_into().unwrap();
                let op = protocol::operation(&input.intent, &fs::read(&a[3])?);
                println!("{}",json!({"classification":protocol::classify(&op,image),
                    "sdkVerify":format!("{:?}", receipt.verify_with_context(&risc0_zkvm::VerifierContext::default().with_dev_mode(false), image)),
                    "journalMatches": receipt.journal.bytes == protocol::journal(&input.intent),
                    "sealReduced": inner.seal.iter().all(|w|*w<2_013_265_921)}));
            }
            Ok(())
        }
        "prepare" if a.len()==5 => prepare(Path::new(&a[3]),Path::new(&a[4])),
        "profile" if a.len()==7 => profile(Path::new(&a[3]),Path::new(&a[4]),Path::new(&a[5]),&a[6]),
        "prove" if a.len()==6 => {
            let p=Path::new(&a[3]); let fixture=Path::new(&a[4]);let out=Path::new(&a[5]);fs::create_dir(out)?;
            let program=fs::read(p.join("classifier.program.bin"))?;
            let input=fs::read(fixture.join("valid-invalid-valid.bin"))?;
            let receipt=prove(out,"classifier",&input,&program,&[],true,false)?;
            let claim=receipt.claim()?;
            save(out,"claim.txt",format!("{claim:#?}").as_bytes())?;
            assert_eq!(&receipt.journal.bytes[..32],&input[..32]);
            assert_eq!(receipt.journal.bytes[44..].chunks_exact(41).map(|r|r[32]).collect::<Vec<_>>(),[0,3,0]);
            Ok(())
        },
        _ => Err("classifier prepare PROGRAMS NEW_DIR | profile PROGRAMS FIXTURE NEW_DIR CASE | prove PROGRAMS FIXTURE NEW_DIR".into())
    }
}
