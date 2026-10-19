# Staged private/native TN10 preparation

**Offline preparation, not a funded or completed TN10 rehearsal.** PR51's four
real local receipts remain intact. Actual chain data requires new receipts.
The new initialization script is explained in [ADR-0015](../../docs/adr/0015-tn10-private-native-preparation.md)
and must be reviewed before funding. See [runmanifest.json](runmanifest.json)
for release gates and the exact staged plan.

## Build and fresh identity

Use Rust 1.91.0 and the locked pinned dependencies. Reuse the vendored vProgs
wallet/mass helpers already adapted to native pin `01b532e8…`; do not resolve
the `master` dependency names to current upstream. The reviewed guest is
`794cfff4cfa509799ec1f6750678d3fe4bc8623522aa647cc65e6b53955c4bc9`.

```sh
cargo +1.91.0 build --locked --release --manifest-path poc/private-native-tn10/Cargo.toml
TN10_PREP=.local/ci-target/release/kpi-private-native-tn10
"$TN10_PREP" init .local/my-new-unfunded-private-trial
```

`init` is one offline command. It creates fresh Alice/Bob wallet backups and
Bob/sponsor native keys in separate 0700 directories/0600 files. It prints no
keys and creates no UTXO, address balance, provider lease or network operation.
Never archive that directory. Bob's wallet and native recipient are distinct
keys; his role files must be under his control before any actual release.
Local root/operator can access them. This is explicit custody, not cryptographic
isolation from the administrator. Do not use the fixture scalar-one recipient.

## Read-only chain inputs

Manage through the existing Cloud → TN10 gateway route. B remains the independent
rental guard; it is not a second chain executor. On the existing gateway,
`read-only.mjs METHOD PARAMS_JSON NEW_RESPONSE_FILE` permits only the eight
read-only methods in its allowlist, at `ws://127.0.0.1:18210`. It retains raw
JSON without converting response amounts to JS numbers. Never invoke historical
trial `run.mjs` scripts: they can broadcast.

Use the existing `poc/lane-completeness/integration/capture.mjs` for full captures
with explicit start/end endpoints, complete accepted bodies, independent recheck,
minimum confirmations and failure/reorg detection. Derive the lane key with the
native validator's `key` command. If the fixed reviewed lane is inactive, a
future separately released harmless `activate` transaction must first establish
an active inclusion. Preparation cannot create that activity.

```text
seed VALIDATOR EXPECTED_VALIDATOR_SHA CAPTURE NEW_SEED_JSON
build TRIAL_JSON REQUEST_JSON OWN_SPONSOR_KEY NEW_OUTPUT_DIR
checkpoint VALIDATOR EXPECTED_VALIDATOR_SHA ACCEPTANCE_CAPTURE SIGNED_RECORD PREVIOUS_RECORD NEW_CHECKPOINT_DIR
freeze VALIDATOR EXPECTED_VALIDATOR_SHA PROGRAM STAGE CAPTURE CHECKPOINT_JSON NEW_BATCH_DIR
verify TRUSTED_TARGET_JSON EXPECTED_TARGET_SHA RECEIPT NEW_VERIFICATION_DIR
wallet TRIAL_JSON PUBLIC_STATE_BIN OWN_BACKUP PUBLIC_PARAMETERS credit-transfer|exit NEW_OUTPUT_DIR
```

`seed`, `checkpoint` and `freeze` preserve their own capture copy before running
the hash-pinned existing native validator's
full `verify`. Its short-interval `export` is intentionally not used. An active
collapsed inclusion is required. Public input is mapped from **all** accepted
native lane bodies in canonical order, without dropping irrelevant or app-invalid
operations. A verified native endpoint is not an RPC submit-success flag.

## Signed request shapes and order

Every `build` request contains `trial` from the fresh public trial file,
`server` (synced testnet-10 snapshot including `virtualDaaScore`), an actual
`sponsorUtxo` in `RpcUtxosByAddressesEntry` format, and an explicit integer
`feeRateSompiPerGram` at least 100. Choose the rate from a fresh retained fee
quote; it is not a claim about custom node relay settings. The request kind is:

| Kind | Additional fields | Produced/checked result |
| --- | --- | --- |
| `activate` | none | Harmless trial-ID lane carrier; future release only |
| `bootstrap` | `seedPath`, independently retained `seedSha256` | Native genesis ID + lane-restricted rent-only initializer |
| `initialize` | `bootstrapPath`, actual `stateUtxo` | Exact reviewed state script for actual covenant; `state.bin` |
| `deposit` | actual `covenantId`, accepted initialization `checkpointPath`, fresh `stateUtxo` | 1,000M unbound delegate principal, Alice owner descriptor at output zero |
| `publish` | `operationPayloadHex` from role-local wallet output | Actual payload and sponsor signature before final mass/fee measurement |
| `settlement` | `targetPath`, independently retained `targetSha256`, `receiptPath`, actual `stateUtxo`, fresh `anchorBlock` and `selectedParentBlock` RPC block responses | Real receipt verification, exact continuation and optional restricted permission |
| `payout` | `publicStatePath` (C post-state), `exitId`, `permissionTransactionPath` (genuine C settlement), actual `permissionUtxo` and selected `reserveUtxo` | permission0/reserve1/sponsor2; Bob principal+rent0/reserve change1/sponsor change2 |

All builds are **offline** and emit `transaction.json` plus the non-secret request.
No submit path is implemented. Every input script is run on the fully signed
transaction; compute budgets are measured before final signing and rechecked.
Storage mass is committed and compute/storage/transient mass must fit the pinned
native limits. Fee calculations cover the fully signed layout and supplied
integer quote. Reports distinguish consensus estimated serialized bytes from
RPC JSON bytes. All inputs/outputs and fees use checked integer sompi arithmetic.
Principal, state rent, permission rent and sponsor fees are never pooled.

For initialization, `checkpoint` takes the bootstrap record as `PREVIOUS_RECORD`,
and requires both bootstrap and initialization IDs in the complete accepted
capture starting at the verified seed endpoint. It retains the genesis state
and actual continuation outpoint. For subsequent settlements, pass their frozen
`target.json`; the command re-verifies the genuine receipt from the retained
build request, exact accepted transaction and successor script. A checkpoint is
captured historical acceptance, **not a substitute for fresh live spentness and
selected-chain checks before the next spend**.

After each accepted settlement, capture again from the **preceding proof endpoint**,
not from the settlement block. This includes settlement activity in the next
batch. Batches are deposit → credit-transfer → exit → reconcile. Their expected
accounting is enforced by `freeze`. It copies the capture before checking, derives
the complete journal locally, checks state/tip continuity, and writes immutable
input/state/program/journal/target files. Record the printed target SHA on B
before uploading the public package. `wallet credit-transfer` uses the unique
actual registered deposit reference, generates fresh reviewed wallet proofs,
and verifies them against the public ledger. Bob independently discovers his
note and builds `wallet exit` using his own backup and fresh native recipient.
No new setup or fixture deposit/recipient is substituted.

The payout builder derives a build-only permission view by applying the actual
C settlement to C's post-state. This view never replaces the proven checkpoint:
batch D starts at C's original state and processes the full issuance/payout lane.

## Proof waiting, public package and limits

`bundle.py BATCH_DIR EXPECTED_TARGET_SHA NEW_ARCHIVE` packages only the four
allowlisted public files, verifies their hashes, and excludes all role keys.
Copy/retain the exact target on B independently of GPU responses. Run the trusted
CPU `verify` command on returned receipt bytes; it checks the fixed guest/join,
exact journal, real Succinct seal, no assumptions, real mode and existing
cryptographic negative controls. Use `build settlement` to exercise the genuine
receipt on the native script engine; an exit receipt issues the actual restricted
permission, whose real outpoint then feeds the payout builder.

The future `run_stage.py` reuses the existing CUDA sampler/process-group runner,
wraps proof and separate CPU verification in external GNU timeout, and stores
one attempt ledger across four arrivals. Its raw Rust `prove` entry point is an
internal child, not a safe standalone operational command. A failed/interrupted
stage cannot retry; candidate receipts remain available. One hour begins at the
first stage and includes chain waits, compression and checks; no later stage
resets it. The unchanged independent B guard still caps rental at two hours
from actual provider creation. Leave at least six minutes beyond the initial
hour before B's effective stop. No automatic retry, extension or budget increase.

`run_stage.py STATE_DIR LEASE_JSON TARGET TARGET_SHA TRUSTED_BINARY BINARY_SHA NEW_OUTPUT`
expects B's authenticated lease preflight: `podId`, actual `createdUnix`,
effective `stopUnix`, `workloadScope=STAGED_TN10_PRIVATE_LIFECYCLE_V1` and a
`guardHeartbeatUnix` less than 30 seconds old. No account credentials enter it.
Do not run it before the separate staged image/service transport binding and
live release. The PR50/51 fixed-input image is not this staged service.

A proof wait cannot rewrite a receipt's end commitment. Re-read the exact end
block's selected-chain status, seq and current selected parent's blue score.
The settlement builder requires native finality-depth eligibility; actual node
execution remains authoritative. When making the next input, reuse/refresh a
start anchor only when its active tip and last-touch are identical. Otherwise
recapture from the prior checkpoint, preserving all activity. On expiry or reorg,
halt, preserve the candidate and identify the last still-selected checkpoint.
Never mark an orphan receipt accepted or replay a broadcast blindly.

## Qualification and release boundary

Run the focused checks:

```sh
cargo +1.91.0 test --locked --release --manifest-path poc/private-native-tn10/Cargo.toml
python3 -m unittest discover -s poc/private-native-tn10 -p 'test_*.py' -v
node poc/private-native-tn10/read-only.test.mjs
```

Tests use fresh **unfunded** keys, synthetic UTXOs and retained real fixture
receipts. They test actual script execution, bootstrap/deposit lineage,
accounting, fake/wrong-target receipt rejection, receipt cryptographic controls,
package exclusion and deadline/restart logic. They do not execute new proofs,
exercise a staged GPU service, observe new TN10 transactions or qualify a provider
stop. Existing PR51 evidence is unchanged. Final TN10 replay rejection, selected
chain acceptance, Bob's actual output, fresh spentness and final native state
must be collected under a later explicit live release.
