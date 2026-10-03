#!/usr/bin/env bash
# Foreground, loopback-only node. Stop with Ctrl-C; data stays in ignored .local.
set -euo pipefail
kpi_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$kpi_root"
printf '%s\n' 'adf711b68abb2fabbb33cfdaab8f915bb615f8d7d1b33a867328b4672ddd376f  .local/node/bin/kaspad' | sha256sum --check
if [[ -f .local/node/pid ]] && kill -0 "$(cat .local/node/pid)" 2>/dev/null; then
    echo 'Recorded node process still exists; inspect before starting another.' >&2
    exit 1
fi
printf '%s\n' "$$" > .local/node/pid
exec .local/node/bin/kaspad --testnet --utxoindex \
    --appdir=.local/node/data --logdir=.local/node/logs \
    --rpclisten=127.0.0.1:16210 --rpclisten-borsh=127.0.0.1:17210 \
    --rpclisten-json=127.0.0.1:18210 --listen=127.0.0.1:16211 \
    --maxinpeers=0 --disable-upnp --ram-scale=0.3 --outpeers=4
