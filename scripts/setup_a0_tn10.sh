#!/usr/bin/env bash
# Pinned public artifacts only. Does not start a node or access a wallet.
set -euo pipefail
kpi_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$kpi_root"
mkdir -p .local/sdk .local/node
kpi_sdk=.local/sdk/kaspa-wasm32-sdk-v2.1.0.zip
kpi_node=.local/node/rusty-kaspa-v2.1.0-linux-amd64.zip
[[ -f "$kpi_sdk" ]] || curl -fLsS -o "$kpi_sdk" https://github.com/kaspanet/rusty-kaspa/releases/download/v2.1.0/kaspa-wasm32-sdk-v2.1.0.zip
[[ -f "$kpi_node" ]] || curl -fLsS -o "$kpi_node" https://github.com/kaspanet/rusty-kaspa/releases/download/v2.1.0/rusty-kaspa-v2.1.0-linux-amd64.zip
sha256sum --check <<'CHECKSUMS'
ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124  .local/sdk/kaspa-wasm32-sdk-v2.1.0.zip
5ba61c05c013a4856491a8a17666fa73f7bd2aecbfed8affe8ffdc077361dad8  .local/node/rusty-kaspa-v2.1.0-linux-amd64.zip
CHECKSUMS
unzip -qo "$kpi_sdk" 'kaspa-wasm32-sdk/nodejs/kaspa/*' -d .local/sdk
unzip -qo "$kpi_node" bin/kaspad -d .local/node
chmod +x .local/node/bin/kaspad
