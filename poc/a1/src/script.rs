//! Frozen ADR-0003 script ABI. Offline only; no broadcast/funding support.
use ark_bn254::Fr;
use ark_serialize::CanonicalSerialize;
use kaspa_consensus_core::tx::ScriptPublicKey;
use kaspa_txscript::{opcodes::codes::*, script_builder::ScriptBuilder};

#[derive(Clone, Debug)]
pub struct ScriptPolicy {
    pub reserve: u64,
    pub outputs: Vec<(u64, ScriptPublicKey)>,
}

pub fn encode_spk(spk: &ScriptPublicKey) -> Vec<u8> {
    let mut bytes = spk.version().to_be_bytes().to_vec();
    bytes.extend_from_slice(spk.script());
    bytes
}

fn op(b: &mut ScriptBuilder, code: u8) -> Result<(), String> {
    b.add_op(code).map_err(|e| e.to_string())?;
    Ok(())
}
fn num(b: &mut ScriptBuilder, n: i64) -> Result<(), String> {
    b.add_i64(n).map_err(|e| e.to_string())?;
    Ok(())
}
fn data(b: &mut ScriptBuilder, bytes: &[u8]) -> Result<(), String> {
    b.add_data(bytes).map_err(|e| e.to_string())?;
    Ok(())
}
fn eqnum(b: &mut ScriptBuilder, code: u8, n: i64) -> Result<(), String> {
    op(b, code)?;
    num(b, n)?;
    op(b, OpNumEqualVerify)
}
fn envelope(b: &mut ScriptBuilder) -> Result<(), String> {
    // Stack-neutral common constraints. Native consensus still validates the body.
    eqnum(b, OpTxVersion, 1)?;
    op(b, OpTxSubnetId)?;
    data(b, &[0; 20])?;
    op(b, OpEqualVerify)?;
    for code in [OpTxGas, OpTxPayloadLen, OpTxLockTime] {
        eqnum(b, code, 0)?;
    }
    eqnum(b, OpDepth, 4)
}
fn body(b: &mut ScriptBuilder, vk: &[u8], policy: &ScriptPolicy) -> Result<(), String> {
    if vk.len() != 424 {
        return Err("VK must be compressed five-public-input BN254 Groth16 (424 bytes)".into());
    }
    if policy.reserve == 0 || policy.reserve > 2_900_000_000_000_000_000 {
        return Err("reserve range".into());
    }
    if !(1..=2).contains(&policy.outputs.len()) {
        return Err("output count".into());
    }
    let mut sum = 0u64;
    for (value, spk) in &policy.outputs {
        if *value == 0 || *value > 2_900_000_000_000_000_000 || spk.version() != 0 {
            return Err("output amount/SPK version".into());
        }
        sum = sum.checked_add(*value).ok_or("output sum overflow")?;
    }
    if sum >= policy.reserve {
        return Err("outputs must leave a positive fixed fee".into());
    }
    eqnum(b, OpTxInputCount, 1)?;
    eqnum(b, OpTxInputIndex, 0)?;
    num(b, 0)?;
    eqnum(b, OpTxInputAmount, policy.reserve as i64)?;
    eqnum(b, OpTxOutputCount, policy.outputs.len() as i64)?;
    for (i, (value, spk)) in policy.outputs.iter().enumerate() {
        num(b, i as i64)?;
        eqnum(b, OpTxOutputAmount, *value as i64)?;
        num(b, i as i64)?;
        op(b, OpTxOutputSpk)?;
        data(b, &encode_spk(spk))?;
        op(b, OpEqualVerify)?;
        num(b, i as i64)?;
        eqnum(b, OpOutputAuthorizingInput, -1)?;
    }
    eqnum(b, OpSize, 128)?;
    op(b, OpToAltStack)?;
    eqnum(b, OpSize, 32)?;
    op(b, OpOver)?;
    eqnum(b, OpSize, 32)?;
    op(b, OpDrop)?;
    num(b, 0)?;
    op(b, OpOutpointIndex)?;
    num(b, 8)?;
    op(b, OpNum2Bin)?;
    data(b, &[0; 24])?;
    op(b, OpCat)?;
    for (start, end) in [(16, 32), (0, 16)] {
        num(b, 0)?;
        op(b, OpOutpointTxId)?;
        num(b, start)?;
        num(b, end)?;
        op(b, OpSubstr)?;
        data(b, &[0; 16])?;
        op(b, OpCat)?;
    }
    num(b, 5)?;
    op(b, OpFromAltStack)?;
    data(b, vk)?;
    data(b, &[0x20])?;
    op(b, OpZkPrecompile)
}

pub fn build_s1(vk: &[u8], policy: &ScriptPolicy) -> Result<Vec<u8>, String> {
    if policy.outputs.len() != 1 {
        return Err("S1 must be terminal".into());
    }
    let mut b = ScriptBuilder::new();
    envelope(&mut b)?;
    data(&mut b, &[1])?;
    op(&mut b, OpEqualVerify)?;
    body(&mut b, vk, policy)?;
    Ok(b.drain())
}
pub fn build_s0(
    vkc: &[u8],
    vkt: &[u8],
    continuing: &ScriptPolicy,
    terminal: &ScriptPolicy,
) -> Result<Vec<u8>, String> {
    if continuing.reserve != terminal.reserve
        || continuing.outputs.len() != 2
        || terminal.outputs.len() != 1
    {
        return Err("S0 branch shape/reserve".into());
    }
    let mut b = ScriptBuilder::new();
    envelope(&mut b)?;
    op(&mut b, OpDup)?;
    data(&mut b, &[0])?; // Raw 00 is NOT an empty script-number zero.
    op(&mut b, OpEqual)?;
    op(&mut b, OpIf)?;
    op(&mut b, OpDrop)?;
    body(&mut b, vkc, continuing)?;
    op(&mut b, OpElse)?;
    data(&mut b, &[1])?;
    op(&mut b, OpEqualVerify)?;
    body(&mut b, vkt, terminal)?;
    op(&mut b, OpEndIf)?;
    Ok(b.drain())
}
pub fn signature(
    proof: &[u8],
    inputs: &[Fr; 5],
    selector: &[u8],
    redeem: &[u8],
) -> Result<Vec<u8>, String> {
    if proof.len() != 128 || (selector != [0] && selector != [1]) {
        return Err("proof/selector ABI".into());
    }
    let mut b = ScriptBuilder::new();
    for index in [4, 3] {
        let mut scalar = vec![];
        inputs[index]
            .serialize_compressed(&mut scalar)
            .map_err(|e| e.to_string())?;
        data(&mut b, &scalar)?;
    }
    data(&mut b, proof)?;
    data(&mut b, selector)?;
    data(&mut b, redeem)?;
    Ok(b.drain())
}
