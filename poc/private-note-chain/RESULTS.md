# Private-state integration calibration — 2026-10-18

## Outcome

**The new private-note state relation executes correctly in the pinned zkVM for
21 of 22 selected scenarios. The complete valid-invalid-valid three-proof
sequence reaches the original 128,000,000-cycle limit before completion.**
It is a failed bounded full-sequence qualification, not a successful full run or
a proof. The campaign stopped there, with no retry/budget increase, GPU rental,
new receipt, native script acceptance or TN10 broadcast.

The completed cases include real credit/transfer/exit proofs, native deposit
output checks, state/config/lane/start authentication aborts, a distinct valid
old-root competing spend after an earlier batch, replay, credit/recovery races,
malformed-then-valid and canonical cryptographically-invalid-then-valid processing.
Current spentness survives the previous state transition; rejected operations do
not partly change notes, nullifiers, deposits or liabilities. Every native lane
ID/payload, including rejected operations, contributes to the computed endpoint.

## Exact execution results

| Selected scenario | User cycles | Executor seconds | Outcome |
|---|---:|---:|---|
| Native deposit descriptor/output | 601,274 | 0.164 | Completed |
| Credit | 46,496,204 | 4.165 | Completed; dynamic profiler enabled |
| Transfer | 47,354,991 | 1.089 | Completed |
| Bob exit | 44,014,742 | 1.037 | Completed; unpaid principal still backed |
| Old-root competing proof in next batch | 47,188,198 | 1.165 | Correct atomic rejection |
| Credit/recovery replay | 44,770,315 | 1.190 | Correct atomic rejection |
| Recovery then credit | 90,731,457 | 2.081 | Recovery accepted, credit rejected |
| Malformed then valid | 48,152,733 | 1.143 | Rejected then accepted |
| Canonical invalid then valid | 93,764,328 | 2.142 | Rejected then accepted |
| Full valid-invalid-valid | **Incomplete at 128M** | 3.007 | **Session limit exceeded** |

All four authentication aborts were matched to their intended guest assertions;
resource/IPC failures cannot pass those checks. Seven native-deposit/destination controls, plus cross-batch replay, also completed. The
full inventory and process-group resources are in [campaign.json](evidence/campaign.json).
Every completed 352-byte journal matched the independent native Arkworks result.
The final journal commits state, full lane endpoint, covenant and permissions;
public reference events/transaction journals are retained separately, not appended
to the native 352-byte ABI.

The last full-run stages were two completed pairings, then checked decoding of
the third proof at 102,650,991 cycles and input preparation at 114,767,884 cycles.
The third pairing did not complete. **Total full-run cycles are unknown.**
The observed stages suggest roughly 139–140M, but that is an extrapolation, not a
completed measurement or authorization to increase the budget.

Four CPU affinity slots/compute threads and the existing 16 GiB environment were
used, without RLIMIT_AS. Sampled process-group RSS stayed below 80 MiB during
execution; wait4 maxima are also retained and are not sums of simultaneous RSS.
Credit profiling changes wall time, not the guest-cycle statement. Dynamic pprof
observes `sys_bigint2_3`, `_4`, `_5` and the bigint2 field module in this guest;
acceleration is measured, not assumed from dependencies.

A first preflight failed before starting a guest because RISC0_SERVER_PATH was
missing. Selecting the existing checksum-pinned r0vm fixed setup. That observation
is retained separately and never counted as a passed rejection or resource run.

## New wallet/setup and recovery

The chosen TN10-domain circuit has 774,608 constraints and fourteen packed public
field inputs (the previous proxy baseline used four). New VK:
`d3c179aae5c2c6c013b1de1da5ad4412e4b2c8bae7288c0b9d85e0c986b5a3ec`.
New monolithic guest image:
`20d8431e18f42c6e337ab726f166914516e3ebcd70577e67d49e687737901f8b`.
Both were frozen before execution. The compiled guest rebuild is byte-identical.
PR44's local-domain artifacts and PR43's old classifier remain their own baselines.

New setup took 14.279s. Public parameters are 156,439,536 bytes; checked reload in
the generation process took 48.591s. A separate process restored Bob's own keys,
found his note using public accepted data and made a fresh actual exit proof with
the same economic nullifier. Its full reload/discovery/proof/check took 53.360s
including process overhead, with 2.43 GiB peak wait4 RSS. The generation job took
111.640s and 2.77 GiB. These are local CPU observations, not mobile measurements.
The parameters remain local, hash-pinned; off-machine durable availability is not
established. No wallet secret/opening/path enters public evidence or guest input.

Five focused chain tests pass, including all fourteen field-input mutations
compared with native Groth16, false pairing, wrong subgroup/identity points,
state/config substitution and eighteen archived reference/backend scenarios.
All nine original PR44 tests still pass. Passing these tests is not a security
audit or proof of production correctness.

## What remains

This is a monolithic native-preimage calibration, not a completed recursive
transaction/batch/aggregate chain. Native endpoints are locally constructed
fixtures, not observed canonical TN10 anchors. A real outer receipt and actual
native script checks, stable funded deposit recovery, permission-consumption/
exact payout confirmation, rent/fees and independent durable recovery remain
unqualified. The reserve stays at 10 with private liability 6 and unpaid exit 4;
no native payout has happened. See [BINDINGS.md](BINDINGS.md).

Keep the 128M failure intact. The [GPU decision](GPU-PROPOSAL.md) recommends no
rental now: first decide a bounded CPU-only response to this measured execution
limit, then qualify a complete route before proposing an actual proof job.
