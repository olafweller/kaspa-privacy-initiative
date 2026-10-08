//! Strict machine schema framing. Semantic/compiler checking is independently
//! implemented in scripts/a1_check.py, not imported by this loader.
use serde::{
    Deserialize, Deserializer,
    de::{self, MapAccess, SeqAccess, Visitor},
};
use serde_json::{Number, Value};
use std::fmt;
struct Unique(Value);
impl<'de> Deserialize<'de> for Unique {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Unique;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("duplicate-free nonfloating JSON")
            }
            fn visit_map<A: MapAccess<'de>>(self, mut a: A) -> Result<Unique, A::Error> {
                let mut m = serde_json::Map::new();
                while let Some((k, v)) = a.next_entry::<String, Unique>()? {
                    if m.insert(k, v.0).is_some() {
                        return Err(de::Error::custom("duplicate JSON key"));
                    }
                }
                Ok(Unique(Value::Object(m)))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut a: A) -> Result<Unique, A::Error> {
                let mut v = vec![];
                while let Some(x) = a.next_element::<Unique>()? {
                    v.push(x.0);
                }
                Ok(Unique(Value::Array(v)))
            }
            fn visit_str<E: de::Error>(self, x: &str) -> Result<Unique, E> {
                Ok(Unique(Value::String(x.into())))
            }
            fn visit_string<E: de::Error>(self, x: String) -> Result<Unique, E> {
                Ok(Unique(Value::String(x)))
            }
            fn visit_u64<E: de::Error>(self, x: u64) -> Result<Unique, E> {
                Ok(Unique(Value::Number(Number::from(x))))
            }
            fn visit_i64<E: de::Error>(self, _: i64) -> Result<Unique, E> {
                Err(E::custom("signed JSON numeric field forbidden"))
            }
            fn visit_f64<E: de::Error>(self, _: f64) -> Result<Unique, E> {
                Err(E::custom("floating JSON forbidden"))
            }
            fn visit_bool<E: de::Error>(self, x: bool) -> Result<Unique, E> {
                Ok(Unique(Value::Bool(x)))
            }
            fn visit_unit<E: de::Error>(self) -> Result<Unique, E> {
                Ok(Unique(Value::Null))
            }
        }
        d.deserialize_any(V)
    }
}
pub fn strict_json(bytes: &[u8]) -> Result<Value, String> {
    let mut d = serde_json::Deserializer::from_slice(bytes);
    let v = Unique::deserialize(&mut d).map_err(|e| e.to_string())?;
    d.end().map_err(|e| e.to_string())?;
    Ok(v.0)
}
fn keys(v: &Value, names: &str) -> Result<(), String> {
    let m = v.as_object().ok_or("record required")?;
    if m.len() != names.split_whitespace().count()
        || names.split_whitespace().any(|n| !m.contains_key(n))
    {
        return Err(format!("exact schema keys required: {names}"));
    }
    Ok(())
}
fn dec(v: &Value, bits: u32) -> Result<u64, String> {
    let s = v.as_str().ok_or("canonical decimal string required")?;
    if s.is_empty() || (s.len() > 1 && s.starts_with('0')) || !s.bytes().all(|b| b.is_ascii_digit())
    {
        return Err("canonical decimal string".into());
    }
    let n: u64 = s.parse().map_err(|_| "decimal overflow")?;
    if bits < 64 && n >= (1u64 << bits) {
        return Err("decimal width".into());
    }
    Ok(n)
}
fn hex(v: &Value, n: Option<usize>) -> Result<(), String> {
    let s = v.as_str().ok_or("canonical hex string required")?;
    if s.len() % 2 != 0
        || n.is_some_and(|n| s.len() != 2 * n)
        || !s
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("canonical hex length/case".into());
    }
    Ok(())
}
fn descriptor(v: &Value, r1cs: bool) -> Result<(), String> {
    keys(
        v,
        if r1cs {
            "path bytes sha256 format"
        } else {
            "path bytes sha256"
        },
    )?;
    let p = std::path::Path::new(v["path"].as_str().ok_or("path string")?);
    if p.as_os_str().is_empty()
        || p.components()
            .any(|c| !matches!(c, std::path::Component::Normal(_)))
    {
        return Err("relative artifact path required".into());
    }
    dec(&v["bytes"], 64)?;
    hex(&v["sha256"], Some(32))?;
    if r1cs && v["format"] != "KPI-A1/R1CS/v1" {
        return Err("R1CS format".into());
    }
    Ok(())
}
pub fn manifest(bytes: &[u8]) -> Result<Value, String> {
    let v = strict_json(bytes)?;
    keys(
        &v,
        "schema protocol network genesis_hex instance_hex claim_commitment_hex recipient states branches abi envelope pins inspection recovery",
    )?;
    if v["schema"] != "kpi-a1-artifacts/v1"
        || v["protocol"] != "KPI-A1/TN10/finite/v1"
        || v["network"] != "testnet-10"
    {
        return Err("artifact identity".into());
    }
    for f in ["genesis_hex", "instance_hex", "claim_commitment_hex"] {
        hex(&v[f], Some(32))?;
    }
    keys(&v["recipient"], "address spk_version spk_hex")?;
    if v["recipient"]["spk_version"] != "0" {
        return Err("recipient SPK version".into());
    }
    hex(&v["recipient"]["spk_hex"], Some(36))?;
    keys(&v["states"], "s0 s1")?;
    for s in ["s0", "s1"] {
        let s = &v["states"][s];
        keys(s, "stage R L B redeem spk_hex")?;
        dec(&s["stage"], 8)?;
        for n in ["R", "L", "B"] {
            if dec(&s[n], 64)? > crate::model::MAX_SOMPI {
                return Err("state amount range".into());
            }
        }
        descriptor(&s["redeem"], false)?;
        hex(&s["spk_hex"], Some(37))?;
    }
    keys(&v["branches"], "s0_continue s0_terminal s1_terminal")?;
    for name in ["s0_continue", "s0_terminal", "s1_terminal"] {
        let b = &v["branches"][name];
        keys(
            b,
            "stage mode selector_hex fee next_R next_L next_B outputs context_hex context_sha256 relation_id r1cs pk vk",
        )?;
        dec(&b["stage"], 8)?;
        dec(&b["mode"], 8)?;
        hex(&b["selector_hex"], Some(1))?;
        for n in ["fee", "next_R", "next_L", "next_B"] {
            if dec(&b[n], 64)? > crate::model::MAX_SOMPI {
                return Err("branch amount range".into());
            }
        }
        for o in b["outputs"].as_array().ok_or("outputs array")? {
            keys(o, "index value spk_hex covenant")?;
            dec(&o["index"], 32)?;
            dec(&o["value"], 64)?;
            hex(&o["spk_hex"], None)?;
            if !o["covenant"].is_null() {
                return Err("unexpected covenant".into());
            }
        }
        hex(&b["context_hex"], None)?;
        hex(&b["context_sha256"], Some(32))?;
        descriptor(&b["r1cs"], true)?;
        descriptor(&b["pk"], false)?;
        descriptor(&b["vk"], false)?;
    }
    keys(
        &v["abi"],
        "verifier_tag_hex public_inputs scalar_bytes proof_bytes vk_bytes witness_order",
    )?;
    keys(
        &v["envelope"],
        "tx_version subnetwork_hex gas payload_hex lock_time sequence_policy compute_budgets",
    )?;
    keys(
        &v["envelope"]["compute_budgets"],
        "s0_continue s0_terminal s1_terminal",
    )?;
    for n in v["envelope"]["compute_budgets"]
        .as_object()
        .unwrap()
        .values()
    {
        dec(n, 16)?;
    }
    keys(
        &v["pins"],
        "kpi_source_commit rusty_kaspa_commit rust_toolchain target cargo_lock_sha256 dependency_versions sdk_archive_sha256 node_archive_sha256 build_commands checker_source_commit",
    )?;
    for f in [
        "kpi_source_commit",
        "rusty_kaspa_commit",
        "checker_source_commit",
    ] {
        hex(&v["pins"][f], Some(20))?;
    }
    for f in [
        "cargo_lock_sha256",
        "sdk_archive_sha256",
        "node_archive_sha256",
    ] {
        hex(&v["pins"][f], Some(32))?;
    }
    keys(
        &v["inspection"],
        "normalized_r1cs_sha256 script_disassembly_sha256 checker_report_sha256 setup_observation_receipt_sha256",
    )?;
    keys(
        &v["inspection"]["normalized_r1cs_sha256"],
        "s0_continue s0_terminal s1_terminal",
    )?;
    for x in v["inspection"]["normalized_r1cs_sha256"]
        .as_object()
        .unwrap()
        .values()
    {
        hex(x, Some(32))?;
    }
    for f in [
        "script_disassembly_sha256",
        "checker_report_sha256",
        "setup_observation_receipt_sha256",
    ] {
        hex(&v["inspection"][f], Some(32))?;
    }
    keys(
        &v["recovery"],
        "source_id network_genesis_hex retention_start_hash retention_policy locator_schema private_backup_items public_artifact_items",
    )?;
    hex(&v["recovery"]["network_genesis_hex"], Some(32))?;
    hex(&v["recovery"]["retention_start_hash"], Some(32))?;
    Ok(v)
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn duplicate_float_and_trailing_fail() {
        for b in [
            br#"{"x":1,"x":2}"#.as_slice(),
            br#"{"x":{"z":1,"z":2}}"#,
            br#"{"x":0.5}"#,
            br#"{} {}"#,
            br#"{"x":-1}"#,
        ] {
            assert!(strict_json(b).is_err());
        }
        assert_eq!(
            strict_json(br#"{"x":"18446744073709551615","y":[true,null]}"#).unwrap()["x"],
            "18446744073709551615"
        );
    }
    #[test]
    fn canonical_scalars_paths() {
        for b in ["01", "-1", "18446744073709551616", "1.0"] {
            assert!(dec(&Value::String(b.into()), 64).is_err());
        }
        assert!(hex(&Value::String("Aa".into()), Some(1)).is_err());
        assert!(
            descriptor(
                &serde_json::json!({"path":"../x","bytes":"1","sha256":"00".repeat(32)}),
                false
            )
            .is_err()
        );
    }
}
