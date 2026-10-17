#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
setup="${1:?setup directory required}"
output="${2:?new program directory required}"
mkdir "$output"
mkdir -p poc/groth16-comparison/pins
cp "$setup/vk.bin" poc/groth16-comparison/pins/vk.bin
cp "$setup/pvk.bin" poc/groth16-comparison/pins/pvk.bin
if [[ ! -f "$setup/pvk-uncompressed.bin" ]]; then
  RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host groth16 export-key "$setup" "$setup/pvk-uncompressed.bin"
fi
cp "$setup/pvk-uncompressed.bin" poc/groth16-comparison/pins/pvk-uncompressed.bin
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host groth16 validate-key "$setup"
RUSTFLAGS='-C passes=lower-atomic -C link-arg=-Ttext=0x00200800 -C link-arg=--fatal-warnings -C panic=abort --cfg getrandom_backend="custom"' \
  cargo +kpi-risc0 build --locked --release --target riscv32im-risc0-zkvm-elf \
  --manifest-path poc/groth16-comparison/classifier-guest/Cargo.toml
cp "$CARGO_TARGET_DIR/riscv32im-risc0-zkvm-elf/release/kpi-groth16-classifier-guest" "$output/classifier.raw.elf"
.local/ci-target/release/kpi-takeover-host wrap "$output/classifier.raw.elf" "$output/classifier.program.bin"
