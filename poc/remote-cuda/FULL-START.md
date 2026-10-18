# Full-classifier attempt runbook

Use this separate fixed workload only after the owner authorizes a new attempt.
The earlier qualification Pod, lease and attempt marker are historical evidence;
do not restart/reset them for this workload.

1. Build the public package with `full_package.py`. It pins the PR39 archive and
   all 116 required program/fixture/expectation/qualification files. Run the
   rebuilt CPU host's `outer-proof-128m check PROGRAMS FIXTURES EXPECTATIONS
   QUALIFICATION` entry point to validate the reused 24 cases without new proofs.
2. Build `Dockerfile.full` using that package and run `check_full_image.py`.
   Publish via the `cuda-full-classifier-*` tag workflow, then record/check the
   actual immutable registry digest and source revision. The base CUDA prover
   remains 4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb;
   the base image's proof host remains
   3794fd416c903b1034801adcae647681c9442c67f963d3e2b2db915e50bde6d6.
   The independently rebuilt CPU verifier has its own recorded hash.
3. Prepare B's separate `/var/lib/kpi-cuda-guard/full-20261018-01` directory and
   `kpi-cuda-full-guard.service`, using the existing root-only credential file.
   Validate permissions/unit and leave inactive until a real valid lease exists.
   Existing stopped qualification and old experiment states must remain intact.
4. Obtain the current L40S secure on-demand quote from the provider; evaluate
   two-hour compute plus allocated active/stopped storage and retention against
   USD5. Allocate exactly one GPU Pod by the reviewed full image digest with
   90GB container/10GB /workspace, 8080/http and the existing service token,
   sourced only inside B. Do not log credentials or the full provider response.
   Save the returned Pod identity immediately, then verify actual quote/resources.
5. Use the provider creation time plus at most 7,200s for the separate lease.
   Write it readable by the existing service user, start/enable the prepared
   full guard, and require matching authenticated idle status and fresh heartbeat.
   Cloud administration remains through TN10 -> B only. No Cloud secret/domain
   change and no runtime dependency on Cloud/gateway/laptop is required.
6. Require over 3,660s remaining, then send `/v1/start` once via B. Save durable
   start intent/response. Poll status and let B store size/hash-checked snapshots.
   Do not reset attempt state, retry a failed proof, or raise resource limits.
7. Retrieve the final B archive over the existing management route and unpack
   only checked regular paths. Compare all returned public inputs to the locally
   trusted package. Check the independent local CPU verifier's saved hash, then
   run `outer-proof-128m verify LOCAL_EXPECTATIONS RETURNED_PROOF NEW_OUTPUT`
   with `RISC0_DEV_MODE` absent and `RISC0_PROVER=ipc`. Require the verification
   JSON's exact journal, wrong-image/journal-mutation and corrupted-seal results.
8. Preserve that CPU report on B as well as the proof archive and metrics.
   The independent B guard stops after its bounded terminal-backup grace or
   absolute deadline. Read the exact Pod back through the provider and require
   EXITED; a stop-request acknowledgment alone is insufficient. Save observations,
   reconcile available charges, and explicitly report retained volume storage.
   Do not delete evidence or a retained volume as part of proving.

The new fixed service uses `/workspace/kpi-full` and never accepts a client-chosen
workload. Its one-hour clock includes execution and all succinct receipt work.
The qualified RSS/affinity/telemetry wrapper is reused without the old RLIMIT_AS.
A completed full classifier receipt remains a toy test-model milestone, separate
from a full private-note relation, private payments or native settlement.
