# User-held wallet recovery and exact-reserve exit — local package

PR54 is merged at `40b39a6503d2133da93b9dd7e77a5a1ee8652658`.
Its four actual TN10 receipts, transactions and archives remain unchanged.
This package prepares the next experiment; it performs no rental, outer proving,
funding or broadcasts. [Decision and alternatives](../../docs/adr/0016-user-held-recovery-and-terminal-exit.md).

## What runs locally

`user-recovery` is a separate executable in the existing private-native-tn10
crate. It creates a wallet/native key, discovers spendable notes from an
independently root-checked state, prepares a real wallet EXIT proof using the
user's own backup/key, and reconstructs public state from ordered input history.
The program contains no RPC, provider credentials, broadcast, signing service or
remote witness-upload command. Native signing in the rehearsal uses only an
explicit unfunded public test sponsor key.

The full-drain relation reuses upstream's terminal zero-change branch: permission,
exact selected reserve and sponsor inputs; recipient plus sponsor outputs. It
uses real native script verification and genuine wallet proofs. It does not
create a zero-value reserve output, spend state rent, add an administrator key,
or modify an old permission. Sponsor top-ups do not create private value.

**This is a host-only local policy experiment, not a new guest/outer proof.**
Its tagged terminal-claim commitment distinguishes it from the old policy, but
is not a native settlement ABI. Integrating the policy into a new guest/image,
genuine proof-authorized permission issuance and canonical TN10 acceptance remain
next steps. The current live trial's old reserve is not upgraded by this code.
The old guest intentionally still rejects an exact-reserve exit.

## User commands and trust boundary

Build from the reviewed source with its locked dependencies:

```bash
source /workspace/.onboarding/activate.sh
CARGO_TARGET_DIR=.local/ci-target cargo +1.91.0 build --locked --release \
  --manifest-path poc/private-native-tn10/Cargo.toml --bin user-recovery
RECOVERY=.local/ci-target/release/user-recovery
"$RECOVERY" init /user/backup-directory
```

Run `init` on a machine administered by Bob, not on Cloud, B, TN10, a provider
image or an operator-controlled VM. It creates a 0700 directory and 0600 files:
`wallet.backup` (64 raw bytes, spending and incoming-view secrets), `native.key`
(32 raw bytes), and `receive.json` (public). Back up both secret files on user
media. Only `receive.json` crosses to the sender. It contains exactly `schema`,
`domain`, `owner` and `incoming`; it contains no native payout key or address.
The native public key is disclosed only in the public EXIT result when the user
chooses to withdraw. Check the receiving file's fingerprint/domain
with Bob over an authenticated channel; no receiving-address directory authority
is introduced here. Do not use this experimental key format for mainnet funds.

On a clean user machine, restore **only those own backup files** and obtain:

| Required material | Source and check |
|---|---|
| Full public state or complete replay inputs | Replaceable public history/archive; verify against an independently obtained accepted checkpoint |
| Ciphertexts, note tree/leaves, current nullifiers, permitted anchors, deposits/exits, native reserve/permission lineage | Included in committed state; no note cache or sender secrets are required |
| Current accepted state root, covenant/lane-tip, state outpoint and selected-chain anchor | Independent synchronized native node; check canonicality and fresh UTXO state before a future spend |
| Public proving parameters and VK | Exact reviewed parameter SHA256 and pinned VK enforced by the executable |
| Reviewed executable/source and later outer prover | User-trusted software and replaceable infrastructure; no operator secret is needed |
| Fees and native consensus support | Separate live prerequisites; not supplied by a backup |

```bash
"$RECOVERY" rebuild "$INDEPENDENT_START_ROOT" "$INDEPENDENT_END_ROOT" \
  /user/reconstructed.state.bin /public/deposit.input.bin /public/payment.input.bin
"$RECOVERY" scan /user/reconstructed.state.bin "$INDEPENDENT_END_ROOT" /user/backup-directory
"$RECOVERY" exit /user/reconstructed.state.bin "$INDEPENDENT_END_ROOT" \
  /user/backup-directory /public/public-proving-parameters.bin /user/new-exit-output
```

Root arguments must come from independent accepted-chain verification. Do not
copy a root from the same untrusted snapshot/target and call it authenticated.
`rebuild` checks canonical bounded inputs, complete prior-state continuity,
wallet proofs, native/lane relation and the exact independently expected final
root. It does not implement native consensus selection or establish checkpoint
freshness. Replaying to a historical root cannot authorize a spend against a
newer state. A fresh native outpoint/selected-chain check and a new outer proof
are still mandatory for a future settlement. Missing/pruned public data can block
recovery; a backup alone cannot manufacture it. No generic expiry/reset or reorg
rollback is added. On reorg, discard unaccepted outputs and reconstruct from a
new independently canonical checkpoint; never relabel a stale anchor.

The scan's balance is private local user output. Exit output contains only the
public operation, binding and ciphertext-free public exit payload; no secret,
note plaintext, Merkle witness or backup is sent to an outer prover. Restoring
another wallet yields no owned notes and cannot create the authorized exit.

## One-command synthetic rehearsal and checks

```bash
RAYON_NUM_THREADS=4 "$RECOVERY" rehearse \
  /public/public-proving-parameters.bin /private/new-rehearsal-directory
cargo +1.91.0 test --locked --release \
  --manifest-path poc/private-native-tn10/Cargo.toml --bin user-recovery
python3 poc/user-recovery/test_cli.py "$RECOVERY"
```

Rehearsal creates fresh wallets, gives the sender only Bob's public address,
makes real credit/transfer proofs, moves Bob's backup directory to a clean path,
replays the public history and prepares Bob's exit in separate processes. After
Bob's native fixture payout, Alice makes a genuine exit proof for the last 6 KAS;
the new terminal script pays all 6 plus its separately sponsored rent refund.
Only the resulting `public` subdirectory is eligible for evidence publication.
Actual secrets remain in the fresh private rehearsal directory and must not be
uploaded. The subprocess separation is a software boundary test, **not independent
administration or protection from an operator/root who owns the machine**.

The original hosted application services are never contacted. This demonstrates
offline replacement of their tested functions with available archived data;
it does not demonstrate independent archive availability or a physical shutdown
of separately administered machines. No original live wallet backup is used.

## Next reviewable live experiment

1. Bob runs the user commands on his separately administered machine; confirm
   public receiving data without transferring secrets. Record who controls every
   machine and which original services are actually unavailable.
2. Integrate/review the local terminal policy in a new guest and pin its identity,
   journals, native permission issuance and fresh trial configuration. Rehearse
   full drain and all native/ledger regressions before any live release.
3. Replace original services with independently reconstructed public history,
   a replacement executor/prover and sponsor. Users retain all wallet witnesses.
4. Obtain an explicit bounded testnet/GPU release for that concrete configuration.
   Retain the earlier one-L40S/one-attempt/one-hour aggregate/two-hour lease/$5
   planning constraints unless the owner separately changes them. No automatic
   lease, retry or budget increase is included now.
5. With original services unavailable, pay **every** user, including the last
   exact-reserve user, with real proofs and independently observed TN10 payouts.
   Record missing-data failure, spent/stale/reorg rejection and final backing.

Only that later experiment can pass the N-user shutdown/recovery gate. Multiple
concurrent exits, combining small reserves, production setup/security/privacy and
arbitrary pruned-history recovery remain outside this package.

## Retained result

The [fresh local run](evidence/local/qualification.json) completed four real
wallet proofs and the two native payout fixtures in 175.03 seconds. Maximum
reported child RSS was 2,483,256 KiB (not a summed process-group peak or a phone
benchmark). Bob received 4 + 0.5 test-KAS; Alice received 6 + 0.5, with both rent
refunds separately sponsored. Final reserve/private/pending-exit liabilities are
zero. The state covenant's 1 test-KAS rent remains separate.

[Seven Rust tests](evidence/rust-tests.txt) include thirteen semantic native
negative variants, sponsor top-up acceptance, current-state proof checks and an
explicit regression that the old policy still rejects full drain. The original
twelve private-native-tn10 tests also pass. [CLI checks](evidence/cli-tests.json)
reconstruct all four retained actual TN10 inputs exactly to state SHA256
`da80fa5def53ad997694141745e651f15c45ecf83b0d6e9282c2f70c93f0f650`
and reject eleven malformed, missing-history or unauthorized cases. The
[adversarial review](ADVERSARIAL-REVIEW.md) records the remaining proof/chain and
administrative boundaries. These are evidence about tested code, not an audit
or a completed independent recovery milestone.


## Targeted PR55 review correction

The original `receive.json` unnecessarily disclosed the user's native payout
key alongside private receiving data. The current receiving file contains only
the four required fields; both Rust and CLI tests assert that exact allowlist.
The rehearsal reads Bob's native key and payload from his public exit result
only after he prepares withdrawal, checking the result against the operation
and prior root. This removes an automatic sender-to-native-key link at receipt;
future reuse of native withdrawal addresses and other correlation remain wallet
privacy choices, not solved anonymity properties.

The original PR55 addition to `.github/workflows/code.yml` broke the historical
preparation source hash check. That workflow is restored byte-for-byte to its
reviewed main version; the historical hash and checking code are unchanged.
The separate `user-recovery.yml` workflow builds the wallet executable and runs
the CLI/receive checks plus the original preparation integrity check. Rust
regressions remain in the original Rust job's automatic test discovery.

Original fixtures, logs and source/executable identities remain preserved.
`evidence/review-fix` records the prior runmanifest and fresh post-fix results;
the active runmanifest identifies the corrected source/executable. No old
fixture is relabelled as an execution of the corrected receiving interface.

The [targeted review response](REVIEW-FIX.md) records both fixes and the fresh
185.21-second post-fix local rehearsal, with the same zero final user liabilities.
