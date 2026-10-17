# Bounded accelerated BN254 qualification

Declared before new backend execution, 2026-10-17. Follow-up to merged PR37
(`a1d1b08dda867d9c0c8c47c16bddeece1d85dc76`). Local and unfunded only.

## Fixed inputs and candidate

Reuse PR37's wallet circuit, circuit VK, 128-byte proofs, 702-byte operations,
native-ID/order fixtures and independently expected journals. No new setup or
wallet proof generation. Arkworks 0.5 remains the verification reference.

Qualify only `risc0/paritytech-bn`, tag `v0.6.0-risczero.0`, resolved commit
`22108fe8c6ea1ebc1358fc4fd6854a6bf46e3509` (`substrate-bn` 0.6.0), against
the existing RISC Zero SDK 3.0.3, custom guest toolchain and pinned v1-compatible
r0vm. The upstream patch uses target-specific bigint2 1.4 with `unstable`;
compatibility must be demonstrated by actual build and execution, not inferred.

## Limits and progression

- Build and smoke qualification: 1,800 seconds per build; actual smoke guest
  execution at most 32,000,000 cycles and 600 seconds.
- Practical full classifier target: 32,000,000 cycles and 600 seconds for the
  complete valid-invalid-valid sequence. Each adversarial case has the same cap.
- If needed, one separately labelled execution-only full-sequence calibration:
  **128,000,000 cycles and 900 seconds**. This does not revise PR37's original
  32M result or qualify an outer proof above the practical cap.
- Only after the full practical profile and adversarial controls pass: one real
  outer proof, **3,600 seconds** for the entire process group. Verify in a separate
  process with development mode disabled and no unresolved assumptions.
- A timeout, cycle/resource/IPC failure is never an authenticated rejection.
- If the pinned candidate cannot build/execute or requires custom curve,
  pairing or subgroup arithmetic, retain the concrete failure and stop that
  branch. Do not upgrade the VM, alter the circuit, weaken point validation or
  substitute an easier proof to claim success.

## Acceptance and identity

Retain canonical compressed proof decoding, curve/subgroup checks, full-intent
public-input binding, native operation IDs, authenticated ordering, replay and
balance behavior. A thin adapter using established library operations is allowed.
Measure decoding, conversion/public-input preparation and pairing separately.
Record actual precompile use, not merely dependency inclusion.

The changed classifier necessarily has a new program/image identity. Record it
before proof production and compare receipt verification to that independently
expected identity, as well as the expected root, operation IDs, outcomes and
final state. A receipt-derived identity is not an expected identity.

No private-note circuit, signing key, funds, native settlement or new TN10
transaction is included. Preserve the PR37 comparison and its published archive.
