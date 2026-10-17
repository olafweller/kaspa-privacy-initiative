#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
task_context="${1:?provide fresh build context directory}"
task_image="${2:?provide local image name}"
test ! -e "$task_context"
mkdir -p "$task_context"
cp poc/remote-cuda/{Dockerfile,build_cuda.sh,common.py,worker.py,service.py} "$task_context/"
cp -a .local/remote-cuda-preparation/dist "$task_context/dist"
task_zkr="${3:-/workspace/scratch/kpi-lane-tools/recursion_zkr.zip}"
if [[ -f "$task_zkr" ]]; then
  cp "$task_zkr" "$task_context/recursion_zkr.zip"
else
  curl --proto '=https' --tlsv1.2 -fsS \
    https://risc0-artifacts.s3.us-west-2.amazonaws.com/zkr/744b999f0a35b3c86753311c7efb2a0054be21727095cf105af6ee7d3f4d8849.zip \
    -o "$task_context/recursion_zkr.zip"
fi
echo "744b999f0a35b3c86753311c7efb2a0054be21727095cf105af6ee7d3f4d8849  $task_context/recursion_zkr.zip" | sha256sum --check
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock build --platform linux/amd64 \
  --secret id=system_ca,src=/etc/ssl/certs/ca-certificates.crt \
  -t "$task_image" "$task_context"
