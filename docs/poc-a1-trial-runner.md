# A1 trial runner — design

Status: draft, 2026-10-08. Tooling design for repeating A1 testnet trials; it
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
| C | `a1_trial.py c checkpoint BUNDLE` | record the pre-funding checkpoint and S0 locator; start history capture |
| A | `a1_trial.py a fund` | fund S0 from the test wallet; wait for C to confirm S0 |
| A | `a1_trial.py a continue` | fresh continuation proof, native Full check, submit S1 |
| — | A is switched off | operator step; B has no access to A |
| B | `a1_trial.py b recover` | fetch C's history, scan lineage from the checkpoint, fresh terminal proof, native Full, submit via C, observe payout ≥120 s |
| any | `a1_trial.py verify RUN` | recheck the public result: txids, amounts, recipient, spentness |

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
- one submission per identity and branch; ambiguous submission is reconciled,
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
- Which capture interface on C (current `finite_capture.py` paging versus a
  simpler virtual-chain export) gives B complete history with the least code.
- Whether B should submit through C or through any TN10 node; the official
  trial used C.
