#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ -v RISC0_DEV_MODE ]]; then
    printf 'RISC0_DEV_MODE must be absent; development receipts are prohibited.\n' >&2
    exit 1
fi
task_tools="${KPI_LANE_TOOLS:-/workspace/scratch/kpi-lane-tools}"
task_evidence="${1:-evidence/reproduced}"
task_toolchain="${KPI_RISC0_TOOLCHAIN:-kpi-risc0}"
export RECURSION_SRC_PATH="$task_tools/recursion_zkr.zip"
export RISC0_SERVER_PATH="$task_tools/r0vm"
export RISC0_PROVER=ipc
export RAYON_NUM_THREADS=4
python3 - <<'PY'
import pathlib, tomllib
for filename in ['Cargo.lock', 'guest/Cargo.lock']:
    packages = tomllib.loads(pathlib.Path(filename).read_text())['package']
    for p in packages:
        source = p.get('source', '')
        if 'github.com/kaspanet/rusty-kaspa' in source:
            assert source.endswith('#01b532e8b553523216471682649693af92f0fd16'), source
        if 'github.com/kaspanet/vprogs' in source:
            assert source.endswith('#f9b84a863a7c7c20586a9cf947550475e894f72e'), source
PY
cargo build --locked -p kpi-lane-host
cargo test --locked -p kpi-lane-host
mkdir -p "$task_evidence"
target/debug/kpi-lane-host fixture "$task_evidence"
python3 independent_executor.py "$task_evidence/kaspa-fixture.json" > "$task_evidence/independent-executor.json"
(
    cd guest
    RUSTFLAGS='-C passes=lower-atomic -C link-arg=-Ttext=0x00200800 -C link-arg=--fatal-warnings -C panic=abort --cfg getrandom_backend="custom"' \
        cargo +"$task_toolchain" build --locked --release --target riscv32im-risc0-zkvm-elf
)
task_elf=guest/target/riscv32im-risc0-zkvm-elf/release/kpi-lane-guest
python3 measure.py "$task_evidence/resource-usage.json" "$task_evidence/run.log" \
    target/debug/kpi-lane-host prove "$task_evidence" "$task_elf"
target/debug/kpi-lane-host verify "$task_evidence" "$task_elf" > "$task_evidence/reverification.log" 2>&1
python3 independent_executor.py "$task_evidence/kaspa-fixture.json" > "$task_evidence/independent-executor.json"
python3 check_independent.py "$task_evidence/kaspa-fixture.json" > "$task_evidence/independent-negative-checks.json"
python3 - "$task_evidence" <<'PY'
import hashlib, json, pathlib, sys
p = pathlib.Path(sys.argv[1])
files = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in p.iterdir() if f.is_file() and f.name != 'sha256.json'}
(p/'sha256.json').write_text(json.dumps(files, indent=2)+'\n')
PY
printf 'Offline evidence saved to %s\n' "$task_evidence"
