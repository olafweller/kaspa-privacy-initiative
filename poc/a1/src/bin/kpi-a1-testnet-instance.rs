//! Testnet-10-only A1 instance constructor for funded trials with test KAS.
//!
//! Separate from the `kpi-poc-a1` harness, which keeps its fixture-only scope.
//! This binary has no RPC, funding or broadcasting API: it writes a new bundle
//! with explicit terms and a fresh private recipient/backup key. Funding it is
//! an operator decision under the testnet trial rules; never use real funds.
//! The protocol library, circuits, scripts and validator are shared unchanged.
#[path = "../main.rs"]
#[allow(dead_code)]
mod harness;

use kpi_poc_a1::model::Terms;
use rand::{RngCore, rngs::OsRng};
use serde_json::Value;
use std::{fs, path::Path};

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

const USAGE: &str = "Usage: kpi-a1-testnet-instance testnet-10 NEW_DIRECTORY TERMS.json";

/// Exactly the six terms as integer sompi; unknown or missing keys are rejected.
fn read_terms(path: &Path) -> Result<Terms> {
    let v: Value = serde_json::from_slice(&fs::read(path)?)?;
    let o = v.as_object().ok_or("terms must be a JSON object")?;
    let names = ["l0", "b0", "w", "f0", "fc", "f1"];
    if o.len() != names.len() || !names.iter().all(|n| o.contains_key(*n)) {
        return Err("terms must contain exactly l0, b0, w, f0, fc, f1".into());
    }
    let get = |n: &str| -> Result<u64> {
        match &o[n] {
            Value::String(s) if !s.is_empty() && s.bytes().all(|b| b.is_ascii_digit()) => {
                Ok(s.parse()?)
            }
            Value::Number(x) => x.as_u64().ok_or_else(|| format!("{n}: not u64 sompi").into()),
            _ => Err(format!("{n}: integer sompi required").into()),
        }
    };
    Ok(Terms { l0: get("l0")?, b0: get("b0")?, w: get("w")?, f0: get("f0")?, fc: get("fc")?, f1: get("f1")? })
}

/// Fresh valid secp256k1 secret, never the public fixture key 1.
fn fresh_recipient_key() -> [u8; 32] {
    loop {
        let mut raw = [0u8; 32];
        OsRng.fill_bytes(&mut raw);
        let fixture = raw[..31].iter().all(|b| *b == 0) && raw[31] == 1;
        if !fixture && secp256k1::SecretKey::from_slice(&raw).is_ok() {
            return raw;
        }
    }
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    // The constructor is fixed to the TN10 genesis and testnet address prefix;
    // the explicit network argument makes that visible at every call site.
    if args.len() != 3 || args[0] != "testnet-10" {
        return Err(USAGE.into());
    }
    let terms = read_terms(Path::new(&args[2]))?;
    let report = harness::construct(Path::new(&args[1]), terms, fresh_recipient_key())?;
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}
