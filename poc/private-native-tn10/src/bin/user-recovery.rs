//! User-side offline research tooling. No RPC/provider clients or broadcast path.
use bincode::Options;
use kpi_private_native::{
    self as app, chain, lane,
    wallet::{protocol::*, ProofVerifier},
    AcceleratedVerifier, State,
};
use kpi_private_note_wallet::wallet::{Engine, Wallet};
use serde_json::json;
use std::{
    fs,
    io::Write,
    os::unix::fs::{DirBuilderExt, OpenOptionsExt, PermissionsExt},
    path::Path,
};
type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
#[allow(dead_code)]
#[path = "../../../private-native/host/src/native.rs"]
mod native;
#[path = "user_recovery/qualification.rs"]
mod qualification;
#[path = "user_recovery/terminal.rs"]
mod terminal;
#[cfg(test)]
#[path = "user_recovery/tests.rs"]
mod tests;

const PARAM_SHA: &str = "812b3bda0ec5f9b0c17fc1d530e49fc21defc9dcc5ea9c70a133ca62fec31e99";
fn require(ok: bool, reason: &str) -> Result<()> {
    if !ok {
        return Err(reason.into());
    }
    Ok(())
}
fn h(s: &str) -> Result<H> {
    Ok(hex::decode(s)?.try_into().map_err(|_| "hash length")?)
}
fn verifier() -> AcceleratedVerifier {
    AcceleratedVerifier::checked(
        include_bytes!("../../../private-note-chain/pins/vk.bin"),
        *include_bytes!("../../../private-note-chain/pins/vk-id.bin"),
    )
    .unwrap()
}
fn mkdir(p: &Path) -> Result<()> {
    fs::DirBuilder::new().mode(0o700).create(p)?;
    Ok(())
}
fn save(p: &Path, bytes: &[u8]) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(p)?;
    f.write_all(bytes)?;
    f.sync_all()?;
    fs::File::open(p.parent().ok_or("parent")?)?.sync_all()?;
    Ok(())
}
fn report(p: &Path, v: &serde_json::Value) -> Result<()> {
    save(p, &serde_json::to_vec_pretty(v)?)
}
fn bounded(p: &Path) -> Result<Vec<u8>> {
    use std::io::Read;
    let mut bytes = vec![];
    fs::File::open(p)?.take(2_097_153).read_to_end(&mut bytes)?;
    require(bytes.len() <= 2_097_152, "public input exceeds 2 MiB")?;
    Ok(bytes)
}
fn decode<T: serde::de::DeserializeOwned + serde::Serialize>(p: &Path) -> Result<T> {
    let bytes = bounded(p)?;
    let value = bincode::DefaultOptions::new()
        .with_fixint_encoding()
        .with_limit(2_097_152)
        .reject_trailing_bytes()
        .deserialize(&bytes)?;
    require(
        bincode::serialize(&value)? == bytes,
        "canonical public bytes",
    )?;
    Ok(value)
}
fn secret(p: &Path) -> Result<Vec<u8>> {
    let m = fs::symlink_metadata(p)?;
    require(
        m.is_file() && m.permissions().mode() & 0o077 == 0,
        "own secret must be a regular 0600 file",
    )?;
    bounded(p)
}
fn own(p: &Path) -> Result<Wallet> {
    let b: [u8; 64] = secret(&p.join("wallet.backup"))?
        .try_into()
        .map_err(|_| "wallet backup length")?;
    Ok(Wallet::restore_local(&b))
}
fn recipient(p: &Path) -> Result<H> {
    let key = secp256k1::SecretKey::from_slice(&secret(&p.join("native.key"))?)?;
    Ok(
        secp256k1::Keypair::from_secret_key(secp256k1::SECP256K1, &key)
            .x_only_public_key()
            .0
            .serialize(),
    )
}
fn init(p: &Path) -> Result<()> {
    mkdir(p)?;
    let w = Wallet::new();
    let key = secp256k1::SecretKey::new(&mut rand::rngs::OsRng);
    save(&p.join("wallet.backup"), &w.local_backup())?;
    save(&p.join("native.key"), &key.secret_bytes())?;
    report(
        &p.join("receive.json"),
        &json!({
            "schema":"KPI_USER_RECEIVE_V1", "domain":hex::encode(domain()),
            "owner":hex::encode(w.address.owner), "incoming":hex::encode(w.address.incoming)
        }),
    )
}
fn public_state(p: &Path, root: H) -> Result<State> {
    let state: State = decode(p)?;
    state.accounting()?;
    require(
        state.ledger.verifier == verifier().id(),
        "fixed wallet verifier",
    )?;
    require(
        state.root() == root,
        "independently expected accepted state root",
    )?;
    Ok(state)
}
fn discover(s: &State, w: &Wallet) -> Vec<(Note, usize)> {
    w.discover(&s.ledger.deliveries, &s.ledger.tree, &s.ledger.nullifiers)
}
fn scan(state: &Path, root: H, user: &Path) -> Result<()> {
    let s = public_state(state, root)?;
    let notes = discover(&s, &own(user)?);
    let total = notes.iter().try_fold(0u64, |n, (note, _)| {
        n.checked_add(note.value).ok_or("balance overflow")
    })?;
    println!(
        "{}",
        json!({"scope":"LOCAL_PRIVATE_WALLET_OUTPUT_NOT_PUBLIC_EVIDENCE", "stateRoot":hex::encode(root),"notes":notes.len(),"spendableSompi":total,"checkpointFreshnessEstablished":false})
    );
    Ok(())
}
fn engine(parameters: &Path) -> Result<Engine> {
    let bytes = fs::read(parameters)?;
    require(
        hex::encode(hash(&bytes)) == PARAM_SHA,
        "reviewed public parameter SHA256",
    )?;
    Ok(Engine::from_public_parameters(&bytes, verifier().id())?)
}
fn exit(state: &Path, root: H, user: &Path, parameters: &Path, out: &Path) -> Result<()> {
    let s = public_state(state, root)?;
    let w = own(user)?;
    let found = discover(&s, &w);
    require(
        found.len() == 1,
        "one current recovered note required by this experiment",
    )?;
    let (note, index) = found[0].clone();
    let key = recipient(user)?;
    let (path, bits) = s.ledger.tree.path(index)?;
    let mut st = Statement::new(EXIT, verifier().id(), s.ledger.tree.root());
    st.nullifier = w.nf(&note);
    st.exit_value = note.value;
    st.exit_destination = chain::destination(&key);
    let op = engine(parameters)?.prove(
        st,
        w.witness(note, [Note::dummy(), Note::dummy()], path, bits),
        [Delivery::absent(), Delivery::absent()],
    )?;
    // Check current-nullifier/authorization acceptance locally before publishing.
    let mut ledger = s.ledger.clone();
    ledger.apply(&verifier(), &op)?;
    mkdir(out)?;
    report(&out.join("exit.json"), &serde_json::to_value(&op)?)?;
    report(
        &out.join("public.json"),
        &json!({"sourceRoot":hex::encode(root),"nativePubkey":hex::encode(key),"operationId":hex::encode(op.statement.id()),"payloadHex":hex::encode(chain::operation_payload(&op,key)?),"witnessExported":false,"broadcast":false}),
    )
}
fn rebuild(start: H, end: H, out: &Path, files: &[String]) -> Result<()> {
    require(!files.is_empty(), "complete ordered input history required")?;
    let v = verifier();
    let mut previous: Option<State> = None;
    for file in files {
        let input: app::Input = decode(Path::new(file))?;
        let expected = previous.as_ref().map(State::root).unwrap_or(start);
        require(
            input.state.root() == expected,
            "history discontinuity/start root",
        )?;
        if let Some(p) = &previous {
            require(
                bincode::serialize(p)? == bincode::serialize(&input.state)?,
                "complete prior state continuity",
            )?;
        }
        let result =
            std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| app::execute(&input, &v)))
                .map_err(|_| "invalid authenticated-history relation")?;
        previous = Some(result.state);
    }
    let s = previous.unwrap();
    require(
        s.root() == end,
        "independently expected final accepted root",
    )?;
    save(out, &bincode::serialize(&s)?)?;
    println!(
        "{}",
        json!({"scope":"OFFLINE_REPLAY_TO_INDEPENDENT_CHECKPOINT_NOT_CHAIN_SELECTION", "batches":files.len(),"stateRoot":hex::encode(s.root()),"accounting":s.accounting()?,"chainFreshnessEstablished":false})
    );
    Ok(())
}
fn run() -> Result<()> {
    require(
        std::env::var_os("RISC0_DEV_MODE").is_none(),
        "development mode forbidden",
    )?;
    let args: Vec<_> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("init") if args.len() == 3 => init(Path::new(&args[2])),
        Some("scan") if args.len() == 5 => scan(Path::new(&args[2]), h(&args[3])?, Path::new(&args[4])),
        Some("exit") if args.len() == 7 => exit(Path::new(&args[2]), h(&args[3])?, Path::new(&args[4]), Path::new(&args[5]), Path::new(&args[6])),
        Some("rebuild") if args.len() >= 6 => rebuild(h(&args[2])?, h(&args[3])?, Path::new(&args[4]), &args[5..]),
        Some("rehearse") if args.len() == 4 => qualification::run(Path::new(&args[2]), Path::new(&args[3])),
        _ => Err("usage: user-recovery init USERDIR | scan STATE EXPECTED_ROOT USERDIR | exit STATE EXPECTED_ROOT USERDIR PARAMETERS NEW_OUTDIR | rebuild START_ROOT END_ROOT NEW_STATE INPUT...".into()),
    }
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}
