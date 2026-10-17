//! Bounded LOCAL proxy envelope and ordinary RISC Zero receipt classification.
//! Not a private payment protocol; no note ownership/membership/nullifier circuit.
use bincode::Options;
use risc0_zkvm::{
    sha::{Impl, Sha256},
    InnerReceipt, Receipt, VerifierContext,
};
use serde::{Deserialize, Serialize};

pub const MAX_PROOF: usize = 240_000;
pub const INTENT_LEN: usize = 570;
pub const MAX_OPERATION: usize = 250_000; // Entire pinned native block footprint, including bad proofs.
pub const MAX_BATCH: usize = 3;
pub const MAX_INPUT: usize = 32 + 8 + 4 + MAX_BATCH * (4 + 4096 + 4 + MAX_OPERATION);
pub const NETWORK: [u8; 32] = [0x10; 32]; // LOCAL domain, not the real TN10 genesis.
pub const POOL: [u8; 32] = [0x35; 32];

pub fn hash(bytes: &[u8]) -> [u8; 32] {
    Impl::hash_bytes(bytes).as_bytes().try_into().unwrap()
}
pub fn tagged(tag: &[u8], bytes: &[u8]) -> [u8; 32] {
    hash(&[tag, bytes].concat())
}
#[derive(Clone, Serialize, Deserialize)]
pub struct WalletInput {
    pub intent: Vec<u8>,
    pub secret: [u8; 32],
    pub values: [u64; 4], // amount, pay, change, fee: public test witnesses only.
}
pub fn values_hash(values: &[u64; 4]) -> [u8; 32] {
    hash(
        &values
            .iter()
            .flat_map(|n| n.to_le_bytes())
            .collect::<Vec<_>>(),
    )
}
// Layout: magic8, version2, network32, pool32, nonce32, image32,
// secretCommit32, valuesCommit32, effect8, fee8, feeRecipient32,
// outputCommitments64, opaque delivery bytes256. Integers are little-endian.
pub fn intent(image: [u8; 32], nonce: u8, secret: [u8; 32], values: [u64; 4]) -> Vec<u8> {
    let mut b = b"KPICLF01".to_vec();
    b.extend(1u16.to_le_bytes());
    b.extend(NETWORK);
    b.extend(POOL);
    b.extend([nonce; 32]);
    b.extend(image);
    b.extend(hash(&secret));
    b.extend(values_hash(&values));
    b.extend(values[1].to_le_bytes());
    b.extend(values[3].to_le_bytes());
    b.extend([0x61; 32]);
    b.extend(tagged(b"proxy-output-A", &[nonce]));
    b.extend(tagged(b"proxy-output-B", &[nonce]));
    // Opaque synthetic delivery records: retained/bound, not encryption evidence.
    b.extend([0x62; 128]);
    b.extend([0x63; 128]);
    assert_eq!(b.len(), INTENT_LEN);
    b
}
pub fn intent_valid(b: &[u8], image: [u8; 32]) -> bool {
    b.len() == INTENT_LEN
        && &b[..8] == b"KPICLF01"
        && b[8..10] == 1u16.to_le_bytes()
        && b[10..42] == NETWORK
        && b[42..74] == POOL
        && b[106..138] == image
}
pub fn journal(intent: &[u8]) -> Vec<u8> {
    let mut b = tagged(b"KPI-local-intent-v1", intent).to_vec();
    b.extend(&intent[138..202]);
    b
}
pub fn operation(intent: &[u8], proof: &[u8]) -> Vec<u8> {
    let mut b = intent.to_vec();
    b.extend((proof.len() as u32).to_le_bytes());
    b.extend(proof);
    b
}
pub struct Reader<'a>(pub &'a [u8]);
impl<'a> Reader<'a> {
    pub fn take(&mut self, n: usize) -> Result<&'a [u8], &'static str> {
        if n > self.0.len() {
            return Err("truncated encoding");
        }
        let (a, b) = self.0.split_at(n);
        self.0 = b;
        Ok(a)
    }
    pub fn u32(&mut self) -> Result<u32, &'static str> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    pub fn blob(&mut self, max: usize) -> Result<&'a [u8], &'static str> {
        let n = self.u32()? as usize;
        if n > max {
            return Err("length bound");
        }
        self.take(n)
    }
}
pub fn blob(b: &mut Vec<u8>, value: &[u8]) {
    b.extend((value.len() as u32).to_le_bytes());
    b.extend(value);
}
pub fn order_step(previous: [u8; 32], index: u32, native_id: [u8; 32]) -> [u8; 32] {
    tagged(
        b"KPI-local-ordered-native-v1",
        &[&previous[..], &index.to_le_bytes(), &native_id].concat(),
    )
}
// Outcome codes are stable and deliberately coarse; no host-supplied verdict.
// 0 accepted, 1 envelope, 2 proof encoding/profile, 3 cryptographic invalidity,
// 4 current-state replay/insufficient proxy balance. Unavailable input aborts.
pub fn classify(op: &[u8], image: [u8; 32]) -> u8 {
    if op.len() > MAX_OPERATION || op.len() < INTENT_LEN + 4 {
        return 1;
    }
    let intent = &op[..INTENT_LEN];
    if !intent_valid(intent, image) {
        return 1;
    }
    let mut r = Reader(&op[INTENT_LEN..]);
    let Ok(bytes) = r.blob(MAX_PROOF) else {
        return 2;
    };
    if !r.0.is_empty() || bytes.len() < 4 || bytes[..4] != 1u32.to_le_bytes() {
        return 2;
    }
    let codec = || {
        bincode::DefaultOptions::new()
            .with_fixint_encoding()
            .with_limit(MAX_PROOF as u64)
            .reject_trailing_bytes()
    };
    let Ok(receipt) = codec().deserialize::<Receipt>(bytes) else {
        return 2;
    };
    // Only the measured succinct format is permitted; no Fake/Composite/Groth16.
    let InnerReceipt::Succinct(inner) = &receipt.inner else {
        return 2;
    };
    if inner.seal.len() > MAX_PROOF/4 || inner.seal.len() < 33
        || inner.hashfn != "poseidon2" || inner.control_inclusion_proof.digests.len() != 8
        || inner.control_inclusion_proof.index >= 256
        // Poseidon2's SDK hash_pair asserts reduced field words. Classify these
        // malformed encodings before entering the verifier, including raw Merkle
        // digests that its field-slice decoder does not validate itself.
        || inner.seal.iter().any(|w| *w >= 2_013_265_921)
        || inner.control_id.as_words().iter().any(|w| *w >= 2_013_265_921)
        || inner.control_inclusion_proof.digests.iter().any(|d| d.as_words().iter().any(|w| *w >= 2_013_265_921))
        // read_slice_with_po2 extracts this raw word via to_u32_words(), not
        // as_u32(). Restrict it to the bounded experimental recursion profile.
        || !(14..=24).contains(&inner.seal[32])
        || receipt.journal.bytes != journal(intent)
        || codec().serialize(&receipt).ok().as_deref() != Some(bytes)
    {
        return 2;
    }
    // Actual seal verifier as ordinary guest computation. No recursive syscall,
    // optional assumption, host decision or successful-execution catch is used.
    let ctx = VerifierContext::default().with_dev_mode(false);
    if receipt.verify_with_context(&ctx, image).is_ok() {
        0
    } else {
        3
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn malformed_proof_lengths_and_tags_are_bounded() {
        let image = [9; 32];
        let body = intent(image, 1, [7; 32], [10, 4, 6, 0]);
        for n in [0, 1, 3, 4, 8, 32, 1024, MAX_PROOF, MAX_PROOF + 1] {
            let op = operation(&body, &vec![0xff; n]);
            assert_ne!(classify(&op, image), 0);
        }
        for n in [0, 1, MAX_PROOF as u32, u32::MAX] {
            let mut op = body.clone();
            op.extend(n.to_le_bytes());
            assert_ne!(classify(&op, image), 0);
        }
        let mut op = operation(&body, &[]);
        op.extend([0; 8]);
        assert_ne!(classify(&op, image), 0);
    }

    #[test]
    fn intent_excludes_proof_but_native_order_includes_it() {
        let image = [9; 32];
        let body = intent(image, 1, [7; 32], [10, 4, 6, 0]);
        assert!(intent_valid(&body, image));
        assert!(!intent_valid(&body, [8; 32]));
        for offset in [8, 10, 42, 106] {
            let mut changed = body.clone();
            changed[offset] ^= 1;
            assert!(!intent_valid(&changed, image));
        }
        let a = operation(&body, &[1]);
        let b = operation(&body, &[2]);
        assert_eq!(journal(&a[..INTENT_LEN]), journal(&b[..INTENT_LEN]));
        assert_ne!(hash(&a), hash(&b));
        assert_ne!(
            order_step([0; 32], 0, hash(&a)),
            order_step([0; 32], 0, hash(&b))
        );
        assert_ne!(
            order_step([0; 32], 0, hash(&a)),
            order_step([0; 32], 1, hash(&a))
        );
    }

    #[test]
    fn deterministic_arbitrary_encoding_vectors_never_accept() {
        let image = [9; 32];
        let body = intent(image, 1, [7; 32], [10, 4, 6, 0]);
        let mut state = 0x350036u64;
        for n in 0..256 {
            let bytes: Vec<u8> = (0..n * 7)
                .map(|_| {
                    state ^= state << 13;
                    state ^= state >> 7;
                    state ^= state << 17;
                    state as u8
                })
                .collect();
            assert_ne!(classify(&operation(&body, &bytes), image), 0);
        }
    }
}
