#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/../.."
output="${1:?new output directory required}"
mkdir "$output"
python3 - <<'PY'
from pathlib import Path
import hashlib, tomllib
p=Path('poc/private-note-chain/pins')
assert hashlib.sha256((p/'vk.bin').read_bytes()).digest()==(p/'vk-id.bin').read_bytes()
v=tomllib.loads(Path('poc/recovery-native/guest/Cargo.lock').read_text())
for pkg in v['package']:
    if pkg.get('source','').startswith('git+https://github.com/kaspanet/rusty-kaspa'):
        assert pkg['source'].endswith('#01b532e8b553523216471682649693af92f0fd16')
PY
RISC0_FEATURE_bigint2=1 \
RUSTFLAGS='-C passes=lower-atomic -C link-arg=-Ttext=0x00200800 -C link-arg=--fatal-warnings -C panic=abort --cfg getrandom_backend="custom"' \
 cargo +kpi-risc0 build --offline --locked --release --target riscv32im-risc0-zkvm-elf --manifest-path poc/recovery-native/guest/Cargo.toml
cp "$CARGO_TARGET_DIR/riscv32im-risc0-zkvm-elf/release/kpi-recovery-native-guest" "$output/guest.raw.elf"
.local/ci-target/release/kpi-takeover-host wrap "$output/guest.raw.elf" "$output/guest.program.bin" > "$output/expected-image.txt"
