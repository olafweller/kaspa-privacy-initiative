# Adversarial second pass

This is an AI implementation review and finite test record, not an independent
audit or a statement that the cryptography is production safe.

- Inflation/unauthorized value effects: same wallet circuit, exact public-input
  packing and bound pay/fee fields; no new value equation or payout path.
  Native differential mutation checks and full calibration journal equality pass.
- Double spend: replay logic and its native reference remain unchanged. Full
  replay-after-valid guest qualification is blocked by the 32M cap; do not claim
  that missing larger execution test passed.
- Invalid proofs/hidden host authority: guest performs real substrate-bn pairing
  verification. Arkworks still checks canonical encoding, curve and subgroup of
  every submitted proof before private coordinate conversion. No host verdict
  is accepted. Static unchecked loading applies only to program-pinned parameters.
- Native IDs and ordering: same full-operation native hashes; withholding,
  substitution, omission, reordering and trailing verdict require specific
  authentication failures. No L1 ordering-source integration is added.
- Wrong identity/stale state: new program ID pinned before runs, compared to the
  compiled program. No receipt exists to verify. Existing state/root/recovery
  limits remain; a host identity guard alone does not prove execution.
- Privacy: no additional private witness enters the classifier. Public synthetic
  fixtures do not establish private notes, recipient encryption or scanning.
- Dependency/setup failure: exact upstream commit and dependency locks retained.
  Single-party setup trust persists. SDK/r0vm compatibility and sampled precompile
  execution are demonstrated, not inferred; they do not establish production
  stability or constant-time behavior.
- Safety/liveness/evidence: practical and calibration cycle/wall limits were
  committed before new execution. Practical budget failure is retained; full
  calibration success is labelled separately. It cannot trigger an outer proof.
  No funds or native reserve are touched. No protocol invariant is weakened.
