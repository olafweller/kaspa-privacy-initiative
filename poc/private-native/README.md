# Native KAS private lifecycle — local integration package

Owner-directed follow-up after merged PR48, 2026-10-18. This package connects
native deposit registration, private credit/payment, Bob's independent exit,
permission consumption and native payout reconciliation. It reuses the existing
wallet relation/VK and native bridge. No new setup, GPU rental, funding or TN10
broadcast occurs. See [ADR-0014](../../docs/adr/0014-private-native-lifecycle.md),
[reuse review](SOURCES.md), [results](RESULTS.md) and [TN10 plan](TN10-PLAN.md).

## What is implemented

`common` derives native IDs from complete canonical v1 preimages and authenticates
their ordered lane activity, including failed operations. State commits the
ledger, exact reserve outpoints, unpaid exits, permission outpoints, last lane
tip and last-touch score. Deposits start at zero backing and bind to a unique,
positive, covenant-specific unbound delegate output. The real wallet verifier
retains current nullifiers, known note anchors, constrained amounts and recipient
binding. Invalid wallet operations atomically leave monetary state unchanged.
Unreconciled consumption of a tracked native outpoint aborts the guest.

An exit keeps its principal in unpaid liabilities. Accepted covenant-bound
permission outputs are recognized from their bytes, not a host success flag.
Payout reconciliation requires consumption of that exact permission and tracked
delegate, exact destination, at least principal plus separate permission-rent
refund and exact remaining delegate principal. The restricted permission and
existing delegate scripts enforce
release; native UTXO consensus supplies spentness. The local replay test uses an
explicit fixture UTXO set; it is not a node's consensus acceptance result.

Recognition of permission/payout events does not depend on honest payload tags.
A third-party payout with an empty payload is still reconciled. Disguising it as
a fresh deposit does not mint another credit. All three inputs/outputs and their
roles are natively fixed for this single-reserve-input/one-outstanding-exit
experiment; additional registered reserves/deposits remain tracked.

The state covenant retains **100,000,000 sompi** throughout. It is separate from
the initial **1,000,000,000-sompi** delegate reserve, the **50,000,000-sompi**
permission rent and sponsor fees. The reserve changes to **600,000,000 sompi**
only upon authenticated payout, while Bob receives **400,000,000 principal +
50,000,000 rent refund**. No treasury value is counted as user backing.

## Build and local checks

Use Rust 1.91.0 and the committed locks (Rusty Kaspa remains `01b532e8`, not
current master). With the repository build environment:

```bash
cargo +1.91.0 build --locked --release --manifest-path poc/private-native/Cargo.toml --features proof
cargo +1.91.0 test --locked --release --manifest-path poc/private-native/Cargo.toml --features proof -- --test-threads=1
python3 poc/private-native/check_evidence.py
```

The host's `prepare NEW_OUTPUT [PUBLIC_BOB_EXIT]` replays the retained real wallet
proofs, creates connected public fixtures and checks actual native payout scripts.
`bob-public NEW_FILE` exports public pre-exit state. In a separate local process,
`bob-exit OWN_BACKUP PUBLIC_STATE PUBLIC_PARAMETERS NEW_OUTPUT [RECIPIENT_HEX]` validates the
whole public-parameter SHA256, restores only Bob's own owner-only backup,
discovers/validates his note and generates a fresh exit proof. The backup and
parameters never enter outer guest input or repository evidence. No wallet setup
command is included. Future changed native deposit bytes require a new credit
proof made with the same relation/parameters and the actual depositor's keys.

For a funded rehearsal supply Bob's actual fresh native public key. The omitted
recipient argument uses the publicly known scalar-one test destination and is
strictly a local fixture default. The CLI validates the supplied x-only key with
the existing secp256k1 library. Never fund the public fixture destination.

`genesis COVENANT_HEX SEED_TIP_HEX LAST_TOUCH NEW_STATE_FILE` creates a fresh,
unfunded zero-liability state without overwriting a file. The command
`prepare-capture PROGRAM LANE_JSON PRIOR_STATE_BIN CASE NEW_DIRECTORY` consumes
the existing canonical lane-capture format and exact prior state, preserving all
root/tip/anchor checks. It emits canonical public input, expected journal and next
state; it does not attest that the capture was accepted on chain. Freeze actual
captured targets separately before rebuilding their trusted verifier/package.

The isolated `guest` uses the existing accelerated verifier with the same
validated pinned VK. Build with the existing `kpi-risc0` toolchain and
`RISC0_FEATURE_bigint2=1`, following the previous
[guest build recipe](../private-note-chain/build_guest.sh) with this package's
manifest and binary name. The program is wrapped with the existing host `wrap`
command. Its identity was recorded before execution in
[expected-image.txt](evidence/expected-image.txt).

For execution-only reproduction:

```bash
python3 poc/private-native/run_qualification.py --r0vm /path/to/pinned/r0vm --host .local/ci-target/release/kpi-private-native-host --program poc/private-native/evidence/guest.program.bin --fixtures poc/private-native/evidence --out /path/to/new-directory
```

The campaign runs four lifecycle batches and seventeen additional cases: four
positive regressions, six economic rejections and seven exact required aborts. Limits
are 160M cycles / 900 seconds per case, 3,600 seconds for the campaign, four CPU
threads. Resource failures never qualify as rejection. Recent unchanged-active
lane anchors permit idle gaps beyond the older `MAX_SPAN=100`; the old guest and
evidence are unchanged. True expiry/reset is unsupported and cannot be bridged
by relabelling a last-touch score.

## Prepared future proof entrypoints

`kpi-private-native-proof` compiles the independent
[targets](evidence/targets.json), including full expected journals. Its commands:

```text
check-target CASE PUBLIC_PACKAGE
prove CASE PUBLIC_PACKAGE NEW_OUTPUT
verify-receipt CASE RECEIPT NEW_OUTPUT
verify-native-exit EXIT_RECEIPT NEW_OUTPUT
qualify-state-guard ARCHIVED_PR48_RECEIPT NEW_OUTPUT
```

These four targets are **local fixtures**, not captures for broadcasting on TN10.
Target/rejection checks and archived-receipt state-guard qualification ran
during preparation. `prove` is a
future entrypoint, requiring separate release and the existing 3,600-second
process-group watchdog; its post-completion time assertion is not a kill timer.
Returned candidates are saved durably before verification. There is no automatic
retry. The independent verifier reuses PR47's official seal/control/allowed-root
callback and SDK verification, disallows development mode/unresolved assumptions
and requires the compiled image and byte-exact journal. Fake and old PR48 receipts
cannot substitute for a new lifecycle receipt.

The prepared native-exit entrypoint builds the lane-restricted state-covenant
settlement from a genuine new receipt, separately funds permission rent and
checks actual issuance scripts before rerunning the payout campaign. It requires
its native issuance ID to equal the predeclared reconciliation transaction ID.
**Its positive receipt path has not run**, because no new outer receipt was
produced. The public issuance fixture contains the actual next covenant script,
but its accepted-L1 status remains synthetic.

Small deposit/reconciliation profiles use segment po2=16 and wallet batches use
po2=20. Measured multi-segment execution supports the fixed official join route.
This avoids assuming that a one-segment lift receipt has join identity; it adds
no dummy wallet operation. The additional joins affect future proving cost.

## Deployment boundary

The native sponsor payout builder now accepts optional `privateExitId`, selecting
the fixed private lane and payout payload **before** fee measurement and signing.
Default public-account behavior is preserved. Tests execute the permission path
in both modes, verify the real sponsor signature and reject post-signing payload
mutation. The additional public `permissionRedeem` field carries the restricted
redeem bytes; the builder checks their upstream verifier body and actual UTXO
script hash before native fee measurement/signing. A test uses this package’s
frozen policy and verifies all three input scripts, including the sponsor. The
local helper uses a public test-only sponsor key; never fund that key.

No immutable CUDA deployment image is published for this new workload yet. The
qualified prover/guard can be reused, but the new binaries/inputs need their own
fixed-job package, image identity and CPU startup/lease checks before a paid run.
The old PR47 image still runs its old frozen job. A future TN10 trial additionally
requires actual bootstrap/deposit/permission outpoints, canonical captures,
matching new credit proof, genuine receipts and terminal chain confirmation.
Do not describe this local package as live-trial readiness.

## Review correction

[Native/accounting alignment](REVIEW-FIX.md) records the reproduced blockers,
actual native enforcement restrictions, multiple-deposit bookkeeping and the
21-case requalification. The issued permission binds the private lane and exact
reserve chosen at exit admission. The state covenant also preserves that lane
restriction through continuation. A top-up is allowed; partial consumption and
extra sponsor inputs/outputs are natively rejected. A lane flag alone is
insufficient: the real sponsor builder also needs the matching `permissionRedeem`
public bytes. Native state-contract construction must use the restriction adapter.
PR49 remains open; no live trial, image publication or new proving is authorized.
