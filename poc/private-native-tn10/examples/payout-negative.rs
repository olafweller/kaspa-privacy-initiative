//! Re-sign three precise native payout controls using the operator's own sponsor.
//! No networking; never emits a candidate that unexpectedly passes every script.
use kaspa_consensus_core::{
    config::params::TESTNET_PARAMS,
    hashing::{sighash::SigHashReusedValuesUnsync, sighash_type::SIG_HASH_ALL},
    sign::sign_input,
    tx::*,
};
use kaspa_rpc_core::{RpcTransaction, RpcUtxosByAddressesEntry};
use kaspa_txscript::{
    caches::Cache, covenants::CovenantsContext, engine_context::EngineContext, EngineFlags,
    TxScriptEngine,
};
use serde_json::{json, Value};
use std::{fs, os::unix::fs::PermissionsExt, str::FromStr};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a: Vec<_> = std::env::args().collect();
    let source: Value = serde_json::from_slice(&fs::read(&a[1])?)?;
    let mut tx: Transaction =
        serde_json::from_value::<RpcTransaction>(source["record"]["transaction"].clone())?
            .try_into()?;
    assert_eq!(source["record"]["kind"], "payout");
    assert_eq!(tx.inputs.len(), 3);
    assert_eq!(tx.outputs.len(), 3);
    assert_eq!(tx.outputs[0].value, 450_000_000);
    assert_eq!(tx.outputs[1].value, 600_000_000);
    let es: Vec<RpcUtxosByAddressesEntry> = serde_json::from_value(source["entries"].clone())?;
    let entries: Vec<UtxoEntry> = es.into_iter().map(|e| e.utxo_entry.into()).collect();
    assert_eq!(entries.len(), 3);
    assert_eq!(fs::metadata(&a[2])?.permissions().mode() & 0o777, 0o600);
    let secret = secp256k1::SecretKey::from_str(fs::read_to_string(&a[2])?.trim())?;
    let key = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &secret);
    let address = kaspa_addresses::Address::new(
        kaspa_addresses::Prefix::Testnet,
        kaspa_addresses::Version::PubKey,
        &key.x_only_public_key().0.serialize(),
    );
    assert_eq!(
        entries[2].script_public_key,
        kaspa_txscript::pay_to_address_script(&address)
    );
    match a[3].as_str() {
        "underpay" => {
            tx.outputs[0].value -= 1;
            tx.outputs[2].value += 1;
        }
        "reserve" => {
            tx.outputs[1].value -= 1;
            tx.outputs[2].value += 1;
        }
        "recipient" => {
            tx.outputs[0].script_public_key = kaspa_txscript::pay_to_address_script(&address);
        }
        _ => return Err("fixed negative only".into()),
    }
    vprogs_l1_wallet::build::commit_storage_mass(&TESTNET_PARAMS, &tx, &entries);
    tx.inputs[2].signature_script = sign_input(
        &PopulatedTransaction::new(&tx, entries.clone()),
        2,
        &key.secret_bytes(),
        SIG_HASH_ALL,
    );
    tx.finalize();
    let pop = PopulatedTransaction::new(&tx, entries.clone());
    let cache = Cache::new(10);
    let cov = CovenantsContext::from_tx(&pop)?;
    let reused = SigHashReusedValuesUnsync::new();
    let mut checks = vec![];
    for i in 0..3 {
        let mut vm = TxScriptEngine::from_transaction_input(
            &pop,
            &tx.inputs[i],
            i,
            &entries[i],
            EngineContext::new(&cache)
                .with_reused(&reused)
                .with_covenants_ctx(&cov),
            EngineFlags::default(),
        );
        let result = vm.execute();
        checks.push(match result {
            Ok(()) => json!({"input":i,"accepted":true}),
            Err(e) => json!({"input":i,"accepted":false,"error":format!("{e:?}")}),
        });
    }
    assert_eq!(
        checks[2]["accepted"], true,
        "sponsor signature must remain valid"
    );
    assert!(
        checks[0]["accepted"] == false || checks[1]["accepted"] == false,
        "negative must fail native enforcement"
    );
    println!(
        "{}",
        json!({"record":{"kind":"payout-negative","transactionId":tx.id().to_string(),"transaction":RpcTransaction::from(&tx)},"entries":source["entries"],"negative":a[3],"expectedNativeRejection":true,"localInputChecks":checks})
    );
    Ok(())
}
