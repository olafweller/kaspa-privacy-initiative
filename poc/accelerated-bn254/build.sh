#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
setup="${1:?existing PR37 setup directory required}"
output="${2:?new program directory required}"
mkdir "$output"
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host groth16 validate-key "$setup"
cmp "$setup/vk.bin" poc/groth16-comparison/pins/vk.bin
cmp "$setup/pvk-uncompressed.bin" poc/groth16-comparison/pins/pvk-uncompressed.bin
# Matches risc0-build 3.0.x's normal bigint2 feature advertisement when using
# this repository's custom toolchain/direct Cargo invocation. Actual runtime
# compatibility and accelerated execution are separately tested, never assumed.
RISC0_FEATURE_bigint2=1 \
RUSTFLAGS='-C passes=lower-atomic -C link-arg=-Ttext=0x00200800 -C link-arg=--fatal-warnings -C panic=abort --cfg getrandom_backend="custom"' \
  cargo +kpi-risc0 build --locked --release --target riscv32im-risc0-zkvm-elf \
  --manifest-path poc/accelerated-bn254/classifier-guest/Cargo.toml
cp "$CARGO_TARGET_DIR/riscv32im-risc0-zkvm-elf/release/kpi-accelerated-bn254-classifier" "$output/classifier.raw.elf"
.local/ci-target/release/kpi-takeover-host wrap "$output/classifier.raw.elf" "$output/classifier.program.bin"
RISC0_PROVER=ipc .local/ci-target/release/kpi-takeover-host accelerated-bn254 pin "$output"
