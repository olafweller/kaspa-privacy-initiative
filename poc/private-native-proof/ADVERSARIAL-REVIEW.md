# Package adversarial second pass

- **Mint, reserve release, replay, stale state:** this preparation does not change
  the reviewed guest, native scripts or wallet relation. Exact binary/input pins
  and compiled receipt expectations retain those constraints. Complete journals
  and root/tip continuity prohibit switching or reordering batches. No arbitrary
  target/command can be selected through the authenticated start request.
- **Malicious GPU:** its receipts, status, logs and binaries are untrusted.
  Independent CPU/B verification uses only the trusted package executable and
  its compiled image/journal/control expectations. Downloaded executables are
  never run. All returned inputs are hash-checked and archives reject links,
  traversal, duplicate members and oversized payloads. Partial cryptographic
  success is reported as partial, not full qualification.
- **Timeout, controller loss and dependencies:** one external GNU timeout
  supervises the same group as all four prover/compression/check jobs; the
  independent service-side timer is also retained. Real local tests kill hung
  descendants and lose the controlling process. Current pinned SDK subprocesses
  inherit their caller's group; the runner never detaches children. A future
  SDK/worker change needs renewed qualification. Missing runtime libraries or
  CUDA telemetry prevent qualification; there is no CPU fallback claim or retry.
- **Completed results and guard failure:** candidates are saved before producer
  verification; prior stage files/receipts remain after later failure. Existing
  checkpoint archives and B's hash/size/fsync/atomic preservation remain unchanged.
  The absolute provider-stop deadline is independent of backups/Cloud. Durable
  preservation and confirmed EXITED/deletion are still real-rental qualifications,
  not outcomes fabricated by these local mock/provider tests.
- **Secrets and privacy:** allowlisted public inputs and public executables only;
  no wallet backup, witness, setup parameters or provider account key are copied.
  Proof children receive a restricted environment without service/provider tokens.
  Public fixture keys must never be funded. Tiny-tree and public deposit/exit
  leakage, setup trust, compiler/verifier trust and public-data availability remain
  the existing experimental limitations. This is not an anonymity improvement.
- **Operator trust and spending:** B root remains a trusted administrative role;
  a management connection does not protect secrets from a malicious root. The
  new service retains one-attempt, concrete-lease and fresh-guard requirements.
  It gets no account-level provider credential. Existing two-hour rental, one-hour
  aggregate diagnostics and USD5 quote-based planning remain unchanged. Actual
  charges, stop/write rights and GPU execution cannot be established by package
  preparation. There is no native broadcast/funding command in this workload.

No automatic Astra agent, provider call or proof job is used for this review.
