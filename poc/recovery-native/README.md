# Integrated partial/full reserve exit guest — local execution qualification

PR55 was merged at `05ea24a5cdb89ba5dd2cfec1041b1e69fa8de68d`. This separate
relation integrates its terminal native policy into the actual zkVM guest,
retaining PR54/55's original code, proofs and evidence unchanged.

**Result:** all six linked batches and nine additional CPU cases completed under
the predeclared limits. Both native payout forms pass the real pinned script
engine. Genuine new outer receipts and proof-authorized native permission
issuance have not been produced. The corrected main history contains 13 transactions
and 22 distinct native inputs. No GPU/provider, funding, RPC or broadcast was
performed. This is execution/implementation qualification, not a new TN10 trial.

## New identity and enforcing relation

- Guest image: `095a2fb2f58c350ccd2688ae7f72748c915bd973c60fd4abaa8d87b282ad68b5`.
- Guest program SHA256: `6039c3ef645d620bdd7eef6384750e73f51bcc8f9182aae1b1ac3c963601e75b`.
- SDK/r0vm 3.0.3; same fixed wallet circuit, VK, public parameters, economic
  nullifiers and checked accelerated BN254 verifier. No new setup.
- Separate resource `0x76*32`, state tag `KPI-recovery-native-state-v1`, and
  transaction/batch domain tags. The old `0x75` state/guest cannot settle this
  instance. [ADR-0017](../../docs/adr/0017-integrated-recovery-native-guest.md).

The relation admits one pending exit against one selected reserve **at least**
as large as the requested amount. The real wallet proof authorizes the recipient,
amount and current nullifier. Until payment, private liability becomes an unpaid
exit liability without reducing backing. The exit journal commits the exact
permission script hash. An accepted covenant-bound issuance is recognized from
its actual output/script/rent/outpoint; an RPC or host success flag cannot grant
or discharge value.

Native enforcement fixes the lane and three inputs: permission, selected reserve,
sponsor. With positive change it requires three outputs; with exact reserve it
requires two. The exact-reserve prefix reuses upstream's zero-change branch and
pins the reserve amount. Principal plus permission-rent refund goes to the bound
recipient; optional sponsor top-ups do not create private value. No covenant
continuation/partial permission, extra sponsor inputs, diverted reserve or
untracked delegate output is allowed. State rent is separate.

Accepted permission/reserve consumption is matched by outpoint, independent of
honest payload tags. Unreconciled accepted consumption aborts the guest rather
than committing stale backing. A consumed reserve is replaced only when change
is positive; otherwise it is removed. A second unrelated registered deposit is
preserved. Paid exit history is retained without trying to rebuild scripts from
its retired reserve.

## Fixed six-batch chain

| Batch | User cycles | Segments | CPU guest execution |
|---|---:|---:|---:|
| Deposit registration | 552,697 | 34 | 0.215 s |
| Credit → invalid transfer → valid payment | 139,741,397 | 143 | 3.142 s |
| Bob exit: 4 test-KAS, 6 remain | 43,994,671 | 46 | 1.158 s |
| Bob permission/payout reconciliation | 1,496,280 | 79 | 0.299 s |
| Alice exit: exact remaining 6 test-KAS | 44,189,850 | 46 | 1.168 s |
| Alice permission/payout reconciliation | 1,623,712 | 85 | 0.305 s |

Full 352-byte journals are fixed in [targets.json](evidence/targets.json), with
prior/next root and lane-tip continuity. Every state settlement template consumes
the prior template's state output, using distinct sponsor inputs. Both issued
permission IDs and payout bodies are fixed before their reconciliation input is
frozen. Signature witnesses are absent from these non-broadcastable templates;
no fake receipt is substituted. Their IDs exclude signatures by the native v1
format, allowing a later genuine receipt to complete the same transaction.

The final accounting is zero reserve, private liability, pending deposits,
unpaid exits and permission rent; the state covenant retains its separate
100,000,000 sompi. Each user receives principal plus a separately sponsored
50,000,000 sompi permission-rent refund. The data context is synthetic, with
real public wallet-proof fixtures from PR55. No wallet secret is read or copied.
The rejected transfer has canonical proof points but a false intent binding. It
has a separate native funding input: application rejection does not undo an L1
input spend. Bob and Alice also have separate deterministic payout sponsor UTXOs.
The host scans the captured six-batch history as one sequence for native input
reuse. Templates already included in later batches are not counted twice;
alternative attacks and deliberate replay controls are separate histories.
This fixture check does not establish canonical UTXO availability or chain
acceptance and adds no native UTXO ledger to the guest.

[The measurement plan](measurement-plan.json) predates execution: 160M cycles
and 900 seconds per case, four CPU threads, 3,600 seconds aggregate. The final
15-case corrected campaign completed in **11.035 seconds**; sampled process-group RAM peak
was **80,941,056 bytes**. This is execution time, not outer proving time. The six
main guest sessions total 6.286 seconds; process setup/control cases explain the
larger campaign duration. All main sessions have multiple segments for the fixed
join profile. Nothing revises the original 32M comparison result.

The nine additional guest cases cover permission issuance without payout (the
full exit obligation remains), a replayed wallet exit, six authentication changes,
and an unreconciled accepted payout. Only explicit semantic guest panics count
as required aborts; resource failures never count as successful rejection.

Nine Rust tests retain both payout forms, 17 semantic native rejection variants,
sponsor top-ups, tagless payouts, a second pending deposit during full drain,
zero-output rejection, amount/rent overflow, bad permission and replay, and
old-real/fake receipt rejection. The new regression reintroduces each reviewed
native conflict independently and requires the whole-history check to fail.
[Wallet CLI checks](evidence/wallet-cli.json)
reconstruct all six states exactly, enforce the four receiving fields, reject
unauthorized exits/history changes and refuse an old relation's accepted root.
CI repeats host/native regressions and regenerates the frozen public package;
it checks stored CPU evidence but does not rerun the zkVM or produce receipts.

## Focused fixture correction after review

The original `8922c193` corpus reused the invalid/valid transfer funding input
and both payouts' sponsor input. Both conflicts were reproduced from its actual
binary inputs. That corpus cannot represent one accepted native history, although
its CPU measurements still describe those exact inputs. Its complete evidence
and runmanifest remain byte-preserved in
[prior-input-set-8922c19](evidence/prior-input-set-8922c19/README.md), with a
[conflict reproduction](evidence/prior-input-set-8922c19/reproduced-conflicts.json).

Only fixture funding outpoints and the dependent inputs, IDs, roots, journals,
compiled host expectations and measurements changed. Guest image, wallet proofs,
VK/setup, native restrictions and measurement limits are unchanged. The active
[native-history report](evidence/fixtures/native-history.json) is regenerated
from actual input bytes during package checks. CI also reproduces the two old
conflicts and verifies the archived manifest. The review scope is these fixture
changes; no new subsystem or design decision is introduced.

## Reproduce locally

Use the existing pinned toolchain/native prerequisites. Standard host preparation
and checks require Rust 1.91.0; guest rebuild uses the qualified `kpi-risc0`
toolchain and bigint2 advertisement, not a new unpinned SDK.

```bash
source /workspace/.onboarding/activate.sh
cargo +1.91.0 test --locked --release --manifest-path poc/recovery-native/Cargo.toml
cargo +1.91.0 build --locked --release --manifest-path poc/recovery-native/Cargo.toml
python3 poc/recovery-native/check_evidence.py .local/ci-target/release/kpi-recovery-native-host
python3 poc/recovery-native/test_wallet_cli.py .local/ci-target/release/kpi-recovery-native-wallet
bash poc/recovery-native/build_guest.sh /new/guest-directory
```

A separate user wallet binary adapts PR55's reviewed wallet only to this new
relation/root namespace. `init USERDIR` creates private wallet/native key files
and receive-only public fields; `scan STATE INDEPENDENT_ROOT USERDIR` verifies
the new committed root before discovery. `exit STATE INDEPENDENT_ROOT USERDIR
PARAMETERS NEW_OUT` creates a real wallet proof locally, deriving the native
recipient from that user's local key. `rebuild START_ROOT END_ROOT NEW_STATE
INPUT...` reconstructs the committed public history. No secrets enter an outer
input. The original PR55 binary remains unchanged and checks old roots only.
Neither binary establishes checkpoint freshness, canonical selection or independent
administration. Use an independently verified current chain root before a future
spend; missing/pruned history and expired/reorganized anchors still require the
specified recovery procedure, never a relabelled root.

`prepare NEW_OUT` deterministically recreates the local six-batch corpus from
retained public data. `profile PROGRAM FIXTURES CASE NEW_OUT` executes only and
must be wrapped in [run_qualification.py](run_qualification.py) for the stated
process-group wall deadline. There is no proving or broadcast command here.

## Prepared genuine-receipt boundary

`verify STAGE RECEIPT` requires a real Succinct receipt, the independently compiled
new program and exact complete journal, official join control, disabled development
mode and no unresolved assumptions. Old real receipts and fakes are rejected.

`native-issuance bob-exit|alice-exit RECEIPT NEW_OUT` first performs that cryptographic
verification. It then builds the actual receipt-bearing settlement, requires its
ID to match the frozen permission transaction, runs all actual native input
scripts, and checks the restricted payout and accounting. The native chain accessor
is explicitly a local context. This entrypoint has been compiled and guarded
against old/fake receipts; its **positive new-receipt route remains unexecuted**
until an outer proof is separately released and produced. Synthetic permission
UTXOs in current payout tests do not qualify issuance by themselves.

## Fresh-instance requirement and next bounded package

The old PR54 pool remains under its old guest and positive-change restriction.
This code neither upgrades it nor releases its remaining 6 test-KAS. The local
fixture covenant is not that actual TN10 covenant. A future TN10 rehearsal must
create a fresh native bootstrap/outpoint/covenant with this new image from inception;
actual deposit IDs/captures require fresh user wallet proofs and outer receipts.
Do not point the old fixed GPU service/image at this workload or reuse its lease.

[runmanifest.json](runmanifest.json) identifies this unfunded local instance and
six frozen targets. The next concrete software package must add a bounded producer
for these six jobs, preserve candidates immediately, independently verify every
receipt and run both genuine permission-issuance checks. Retain one aggregate
3,600-second proving/compression/check limit, one attempt, one L40S and the
7,200-second actual-creation lease and USD5 planning allowance. Image publication
and actual rental/proving require their own concrete release. CPU speed is not
a guarantee of proving time/cost.

Independent Bob custody, archive availability, replacement services and every
user's canonical TN10 payout after original-service shutdown remain unproven.
Multiple concurrent exits, reserve combination and production privacy/security
remain outside this qualification. See the [adversarial review](ADVERSARIAL-REVIEW.md).
