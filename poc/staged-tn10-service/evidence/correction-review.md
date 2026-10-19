# PR53 targeted correction after Astra review

Baseline: `71575ad40826b59efed6fe6b08a5780876452a07`. Historical reports and
manifests remain in `history/pr53-71575ad/`; the public host/guest package and
all native/proof identities are unchanged. This is a focused implementation
self-review, not a renewed independent Astra review.

## Reproduction and correction

Three new regression tests were run against the original baseline functions
loaded in memory. All three failed as expected (four failures including metadata
subcases); see `old-head-regressions.txt`. No repository source swap was needed.
The corrected versions pass. Tests allocate small metadata fixtures and use low
injected expansion limits instead of memory exhaustion.

- PAX/GNU extension metadata: the former parser received compressed bytes before
  its file-size checks. Both upload and external-verification regressions now
  assert that over-limit expansion fails **before tarfile.open is called**.
  `staged_archive.py` bounds gzip expansion including headers/extensions/padding,
  then passes only bounded uncompressed bytes to tarfile. Upload limits are
  8 MiB compressed / 16 MiB expanded / four logical members. B evidence limits
  are 64 MiB compressed / 256 MiB expanded / 2,048 logical members. The compressed
  B file read is bounded before allocation; exact expansion-boundary and member
  count cases are tested too. File/type/hash/journal checks are retained.
- Repeated process loss: a real CPU wait process runs in a separate group under
  GNU timeout. The first injected recovery loss occurs after durable interrupted
  state but before the kill, and the process is shown still alive. The next
  restart invokes identity-checked cleanup and the real process exits by signal.
  A further restart is safe; ledger, deadline and consumed attempt are identical.
  The gate still closes before cleanup, and no second job is launched.

## Adversarial second pass

The changes add no monetary operation, key path, proof relation or native policy.
They cannot mint, double-spend or authorize reserve release. Trusted targets and
independent real receipt checks still determine acceptance. Tar parsing remains
non-extracting; data cannot replace an executable or expectations. Caps include
hidden metadata rather than just surfaced files. A malicious/unavailable prover
can still deny progress; it cannot extend either deadline or gain a retry.
Repeated cleanup retains PID/start-time/boot-ID matching and avoids killing a
reused unrelated PID. No new credential or administrator trust is introduced.
Privacy, reorg and actual-chain freshness limitations remain unchanged.

The selected wallet/guest/native code and USD5 planning / one L40S / one attempt /
3,600 aggregate seconds / 7,200 rental seconds are unchanged. This work starts no
new proof, GPU rental, provider action, funding or TN10 broadcast.

## Requalification

All 44 remote-CUDA tests passed, including the 15 staged service tests. The
corrected image publication workflow passed, pulled its immutable digest and
repeated CPU image checks. This Cloud task also pulled that exact digest and
repeated the source/binary/startup/restart/retained-receipt checks; see
`publication.json` and `published-image-smoke.json`. Runtime code is unchanged
between the published source commit and the publication-metadata follow-up.
The old image is historical evidence and is superseded for any future trial.
