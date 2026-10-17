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
mkdir -p .local/codex-cloud-tn10/admin .local/pr31
curl --fail --silent --show-error --max-time 20 \
  -H "Authorization: Bearer $TN10_RPC_TOKEN" \
  -o .local/codex-cloud-tn10/admin/vps-exec.mjs \
  https://vmi3633138.contaboserver.net/admin/client.mjs
printf '%s\n' '445870f69461ca0e23934301de3eeeba008aed5b524436da1b255c65f6f8a072  .local/codex-cloud-tn10/admin/vps-exec.mjs' | sha256sum --check
KPI_LANE_TOOLS=/workspace/scratch/kpi-lane-tools bash poc/lane-completeness/bootstrap.sh
export RECURSION_SRC_PATH=/workspace/scratch/kpi-lane-tools/recursion_zkr.zip
cargo build --locked --release --manifest-path poc/lane-completeness/integration/Cargo.toml
cp .local/ci-target/release/kpi-tn10-integration .local/pr31/kpi-integration-lift19-v2
cargo build --locked --release --no-default-features --manifest-path poc/lane-completeness/integration/Cargo.toml
cp .local/ci-target/release/kpi-tn10-integration .local/pr31/kpi-integration-lift20-v2
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
this trial does not rebuild or change the guest. The integration builds two explicit fixed-circuit variants: default lift-19,
and lift-20 with `--no-default-features`. The historical offline build keeps
lift-20 by default. Profile the actual input before selecting a new covenant;
its circuit is then fixed for that identity. Other shapes remain unsupported.
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
node poc/lane-completeness/integration/upload.mjs .local/pr31/kpi-integration-lift19-v2 kpi-tn10-integration-lift19-v2
node poc/lane-completeness/integration/upload.mjs .local/pr31/kpi-integration-lift20-v2 kpi-tn10-integration-lift20-v2
node poc/lane-completeness/integration/upload.mjs poc/lane-completeness/evidence/offline/guest.program.bin guest.program.bin
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/capture.mjs capture-v2.mjs
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/run-trial.mjs run-trial-v5.mjs
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/settle-trial.mjs settle-trial-v4.mjs
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/create-wallet.mjs create-wallet.mjs
python3 poc/lane-completeness/integration/remote.py put poc/lane-completeness/integration/bootstrap-trial.mjs bootstrap-trial-v1.mjs
```

Run the finite input stage detached through `systemd-run`. Give each invocation a
fresh unit name. `run-trial.mjs` creates a new namespace, covenant and trial
directory in one invocation. A failed identity is preserved and never rebroadcast.

```bash
python3 poc/lane-completeness/integration/remote.py exec 'systemd-run --unit=kpi-pr31-input-NEW --property=WorkingDirectory=/opt/kpi-pr31-cloud-20261017 --property=UMask=0077 --property=Nice=10 --property=StandardOutput=append:/opt/kpi-pr31-cloud-20261017/input-NEW.log --property=StandardError=append:/opt/kpi-pr31-cloud-20261017/input-NEW.log /opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/run-trial-v5.mjs'
```

Read its log and `input-prepared.json`. Substitute the actual generated `trial-*`
basename below. The stage seeds the lane outside the measured interval, confirms operations
1–3, captures the fixed interval, rechecks chain membership/order and exports
`profile-input.json` with a placeholder covenant identity. This file is only
for execution profiling, never real proving or settlement. The next stage
bootstraps a catch-up checkpoint at that known seed tip and initial public state;
this does not establish an arbitrary deployment/first-touch history.
It writes submission intents **before** every broadcast. If transport fails,
inspect those intents and the node first; never automatically repeat a mutation.
Recent confirmation counts are observations, not finality guarantees. A lost
checkpoint/reorg or an interval outside the old guest's supported 100-score span
is preserved as an unsuccessful trial, without relaxing the guest relation.

## Profile, bootstrap, real proof and settlement

The workload's SMT path can change the required circuit size. First profile it
without creating a receipt. Transfer that public result and deploy the selected
fixed-circuit covenant, preserving the earlier capture:

```bash
python3 poc/lane-completeness/integration/remote.py get TRIAL/profile-input.json .local/pr31/profile-input.json
RISC0_SERVER_PATH=/workspace/scratch/kpi-lane-tools/r0vm .local/pr31/kpi-integration-lift19-v2 profile .local/pr31/profile-input.json poc/lane-completeness/evidence/offline/guest.program.bin > .local/pr31/execution-profile.json
python3 poc/lane-completeness/integration/remote.py put .local/pr31/execution-profile.json TRIAL/execution-profile.json
python3 poc/lane-completeness/integration/remote.py exec 'systemd-run --unit=kpi-pr31-bootstrap-NEW --property=WorkingDirectory=/opt/kpi-pr31-cloud-20261017 --property=UMask=0077 --property=Nice=10 /opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/bootstrap-trial-v1.mjs /opt/kpi-pr31-cloud-20261017/TRIAL'
```

Wait for `prepared.json`. The real input then contains the actual covenant ID.
Profile it again and require the same single-segment `po2` as the deployment
before spending time proving. Profiling is **not a cryptographic proof** and
uses no development receipt. Generate a real receipt only from the real input:

```bash
python3 poc/lane-completeness/integration/remote.py get TRIAL/input.json .local/pr31/kpi-input.json
python3 poc/lane-completeness/integration/remote.py get TRIAL/capture.json .local/pr31/kpi-capture.json
RISC0_PROVER=ipc RISC0_SERVER_PATH=/workspace/scratch/kpi-lane-tools/r0vm RAYON_NUM_THREADS=4 \
  python3 poc/lane-completeness/measure.py .local/pr31/live-proof-resources.json .local/pr31/live-proof.log \
  .local/pr31/kpi-integration-lift19-v2 prove .local/pr31/kpi-input.json .local/pr31/live-proof \
  poc/lane-completeness/evidence/offline/guest.program.bin
node poc/lane-completeness/integration/upload.mjs .local/pr31/live-proof/full.receipt.bin TRIAL/full.receipt.bin
python3 poc/lane-completeness/integration/remote.py exec 'systemd-run --unit=kpi-pr31-settle-NEW --property=WorkingDirectory=/opt/kpi-pr31-cloud-20261017 --property=UMask=0077 --property=Nice=10 --property=StandardOutput=append:/opt/kpi-pr31-cloud-20261017/settle-NEW.log --property=StandardError=append:/opt/kpi-pr31-cloud-20261017/settle-NEW.log /opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/settle-trial-v4.mjs /opt/kpi-pr31-cloud-20261017/TRIAL'
```

The prover command is independent of the host binary's covenant-builder feature:
its receipt records the actual circuit; the selected L1 builder must match it.
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


To check the retained final capture without node access or wallet keys:

```bash
mkdir -p .local/pr31
gzip -dc poc/lane-completeness/evidence/cloud-tn10/kpi-capture.json.gz > .local/pr31/retained-kpi-capture.json
.local/pr31/kpi-integration-lift19-v2 verify 4b353df600000000000000000000000000000000 .local/pr31/retained-kpi-capture.json
PYTHONPATH=.local/pr31/python python3 poc/lane-completeness/integration/check_capture.py .local/pr31/retained-kpi-capture.json 4b353df600000000000000000000000000000000
```

This checks the retained node observation; it does not independently synchronize
consensus or attest that a single node's report is honest. The original raw
responses and final receipt/journal remain separate evidence artifacts.

## Lossless JSON follow-up

The native-value follow-up preserves integer tokens with Node 22's JSON source
context and `JSON.rawJSON`. Current `capture.mjs`, `run-trial.mjs`,
`bootstrap-trial.mjs` and `settle-trial.mjs` import `exact-json.mjs`; deploy that
helper **in the same remote directory** when reproducing these corrected scripts:

```bash
python3 poc/lane-completeness/integration/remote.py put \
  poc/lane-completeness/integration/exact-json.mjs exact-json.mjs
node poc/lane-completeness/integration/test-exact-json.mjs
python3 poc/lane-completeness/integration/check_rpc_derivatives.py
```

Do not overwrite recorded VPS artifact versions while preserving the original
trial. The original RPC strings and proof bytes are unchanged. Derived nonce
corrections and archive-member provenance are recorded in
[integer-correction.json](../evidence/cloud-tn10/integer-correction.json).
The original published rounded derivatives remain available at commit `6810058`;
current derivatives/manifest and public archive contain the exact values. No
historical funding, publication, proving or settlement was repeated for this fix.

The distinct [native-value follow-up](../../native-value/README.md) uses an
isolated VPS subdirectory and separate draft PR32; PR31 remains its milestone.
