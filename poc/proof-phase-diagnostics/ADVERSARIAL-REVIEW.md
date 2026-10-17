# Adversarial second-pass review

AI self-review of the scoped diagnostic integration, not an independent audit.

- **Inflation, double spending or reserve release:** no classifier/guest, wallet
  circuit, value rules, settlement, keys or transactions are changed. The added
  entry points only execute fixed public fixtures and produce diagnostic partial
  receipts. They are not accepted as settlement or a complete batch proof.
- **Unrelated, stale or reordered claims:** the existing full qualification gate,
  independently pinned program image and expected full journal are checked before
  exporting assets. Submitted trace hashes are frozen in the execution manifest.
  Lift must preserve its segment claim; join requires adjacent state commitments
  and the exact composed claim. Partial receipts still rely on the trusted pinned
  executor/export for association with the original workload. They do not establish
  a cryptographically composed path from the initial image to the final journal.
- **Fake receipts or altered claims/seals:** development mode is forbidden and
  receipt integrity is cryptographically verified. Actual seal and claim mutations
  are tested when a receipt exists. A missing receipt or timeout is not a passed
  verification or rejection test.
- **Witness leakage:** the reused operations, traces, VK and wallet proofs are
  public synthetic research data. No wallet secret/proving parameters are read.
  Evidence collection uses an explicit whitelist rather than uploading caches or
  process environments. This does not establish financial privacy.
- **Dependency loss and recoverability:** retain actual verified receipts,
  selected trace bytes, source/SDK/prover identities, input hashes and public
  measurements in the repository. The old temporary files are never treated as
  proof progress based on their existence. Existing archives remain unchanged.
- **Resource/dependency failure:** each phase records its start and actual result;
  kill the entire IPC process group on a declared stop. Per-phase limits and the
  original aggregate clock remain binding. The one guarded pre-proof pathname
  repair preserves the failure, reuses exported bytes and cannot retry a proof.
