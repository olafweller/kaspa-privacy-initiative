#!/usr/bin/env bash
# Download official public toolchain artifacts; no wallet, signing, funding or RPC.
set -euo pipefail
task_tools="${KPI_LANE_TOOLS:-/workspace/scratch/kpi-lane-tools}"
mkdir -p "$task_tools"
curl -fL --max-time 60 https://github.com/risc0/risc0/releases/download/v3.0.3/cargo-risczero-x86_64-unknown-linux-gnu.tgz -o "$task_tools/cargo-risczero.tgz"
curl -fL --max-time 60 https://github.com/risc0/rust/releases/download/r0.1.97.0/rust-toolchain-x86_64-unknown-linux-gnu.tar.gz -o "$task_tools/risc0-rust.tgz"
python3 - "$task_tools" <<'PY'
import hashlib, pathlib, sys
p = pathlib.Path(sys.argv[1])
for name, digest in {
    'cargo-risczero.tgz': '71a0adaa64235be13e9b8471bea5c4ded64bf97c6bd1eb9c2285b966c0b62fee',
    'risc0-rust.tgz': '100b597d605b706bec94e1d32bfaaf5851df8d75173f986d4b56a3e90916be53',
}.items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest() == digest, name
PY
tar -xzf "$task_tools/cargo-risczero.tgz" -C "$task_tools"
mkdir -p "$task_tools/risc0-rust"
tar -xzf "$task_tools/risc0-rust.tgz" -C "$task_tools/risc0-rust"
rustup toolchain link kpi-risc0 "$task_tools/risc0-rust"
# Official r0vm already contains the exact recursion artifact needed by crate build.rs.
# This uses RECURSION_SRC_PATH, a supported build input; no dependency is patched.
python3 - "$task_tools" <<'PY'
import hashlib, pathlib, sys
p = pathlib.Path(sys.argv[1]); data = (p/'r0vm').read_bytes()
size = 59768781; expected = '744b999f0a35b3c86753311c7efb2a0054be21727095cf105af6ee7d3f4d8849'
offset = 0
while True:
    offset = data.find(b'PK\x03\x04', offset)
    if offset < 0: raise SystemExit('Exact upstream recursion ZIP not found in release binary')
    content = data[offset:offset+size]
    if len(content) == size and hashlib.sha256(content).hexdigest() == expected:
        (p/'recursion_zkr.zip').write_bytes(content); break
    offset += 4
PY
printf 'Toolchain ready at %s\n' "$task_tools"
