#!/usr/bin/env bash
# File-only A1 runner. No node management, network submissions or funding.
set -euo pipefail
kpi_a1_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
kpi_a1_upstream="$(dirname -- "$kpi_a1_root")/upstream/rusty-kaspa"
[[ "$(git -C "$kpi_a1_upstream" rev-parse HEAD)" == 01b532e8b553523216471682649693af92f0fd16 ]] || { echo 'Pinned upstream checkout required.' >&2; exit 1; }
[[ -z "$(git -C "$kpi_a1_upstream" status --porcelain --untracked-files=all)" ]] || { echo 'Upstream must be clean.' >&2; exit 1; }
command -v cargo >/dev/null || { echo 'Add Rust 1.91.0 rustup binaries to PATH.' >&2; exit 1; }
if [[ -z "${BINDGEN_EXTRA_CLANG_ARGS:-}" ]] && command -v cc >/dev/null; then
    kpi_a1_headers="$(cc -print-file-name=include)"
    [[ ! -f "$kpi_a1_headers/stdbool.h" ]] || export BINDGEN_EXTRA_CLANG_ARGS="-isystem $kpi_a1_headers"
fi
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-4}"
export RAYON_NUM_THREADS="${RAYON_NUM_THREADS:-4}"
cd -- "$kpi_a1_root/poc/a1"
case "${1:-test}" in
    build) exec cargo +1.91.0 build --locked --release --bins ;;
    test) exec cargo +1.91.0 test --locked --release -- --test-threads=2 ;;
    experiment|stateful|prepare-body|validate-body|check-backup|fresh-terminal|fresh-continue|native-path|native-checkpoint)
        exec cargo +1.91.0 run --locked --release --bin kpi-poc-a1 -- "$@" ;;
    *) echo 'Usage: run_poc_a1.sh build|test|experiment NEW_DIR|stateful BUNDLE|validate-body REQUEST|fresh-terminal BUNDLE BRANCH SECRET REQUEST OUTPUT' >&2; exit 2 ;;
esac
