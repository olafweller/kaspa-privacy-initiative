# Approved 128M outer-proof attempt — 2026-10-17

**All 24 existing execution cases pass under the newly approved 128M budget.
The single real outer-proof job is stopped at its 3,600-second wall limit without
returning a receipt.** No retry or budget increase is performed. The full compact
wallet classifier is execution-qualified for these fixtures, but a completed
outer classification receipt remains an open milestone.

PR38 was finalized and merged as `99d35099d6640108db76a5ba6db8eff18d2b79d3`.
Its calibration and PR37's original 32M failure remain unchanged. New limits
were committed before execution in `3fa6a56e0966a40d28cdeb3cedcc2f9af217231b`;
the executed proof harness source is `ccd3d51` (full revision in the evidence).

## Retained statement and completed qualification

No guest code, wallet circuit, VK, wallet proof or operation fixture changed.
The image remains
`397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.
Qualification checks program, fixture and public key bytes against the published
PR38 archive. No setup or wallet proving job is run.

Independent expected journals are prepared before execution/proving. Main root,
initial state, every native ID, outcome and balance come from the original
retained expected fixture; other complete journals use the unchanged native
Arkworks reference plus explicit outcome/state assertions.

| Existing cases | Count | Result |
| --- | ---: | --- |
| Full valid-invalid-valid, replay, changed-public-input, eight malformed-then-valid sequences | 11 | All exact journals match |
| Withheld, substituted, omitted, reordered, trailing host verdict | 5 | All specific expected authentication assertions |
| Eight malformed-only sequences, including wrong-subgroup G2 | 8 | Outcome 2; initial balance unchanged |

Main outcomes remain **[0, 3, 0]**, with proxy balances
**[600,000,000, 600,000,000, 500,000,000]** integer sompi. Full replay yields
**[0, 4, 0]**; all full malformed cases yield **[0, 2, 0]**. Corrupting a
canonical on-curve subgroup C point still fails the actual pairing equation,
after which genuine C is accepted. No resource/IPC failure counts as rejection.

## The one real proof job

The host checks all 24 qualification reports/input/journal hashes, reruns the
main bounded execution and invokes the existing pinned SDK's real
`prove_with_opts(..., ProverOpts::succinct())` exactly once. This requests the
completed succinct receipt, including required proving/compression/resolution,
inside the same process-group clock. Development mode and supplied assumptions
are forbidden; no easier malformed-only proof or fake receipt is substituted.

| Measurement | Observed result |
| --- | ---: |
| Whole proof-job budget | 3,600 seconds |
| Stop and cleanup wall time | **3,600.31 seconds** |
| Stop reason | **Wall-time limit; process group killed; runner exit 124** |
| Main execution user cycles | **117,473,222** |
| Main execution total cycles, including paging/reserved | **125,960,192** |
| Executed segments | **121** |
| Pre-proof executor wall time | **2.91 seconds** |
| Peak sampled summed process-group RSS | **9,870,041,088 bytes (9.19 GiB)** |
| Sampled cumulative CPU | **14,100.15 user + 23.79 system seconds (3.92 CPU-hours)** |
| Peak sampled group OS threads / processes | **11 / 2** |
| Returned candidate/completed receipt | **None / none** |

The last completed host checkpoint is the exact main execution profile.
`prover-started.json` and the prover's completed execution/session log are
retained, but the prove API did not return any receipt or proof stats. The log
does not expose reliable intermediate STARK/lift/join completion counts; **121
executed segments must not be reported as 121 proven segments**. Complete
proving time, completed receipt size and complete proof-stage costs remain unknown.

## Hardware, limits and measurement boundaries

The environment reports x86_64 AMD EPYC 9V74 hardware. The proof is confined to
logical CPUs 0–3, under a **4-CPU quota**, with Rayon/OMP thread settings of 4.
The 11 observed OS threads include helper threads; affinity/quota still restrict
actual CPU use. No GPU or remote proving service is requested.

Every process inherits a hard **12 GiB address-space limit**; a 200 ms sampler
also enforces a **12 GiB summed process-group RSS stop threshold**. The separate
environment cgroup cap is **16 GiB**. The watchdog stops the whole group at the
deadline with normal polling/termination latency; no 15-second grace extends
proof production. The watchdog was exercised before the attempt.

Summed RSS can double-count shared pages and miss brief peaks. A late kernel
`VmHWM` snapshot records the prover's individual peak at 9,625,344 KiB; the
snapshot is not an after-exit whole-job maximum. The environment-wide cgroup
reports 11,296 `memory.max` events and **zero OOM/OOM-kill events** at job end.
Those counters include page-cache/other environment usage and do not prove a
pure CPU bottleneck or attribute every event to this process group.

After the hard kill, parent `wait4` reports only 3.36 user CPU seconds and a
small parent RSS: it cannot account for an unreaped prover child. The additional
`/proc` monitor records cumulative own/waited-child CPU counters, yielding the
3.92 CPU-hours above. Observation began during the job; counters already include
the processes' prior CPU work. Exit transitions and sampling can cause gaps, so
these are sampled cumulative measurements, not exact full-group kernel totals.
Both raw forms are retained rather than reporting the parent's tiny usage as
the proof cost. No active prover remains after termination.

## Receipt verification and conclusion

Real proof-production and separate receipt-verification entry points are
implemented and build. The verifier requires a genuine succinct receipt,
successful exit, the independently expected image and exact journal, development
mode disabled, and no unresolved assumptions. It invokes actual receipt
verification for a wrong expected image and five journal mutations covering
root, initial balance, native ID, outcome and final balance.

**These receipt-verification executions were not run: no receipt was produced.**
Execution-artifact comparisons and 24 passing guest controls do not substitute
for cryptographic receipt verification. There is no completed outer proof,
privacy-payment demonstration, accepted L1 lane or native settlement claim here.
All work is local and unfunded; no new private-note circuit or TN10 transaction.

The approved experiment closes the missing full adversarial execution checks
and supplies a concrete negative result for one bounded CPU proof attempt.
It does not show that Groth16 or the classifier cannot be proved with another
implementation/resource profile. The next useful step is bounded profiling of
segment proving and recursive compression, including memory/cache pressure,
before selecting another experiment. Do not automatically extend the budget,
weaken the statement or expand to the full private-note circuit as if this
receipt milestone had passed.
