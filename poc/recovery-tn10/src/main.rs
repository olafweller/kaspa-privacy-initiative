//! Offline TN10 preparation. No RPC client, provider client or broadcast command.
use kaspa_consensus_core::{config::params::TESTNET_PARAMS, tx::*};
use kaspa_hashes::Hash;
use kpi_private_note_proof as trusted;
use kpi_recovery_native::{
    self as app, chain, lane,
    wallet::{protocol::*, ProofVerifier},
    AcceleratedVerifier, Input, State,
};
use serde_json::{json, Value};
use std::{
    fs,
    io::Write,
    os::unix::fs::{DirBuilderExt, OpenOptionsExt, PermissionsExt},
    path::Path,
    time::Instant,
};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
mod batch;
mod bootstrap;
#[allow(dead_code)]
#[path = "../../recovery-native/host/src/native.rs"]
mod native;
mod transaction;
mod wallet;

const IMAGE: &str = "095a2fb2f58c350ccd2688ae7f72748c915bd973c60fd4abaa8d87b282ad68b5";
const PROGRAM_SHA: &str = "6039c3ef645d620bdd7eef6384750e73f51bcc8f9182aae1b1ac3c963601e75b";
const JOIN: &str = trusted::JOIN;
const PARAM_SHA: &str = "812b3bda0ec5f9b0c17fc1d530e49fc21defc9dcc5ea9c70a133ca62fec31e99";
fn require(ok: bool, why: &str) -> Result<()> {
    if ok {
        Ok(())
    } else {
        Err(why.into())
    }
}
fn read(p: impl AsRef<Path>) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(p)?)?)
}
fn h(v: &Value) -> Result<H> {
    Ok(hex::decode(v.as_str().ok_or("expected hex hash")?)?
        .try_into()
        .map_err(|_| "hash length")?)
}
fn n(v: &Value) -> Result<u64> {
    v.as_u64().ok_or("expected integer sompi/u64".into())
}
fn verifier() -> AcceleratedVerifier {
    AcceleratedVerifier::checked(
        include_bytes!("../../private-note-chain/pins/vk.bin"),
        *include_bytes!("../../private-note-chain/pins/vk-id.bin"),
    )
    .unwrap()
}
fn state(p: impl AsRef<Path>) -> Result<State> {
    let b = fs::read(p)?;
    let s: State = bincode::deserialize(&b)?;
    require(bincode::serialize(&s)? == b, "canonical state bytes")?;
    s.accounting()?;
    Ok(s)
}
fn mkdir(p: &Path) -> Result<()> {
    fs::DirBuilder::new().mode(0o700).create(p)?;
    Ok(())
}
fn save(p: &Path, b: &[u8]) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(p)?;
    f.write_all(b)?;
    f.sync_all()?;
    fs::File::open(p.parent().ok_or("parent")?)?.sync_all()?;
    Ok(())
}
fn report(p: &Path, v: &Value) -> Result<()> {
    save(p, &serde_json::to_vec_pretty(v)?)
}
fn secret(p: &Path) -> Result<Vec<u8>> {
    let m = fs::symlink_metadata(p)?;
    require(
        m.is_file() && m.permissions().mode() & 0o077 == 0,
        "own secret must be a regular 0600 file",
    )?;
    Ok(fs::read(p)?)
}
fn state_script(s: &State) -> Vec<u8> {
    use vprogs_zk_backend_risc0_covenant::script::*;
    let image: H = hex::decode(IMAGE).unwrap().try_into().unwrap();
    let tx = hash(b"KPI-recovery-native-tx-domain-v1");
    let batch = hash(b"KPI-recovery-native-batch-domain-v1");
    let lane = kaspa_seq_commit::hashing::lane_key(&chain::LANE);
    native::state_redeem(
        &s.root(),
        &Hash::from_bytes(s.lane_tip),
        &RedeemPins::SuccinctJoin(SuccinctPins {
            common: CommonPins {
                program_id: &image,
                tx_image_id: &tx,
                batch_image_id: &batch,
                lane_key: &lane,
                permission_output_value: app::PERMISSION_RENT,
            },
        }),
    )
}
#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct Receive {
    schema: String,
    domain: String,
    owner: String,
    incoming: String,
}
fn receive(path: &Path) -> Result<Value> {
    let bytes = fs::read(path)?;
    require(bytes.len() <= 4096, "bounded public receive file")?;
    let r: Receive = serde_json::from_slice(&bytes)?;
    require(
        r.schema == "KPI_USER_RECEIVE_V1" && r.domain == hex::encode(domain()),
        "receive schema/domain",
    )?;
    for value in [&r.owner, &r.incoming] {
        let key = hex::decode(value)?;
        require(
            key.len() == 32 && hex::encode(&key) == *value && key.iter().any(|b| *b != 0),
            "canonical nonzero public receive key",
        )?;
    }
    Ok(json!({"owner":r.owner,"incoming":r.incoming}))
}
fn init(alice: &Path, bob: &Path, out: &Path) -> Result<()> {
    use rand::{rngs::OsRng, RngCore};
    let a = receive(alice)?;
    let b = receive(bob)?;
    require(
        a["owner"] != b["owner"] && a["incoming"] != b["incoming"],
        "distinct Alice/Bob wallets required",
    )?;
    mkdir(out)?;
    mkdir(&out.join("sponsor"))?;
    let mut id = [0u8; 32];
    OsRng.fill_bytes(&mut id);
    let key = secp256k1::SecretKey::new(&mut OsRng);
    let kp = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &key);
    save(
        &out.join("sponsor/native.key"),
        hex::encode(key.secret_bytes()).as_bytes(),
    )?;
    let pk = kp.x_only_public_key().0.serialize();
    let public = json!({"schema":"KPI_RECOVERY_TN10_TRIAL_V1","trial":hex::encode(id),"network":"testnet-10",
        "scope":"UNFUNDED_PREPARATION_NOT_LIVE_READY","lane":hex::encode(chain::LANE),"domain":hex::encode(domain()),
        "guestImage":IMAGE,"joinControl":JOIN,"programSha256":PROGRAM_SHA,"walletParametersSha256":PARAM_SHA,
        "alice":a,"bob":b,"sponsorNative":{"pubkey":hex::encode(pk),"address":kaspa_addresses::Address::new(kaspa_addresses::Prefix::Testnet,kaspa_addresses::Version::PubKey,&pk).to_string()},
        "principalSompi":1000000000u64,"bobPrincipalSompi":400000000u64,"aliceFinalPrincipalSompi":600000000u64,
        "stateRentSompi":app::STATE_RENT,"permissionRentSompi":app::PERMISSION_RENT,
        "fundingAuthorized":false,"broadcastAuthorized":false,"gpuAuthorized":false,
        "roleCustody":"Both user wallets stay on owner Mint PC; operator has only public receive data. Same owner controls logical Alice/Bob and operator. Native payout keys disclosed only in wallet exit output.",
        "batches":CASES,"sharedProofSeconds":3600,"maxRentalSeconds":7200,"gpuAttempts":1,"planningLimitUsd":5});
    report(&out.join("trial.json"), &public)?;
    save(&out.join("alice-receive.json"), &fs::read(alice)?)?;
    save(&out.join("bob-receive.json"), &fs::read(bob)?)?;
    println!("Fresh unfunded trial created from public receive files. No Alice/Bob secrets or native payout keys imported.");
    Ok(())
}
pub const CASES: [&str; 6] = [
    "deposit",
    "credit-transfer",
    "bob-exit",
    "bob-reconcile",
    "alice-exit",
    "alice-reconcile",
];

fn main() -> Result<()> {
    require(
        std::env::var_os("RISC0_DEV_MODE").is_none(),
        "development mode forbidden",
    )?;
    let a: Vec<_> = std::env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("seed") if a.len()==6 => batch::seed(Path::new(&a[2]),&a[3],Path::new(&a[4]),Path::new(&a[5])),
        Some("checkpoint") if a.len()==8 => batch::checkpoint(Path::new(&a[2]),&a[3],Path::new(&a[4]),Path::new(&a[5]),Path::new(&a[6]),Path::new(&a[7])),
        Some("init") if a.len()==5 => init(Path::new(&a[2]),Path::new(&a[3]),Path::new(&a[4])),
        Some("build") if a.len()==6 => transaction::build(Path::new(&a[2]),Path::new(&a[3]),Path::new(&a[4]),Path::new(&a[5])),
        Some("freeze") if a.len()==9 => batch::freeze(Path::new(&a[2]),&a[3],Path::new(&a[4]),&a[5],Path::new(&a[6]),Path::new(&a[7]),Path::new(&a[8])),
        Some("prove") if a.len()==5 => batch::prove(Path::new(&a[2]),&a[3],Path::new(&a[4])),
        Some("verify") if a.len()==6 => batch::verify(Path::new(&a[2]),&a[3],Path::new(&a[4]),Path::new(&a[5])),
        Some("wallet") if a.len()==9 => wallet::prepare(Path::new(&a[2]),Path::new(&a[3]),&a[4],Path::new(&a[5]),Path::new(&a[6]),&a[7],Path::new(&a[8])),
        _ => Err("init ALICE_RECEIVE BOB_RECEIVE NEW_TRIAL | build TRIAL REQUEST OWN_SPONSOR_KEY NEW_OUT | freeze VALIDATOR EXPECTED_VALIDATOR_SHA PROGRAM STAGE CAPTURE PRIOR_CHECKPOINT NEW_OUT | verify TRUSTED_TARGET EXPECTED_TARGET_SHA RECEIPT NEW_OUT | wallet TRIAL PUBLIC_STATE EXPECTED_ROOT OWN_BACKUP PUBLIC_PARAMETERS credit-transfer|bob-exit|alice-exit NEW_OUT".into())
    }
}

#[cfg(test)]
mod tests;
