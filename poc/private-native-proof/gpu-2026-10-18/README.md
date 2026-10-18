# Four-batch GPU rehearsal: stopped before the first proof

The owner released one local L40S attempt after review of PR50 at
`39656e33db268cd6c0599e050854397b6d99c850`. PR50 was confirmed unchanged with
nine green checks and squash-merged as `cde2b88de3a16af401a2046bd90a124aa105418a`.
The fixed package was run once. **The proof experiment failed before producing
any receipt.** This does not complete the local four-receipt lifecycle milestone.

## Actual allocation and stop

| Item | Observed result |
| --- | --- |
| Pod | `zx39ajm30jc52a` |
| Image | `ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:aefe98f7e463ba3bbc4cc6b692cc739c04d083718983deb79b2543debb150db7` |
| GPU | One L40S, 46,068 MiB reported, compute capability 8.9 |
| Driver | 580.126.09 |
| Allocation | 16 vCPUs, 188 GB provider RAM, 90 GB container disk, 10 GB local volume |
| Creation | 2026-10-18 21:01:06.648 UTC |
| Proof start | 21:02:06 UTC, about 59 seconds after creation |
| Provider-reported exit | 21:03:20 UTC, about 133.35 seconds after creation |
| Stop independently observed | 21:03:32.950 UTC, API reported `EXITED` |
| Deletion confirmed | 21:04:36.911 UTC, API 404 and absent from a successful Pod-list response |
| Remaining Pods | Zero |
| Guard after cleanup | Disabled and inactive; old experiment state preserved |

B's NTP, approximately 80 GiB free space, unchanged guard hashes and trusted
package were checked before rental. All four compiled target checks passed on B.
The actual quote was USD1.09/hour; the conservative two-hour/storage/retention
plan was USD2.2752. The read-back image, fresh scope
`FIXED_PRIVATE_NATIVE_FOUR_SUCCINCT_RECEIPTS`, lease identity and heartbeat matched.
The controller required a full hour plus 300 seconds of transfer margin **before
B's effective stop time**, rather than relying on the service's minimum margin.

The actual-creation lease remained 7,200 seconds; B's pro-active stop boundary was
23:00:06.648 UTC, one minute before the absolute boundary. Following the failure,
B preserved the terminal archive and stopped compute after its terminal-backup
grace. No limit was increased, retry performed or workload changed.

## Failure and root cause

The first deposit producer exited with code 1 after **0.1149 seconds**:

```text
Error: Os { code: 2, kind: NotFound, message: "No such file or directory" }
RuntimeError: fixed lifecycle stage failed: deposit-prove
```

The runner creates `output/stages`, then passes `output/proofs/deposit` to the
reviewed Rust producer. The producer uses `fs::create_dir(out)`, which does not
create missing parents. `output/proofs` was never created. The producer fails
before saving `started.json` or entering the prover. The following verifier would
have the same defect at `output/cpu/deposit`: `output/cpu` is also absent.

[The local reproduction](reproduce_output_contract.py) uses the exact reviewed
runner and a synthetic executor implementing the pinned Rust filesystem contract.
It performs no proof command, GPU request or provider action. Its three cases show:

1. No parents: failure at the first proof's missing `proofs` parent.
2. Only `proofs` exists: failure at the first verification's missing `cpu` parent.
3. Both exist: all nine synthetic stages complete.

The prior synthetic orchestration test created proof directories recursively and
did not implement verifier directory creation, so it concealed this mismatch.
The prior CPU image checks validated target loading and service startup, which
did not exercise producer output-directory creation. This is a preparation defect
in our runner; passing review and CI did not establish that contract.

The repair must create **both parent directories** before launching children
and retain a regression matching the real producer/verifier contract. The owner
subsequently authorized that narrow correction and one fresh attempt after new
image qualification. The current PR includes the directory fix and a new
real-subprocess regression, while retaining the original runner here for the
historical reproduction. PR50's original preparation records are archived in
`preparation-pr50`; the first failed Pod/lease is never restarted or reset.
The guest, wallet circuit, proof binary, public inputs and PR48/PR49 evidence
remain unchanged. The fresh attempt requires a newly qualified runtime digest.

## Separate outcomes

| Fixed batch | Producer time | Receipt / verification |
| --- | --- | --- |
| Deposit | 0.1149 seconds to failure | None; no cryptographic verification possible |
| Credit-transfer | Not started | None |
| Exit | Not started | None; native exit check not run |
| Reconciliation | Not started | None |

| Criterion | Outcome |
| --- | --- |
| Four actual receipts | 0; no candidate receipts |
| Independent cryptographic verification | 0 receipts available; incomplete result reported on B and Cloud |
| New exit receipt / native permission / payout | Not run; no new exit receipt |
| Matching-process CUDA activity | Not established; zero matching active samples |
| Aggregate process time | 0.2971 seconds; early process failure, no deadline overrun |
| Proving cycles or segment count | Not measured |
| Proving RAM/VRAM | Not measured; 1 MiB launcher RSS sample and zero matching VRAM are not prover benchmarks |
| Public-input/archive verification | Passed independently on B and Cloud |
| Durable external preservation | Passed, 661,894-byte archive, SHA256 `b699a45ef52a5537d871941d6468443a889e09641ccf33ae47aa79e44fd02ffe` |
| Provider stop and deletion | Confirmed after external preservation |

The wrapper records `cuda-process-activity-not-established` after the early
nonzero process exit. That is an absence of GPU evidence, not the primary cause.
No resource failure is counted as a cryptographic or native negative control.
The three remaining batches never started. There is no throughput, four-proof
feasibility, native settlement, TN10 acceptance or privacy conclusion from this run.

## Cost and retained evidence

The provider rate and reported creation/exit times imply about **USD0.0404 compute**.
Using the later independent EXITED observation and charging the conservative
active-storage allowance through deletion gives an estimate of **USD0.0451**.
These are estimates; no itemized invoice was available. There is no remaining
Pod or separately created network volume associated with this attempt.

The [machine-readable result](evidence/result.json),
[cost calculation](evidence/cost-estimate.json),
[B audit](evidence/results/b-verification.json),
[stop observation](evidence/results/provider-stop-observation.json),
[deletion](evidence/results/provider-deletion.json) and
[evidence manifest](evidence/manifest.json) distinguish the failed proof attempt
from successful operational cleanup. The terminal archive remains on B and is
also retained here. No account/service credential was exported or printed.

Run the local evidence and source-contract checks without a provider or prover:

```bash
python3 poc/private-native-proof/gpu-2026-10-18/check_evidence.py
```

No native funding, wallet setup, guest change or TN10 broadcast took place.
