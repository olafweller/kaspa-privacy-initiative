# A1 trial runner — design

Status: phase A reviewed, phase B rehearsal started on 2026-10-08 with operator
approval; no complete payout rehearsal or official S0 result yet.
Tooling for repeating A1 testnet trials; it
changes no protocol rule, script, circuit or invariant.

## Problem

The 2026-10-08 official trial passed, and its executed sources are published
under [`poc/a1/evidence/official-trial-2026-10-08/source/`](../poc/a1/evidence/official-trial-2026-10-08/source/).
Nobody else can repeat it from this repository:

- the funded-instance constructor (private owner key, test-KAS terms) exists
  only as a local modified copy of `poc/a1/src/main.rs`;
- run packages are produced by a local chain of build steps, each copying and
  string-patching the output of an earlier one;
- the executed runtime is about 11,000 lines across 113 files. Most of it is
  installation and qualification ceremony (systemd jails, forced-SSH accounts,
  per-file pin ledgers, authority files, leases), not protocol checks.

Goal: anyone with three machines (or one machine and a local devnet), test KAS
and this repository can run the trial with a few documented commands, and
check the outcome against the same criteria as the official trial.

## Roles (unchanged)

- **A** — owner/prover. Creates the instance, funds S0, performs the S0→S1
  continuation. Holds the owner secrets.
- **B** — recovery. Holds only the public bundle and the user's private backup
  (claim secret, recipient key). Never reads A's files.
- **C** — chain/archive. Runs a TN10 node, records a pre-funding checkpoint and
  the accepted history after it, serves it read-only, relays B's transaction.

## Commands

One entry point, `scripts/a1_trial.py`, with one subcommand per role step and
one local private config file per machine (`a1-trial.local.json`, ignored by
Git) holding endpoints, wallet file and work directory.

| Step | Command | Does |
|---|---|---|
| A | `a1_trial.py a new` | build a fresh instance with a random private owner key; write public bundle and B's private backup |
| C | `a1_trial.py c checkpoint` | independently retain the pre-funding checkpoint and bundle identity |
| A | `a1_trial.py a fund` | fund S0 from the test wallet; wait for C to confirm S0 |
| A | `a1_trial.py a exit-s0` | discover S0 from C's Full history, fresh terminal proof, native Full and SDK check, submit once |
| — | A is switched off | operator step; B has no access to A |
| B | `a1_trial.py b recover` | fetch C's history, scan lineage from the checkpoint, fresh terminal proof, native Full, submit via C, observe payout ≥120 s |
| any | `a1_trial.py verify` | recheck the accepted body, exact payout, recipient and spentness, again after ≥120 seconds |

Each run uses a fresh identity. A used identity is never re-submitted
(testnet practice rule 1).

## Kept strict

These checks are carried over unchanged from the executed runtime and the
repository core (`kpi-poc-a1`, `a1_check.py`, `a1_recovery.py`):

- independent parameter inspection (`a1_check.py`) before proving;
- lineage discovery only from complete accepted history after the retained
  checkpoint; no address-only match, guessed entry or saved S1 pointer;
- fresh proof and native Full validation of the exact body before submission;
- exact amounts (integer sompi), fixed recipient, fee within the fixed terms;
- one funding submission and one terminal attempt per role per identity;
  the race deliberately permits one competing attempt by A and B;
  ambiguous submission is reconciled,
  never retried blindly;
- reorg detection between checkpoint and observation;
- payout observed again after at least 120 seconds.

## Dropped or simplified

- systemd jails, dedicated UIDs, forced-SSH accounts: deployment hardening,
  not part of the research question. Operators may add their own.
- per-file pin ledgers and authority files: replaced by one run manifest that
  records the Git commit, binary hashes and inputs.
- automatic A-absence detection and leases: the operator switches A off before
  starting B. B's independence comes from having no A data, which the runner
  enforces by construction. An optional `b watch` trigger can come later.
- tight operational limits: generous by default (rule 4).

## Phases

1. **Constructor in the repository.** Done: the separate binary
   `kpi-a1-testnet-instance testnet-10 NEW_DIR TERMS.json` (fresh private key,
   scope `testnet-10-test-kas`); observe it with
   `a1_observe.py --testnet-terms TERMS.json`. The `kpi-poc-a1` harness still
   constructs fixture bundles only.
2. **Local devnet rehearsal.** Run the same commands against a local
   `rusty-kaspa` devnet at the pinned commit, so the full path can be repeated
   without test KAS or servers. Open question: whether the pinned build
   activates the covenant opcodes on devnet.
3. **TN10 runner** for A, B and C with the config file above, rehearsed end to
   end including the real terminal payout before any official run (rule 3).
4. **Remaining G5/G6 scenarios** as runner options:
   - B recovers from S0 (A lost before continuation);
   - owner direct S0 exit;
   - competing spend: A and B submit at once; exactly one is accepted;
   - artifact loss and reorg cases from the threat matrix.
5. **Clean-machine guide** in `poc/a1/README.md`.

## Open questions

- Devnet covenant activation at the pinned upstream commit (phase 2).
- Actual C-node Full-history availability over the physical outage, RPC field
  compatibility and throughput must be tested in the authorized rehearsal.
- Race rejection receipts and chain outcome must be reviewed together; a lost
  RPC response is not evidence of rejection.

## Implemented S0 transport and boundaries

B reads C's validating TN10 node through an operator-established SSH tunnel to
loopback wRPC. `getVirtualChainFromBlockV2` with `Full` verbosity supplies complete
accepted bodies starting at C's retained checkpoint; no separate archive server
or copy of A's directory is needed. C must retain that history for the trial:
missing/pruned pages or any selected-chain removal cause a safe stop. The runner
also submits via this C connection; the history operations themselves are read-only.
This selects the direct-node option over extending the old finite-capture chain.

The RPC request/response fields are taken from the locally available upstream
`rpc/core/src/model/message.rs` and `rpc/core/src/wasm/message.rs` at
`01b532e8b553523216471682649693af92f0fd16`; no online upstream refresh was made
in phase A. The node's chain completeness, current entries and acceptance remain
trusted assertions by independently operated C, not light-client proofs.
The bridge checks TN10 identity, v2.1.0, synchronization, UTXO indexing and the
existing SDK file pins. It does not attest C's executable or eliminate node trust.

Only `a new` and file-based checks run by default. All RPC is refused before a
process is started unless `--live` was explicitly supplied. Phase A uses no
network, funds, servers or historic trial identity. `--live` is a technical switch,
not permission: phase B still requires Claude's review and Olaf's explicit agreement.

`a new` observes the existing constructor through `a1_observe.py --testnet-terms`,
retains intent/receipt and binary/source hashes, and separates private backups
from the public bundle. `c checkpoint` binds the bundle and asserts its S0 address
is unfunded. `a fund` plans/signs one exact S0 deposit, checks it with the existing
A0 `live check-generic` native Full adapter, records its locator before submission,
then authenticates acceptance through C's Full history. The locator and checkpoint
are copied unchanged to B; a saved successor pointer is never supplied.

Both exit paths rerun `a1_check.py`, check the actual backups, use `a1_recovery.py`
to discover authenticated S0, generate a fresh proof, validate SDK safe/numeric
round trips and run native Full on the decoded body. Monetary values normalize to
integer sompi at RPC boundaries; fee checks reuse `a1_fee_check.py`'s exact policy
calculation. Unrelated v0 transaction IDs and all Full hashes are independently
recomputed by the existing Python scanner; v1 IDs and reserve spends also use
the native reference/Full callback. No circuit, script or protocol rule changes.

For the race, A uses sequence `u64::MAX-1`, B uses `u64::MAX`. Both disable
relative locks under the existing script, while distinguishing transaction IDs.
The changed A body gets its ID/storage mass recomputed and must pass Full again.
Prepare both offline or online with `--prepare-only`, then use `--submit-prepared
--submit-at UNIX_SECONDS` in parallel on A and B. Each rechecks current history
after proving, completes that expensive scan before the common race barrier,
checks checkpoint/horizon survival at broadcast, and durably creates one exclusive
submission intent. Unknown or
rejected submissions never retry; use `verify` to reconcile. Copy both public
attempt receipts for review. A competitor whose SDK actually invoked submission
reconciles the chain even after an RPC error. After ≥120 seconds it writes a
`lost` result naming the winning txid, its own unaccepted txid and the single
accepted S0 spend, instead of treating that expected race outcome as a failure.
Both attempts and the winning exact body are required; failure to connect or
serialize before submission does not establish a losing race attempt. An RPC
error alone remains uncertain and is never described as definitive rejection.

## Adversarial second pass and qualification limits

- Inflation/unauthorized exit: independently inspect fixed terms and parameters,
  require exact S0 input, output order, recipient, amounts and fee, and Full-check
  the SDK-decoded body. No admin exit, fee bump or replacement setup exists.
- Double spending: intents prevent local retries; native current-UTXO acceptance
  settles competing attempts. Offline proof validity does not settle the race.
- Stale/replayed/cross-instance state: checkpoint binds genesis, instance and
  artifact manifest; pages must be complete/ordered; current UTXO must reconcile;
  checkpoint and horizon must survive before submission. Any removal stops.
- Dependency disappearance: missing PK, backup, retained intent/receipt, history
  or C connectivity prevents a valid step. No fallback guesses or A access.
- Privacy: public amounts, scripts, recipient, outpoints and timing remain visible.
  Config, wallet, backups and retained files are private/local; no anonymity claim.
- Trust: single-party setup and host integrity remain the existing assumptions.
  RPC checks cannot make a dishonest C truthful. Offline synthetic history tests
  exercise rejection and real proof/SDK/Full paths, never testnet acceptance.

Live history and UTXO RPC reads are not atomic. A reconciliation failure caused
only by a missing current UTXO or a still-visible terminal reserve refreshes the
complete read-only snapshot; it never permits a proof or submission using that
inconsistent snapshot. Wrong terms/hashes, incomplete pages and reorgs still halt.
The inherited A0 funding fee cap protects the wallet against accidental fee burn;
exit fees remain exactly the independently inspected fixed terms.

Protocol design remains ADR-0003; this transport/tooling choice introduces no
new primitive or architecture. No mainnet or production-safety conclusion follows.

## Phase A checks (2026-10-08)

Locked/offline Rust 1.91.0 release build passed. One `a new` invocation completed
the fresh unfunded instance and independent parameter observation in 74 seconds.
15 runner unit tests and two native integration tests passed; the nine existing
recovery tests and ten existing fee tests also passed (36 offline cases total).
The integration uses synthetic accepted history, real fresh A/B proofs with
distinct IDs, pinned SDK safe/numeric round trips, native Full, and an actual
signed synthetic funding plan through the existing A0 Full validator. Malformed
proof material, changed payout, corrupted/gapped/reordered history, checkpoint
substitution and reorg cases fail safely. Retry intent, snapshot reconciliation
and the ≥120-second observation condition are unit-tested with a simulated clock.
Final A/B bodies were revalidated and source/binary/SDK receipts retained locally.

No network/RPC connection, test KAS, server mutation or push was used. Actual C
history throughput/pruning, funding/submission, physical loss of A, an accepted
payout sustained ≥120 seconds, and the live race remain untested. Phase A is
completed at stop point 1; it is not trial readiness.

## Claude review follow-up

The operator accepted Claude's review of `75382db` with three changes before
phase B. Every uncaught Python/JavaScript failure retains its full available
exception type, message, traceback/stack and cause chain in a mode-0600
`error-*.private.json` in the configured run directory; the failure message names
that path. Child stderr/stdout is retained too. Locals and config/environment
dumps are never captured. Known wallet/backup/environment secrets are redacted;
unknown 32-byte hex values are masked as a fail-closed fallback, so public txids
in diagnostics can also be masked. Exact public txids remain in intent/result
receipts. A malformed config without a usable run path gets a private fallback
diagnostic run under the source checkout's ignored `.local/` directory.

At the operator's explicit request, `fund`, `discover` and `observe` have a
default 1,800-second monotonic wait budget, configurable through
`wait_timeout_seconds` (positive finite seconds). Nested discovery shares the
outer observation budget; RPC subprocesses use its remaining time. Timeout
stops with a clear diagnostic and never retries, changes terms, accepts a
partial history or shortens the ≥120-second payout observation. A timed-out
funding/submission may have reached the chain: retain the used identity and
reconcile read-only, never rebroadcast it. This is an explicitly requested
operational exception to the default uncapped-wait posture.

The race loser result remains subject to the same Full/history/current-UTXO,
exact-payout, one-transition and stable ≥120-second checks as the winner.
Duplicate/conflicting accepted reserve spends or disappearance/reorg still
stop. Tests cover diagnostics/redaction, shared wait budgets, expiry of all
three waits, successful loser reconciliation, pre-submit failures and no retry.
No cryptographic or protocol rule changed; no test-KAS is authorized by code.

## First live rehearsal finding

The first authorized rehearsal deposited S0 and then halted before any terminal
attempt: the strict scanner rejected an incomplete Full output. The pinned SDK
exposes Rust `Option::None` as an **own** JavaScript property with value
`undefined`; ordinary `JSON.stringify` erased the `covenant` field. Live inspection
confirmed both the own property and the undefined value. Upstream
`rpc/core/src/model/tx.rs` defines `RpcTransactionOutput.covenant` as an Option;
`rpc/core/src/wasm/message.rs` converts accepted bodies through WASM serde, at
the previously pinned commit `01b532e8b553523216471682649693af92f0fd16`.

The bridge now preserves present undefined values as JSON null. It does not add
absent fields: a genuinely missing covenant still fails the scanner. The
regression test also checks unchanged Full hashes and a different hash when a
covenant is present. A fresh, read-only capture of C's Full history authenticated
the original funding body/current S0 through native ID checks; it did not submit
or resume that halted identity. Its files, backup and diagnostic are retained.
Any next rehearsal uses a fresh identity, with no rebroadcast of the old funding.

A scan of 22,175 actual bodies took about 105 seconds. Page replay and repeated
snapshots therefore cache pure native ID/hash results for unrelated v1 bodies,
keyed by their independently computed complete Full body hash. Every asserted
ID/hash, page sequence, UTXO and transition is still checked. Changed bodies get
a new native check; changed asserted IDs fail against the cached native ID.
Relevant reserve spends always rerun native Full using their current authenticated
context. The cache does not retain acceptance or spentness assertions, survive
the process, or shorten the required 120-second payout observation.
Offline replay of that same captured history passed with the cache: about
37 seconds initially and 8 seconds on the second scan, checking 11,261 distinct
native v1 IDs. The 27-case suite including both native integration cases passed
after the serialization fix; the subsequent 28-case unit run (two integrations
not selected) and the actual-history replays cover the cache addition.
