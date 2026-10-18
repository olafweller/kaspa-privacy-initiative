//! Real archived proofs, fresh process, independently expected VK identity.
use std::{
    path::PathBuf,
    process::Command,
    time::{SystemTime, UNIX_EPOCH},
};
#[test]
fn published_wallet_proofs_and_real_state_rejection_controls() {
    let source = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("evidence/public");
    let out = std::env::temp_dir().join(format!(
        "kpi-private-note-replay-{}-{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    std::fs::create_dir(&out).unwrap();
    for name in [
        "verifying-key.bin",
        "credit.json",
        "transfer.json",
        "competing.json",
        "bob-exit.json",
        "recovery.json",
    ] {
        std::fs::copy(source.join(name), out.join(name)).unwrap();
    }
    let r = Command::new(env!("CARGO_BIN_EXE_kpi-private-note-wallet"))
        .args([
            "verify",
            out.to_str().unwrap(),
            "d45e8248eda25a6f6ec85b5074d0f7d217d29741c820c4d8ddfb2667675a5bf2",
        ])
        .output()
        .unwrap();
    assert!(r.status.success(), "{}", String::from_utf8_lossy(&r.stderr));
    let report: serde_json::Value = serde_json::from_slice(&r.stdout).unwrap();
    for key in [
        "separateProcess",
        "stateVerifierPinEnforced",
        "wrongExpectedVkRejected",
        "economicNullifiersAcrossBatches",
        "atomicRejections",
        "canonicalFalsePairingRejected",
        "exitDestinationCryptographicBinding",
        "rehashedCiphertextCryptographicBinding",
        "wrongSubgroupRejected",
        "identityPointRejected",
        "invalidThenValidPreservesState",
        "depositCreditRecoveryRaceRejected",
        "unknownFieldsAndTrailingBytesRejected",
        "exactFixturePayoutAndBacking",
    ] {
        assert_eq!(report[key], true, "{key}");
    }
    assert_eq!(report["actualProofsVerified"], 5);
    assert_eq!(report["canonicalWireRoundTrips"], 5);
    std::fs::remove_dir_all(out).unwrap();
}
