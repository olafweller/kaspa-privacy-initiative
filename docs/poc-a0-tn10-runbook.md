# A0.5 native TN10 runbook

Continue branch `poc-a0-reserve-release` and draft PR #20. No mainnet, real KAS,
merge or A1. The original no-argument harness remains an ephemeral fixture:
**never fund its address**. Read [the report](poc-a0.md), [proof statement](poc-a0-proof.md)
and [ADR-0002](adr/0002-a0-reserve-release-experiment.md) before a new experiment.

## Requirements and isolated setup

Use Linux x86-64, Rust 1.91.0, the native build prerequisites in the original
[handoff](poc-a0-live-tn10-handoff.md), Node with native WebSocket (tested v22),
Python 3, curl, unzip and sha256sum. Reserve several GiB for node data/builds.
A funded test-only source wallet is required; KasPact is not a dependency.
The official v2.1.0 artifacts and extracted binaries are pinned by SHA-256;
source revision is `01b532e8b553523216471682649693af92f0fd16`. Archive hashes
verify the chosen downloads, not an independent reproducible-build attestation.

```bash
./scripts/run_poc_a0.sh
./scripts/run_poc_a0.sh test
./scripts/setup_a0_tn10.sh
node --test scripts/a0_tn10.test.mjs scripts/a0_tn10_preflight.test.mjs
./scripts/start_a0_tn10_node.sh
```

The last command runs in the foreground; use another terminal for subsequent
steps. All RPC/P2P listeners bind loopback, UPnP is disabled and no inbound peers
are accepted. Outbound peers provide TN10 synchronization. Existing local node
services are not reconfigured. Stop this node with Ctrl-C after observation.

The adapter fixes `ws://127.0.0.1:17210`, TN10 and version 2.1.0. It requires a
UTXO index, checks actual network identity and independently recomputes the
retrieved TN10 genesis header hash. Linux `/proc` also verifies the executable
hash, working directory and exact startup arguments. If IBD pruning later removes
the genesis header, only the retained actual RPC header from the same still-running
pinned process is accepted and rehashed; PID plus process start ticks must match.
Archived u64 header fields are restored as bounded BigInt before independent hashing.
Tests reject changed nonce/overflow despite a supplied cached hash.
This relies on the pinned native consensus pruning-proof validation and local host,
not a claim that a pruned node serves genesis. A changed process fails this
fallback and needs explicit identity review. Broadcast paths require `isSynced=true`.
Do not substitute a mainnet/public endpoint or bypass these checks.

## Prepare without broadcasting

```bash
node scripts/a0_tn10.mjs identity
node scripts/a0_tn10.mjs wallet
node scripts/a0_tn10.mjs prefund
node scripts/a0_tn10.mjs funding-fixture
```

Run `wallet` once. It creates separate KPI funding/recipient keys in ignored
`.env.tn10.local` (0600) and a new external mode-0700 claim/proving directory.
The claim, proving key and manifest each have mode 0600, with a reload-verified
backup subdirectory. Keep these and the recipient key available; there is no
admin recovery branch. The backup is on the same host, not independent recovery.
Never print, upload or commit secret files. `.local/a0-tn10` holds public run
artifacts, but inspect and allowlist them before publication.

`prefund` validates a retained-key proof against a supplied synthetic UTXO and
checks every relevant field after native SDK reconstruction. `funding-fixture`
signs an ordinary transaction spending a synthetic KPI-wallet UTXO and subjects
it to the same full upstream validator. Neither broadcasts. These commands can
run while the node synchronizes and are not evidence of actual UTXO existence.

## Review and funding gate

Perform an adversarial source/adapter review before funding. Record the findings
in `.local/a0-tn10/review.json`, with `approved_for_test_funding: true` only after
address/recipient control, retained-key reload, exact SDK roundtrip, all baseline
negatives and adapter tests pass. The `sha256` map must contain current hashes
for the exact files listed in `reviewFiles` in `scripts/a0_tn10.mjs`. Save the
findings as well as hashes. Any change to reviewed source/binaries invalidates
the gate. This local procedure is not an on-chain authority or a security audit.

A funding-source file outside KPI must contain `KASPA_NETWORK=tn10`,
`KASPA_USER_PRIVATE_KEY` and `KASPA_USER_ADDRESS` for a funded **test-only** wallet.
The key-derived address must match. Historical `TN12_USER_*` variable names are
accepted only with explicit TN10 network selection. The source file is parsed
inside the process without shell evaluation and is never copied. Supply its
path, never its contents or a key on the command line.

```bash
node scripts/a0_tn10.mjs bootstrap /absolute/path/to/testnet-source.env
node scripts/a0_tn10.mjs fund
node scripts/a0_tn10.mjs release-prepare
node scripts/a0_tn10.mjs release
node scripts/a0_tn10.mjs replay
# After an additional observation interval:
node scripts/a0_tn10.mjs recheck
```

`bootstrap` transfers 12 test KAS to the fresh KPI funding wallet. Funding uses
10.2 test KAS for the reserve; 10 goes to the fixed recipient and 0.2 is the
reserve-release miner fee. Each ordinary funding transaction has a 0.1 test-KAS
fee cap, a single intended payment and at most one change output to its source.

`fund` first signs the funding transaction, locates the exact reserve output,
proves a release bound to that future txid/index under the retained key and
runs full validation after SDK roundtrip. The current priority fee estimate must
also fit the unchanged release fee. Only then can it broadcast funding.
After acceptance, `release-prepare` queries the actual reserve output/context
and generates a fresh proof. `release` rechecks current UTXO context and the
fixed fee against the native fee estimate before submission. No amount/budget
is silently increased and no sponsor input or alternate payout is added.

The observer uses native accepted transaction IDs with `minConfirmationCount=20`.
In this pinned node implementation that means accepting-block blue-score
distance from the sink **greater than 20**, not a production finality rule.
It also requires the exact payout UTXO, absent reserve and full accepted-body
field comparison. `recheck` repeats acceptance and UTXO observations. RPC frame
byte counts include the wRPC envelope, excluding WebSocket/TCP framing; consensus
Borsh bytes and the upstream estimated transaction bytes are separate metrics.

The exact replay may return already-known or missing-input status. The distinct
replay changes only sequence to u64::MAX-1, has another txid and first passes
local full validation against the original UTXO. Its actual node error must be
inspected to establish spent-input rejection rather than unrelated policy failure.
No second payout may appear.

## Failure and resumption

Artifacts use exclusive creation. Before each submission a durable intent saves
the exact ID and anchor. On a timeout, lost response, unexpected rejection or
process interruption, inspect that saved transaction's chain/mempool/UTXO state.
Do not delete artifacts and rerun funding blindly. There is no automatic
rebroadcast, reset, key replacement, refund or fee-adjustment path. Lost proving
material, wrong network, a changed reserve, or insufficient fixed fees safely
halt the experiment. Resolve the actual cause before any narrowly scoped resume.

The REST preflight is read-only historical diagnostics and never authorizes
funding. Its expected exit 2 on the recorded v2.3.0 schema does not disable native
RPC checks. Keep the original negative suite and distinguish local proof validity,
submitted transaction, accepted-chain observation and later reorg evidence.
