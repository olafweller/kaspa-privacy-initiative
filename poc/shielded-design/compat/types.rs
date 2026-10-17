//! Synthetic public-data compatibility fixture, not the private-payment circuit.
#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct WalletInput {
    pub native_id: [u8; 32],
    pub synthetic_secret: [u8; 32],
    pub amount: u64,
    pub pay: u64,
    pub change: u64,
    pub fee: u64,
}
#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct AdapterInput {
    pub native: kpi_takeover_common::Input,
    pub wallet_journal: Vec<u8>,
    pub host_requests_skip: bool,
}
