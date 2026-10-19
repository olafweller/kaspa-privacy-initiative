//! Offline TN10 preparation. No RPC client, provider client or broadcast command.
use kaspa_consensus_core::{config::params::TESTNET_PARAMS, tx::*};
use kaspa_hashes::Hash;
use kpi_private_native::{
    self as app, chain, lane,
    wallet::{protocol::*, ProofVerifier},
    AcceleratedVerifier, Input, State,
};
use kpi_private_note_proof as trusted;
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
#[path = "../../private-native/host/src/native.rs"]
mod native;
mod transaction;
mod wallet;

const IMAGE: &str = "794cfff4cfa509799ec1f6750678d3fe4bc8623522aa647cc65e6b53955c4bc9";
const PROGRAM_SHA: &str = "213ed12a0f0b514443fcab9608de5d42e0961fc6704fd51d49326106ead1e375";
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
    let tx = hash(b"KPI-private-native-tx-domain-v1");
    let batch = hash(b"KPI-private-native-batch-domain-v1");
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
fn init(out: &Path) -> Result<()> {
    use kpi_private_note_wallet::wallet::Wallet;
    use rand::{rngs::OsRng, RngCore};
    mkdir(out)?;
    mkdir(&out.join("alice"))?;
    mkdir(&out.join("bob"))?;
    mkdir(&out.join("sponsor"))?;
    let mut id = [0u8; 32];
    OsRng.fill_bytes(&mut id);
    let mut public = json!({"schema":"KPI_TN10_PRIVATE_TRIAL_V1","trial":hex::encode(id),"network":"testnet-10",
        "scope":"UNFUNDED_PREPARATION_NOT_LIVE_READY","lane":hex::encode(chain::LANE),"domain":hex::encode(domain()),
        "guestImage":IMAGE,"joinControl":JOIN,"programSha256":PROGRAM_SHA,"walletParametersSha256":PARAM_SHA,
        "principalSompi":1000000000u64,"bobPrincipalSompi":400000000u64,"stateRentSompi":app::STATE_RENT,
        "permissionRentSompi":app::PERMISSION_RENT,"fundingAuthorized":false,"broadcastAuthorized":false,"gpuAuthorized":false,
        "roleCustody":"Separate local role files; operator/root can access them. Bob must control his files before live release."});
    for role in ["alice", "bob"] {
        let w = Wallet::new();
        save(&out.join(role).join("wallet.backup"), &w.local_backup())?;
        public[role] = json!({"owner":hex::encode(w.address.owner),"incoming":hex::encode(w.address.incoming)});
    }
    for role in ["bob", "sponsor"] {
        let key = secp256k1::SecretKey::new(&mut OsRng);
        let kp = secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &key);
        save(
            &out.join(role).join("native.key"),
            hex::encode(key.secret_bytes()).as_bytes(),
        )?;
        let pk = kp.x_only_public_key().0.serialize();
        public[format!("{role}Native")] = json!({"pubkey":hex::encode(pk),"address":kaspa_addresses::Address::new(kaspa_addresses::Prefix::Testnet,kaspa_addresses::Version::PubKey,&pk).to_string()});
    }
    report(&out.join("trial.json"), &public)?;
    println!("Fresh unfunded trial created; keys retained in separate 0600 role files.");
    Ok(())
}

fn main() -> Result<()> {
    require(
        std::env::var_os("RISC0_DEV_MODE").is_none(),
        "development mode forbidden",
    )?;
    let a: Vec<_> = std::env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("seed") if a.len()==6 => batch::seed(Path::new(&a[2]),&a[3],Path::new(&a[4]),Path::new(&a[5])),
        Some("checkpoint") if a.len()==8 => batch::checkpoint(Path::new(&a[2]),&a[3],Path::new(&a[4]),Path::new(&a[5]),Path::new(&a[6]),Path::new(&a[7])),
        Some("init") if a.len()==3 => init(Path::new(&a[2])),
        Some("build") if a.len()==6 => transaction::build(Path::new(&a[2]),Path::new(&a[3]),Path::new(&a[4]),Path::new(&a[5])),
        Some("freeze") if a.len()==9 => batch::freeze(Path::new(&a[2]),&a[3],Path::new(&a[4]),&a[5],Path::new(&a[6]),Path::new(&a[7]),Path::new(&a[8])),
        Some("prove") if a.len()==5 => batch::prove(Path::new(&a[2]),&a[3],Path::new(&a[4])),
        Some("verify") if a.len()==6 => batch::verify(Path::new(&a[2]),&a[3],Path::new(&a[4]),Path::new(&a[5])),
        Some("wallet") if a.len()==8 => wallet::prepare(Path::new(&a[2]),Path::new(&a[3]),Path::new(&a[4]),Path::new(&a[5]),&a[6],Path::new(&a[7])),
        _ => Err("init NEW_TRIAL | build TRIAL REQUEST OWN_SPONSOR_KEY NEW_OUT | freeze VALIDATOR EXPECTED_VALIDATOR_SHA PROGRAM STAGE CAPTURE PRIOR_CHECKPOINT NEW_OUT | verify TRUSTED_TARGET EXPECTED_TARGET_SHA RECEIPT NEW_OUT | wallet TRIAL PUBLIC_STATE OWN_BACKUP PUBLIC_PARAMETERS credit-transfer|exit NEW_OUT".into())
    }
}

#[cfg(test)]
mod tests;
