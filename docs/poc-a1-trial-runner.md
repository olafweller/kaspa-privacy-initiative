# A1 trial runner — design

Status: phase A implementation, 2026-10-08; offline validation, awaiting review.
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
after proving and durably creates one exclusive submission intent. Unknown or
rejected submissions never retry; use `verify` to reconcile. Copy both public
attempt receipts for review. Only actual rejection plus one accepted exact body
can close the race case; a second absent payout alone does not prove rejection.

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

Protocol design remains ADR-0003; this transport/tooling choice introduces no
new primitive or architecture. No mainnet or production-safety conclusion follows.
