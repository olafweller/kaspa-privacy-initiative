#!/usr/bin/env bash
set -euo pipefail
test -z "${RISC0_SKIP_BUILD_KERNELS+x}" && test -z "${DOCS_RS+x}"
task_apt_options=()
if [[ -f /run/secrets/system_ca ]]; then
  export CURL_CA_BUNDLE=/run/secrets/system_ca SSL_CERT_FILE=/run/secrets/system_ca
  export CARGO_HTTP_CAINFO=/run/secrets/system_ca GIT_SSL_CAINFO=/run/secrets/system_ca
  export RUSTUP_USE_CURL=1
  task_apt_options=(-o Acquire::https::CaInfo=/run/secrets/system_ca)
fi
export DEBIAN_FRONTEND=noninteractive
apt-get "${task_apt_options[@]}" update
apt-get "${task_apt_options[@]}" install -y --no-install-recommends \
  ca-certificates curl git build-essential pkg-config libssl-dev libgmp-dev \
  clang cmake protobuf-compiler python3 \
  cuda-nvcc-12-8 cuda-cudart-dev-12-8 cuda-driver-dev-12-8 cuda-cccl-12-8
curl --proto '=https' --tlsv1.2 -fsS https://sh.rustup.rs -o /tmp/rustup-init.sh
bash /tmp/rustup-init.sh -y --profile minimal --default-toolchain 1.89.0
if [[ ! -d /tmp/risc0/.git ]]; then
  git init /tmp/risc0
  git -C /tmp/risc0 remote add origin https://github.com/risc0/risc0.git
fi
test "$(git -C /tmp/risc0 remote get-url origin)" = https://github.com/risc0/risc0.git
git -C /tmp/risc0 fetch --depth 1 origin 14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6
git -C /tmp/risc0 reset --hard FETCH_HEAD
git -C /tmp/risc0 clean -ffdqx
test "$(git -C /tmp/risc0 rev-parse HEAD)" = 14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6
echo '744b999f0a35b3c86753311c7efb2a0054be21727095cf105af6ee7d3f4d8849  /opt/build/recursion_zkr.zip' | sha256sum --check
export RECURSION_SRC_PATH=/opt/build/recursion_zkr.zip
export NVCC_APPEND_FLAGS=-arch=sm_89
# Upstream's Linux build selects Clang; GCC's generated Keccak CPU kernels
# are exceptionally slow to compile. This affects the build, not proof limits.
export CC=clang CXX=clang++
export CARGO_BUILD_JOBS=4
export CARGO_TARGET_DIR=/opt/cuda-target
cd /tmp/risc0
cargo +1.89.0 build --locked --release -p risc0-r0vm --features cuda,disable-dev-mode
install -D -m 0755 /opt/cuda-target/release/r0vm /opt/kpi/bin/r0vm-cuda
python3 - <<'PY'
import hashlib,json,subprocess
from pathlib import Path
p=Path('/opt/kpi/bin/r0vm-cuda')
report={'sourceCommit':'14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6',
        'sdkVersion':'3.0.3','features':['cuda','disable-dev-mode'],
        'nvccFlags':'-arch=sm_89','binarySha256':hashlib.sha256(p.read_bytes()).hexdigest(),
        'upstreamCargoLockSha256':hashlib.sha256(Path('Cargo.lock').read_bytes()).hexdigest(),
        'rustVersion':subprocess.check_output(['rustc','+1.89.0','--version'],text=True).strip(),
        'nvccVersion':subprocess.check_output(['nvcc','--version'],text=True),
        'cxxVersion':subprocess.check_output(['clang++','--version'],text=True),
        'buildJobs':4,
        'gpuExecutionQualified':False}
Path('/opt/kpi/cuda-build.json').write_text(json.dumps(report,indent=2)+'\n')
PY
# Retain provenance, not a compiler cache or this session's trust bundle.
dpkg-query -W > /opt/kpi/build-packages.txt
rm -rf /tmp/rustup-init.sh /opt/cargo /opt/rustup /var/lib/apt/lists/*
