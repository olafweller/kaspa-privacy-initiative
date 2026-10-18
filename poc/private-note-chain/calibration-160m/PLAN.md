# Owner-approved single CPU calibration — declared before execution

The owner supplied Astra's reviewed request after PR45 (695c049), explicitly
approving one separately labelled 160M execution-only measurement. PR45 was
merged as reviewed; its original 128M evidence and failure remain unchanged.

- One scenario only: credit -> canonical cryptographically-invalid transfer ->
  valid transfer, expected outcomes [0,1,0]. Input begins after a synthetic
  deposit registration. Bob's exit and actual native payout are not in this run.
- Maximum 160,000,000 user cycles, maximum 900s for the entire process group.
- Four CPU affinity slots and four Rayon/OpenMP/BLAS threads, original memory
  policy without RLIMIT_AS. Record observed process-group RSS and wait4 RSS.
- Exactly PR45's compiled guest/image, verification key, actual wallet proofs,
  input and expected output. No setup regeneration, guest build/change or input
  simplification. Check artifact hashes against the original Git revision.
- The changed host command is `profile-160m`; it only permits this one scenario.
  Original `profile` and the default campaign remain at 128M. The runner requires
  explicit `--approved-160m` and then selects only this case, with no retry.
- Pin updated host executable/source and runner identities before starting.
- Require byte-for-byte equality with the frozen 352-byte expected aggregate
  journal; report actual user cycles, segment count/po2/sizes, summed padded
  cycle slots, wall time and process-group RSS. Padded cycle slots are not a
  measurement of serialized trace bytes; execution does not materialize a proof.
- If 160M or another declared resource limit fails, stop and record the last
  completed stage. Do not count it as rejection evidence, retry or raise limits.

No other 21 guest scenarios need repeating solely for a host-limit change.
No proof generation, GPU rental, provider action, native signing or TN10 broadcast
is included. Subsequent proof/native work will be specified after measurement.
