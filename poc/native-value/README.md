# Public native-test-KAS based-app cycle

This is a remote, public-account integration experiment following PR31. It uses
native test-KAS only. Public user balances are temporary test state, with no
privacy, production-safety or permissionless-recovery claim. See
[MAPPING](MAPPING.md) for source pins/enforcement and
[ADR-0004](../../docs/adr/0004-public-based-app-native-value.md) for the bounded decision.

## Components and locations

- Cloud `/workspace/kaspa-privacy-initiative`: code/builds, execution profiles,
  real CPU RISC Zero proving, independent checks and evidence.
- Existing VPS `/opt/kpi-pr31-cloud-20261017/native-value`: finite drivers,
  locally built host executable, public guest/program, captures and receipts.
- Existing `kpi-tn10` node, unchanged; JSON RPC `ws://127.0.0.1:18210`.
- Existing authenticated admin terminal and inherited proxy/credential binding;
  use [PR31 connection setup](../lane-completeness/integration/README.md).
  No laptop process, public RPC, VPN, new listener, node restart or Rust install
  on the VPS. Sponsor key remains at the existing protected path; each new user
  key is created under the VPS-only `native-value/secrets/`, mode 0600.

The account runtime/ABI/permission components come from pinned vProgs. The
monolithic guest directly proves their execution together with PR31's lane
relation. It does **not** simulate the full recursive vProgs runner. See
[encoder provenance](host/ORIGIN.md). State-covenant rent is 1 test-KAS;
permission rent is 0.5, paid separately by the sponsor and returned on final
claim payout. A 4-test-KAS principal withdrawal therefore pays 4.5 at L1,
including that explicit rent refund; the reserve supplies only the principal.

## Build and offline checks in Cloud

Use pinned Rust 1.91.0 for the host and the official RISC Zero toolchain retained
by [bootstrap.sh](../lane-completeness/bootstrap.sh) for the guest. The actual
managed environment activates these with `/workspace/.onboarding/activate.sh`.
Do not set `RISC0_DEV_MODE`. Lockfiles are mandatory; Cargo's master git refs
must resolve to `01b532e8...`, not current Rust-1.95 master.

```bash
set -euo pipefail
source /workspace/.onboarding/activate.sh
export RISC0_SERVER_PATH=/workspace/scratch/kpi-lane-tools/r0vm
export RECURSION_SRC_PATH=/workspace/scratch/kpi-lane-tools/recursion_zkr.zip
export RISC0_PROVER=ipc
export RAYON_NUM_THREADS=4
cargo build --locked --release --manifest-path poc/native-value/Cargo.toml
cargo test --locked --release --manifest-path poc/native-value/Cargo.toml -- --nocapture
cargo fmt --manifest-path poc/native-value/Cargo.toml -p kpi-native-common -p kpi-native-host --check
node poc/lane-completeness/integration/test-exact-json.mjs
python3 poc/lane-completeness/integration/check_rpc_derivatives.py

RUSTFLAGS='-C passes=lower-atomic -C link-arg=-Ttext=0x00200800 -C link-arg=--fatal-warnings -C panic=abort --cfg getrandom_backend="custom"' \
  cargo +kpi-risc0 build --locked --release --manifest-path poc/native-value/guest/Cargo.toml \
  --target riscv32im-risc0-zkvm-elf
mkdir -p .local/native-value
.local/ci-target/release/kpi-native-host wrap \
  .local/ci-target/riscv32im-risc0-zkvm-elf/release/kpi-native-guest \
  .local/native-value/guest.program.bin
```

`wrap` encodes the ELF with the v1compat kernel and prints its image ID. It is a
build operation, not proof generation. The executed program's identity is
`52c214c2a4789cb882ac7f4c25996bcba3e0693dec1c8c0c1c093f262dcc6cf0`.

Before funding, exercise representative synthetic inputs with `representative`
and `profile`. Profiling is **execution only**, no receipt and no proof claim.
The guest pads short executions operationally to help target lift-20; a
host-supplied cycle counter never decides account validity. Every actual input
must profile as exactly `[20]` before proving on this fixed covenant. Payloads,
SMT paths and witnesses affect the shape; an operation count is insufficient.

## Remote trial and actual stage commands

The exact executed names are `host-v1` / `guest-v1.program.bin`, `run-v1.mjs`
for input production, `recut-v1.mjs` for read-only resegmentation, then
`host-v2` / `run-v3.mjs` for authorization and settlement/payout. The v2 host
adds a recipient-mutation test utility; it does not change guest or covenant
logic. The following helpers transfer public artifacts over the existing admin
terminal and refuse overwrites:

```bash
node poc/lane-completeness/integration/upload.mjs \
  .local/ci-target/release/kpi-native-host native-value/host-v2
node poc/lane-completeness/integration/upload.mjs \
  .local/native-value/guest.program.bin native-value/guest-v1.program.bin
python3 poc/lane-completeness/integration/remote.py put \
  poc/lane-completeness/integration/exact-json.mjs native-value/exact-json.mjs
python3 poc/lane-completeness/integration/remote.py put \
  poc/lane-completeness/integration/capture.mjs native-value/capture.mjs
python3 poc/lane-completeness/integration/remote.py put \
  poc/native-value/remote/run.mjs native-value/run-v3.mjs
```

For a new reproduction, choose fresh artifact suffixes in the script constants
and transfer to those suffixes, preserving existing artifacts. `init` is one
command that creates a fresh unfunded trial namespace/user wallet and prints only
its public trial path. Never replay an old submission intent. If a terminal
fails after broadcast, inspect the stored intent and real node outcome before
any next mutation; no automatic resubmission.

```bash
python3 poc/lane-completeness/integration/remote.py exec \
  '/opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/native-value/run-v3.mjs init'
```

The remaining commands are **VPS commands issued via `remote.py exec`**, with
`TRIAL` replaced by that printed public path. Run each finite stage with
`systemd-run --collect --property=Type=exec`, project WorkingDirectory and append
stdout/stderr log paths under the trial; this survives terminal loss. The
executed units were `kpi-native-prepare-47c6d76b`, `kpi-native-auth-47c6d76b` and
`kpi-native-prefix-47c6d76b` (later units are recorded with results).

```bash
/opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/native-value/run-v3.mjs prepare TRIAL
/opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/native-value/run-v3.mjs auth-negative TRIAL
```

Preparation funds the user's native wallet with 12 test-KAS (10 principal plus
separate action fees), seeds a fresh lane, bootstraps zero app balance, publishes
the real deposit, unauthorized command, valid withdrawal and copied-command
replay, then captures them. Invalid app commands stay in the lane and become
provable no-ops. It writes public inputs only after native ordering checks pass.

Download public input/profile files through `remote.py get`. Always wait for a
completed preparation/recut marker and compare downloaded input hashes; copying
files while resegmentation runs can return the old version. Preserve failures.
The executed original final interval profiled `[20,17]`. The read-only
`recut.mjs` moved the original inputs/metadata into `original-segmentation/`,
recaptured at the unauthorized-command checkpoint and retained all original raw
responses. No transaction was rebroadcast and no guest/covenant identity changed.
Both resulting valid inputs and the omission input profiled `[20]`.

Real proving runs **in Cloud**, one proof at a time (approximately 9.1 GiB peak
individual-process RSS; do not parallelize on this environment):

```bash
set -euo pipefail
# INPUT and NEW_PROOF_DIR are public Cloud paths; PROGRAM is the wrapped program.
python3 poc/lane-completeness/measure.py RESOURCES_JSON PROOF_LOG \
  .local/ci-target/release/kpi-native-host prove INPUT PROGRAM NEW_PROOF_DIR
```

This verifies the real succinct receipt in the SDK and compares the exact
352-byte journal with native execution; fake/development receipts are rejected.
Transfer each resulting `receipt.bin` with `upload.mjs` into its trial as
`prefix-receipt.bin`, `final-receipt.bin` or `omission-receipt.bin`.

The VPS stage order is:

```bash
/opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/native-value/run-v3.mjs settle TRIAL prefix
/opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/native-value/run-v3.mjs settle TRIAL omission
/opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/native-value/run-v3.mjs settle TRIAL final
/opt/kpi-cloud-https/bin/node /opt/kpi-pr31-cloud-20261017/native-value/run-v3.mjs payout TRIAL
```

The omission removes the valid withdrawal but retains its original legitimate
start/end checkpoints and end SMT witness. Its internally valid receipt derives
a different lane tip/seqcommit, so native settlement must reject against the real
end anchor. The builder intentionally uses that derived commitment only for
local budget sizing, never substitutes it for the node's accessor. This is
separate from the legitimate shorter prefix, which is allowed to settle.

Payout sends balanced underpayment/reserve/receiver mutations, then the real
permission/delegate spend, then a **distinct** transaction replaying the now-spent
claim inputs. The actual node rejection and spentness observations, not merely
a local host assertion, are the required outcomes. The final payout uses ten
selected-chain confirmations before querying recipient/reserve UTXOs.

No completion/readiness claim is valid until real settlement **and** the native
terminal payout have succeeded. If an essential mechanism fails, retain the
specific evidence and state exactly which transition did not execute.

## Public-only verification

After decompressing the recorded evidence, verify the receipt without any wallet
or node. This also verifies a real omission receipt as a *computation*; the
reported `nativeAnchorChecked:false` deliberately distinguishes that SDK check
from the actual TN10 rejection at the canonical endpoint.

```bash
cargo build --locked --release --manifest-path poc/native-value/Cargo.toml --bin kpi-native-verify
.local/ci-target/release/kpi-native-verify INPUT PROGRAM RECEIPT
PYTHONPATH=.local/pr31/python python3 poc/native-value/audit.py poc/native-value/evidence
```

The Python audit independently reconstructs state hashes and all journal fields,
recomputes native transaction IDs and actual fees from public funding entries,
checks original-file hashes and follows the principal from deposit through
permission into payout/change. It does not implement a cryptographic verifier.
For lane reconstruction, use the retained `integration/check_capture.py` against
each saved capture with lane `6b2756b200000000000000000000000000000000`.

The bounded guest does not establish continued withdrawal after a long idle gap.
The remaining six test-KAS are reserved and audited; independent recovery or
continued spendability after such a gap must not be inferred. See
[the explicit limitation](ADVERSARIAL-REVIEW.md).
