# Staged TN10 recovery lifecycle preparation

This adapts the existing four-stage actual-TN10 tooling to the unchanged PR56–58
recovery guest and six stages. It imports public Alice/Bob receive files instead
of creating operator-held user wallets. The owner reports successful local Mint
wallet creation and an independently stored backup; those public receiving files
and the fresh unfunded trial stay under ignored local storage, not this repository
or a public image. No user backup/native key was requested or read in Cloud.

The binaries and service implement preparation, proof production and verification;
**this work does not fund, broadcast, rent, produce a new outer proof, stop an
existing service or establish live readiness**. PR58's genuine local receipts
remain regression evidence, not receipts for this fresh instance. The old PR54
pool and all earlier source/hash bindings are unchanged.

## Changes and reuse

- `src/` is a separate derivative of `private-native-tn10`; the original remains
  byte-identical. It uses `kpi-recovery-native` and its same pinned guest/native
  restrictions. Bootstrap derives the actual covenant-dependent genesis root
  with the recovery state domain and lane guard from inception.
- `init ALICE_RECEIVE BOB_RECEIVE NEW_DIR` accepts exactly the four public fields,
  correct domain and distinct wallets. Only an unfunded sponsor key is created
  for the operator; Alice/Bob have no server-side key directories or predeclared
  native payout keys. User receive data is never a public build fixture.
- Stages are deposit, credit-transfer, bob-exit, bob-reconcile, alice-exit,
  alice-reconcile. Trusted freeze/checkpoint logic validates the complete native
  lane capture and old/new state/tip continuity, including all proof-wait gaps.
- Role-local `wallet` creates Alice's credit/transfer proofs and either user's
  exit using the existing own wallet backup, exact public parameters and an
  independently supplied accepted state root. EXIT obtains the native destination
  from that user's local raw 32-byte key. No witness or secret is exported.
- The signed builder executes all input scripts, preserves compute commitments,
  calculates signed size/mass/fees and keeps principal/state rent/permission rent
  separate. It supports both positive reserve change and exact full drain without
  a zero-value reserve output. Destination authorization comes from the proved
  exit/current ledger, never an operator-configured replacement recipient.
- `service/` is a scoped derivative of the reviewed staged service: six arrivals,
  one durable deadline including interstage waits, fixed profiles and executable,
  independently approved targets, single mutating service, restart interruption,
  candidate preservation, bounded archives and trusted B CPU verification.
  Final and candidate-only collections are reported separately.

The existing official CUDA prover, RISC Zero 3.0.3, wallet circuit/VK/parameters,
recovery guest and Join control are retained. See [pins](service/pins.json),
[source bindings](evidence/source-bindings.json) and [runmanifest](runmanifest.json).
No new curve arithmetic, setup, administrator exit or privacy primitive is added.
The reuse decisions in [PR56](../recovery-native/SOURCES.md) and ADR-0016/0017 apply.

## Trial-neutral image and private runtime binding

The public base archive contains **only the trusted executable and guest**.
The image context excludes both real receive files and every trial file.
`launch.py` accepts the exact B-approved public trial bytes through
`KPI_RECOVERY_PUBLIC_TRIAL_B64`, validates the allowlist and binds them once in the
persistent volume. It cannot accept wallet-secret fields or change the trial on
restart. B builds the same bound package from those exact bytes and computes its
policy hash independently before configuring the lease. No JSON reserialization
changes the expected file/policy hash between B and the GPU.

The RunPod account key remains exclusively in B's existing root-only env file.
Only the existing GPU service token and public trial envelope go to the Pod. They
are not forwarded to prover/CPU child environments. Management remains Cloud →
TN10 → B; no new Cloud domain, secret, SSH key or mutating executor is introduced.
The original independent guard handles backup/deadline/confirmed stop without
Cloud, TN10 gateway or laptop runtime dependencies. The image's CPU smoke test
uses a labelled synthetic public trial, not the owner's addresses or a provider.

## Qualified locally

Eight fast Rust tests pass, including new bootstrap restrictions, signed native
mass/fee checks, both genuine PR58 exit receipts in the new signed issuance/payout
builder and all six exact dynamic-target receipt checks. These receipts use the
old local fixture context, not this owner's new public configuration.

Seventeen Python tests pass: real local HTTP six-arrival orchestration, actual
CPU verification of the retained receipts, externally preserved archive recheck,
authentication/order/guard gates, duplicates, interstage timeout, process-group
kill, lost replies, interrupted/repeated restart cleanup, candidate preservation,
archive metadata bounds and immutable secret-free runtime binding. CUDA/prover
work is a synthetic stand-in in those orchestration tests and is labelled so.

One separately run ignored Rust integration test generated **four fresh wallet
proofs** from new disposable local wallets against the same retained public
parameters. Credit → payment → Bob partial exit/payout → Alice full exit/payout
finished in **230.54 seconds**, leaving zero private/reserve/unpaid obligations
and 100M sompi separate state rent. Its native contexts are synthetic; it creates
no outer receipt or network transaction. It never uses the owner's real wallets.
The public parameters are intentionally not put into Git. CI reruns the eight
fast tests and seventeen service tests; the heavy wallet test is retained evidence.

```bash
CARGO_TARGET_DIR=.local/ci-target cargo +1.91.0 test --locked --release \
  --manifest-path poc/recovery-tn10/Cargo.toml
python3 poc/recovery-tn10/check_preparation.py
python3 -m unittest discover -s poc/recovery-tn10/service -p 'test_*.py' -v
```

## Before an actual release

Follow [START.md](START.md). The generic image must have an immutable published
and pulled digest/CPU qualification. Prepare the new client executable and exact
156,439,536-byte public parameter file on Mint **before rental**; do not generate
another setup or replace the user's wallets. The native capture validator and
accepted checkpoints must be trusted independently of the prover's metadata.

The outage occurs after the accepted credit/payment settlement and before Bob's
exit. Record actual original-controller processes/working directories and their
unavailability; recovery on B and Mint must use backups/public history, not that
controller's private cache. The existing native node/management gateway and B
guard stay available. Merely stopping an unrelated idle service or renaming a
folder is not evidence of original-service-independent recovery.

The read-only host inventory confirms synchronized, distinct TN10 and B hosts
with storage available; it is not new service installation or shutdown evidence.
Existing TN10 history/observer services must not be stopped just to simulate a
missing dependency that this trial never used. Exact run-scoped shutdown/access
boundaries must be qualified at preflight. Same-owner root administration remains
trusted; no independent-human or malicious-administrator claim follows.

No live readiness claim is made until the full terminal payout and confirmations
succeed. State/UTXO/anchor checks, named outage, public-data availability, local
user proof turnaround, the unchanged shared hour/lease limits and real native
acceptance remain gates for the separately released rehearsal.

## Published immutable image

The generic image was built from commit
`aa4fd3381a996acf872313cb800f8c8bb4f9cf34` and published as:

`ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:cd42221a752ac0469e2b78254ab48aa8da0dedd8b491355e4a184cacd142f468`

The [publication](evidence/image-publication/publication.json) and retained built/
pulled-image smoke reports confirm successful CPU binding/startup with six stages,
no owner addresses in the image and no provider/proving call. The source-to-image
binding is preserved; subsequent publication metadata does not change runtime
sources, executable, guest, public parameter identity or the image. Actual CUDA
execution of this new staged package remains for the separately released run.

## Independent B preparation

The [B installation report](evidence/b-installation.json) records the trusted host
and bounded package helpers installed separately at `/opt/kpi-recovery-tn10-aa4fd33`.
The owner's public receiving files and fresh unfunded trial are private runtime
state under `/var/lib/kpi-cuda-guard/recovery-tn10-prep-20261020`, outside Git and
the image. The sponsor key was generated locally on B and was not exported; no
user wallet/native secret was imported. Private state directories are 0700 and
the receiving files/sponsor key are 0600.

B independently verified all six retained PR58 receipts with the new CPU host.
These checks do not produce receipts for the fresh trial or establish live chain
readiness. The existing guard remains disabled/inactive. No provider request,
funding, broadcast, proof job or unrelated-service change was made. Mint client/
parameter delivery and the concrete outage/access contract still need preflight
qualification before a separately authorized live rehearsal.
