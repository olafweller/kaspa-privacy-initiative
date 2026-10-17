#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/../../.."
output="${1:?new program directory required}"
mkdir "$output"
for kind in wallet adapter; do
  manifest="poc/shielded-design/compat/$kind-guest/Cargo.toml"
  RUSTFLAGS='-C passes=lower-atomic -C link-arg=-Ttext=0x00200800 -C link-arg=--fatal-warnings -C panic=abort --cfg getrandom_backend="custom"' \
    cargo +kpi-risc0 build --locked --release --target riscv32im-risc0-zkvm-elf --manifest-path "$manifest"
  if [[ "$kind" == wallet ]]; then binary=kpi-wallet-compat-guest; else binary=kpi-wallet-adapter-compat-guest; fi
  cp "$CARGO_TARGET_DIR/riscv32im-risc0-zkvm-elf/release/$binary" "$output/$kind.raw.elf"
  .local/ci-target/release/kpi-takeover-host wrap "$output/$kind.raw.elf" "$output/$kind.program.bin"
  if [[ "$kind" == wallet ]]; then
    .local/ci-target/release/kpi-takeover-host wallet-image "$output/wallet.program.bin" > poc/shielded-design/compat/wallet-image.rs
  fi
done
