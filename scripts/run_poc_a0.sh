#!/usr/bin/env bash
# Local proof/validation. The live subcommands prepare files, never broadcast.
set -euo pipefail

kpi_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
kpi_upstream="$(dirname -- "$kpi_root")/upstream/rusty-kaspa"
kpi_revision=01b532e8b553523216471682649693af92f0fd16

if [[ ! -e "$kpi_upstream" ]]; then
    mkdir -p -- "$(dirname -- "$kpi_upstream")"
    git clone --depth 1 --branch v2.1.0 -- \
        https://github.com/kaspanet/rusty-kaspa.git "$kpi_upstream"
fi
if [[ "$(git -C "$kpi_upstream" rev-parse HEAD)" != "$kpi_revision" ]]; then
    echo "Refusing unpinned upstream: expected $kpi_revision at $kpi_upstream" >&2
    exit 1
fi
if [[ -n "$(git -C "$kpi_upstream" status --porcelain --untracked-files=all)" ]]; then
    echo "Refusing modified upstream checkout: $kpi_upstream" >&2
    exit 1
fi

command -v cargo >/dev/null || {
    echo 'Install Rust 1.91.0 with rustup and add its bin directory to PATH.' >&2
    exit 1
}
# Bindgen may need GCC's builtin C headers in minimal cloud images.
if [[ -z "${BINDGEN_EXTRA_CLANG_ARGS:-}" ]] && command -v cc >/dev/null; then
    kpi_c_headers="$(cc -print-file-name=include)"
    if [[ -f "$kpi_c_headers/stdbool.h" ]]; then
        export BINDGEN_EXTRA_CLANG_ARGS="-isystem $kpi_c_headers"
    fi
fi
# Select an installed LLVM library directory when the minimal image has no
# llvm-config executable. Keep the selection stable across build and test runs.
if [[ -z "${LIBCLANG_PATH:-}" ]]; then
    for kpi_clang_lib in /usr/lib/llvm-*/lib; do
        if compgen -G "$kpi_clang_lib/libclang*.so*" >/dev/null; then
            export LIBCLANG_PATH="$kpi_clang_lib"
            break
        fi
    done
fi
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-4}"
cd -- "$kpi_root/poc/a0"
case "${1:-run}" in
    run) exec cargo +1.91.0 run --locked --release ;;
    test) exec cargo +1.91.0 test --locked --release ;;
    live) shift; exec cargo +1.91.0 run --locked --release -- live "$@" ;;
    *) echo 'Usage: scripts/run_poc_a0.sh [run|test|live init|prepare|check ...]' >&2; exit 2 ;;
esac
