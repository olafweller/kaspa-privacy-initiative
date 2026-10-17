#!/usr/bin/env bash
# Finite, detached VPS job. Stop on any unexpected outcome; never retry a broadcast.
set -euo pipefail
native_trial="${1:?public trial path required}"
native_root=/opt/kpi-pr31-cloud-20261017/native-value
native_node=/opt/kpi-cloud-https/bin/node
"$native_node" "$native_root/run-v3.mjs" settle "$native_trial" omission
"$native_node" "$native_root/run-v3.mjs" settle "$native_trial" final
"$native_node" "$native_root/run-v3.mjs" payout "$native_trial"
"$native_node" "$native_root/postcheck.mjs" "$native_trial"
