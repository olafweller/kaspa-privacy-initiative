// Reuse the retained real prover without invoking its fixture-writing main().
// Its existing source and evidence remain byte-identical.
#[allow(dead_code)]
mod retained {
    include!("../../host/src/main.rs");

    pub fn prove_live(input: &Input, directory: &Path, program: &[u8]) -> Value {
        assert!(
            std::env::var("RISC0_DEV_MODE").is_err(),
            "development proofs forbidden"
        );
        fs::create_dir(directory).expect("fresh proof output directory");
        let image = compute_image_id(program).unwrap();
        let (receipt, costs) = prove(directory, "full", input, program, image);
        receipt.verify(image).unwrap();
        let output = execute(input);
        save(
            directory,
            "input.json",
            &serde_json::to_value(input).unwrap(),
        );
        let result = json!({"kind":"REAL_SUCCINCT_PROOF_LIVE_TN10_INPUT", "image_id":image.to_string(),
            "costs":costs,"output":output,"development_mode":false});
        save(directory, "proof-report.json", &result);
        result
    }
}

use kaspa_consensus_core::tx::TransactionOutpoint;
use kaspa_hashes::Hash;
use kaspa_seq_commit::hashing::lane_key;
use kpi_lane_common::{Input, Output, BATCH_DOMAIN, TX_DOMAIN};
use risc0_zkvm::{compute_image_id, sha::Digestible, Receipt};
use std::path::Path;
use vprogs_zk_backend_risc0_covenant::{
    script::{build_redeem_script, redeem_script_len, CommonPins, RedeemPins, SuccinctPins},
    Settlement, SettlementInput, SettlementWitness, SuccinctWitness,
};

pub fn prove(input: &Input, directory: &Path, program: &[u8]) -> serde_json::Value {
    retained::prove_live(input, directory, program)
}

pub fn initial_redeem(subnet: &[u8; 20], tip: &Hash, program: &[u8]) -> Vec<u8> {
    let image: [u8; 32] = compute_image_id(program).unwrap().into();
    let key = lane_key(subnet);
    let pins = RedeemPins::Succinct(SuccinctPins {
        common: CommonPins {
            program_id: &image,
            tx_image_id: &TX_DOMAIN,
            batch_image_id: &BATCH_DOMAIN,
            lane_key: &key,
            permission_output_value: 0,
        },
    });
    let state = kpi_lane_common::initial_state();
    build_redeem_script(&state, tip, redeem_script_len(&state, &pins), &pins)
}

pub fn settlement(
    input: &Input,
    output: &Output,
    program: &[u8],
    receipt: &Receipt,
    end: Hash,
    outpoint: TransactionOutpoint,
    value: u64,
) -> Settlement {
    assert!(
        std::env::var("RISC0_DEV_MODE").is_err(),
        "development mode forbidden"
    );
    let image = compute_image_id(program).unwrap();
    receipt.verify(image).expect("real receipt verifies");
    assert_eq!(
        receipt.journal.bytes,
        kpi_lane_common::journal(input, &kpi_lane_common::execute(input))
    );
    let image: [u8; 32] = image.into();
    let succinct = receipt
        .inner
        .succinct()
        .expect("real succinct receipt required");
    let seal: Vec<u8> = succinct.seal.iter().flat_map(|x| x.to_le_bytes()).collect();
    let claim: [u8; 32] = succinct.claim.digest().into();
    let control: Vec<u8> = succinct
        .control_inclusion_proof
        .digests
        .iter()
        .flat_map(|d| <[u8; 32]>::from(*d))
        .collect();
    Settlement::build(&SettlementInput {
        covenant_id: Hash::from_bytes(input.covenant),
        pins: RedeemPins::Succinct(SuccinctPins {
            common: CommonPins {
                program_id: &image,
                tx_image_id: &TX_DOMAIN,
                batch_image_id: &BATCH_DOMAIN,
                lane_key: &lane_key(&input.lane),
                permission_output_value: 0,
            },
        }),
        prev_state: &input.old_state,
        prev_lane_tip: &Hash::from_bytes(input.old_tip),
        new_state: &output.state,
        new_lane_tip: &Hash::from_bytes(output.tip),
        block_prove_to: end,
        prev_outpoint: outpoint,
        value,
        witness: SettlementWitness::Succinct(SuccinctWitness {
            seal: &seal,
            claim: &claim,
            control_index: succinct.control_inclusion_proof.index,
            control_digests: &control,
            deposit_spk_hash: &[0; 32],
        }),
        permission_spk_hash: &[0; 32],
    })
}
