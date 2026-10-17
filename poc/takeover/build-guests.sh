#!/usr/bin/env bash
# Rebuild the three isolated guests; no RPC, keys or transaction construction.
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
task_output="${1:?new program directory required}"
mkdir "$task_output"
# Same official toolchain bootstrap and guest flags as PR31.
task_toolchain="${KPI_RISC0_TOOLCHAIN:-kpi-risc0}"
task_host="${KPI_TAKEOVER_HOST:-.local/ci-target/release/kpi-takeover-host}"
for task_guest in transaction batch aggregate; do
    RUSTFLAGS='-C passes=lower-atomic -C link-arg=-Ttext=0x00200800 -C link-arg=--fatal-warnings -C panic=abort --cfg getrandom_backend="custom"' \
        cargo +"$task_toolchain" build --locked --release --target riscv32im-risc0-zkvm-elf \
        --manifest-path "poc/takeover/$task_guest-guest/Cargo.toml"
    cp "$CARGO_TARGET_DIR/riscv32im-risc0-zkvm-elf/release/kpi-takeover-$task_guest-guest" "$task_output/$task_guest.raw.elf"
    "$task_host" wrap "$task_output/$task_guest.raw.elf" "$task_output/$task_guest.program.bin"
done
