#[cfg(feature = "wallet")]
pub mod circuit;
pub mod ledger;
pub mod protocol;
#[cfg(feature = "wallet")]
pub mod wallet;
pub type Result<T> = std::result::Result<T, String>;
/// Actual ordinary cryptographic verification, never a host-supplied verdict.
pub trait ProofVerifier {
    fn id(&self) -> protocol::H;
    fn verify(&self, op: &protocol::Operation) -> Result<()>;
}
