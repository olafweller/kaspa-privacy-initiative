# One L40S CUDA qualification — 2026-10-18

The owner authorized one fixed GPU diagnostic via the existing Cloud → TN10 → B
management route. B alone used the existing service token and provider key; no
Cloud domain or secret was added. Preflight observed 6,665 seconds remaining,
an active independent guard and an idle worker with a fresh matching heartbeat.
The single start response was `alreadyStarted=false`; the lease was not extended.

The fixed two segment proofs (24/25), two lifts and join completed, with the worker
reporting 8.400876 seconds including hardware checks, phase verification and
comparison. Process-matched GPU activity was observed in all five proof phases.
Sampled peak process RSS was 606,609,408 bytes; sampled matching-process VRAM
peaked at 13,706 MiB. These are sampled values, not guaranteed absolute peaks.
The prover binary SHA and immutable image match the reviewed preparation.
`gpuExecutionQualified=false` inside the archived build metadata describes the
historical CPU-only build; actual runtime activity is in each resources report.

The 1,753,447-byte archive was durably backed up and hash/size checked on B, then
retrieved through the existing management route. An independent CPU process in
Cloud checked the trusted local verifier binary and input hashes and verified
all five receipt seals against the pinned PR40 claims, including seal/claim
mutation rejection. Development mode was disabled. The CPU result was copied
back to `/var/lib/kpi-cuda-guard/gpu-results` on B. The hash-named archive remains
in `/var/lib/kpi-cuda-guard/artifacts`; the downloaded original is preserved here.

This qualifies the selected five partial-proof workload. It does not prove the
whole classifier, its full ordered journal or a complete private payment.
No further GPU attempt or full-classifier job was started. The provider-stop
read-back is recorded separately; billing and persistent-volume cleanup remain
separate from compute stop. No Pod or retained volume was deleted.

To reproduce the independent CPU check with the trusted prepared package:

```bash
python3 poc/remote-cuda/control.py unpack poc/remote-cuda/evidence/gpu-qualification-2026-10-18/gpu-artifacts.tar.gz 08d21b6ce94a3a3aa47d7127e62aafea1e9f802ad0962d83e7daf3faeaef418c NEW_DIRECTORY
python3 poc/remote-cuda/control.py verify .local/remote-cuda-preparation/dist NEW_DIRECTORY
```
