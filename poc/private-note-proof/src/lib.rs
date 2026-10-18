//! Fixed public target. The verifier trusts these compiled expectations, never GPU reports.
use bincode::Options;
use risc0_circuit_recursion::{control_id::ALLOWED_CONTROL_ROOT, CIRCUIT};
use risc0_zkp::{core::hash::poseidon2::Poseidon2HashSuite, verify::VerificationError};
use risc0_zkvm::{
    sha::{Digest, Sha256},
    Receipt, VerifierContext,
};
use std::{error::Error, fs, io::Write, path::Path};

pub type Result<T> = std::result::Result<T, Box<dyn Error>>;
pub const IMAGE: &str = "20d8431e18f42c6e337ab726f166914516e3ebcd70577e67d49e687737901f8b";
pub const JOIN: &str = "7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e";
pub const PROGRAM_SHA: &str = "531e2c5415844446af254634c43e02bd64644cd669625b3edefb554f1e7ab191";
pub const INPUT_SHA: &str = "d43a228f371f30f7bcd80eb7d035f79a9d128245a6d88135b39de2b4c57cfa2f";
pub const JOURNAL_SHA: &str = "88ba872f3aca413a41b83e91ba40c4eb0b27eb9db31150b7af3d133bb6ccf22e";
pub const CYCLES: u64 = 160_000_000;
pub const EXPECTED: &[u8] =
    include_bytes!("../../private-note-chain/calibration-160m/evidence/expected-journal.bin");
pub const MAX_RECEIPT_BYTES: u64 = 24 * 1024 * 1024;

pub fn digest(s: &str) -> Result<Digest> {
    Ok(hex::decode(s)?.as_slice().try_into()?)
}
pub fn sha(b: &[u8]) -> String {
    risc0_zkvm::sha::Impl::hash_bytes(b).to_string()
}
pub fn save(dir: &Path, name: &str, data: &[u8]) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(dir.join(name))?;
    f.write_all(data)?;
    f.sync_all()?;
    fs::File::open(dir)?.sync_all()?;
    Ok(())
}
pub fn target(package: &Path) -> Result<(Vec<u8>, Vec<u8>)> {
    let p = fs::read(package.join("guest.program.bin"))?;
    let i = fs::read(package.join("input.bin"))?;
    assert_eq!(sha(&p), PROGRAM_SHA, "frozen guest bytes");
    assert_eq!(risc0_zkvm::compute_image_id(&p)?, digest(IMAGE)?);
    assert_eq!(sha(&i), INPUT_SHA, "frozen public input/proof bytes");
    assert_eq!(fs::read(package.join("expected-journal.bin"))?, EXPECTED);
    assert_eq!(EXPECTED.len(), 352);
    assert_eq!(sha(EXPECTED), JOURNAL_SHA);
    Ok((p, i))
}
pub fn read_receipt(path: &Path) -> Result<Receipt> {
    assert!(
        fs::metadata(path)?.len() <= MAX_RECEIPT_BYTES,
        "receipt size limit"
    );
    Ok(bincode::DefaultOptions::new()
        .with_fixint_encoding()
        .with_limit(MAX_RECEIPT_BYTES)
        .reject_trailing_bytes()
        .deserialize(&fs::read(path)?)?)
}
/// SDK receipt verification plus explicit seal/metadata/expected control equality.
/// The SDK 3.0.3 check_code closure authenticates the decoded control's inclusion
/// but does not compare it with the receipt's control_id metadata. Use the existing
/// official STARK verifier callback, as Kaspa does; no new crypto arithmetic.
pub fn verify_claim(r: &Receipt, image: Digest, expected: &[u8], control: Digest) -> Result<()> {
    let s = r.inner.succinct()?;
    assert_eq!(s.hashfn, "poseidon2");
    assert_eq!(s.control_id, control, "independently expected control ID");
    r.verify_with_context(&VerifierContext::default().with_dev_mode(false), image)?;
    let suite = Poseidon2HashSuite::new_suite();
    risc0_zkp::verify::verify(&CIRCUIT, &suite, &s.seal, |_, decoded: &Digest| {
        if *decoded != control || *decoded != s.control_id {
            return Err(VerificationError::ControlVerificationError {
                control_id: *decoded,
            });
        }
        s.control_inclusion_proof
            .verify(decoded, &ALLOWED_CONTROL_ROOT, suite.hashfn.as_ref())
            .map_err(|_| VerificationError::ControlVerificationError {
                control_id: *decoded,
            })
    })?;
    let claim = r.claim()?.value()?;
    assert!(
        claim
            .output
            .value()?
            .ok_or("missing output")?
            .assumptions
            .is_empty(),
        "unresolved assumptions forbidden"
    );
    assert_eq!(
        r.journal.bytes, expected,
        "exact independently expected journal"
    );
    Ok(())
}
pub fn verify(r: &Receipt) -> Result<()> {
    verify_claim(r, digest(IMAGE)?, EXPECTED, digest(JOIN)?)
}

/// Panics from explicit pin/assertion failures are not used as attack evidence.
/// Negative receipt tests use Result-returning cryptographic APIs directly.
pub fn crypto_negatives(r: &Receipt, image: Digest) -> Result<serde_json::Value> {
    let ctx = VerifierContext::default().with_dev_mode(false);
    let mut wrong: [u8; 32] = image.into();
    wrong[0] ^= 1;
    assert!(r.verify_with_context(&ctx, Digest::from(wrong)).is_err());
    let offsets: Vec<usize> = (0..r.journal.bytes.len()).step_by(32).collect();
    for offset in &offsets {
        let mut t = r.clone();
        t.journal.bytes[*offset] ^= 1;
        assert!(t.verify_with_context(&ctx, image).is_err());
    }
    let mut seal = r.clone();
    match &mut seal.inner {
        risc0_zkvm::InnerReceipt::Succinct(s) => s.seal[0] ^= 1,
        _ => return Err("not succinct".into()),
    }
    assert!(seal.verify_with_context(&ctx, image).is_err());
    let mut inclusion = r.clone();
    match &mut inclusion.inner {
        risc0_zkvm::InnerReceipt::Succinct(s) => {
            if let Some(d) = s.control_inclusion_proof.digests.first_mut() {
                let mut b: [u8; 32] = (*d).into();
                b[0] ^= 1;
                *d = b.into();
            } else {
                return Err("expected nonempty inclusion path".into());
            }
        }
        _ => return Err("not succinct".into()),
    }
    assert!(inclusion.verify_with_context(&ctx, image).is_err());
    // Exercise the official verifier callback with a wrong expected identity;
    // simply comparing a JSON control label would not test seal equality.
    let s = r.inner.succinct()?;
    let mut bad: [u8; 32] = s.control_id.into();
    bad[0] ^= 1;
    let bad = Digest::from(bad);
    let suite = Poseidon2HashSuite::new_suite();
    assert!(
        risc0_zkp::verify::verify(&CIRCUIT, &suite, &s.seal, |_, decoded: &Digest| {
            if *decoded != bad {
                Err(VerificationError::ControlVerificationError {
                    control_id: *decoded,
                })
            } else {
                Ok(())
            }
        })
        .is_err()
    );
    Ok(
        serde_json::json!({"wrongImageRejected":true,"tamperedJournalOffsetsRejected":offsets,
        "corruptedSealRejected":true,"malformedControlInclusionRejected":true,"wrongExpectedControlRejectedBySealVerifier":true}),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn frozen_journal_and_official_join_pin() {
        assert_eq!(EXPECTED.len(), 352);
        assert_eq!(sha(EXPECTED), JOURNAL_SHA);
        let official = risc0_circuit_recursion::control_id::POSEIDON2_CONTROL_IDS
            .iter()
            .find(|(name, _)| *name == "join.zkr")
            .unwrap()
            .1;
        assert_eq!(official, digest(JOIN).unwrap());
    }
    #[test]
    fn fake_receipt_never_qualifies() {
        let fake = Receipt::new(
            risc0_zkvm::InnerReceipt::Fake(risc0_zkvm::FakeReceipt::new(
                risc0_zkvm::ReceiptClaim::ok(digest(IMAGE).unwrap(), EXPECTED.to_vec()),
            )),
            EXPECTED.to_vec(),
        );
        assert!(verify(&fake).is_err());
    }
}
