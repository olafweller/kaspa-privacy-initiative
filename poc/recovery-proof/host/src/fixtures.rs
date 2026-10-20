//! Fixed public PR56 fixtures compiled into the trusted native verifier.
//! Avoid runtime reads from the build machine's historical corpus paths.
use super::*;
pub use crate::reviewed_fixtures::{native_history, require_single_spend, Prepared, STAGES};
pub fn scenarios() -> Result<Prepared> {
    let mut cases = vec![];
    let mut templates = vec![];
    macro_rules! stage {
        ($name:literal) => {{
            let input: Input = bincode::deserialize(include_bytes!(concat!(
                "../../../recovery-native/evidence/fixtures/",
                $name,
                ".input.bin"
            )))?;
            let output: Output = bincode::deserialize(include_bytes!(concat!(
                "../../../recovery-native/evidence/fixtures/",
                $name,
                ".expected.bin"
            )))?;
            let template: kaspa_consensus_core::tx::Transaction =
                bincode::deserialize(include_bytes!(concat!(
                    "../../../recovery-native/evidence/fixtures/",
                    $name,
                    ".template.bin"
                )))?;
            cases.push(($name.to_string(), input, output));
            templates.push(template);
        }};
    }
    stage!("deposit");
    stage!("credit-transfer");
    stage!("bob-exit");
    stage!("bob-reconcile");
    stage!("alice-exit");
    stage!("alice-reconcile");
    require_single_spend(&native_history(
        cases.iter().map(|(n, i, _)| (n.as_str(), i)),
    )?)?;
    Ok(Prepared { cases, templates })
}
