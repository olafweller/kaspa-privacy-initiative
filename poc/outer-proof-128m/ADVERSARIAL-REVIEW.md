# Adversarial second pass

This is an AI implementation review, not an independent audit or production
security claim. The proof harness reuses existing SDK cryptography.

- Value/authorization: unchanged wallet relation and guest; no note/reserve/payout
  code added. Exact public journal comparison includes all intermediate balances.
- Replay: all existing full replay and invalid/malformed-then-valid fixtures now
  run under the owner-approved 128M limit; an unexpected error cannot pass.
- Host validity authority: no new host verdict or recursive assumption is given
  to the guest. The proof binds the same fixed image doing real verification.
  Qualification guards prevent accidental premature proving; the actual receipt
  verification remains the cryptographic correctness boundary.
- Wrong identity/state: expected image is a pre-existing constant, not read from
  the receipt. Expectations precede proof production, input hashes are checked,
  and the exact root/initial state/IDs/outcomes/final state must match.
- Conditional/fake receipt: succinct type required; SDK verification explicitly
  disables development mode and requires the empty assumptions claim. An actual
  receipt must reject a wrong image and changed journal through seal verification.
- Resource denial/failure: whole-job wall, per-process address space, sampled
  aggregate RSS and inherited CPU affinity are enforced. Failures retain stage
  evidence and cannot become negative-control successes or automatic retries.
- Privacy/reorg/dependency: no secret witness enters the new harness. Static
  fixture source, one-party setup, upstream pins and prior note/recovery/reorg
  limitations remain. No live node, funded reserve or native settlement is used.
