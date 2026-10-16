# Remote TN10 KPI integration

This directory is a thin adapter around existing Kaspa/vProgs code and the
retained monolithic public KPI guest. Read [upstream reuse](UPSTREAM-REUSE.md)
and [current results](../RESULTS.md) before running anything. The scripts can
spend test-KAS; they require the owner's current TN10 authorization.

## Execution locations

- Codex Cloud: source inspection, pinned Rust build, independent Python checks,
  real CPU proof generation and Git publication. No laptop process participates.
- Owner VPS: existing root webterminal, unchanged TN10 node, localhost wRPC,
  test-fee wallet, transaction construction/submission, capture and confirmation.
- Project directory on VPS: `/opt/kpi-pr31-cloud-20261017`, mode 0700. The key is
  `test-wallet.key`, mode 0600. Never transfer it with evidence or print it.

The existing node exposes native wRPC locally at `127.0.0.1:17210` (Borsh) and
`127.0.0.1:18210` (JSON), plus gRPC at `127.0.0.1:16210`. The JSON client talks
directly to localhost; the SDK's missing convenience method for lane proofs
does not require a new public RPC endpoint. `getHeaders` returned "Not
implemented"; capture follows selected parents using supported `getBlock`.

## Cloud bootstrap and build

From the repository root in the existing Cloud environment:

```bash
source /workspace/.onboarding/activate.sh
npm install --prefix .local/codex-cloud-tn10/http-client --save-exact --ignore-scripts --no-audit --no-fund ws@8.22.0 https-proxy-agent@9.1.0
mkdir -p .local/codex-cloud-tn10/admin
curl --fail --silent --show-error --max-time 20 \
  -H "Authorization: Bearer $TN10_RPC_TOKEN" \
  -o .local/codex-cloud-tn10/admin/vps-exec.mjs \
  https://vmi3633138.contaboserver.net/admin/client.mjs
printf '%s\n' '445870f69461ca0e23934301de3eeeba008aed5b524436da1b255c65f6f8a072  .local/codex-cloud-tn10/admin/vps-exec.mjs' | sha256sum --check
KPI_LANE_TOOLS=/workspace/scratch/kpi-lane-tools bash poc/lane-completeness/bootstrap.sh
export RECURSION_SRC_PATH=/workspace/scratch/kpi-lane-tools/recursion_zkr.zip
cargo build --locked --release --manifest-path poc/lane-completeness/integration/Cargo.toml
cargo test --locked --release --manifest-path poc/lane-completeness/vendor/wallet/Cargo.toml
```

The existing destination-scoped `TN10_RPC_TOKEN` is authorized for the root
terminal in this environment. Keep inherited proxy/CA settings and normal TLS
verification. Never print its value or enable shell tracing. The terminal client
checksum and transport were established before this work. `remote.py` uses that
same client and credential; it does not create network infrastructure.

The retained guest's program bytes are reused unchanged, image ID
`0881c8caf405ccaf72c41e3c8a0a3a7dd48a4aaf55f040c4de2d759a6c4226f1`.
The broader bootstrap script also installs its original guest toolchain, although
this trial does not rebuild or change the guest. The integration enables the explicit `monolithic-lift19` covenant feature.
The historical offline build keeps lift-20 by default. This circuit identity is
fixed into each new covenant at bootstrap; other segment shapes are unsupported.
The integration lockfile pins
Kaspa `01b532e8...` and vProgs `f9b84a8...`; do not resolve floating master heads
when reproducing the recorded run.

## Prepare a new trial on the VPS

`remote.py put`/`upload.mjs` refuse to overwrite files. On this VPS the recorded
artifacts already exist: verify their hashes and reuse them. On an empty project
directory, upload public scripts/artifacts, run `create-wallet.mjs` once, fund
only its `kaspatest:` address with TN10 test-KAS, and check its balance via the
local node. The wallet creation script is supplied for future fresh setup;
the recorded wallet was created by the equivalent exclusive-write shell command.

```bash
node poc/lane-completeness/integration/upload.mjs .local/ci-target/release/kpi-tn10-integration kpi-tn10-integration-lift19
node poc/lane-completeness/integration/upload.mjs poc/lane-completeness/evidence/offline/guest.program.bin guest.program.bin
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/capture.mjs capture-v2.mjs
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/run-trial.mjs run-trial-v4.mjs
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/settle-trial.mjs settle-trial-v3.mjs
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/create-wallet.mjs create-wallet.mjs
```

Run the finite input stage detached through `systemd-run`. Give each invocation a
fresh unit name. `run-trial.mjs` creates a new namespace, covenant and trial
directory in one invocation. A failed identity is preserved and never rebroadcast.

```bash
python3 poc/lane-completeness/integration/remote.py exec 'systemd-run --unit=kpi-pr31-input-NEW --property=WorkingDirectory=/opt/kpi-pr31-cloud-20261017 --property=UMask=0077 --property=Nice=10 --property=StandardOutput=append:/opt/kpi-pr31-cloud-20261017/input-NEW.log --property=StandardError=append:/opt/kpi-pr31-cloud-20261017/input-NEW.log /opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/run-trial-v4.mjs'
```

Read its log and `prepared.json`. Substitute the actual generated `trial-*`
basename below. The stage seeds the lane outside the measured interval,
bootstraps one test-KAS into the covenant, confirms operations 1–3, captures
the fixed interval, rechecks chain membership/order and exports guest input.
It writes submission intents **before** every broadcast. If transport fails,
inspect those intents and the node first; never automatically repeat a mutation.
Recent confirmation counts are observations, not finality guarantees. A lost
checkpoint/reorg or an interval outside the old guest's supported 100-score span
is preserved as an unsuccessful trial, without relaxing the guest relation.

## Real proof and settlement

```bash
python3 poc/lane-completeness/integration/remote.py get TRIAL/input.json .local/pr31/kpi-input.json
python3 poc/lane-completeness/integration/remote.py get TRIAL/capture.json .local/pr31/kpi-capture.json
RISC0_PROVER=ipc RISC0_SERVER_PATH=/workspace/scratch/kpi-lane-tools/r0vm RAYON_NUM_THREADS=4 \
  python3 poc/lane-completeness/measure.py .local/pr31/live-proof-resources.json .local/pr31/live-proof.log \
  .local/ci-target/release/kpi-tn10-integration prove .local/pr31/kpi-input.json .local/pr31/live-proof \
  poc/lane-completeness/evidence/offline/guest.program.bin
node poc/lane-completeness/integration/upload.mjs .local/pr31/live-proof/full.receipt.bin TRIAL/full.receipt.bin
python3 poc/lane-completeness/integration/remote.py exec 'systemd-run --unit=kpi-pr31-settle-NEW --property=WorkingDirectory=/opt/kpi-pr31-cloud-20261017 --property=UMask=0077 --property=Nice=10 --property=StandardOutput=append:/opt/kpi-pr31-cloud-20261017/settle-NEW.log --property=StandardError=append:/opt/kpi-pr31-cloud-20261017/settle-NEW.log /opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/settle-trial-v3.mjs /opt/kpi-pr31-cloud-20261017/TRIAL'
```

`RISC0_DEV_MODE` must be **absent**. The builder verifies the receipt image and
exact expected journal, requires a succinct receipt and matches the real covenant
UTXO's identity/value/script. The invalid variant changes the claimed successor
state while keeping the valid receipt; fee signatures are computed over that
invalid transaction too. It must fail with a proof-verification error before
the valid transaction is submitted. An unrelated rejection does not pass the
negative control. Finally require accepted ordering, successor UTXO membership,
unchanged covenant value/identity and old-outpoint spentness. All commands remain
remote; finite VPS services continue if the webterminal or laptop disappears.

## Independent reconstruction and validation

```bash
python3 -m pip install --target .local/pr31/python blake3==1.0.8
.local/ci-target/release/kpi-tn10-integration verify LANE_HEX .local/pr31/kpi-capture.json
PYTHONPATH=.local/pr31/python python3 poc/lane-completeness/integration/check_capture.py .local/pr31/kpi-capture.json LANE_HEX
PYTHONPATH=.local/pr31/python python3 poc/lane-completeness/integration/test_capture.py .local/pr31/kpi-capture.json LANE_HEX
```

These are cryptographic commitment checks with two implementations, not zk proof
verification. They use one retained node capture, not two independent nodes.
Per-block reorder controls need two lane transactions in one accepting block;
otherwise the Rust report explicitly says not exercised. Cross-block ordering,
same-anchor omission, ID substitution and malformed/replayed evidence have
separate scoped checks; do not infer an unexecuted control from a passing suite.
