//! Read-only validation of the one standard funding transaction; no keys or RPC.
use kaspa_consensus_core::{config::params::TESTNET_PARAMS, mass::MassCalculator, tx::*};
use kaspa_rpc_core::{RpcTransaction, RpcUtxosByAddressesEntry};
use kaspa_txscript::{
    caches::Cache, covenants::CovenantsContext, engine_context::EngineContext, EngineFlags,
    TxScriptEngine,
};
use serde_json::{json, Value};
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let a: Vec<_> = std::env::args().collect();
    let r: Value = serde_json::from_slice(&std::fs::read(&a[1])?)?;
    let rpc: RpcTransaction = serde_json::from_value(r["transaction"].clone())?;
    let tx: Transaction = rpc.try_into()?;
    let es: Vec<RpcUtxosByAddressesEntry> = serde_json::from_value(r["entries"].clone())?;
    assert_eq!(tx.version, 0);
    assert_eq!(tx.subnetwork_id.as_bytes(), &[0u8; 20]);
    assert!(tx.payload.is_empty());
    assert_eq!(es.len(), 1);
    assert_eq!(tx.inputs.len(), 1);
    assert_eq!(tx.outputs.len(), 2);
    assert_eq!(
        tx.inputs[0].previous_outpoint,
        es[0].outpoint.clone().into()
    );
    assert!(!es[0].utxo_entry.is_coinbase);
    assert!(es[0].utxo_entry.covenant_id.is_none());
    let entries: Vec<UtxoEntry> = es.into_iter().map(|e| e.utxo_entry.into()).collect();
    let pop = PopulatedTransaction::new(&tx, entries.clone());
    let cache = Cache::new(10);
    let cov = CovenantsContext::from_tx(&pop)?;
    let reused = kaspa_consensus_core::hashing::sighash::SigHashReusedValuesUnsync::new();
    let mut engine = TxScriptEngine::from_transaction_input(
        &pop,
        &tx.inputs[0],
        0,
        &entries[0],
        EngineContext::new(&cache)
            .with_reused(&reused)
            .with_covenants_ctx(&cov),
        EngineFlags::default(),
    );
    engine.execute()?;
    let calc = MassCalculator::new_with_consensus_params(&TESTNET_PARAMS);
    let non = calc.calc_non_contextual_masses(&tx);
    let ctx = calc.calc_contextual_masses(&pop).ok_or("mass")?;
    assert_eq!(ctx.storage_mass, tx.storage_mass());
    let limits = TESTNET_PARAMS.block_mass_limits;
    assert!(
        non.compute_mass <= limits.compute
            && non.transient_mass <= limits.transient
            && ctx.storage_mass <= limits.storage
    );
    let mass = kaspa_consensus_core::mass::Mass::new(non, ctx).normalized_max(&limits.cofactors());
    let fee = entries[0].amount - tx.outputs.iter().map(|o| o.value).sum::<u64>();
    assert!(fee >= 100 * mass && fee <= 10_000_000);
    println!(
        "{}",
        json!({"transactionId":tx.id().to_string(),"allInputScriptsExecuted":true,"computeMass":non.compute_mass,"transientMass":non.transient_mass,"storageMass":ctx.storage_mass,"priorityMass":mass,"feeSompi":fee,"networkAcceptance":false})
    );
    Ok(())
}
