# One complete classifier receipt on the qualified CUDA backend

Declared 2026-10-18 before new allocation/proving, following explicit owner
acceptance of Astra's bounded proposal. Preserve the completed PR42 qualification
and its stopped Pod unchanged; this is a distinct attempt and lease.

Reuse the original PR39 `outer-proof-128m prove` route, succinct receipt options,
128,000,000-cycle limit, unchanged classifier image
`397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`, wallet
proofs, operations and exact expected journal. Reuse the hash-checked 24-case
execution qualification; do not re-prove 24 cases or regenerate wallet setup.
The Rust receipt-check change adds a corrupted-seal negative check in the
independent verifier. A read-only check entry point reuses the existing
qualification gate; the guest and proof-generation implementation are unchanged.

Prepare and CPU-check a derived image before paid compute. Its base is the
previously GPU-qualified immutable CUDA image; retain the exact r0vm binary,
SDK 3.0.3 and CUDA build. Add a fixed full-proof package/worker only. No HTTP
endpoint permits choosing commands, files, inputs or limits. Use a fresh Pod,
volume namespace, attempt marker, B state directory and guard unit. Do not
rearm/reset the completed qualification lease or modify its archived records.

Limits: exactly one NVIDIA L40S; four CPU threads/affinity; 3,600 seconds for the
entire proof job including execution, proving, succinct compression/resolution,
receipt saving and on-host checks. Keep the qualified 12 GiB sampled summed
process-RSS stop policy, without RLIMIT_AS. Maximum rental envelope is 7,200
seconds from actual provider creation, with guard stop/retry beginning one minute
earlier. Before allocation obtain the actual L40S quote, include active/stopped
storage and at most 24-hour retention in the USD5 usage planning envelope.
The envelope is not a guaranteed provider bill. No automatic retry, allocation
retry, larger budget, easier statement, developer mode or fake receipt.

B remains the independent control/backup/stop host. Provider credentials stay
only on B; the existing scoped service token is used there for fixed Pod API
requests. Cloud uses the existing TN10 -> B management route; no new Cloud
secret or allowed domain. Save returned receipts immediately and snapshot
partial logs/checkpoints during proving. Preserve and size/hash check the durable
B archive before guard's terminal grace expires. Confirm stop through a separate
provider GET and retain state/charges where available; deletion is separate.

Independently verify the complete succinct classifier receipt on CPU using the
fixed expected image and exact full journal, successful exit and empty
assumptions, with development mode disabled. Require real cryptographic rejection
of wrong image, journal mutations (root, initial balance, operation ID, outcome,
final balance), and corrupted seal. Record CPU verification separately from the
GPU's self-report. Report full proof wall time, cycles/segments, CPU/RSS/VRAM,
prover/source hashes, stop read-back, retained storage and all limitations.
No TN10 transaction or private-note circuit work is included.
