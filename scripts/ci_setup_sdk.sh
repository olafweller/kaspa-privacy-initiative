#!/usr/bin/env bash
# Install only the public pinned SDK for offline tests; no node or wallet setup.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
kpi_ci_sdk=.local/sdk/kaspa-wasm32-sdk-v2.1.0.zip
mkdir -p .local/sdk
if [[ ! -f "$kpi_ci_sdk" ]]; then
    curl --fail --location --retry 3 --output "$kpi_ci_sdk" \
        https://github.com/kaspanet/rusty-kaspa/releases/download/v2.1.0/kaspa-wasm32-sdk-v2.1.0.zip
fi
sha256sum --check <<'SUM'
ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124  .local/sdk/kaspa-wasm32-sdk-v2.1.0.zip
SUM
unzip -qo "$kpi_ci_sdk" 'kaspa-wasm32-sdk/nodejs/kaspa/*' -d .local/sdk
