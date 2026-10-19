//! One-way, zero-liability initialization. The genesis covenant ID hashes the
//! initial script. That script therefore cannot contain State::genesis(ID).root.
//! Instead it derives that root from OpInputCovenantId when first spent. It can
//! only replace its 1 KAS rent with the reviewed lane-restricted state script.
use super::*;
use kaspa_txscript::{opcodes::codes::*, script_builder::ScriptBuilder};

pub fn redeem(tip: H, touch: u64) -> Result<Vec<u8>> {
    let empty = State::genesis([0; 32], verifier().id(), tip, touch);
    let serialized = bincode::serialize(&empty)?;
    require(serialized[..32] == [0; 32], "genesis serialization layout")?;
    let target = state_script(&empty);
    // The reviewed state script's root is its second 32-byte prefix item.
    require(
        target[33] == OpData32 && target[34..66] == empty.root(),
        "state prefix",
    )?;
    let p2sh = kaspa_txscript::standard::pay_to_script_hash_script(&[]);
    let wire = [p2sh.version().to_le_bytes().as_slice(), p2sh.script()].concat();
    require(wire.len() == 37, "P2SH layout")?;
    let mut b = ScriptBuilder::new();
    b.add_op(OpTxSubnetId)?
        .add_data(&chain::LANE)?
        .add_op(OpEqualVerify)?
        .add_op(OpTxVersion)?
        .add_i64(1)?
        .add_op(OpEqualVerify)?
        .add_op(OpTxInputIndex)?
        .add_i64(0)?
        .add_op(OpEqualVerify)?
        .add_op(OpTxInputCount)?
        .add_i64(2)?
        .add_op(OpEqualVerify)?
        .add_op(OpTxOutputCount)?
        .add_i64(2)?
        .add_op(OpEqualVerify)?;
    // Exactly one continuation bound to our covenant, at output 0. Sponsor is
    // unbound; neither rent nor protocol assets may subsidize its fees.
    b.add_i64(0)?
        .add_op(OpInputCovenantId)?
        .add_op(OpDup)?
        .add_op(OpCovOutputCount)?
        .add_i64(1)?
        .add_op(OpEqualVerify)?
        .add_i64(0)?
        .add_op(OpCovOutputIdx)?
        .add_i64(0)?
        .add_op(OpEqualVerify)?
        .add_i64(0)?
        .add_op(OpOutputAuthorizingInput)?
        .add_i64(0)?
        .add_op(OpEqualVerify)?
        .add_i64(1)?
        .add_op(OpInputCovenantId)?
        .add_data(&[0; 32])?
        .add_op(OpEqualVerify)?
        .add_i64(1)?
        .add_op(OpOutputAuthorizingInput)?
        .add_i64(-1)?
        .add_op(OpEqualVerify)?;
    for op in [OpTxInputAmount, OpTxOutputAmount] {
        b.add_i64(0)?
            .add_op(op)?
            .add_i64(app::STATE_RENT as i64)?
            .add_op(OpEqualVerify)?;
    }
    // SHA256(tag || economic-domain || bincode(State with actual covenant)).
    b.add_data(&[b"KPI-private-native-state-v2\0".as_slice(), &domain()].concat())?
        .add_i64(0)?
        .add_op(OpInputCovenantId)?
        .add_op(OpCat)?
        .add_data(&serialized[32..])?
        .add_op(OpCat)?
        .add_op(OpSHA256)?;
    // Existing SMT leaf hash: SHA256(0x01 || resource || state_hash).
    b.add_data(&[&[1], app::RESOURCE.as_slice()].concat())?
        .add_op(OpSwap)?
        .add_op(OpCat)?
        .add_op(OpSHA256)?;
    // Reconstruct the exact reviewed state script, then its versioned P2SH.
    b.add_data(&target[..34])?
        .add_op(OpSwap)?
        .add_op(OpCat)?
        .add_data(&target[66..])?
        .add_op(OpCat)?
        .add_op(OpBlake2b)?
        .add_data(&wire[..4])?
        .add_op(OpSwap)?
        .add_op(OpCat)?
        .add_data(&wire[36..])?
        .add_op(OpCat)?
        .add_i64(0)?
        .add_op(OpTxOutputSpk)?
        .add_op(OpEqual)?;
    Ok(b.drain())
}

pub fn output(tip: H, touch: u64, funding: TransactionOutpoint) -> Result<(TransactionOutput, H)> {
    use kaspa_consensus_core::hashing::covenant_id::covenant_id;
    let mut output = TransactionOutput::new(
        app::STATE_RENT,
        kaspa_txscript::standard::pay_to_script_hash_script(&redeem(tip, touch)?),
    );
    let id = covenant_id(funding, std::iter::once((0, &output)));
    output.covenant = Some(CovenantBinding::new(0, id));
    Ok((output, id.into()))
}
