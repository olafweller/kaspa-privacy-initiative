# Accelerated BN254 result — 2026-10-17

**The selected backend builds and runs in the pinned VM, and a complete genuine
valid-invalid-valid classifier execution now finishes. It uses 117,473,222 user
cycles, exceeding the predeclared 32M practical target. No outer proof was
attempted or produced.** The complete execution was the separately labelled
128M/900-second calibration; it did not redefine the original target.

## What was retained

PR37's exact wallet circuit/VK, two actual 128-byte wallet proofs, 702-byte
operation format, all operation/ordering fixtures and expected results are
reused byte-for-byte. No new setup or wallet proving job ran. Independent
read-back compares these files to PR37's already published artifact archive.
The original PR37 comparison and its 32M failure remain unchanged.

New classifier program image:
`397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.
It was recorded from the compiled program **before** the full runs, separately
from any result/receipt. SDK and r0vm remain 3.0.3; native and vProgs pins remain.

## Compatibility and acceleration

The official substrate-bn candidate `22108fe8c6ea1ebc1358fc4fd6854a6bf46e3509`
builds unchanged with its locked bigint2 1.4.14 dependency and executes in the
existing r0vm. A first direct-Cargo attempt omitted risc0-build's normal bigint2
feature advertisement; after supplying the same build signal the smoke build
and actual guest execution succeed. This is a build configuration correction,
not an upgrade or replacement of the VM/backend.

The genuine pairing smoke execution uses **16,909,128 cycles**. Its dynamic pprof
contains sampled stacks in `sys_bigint2_3`, `sys_bigint2_4`, `sys_bigint2_5` and
the bigint2 field module. This establishes actual accelerated execution rather
than inferring it from Cargo dependencies. Counts are executor diagnostics, not
proven gas or a production stability/security guarantee.

## Full execution and stages

| Measurement | Result |
| --- | ---: |
| Practical run limit | 32,000,000 cycles / 600 seconds |
| Practical outcome | Session limit exceeded; first valid classification incomplete |
| Separate calibration limit | 128,000,000 cycles / 900 seconds |
| Complete calibration | **117,473,222 cycles**, 121 segments |
| Calibration executor wall time | **2.85 seconds** (not proof generation) |
| Outcomes | **[0, 3, 0]** |
| Proxy balances | **[600,000,000, 600,000,000, 500,000,000]** integer sompi |
| Outer proof / separate receipt verification | **Not attempted / no receipt** |

The middle operation corrupts the C proof's C point while preserving canonical
curve/subgroup encoding; it must fail the actual equation. Genuine C then
succeeds, so this execution demonstrates continuation after a cryptographically
false proof, rather than only after malformed input.

Diagnostic stage counts for the first proof are 1,961,382 after fixed-key loading,
11,506,816 after checked decoding, 16,090,400 after conversion/public-input
preparation, and 40,494,407 after the pairing. Subsequent proofs have similar
costs: approximately **9.55M decode**, **4.5M preparation**, **24.4M pairing**.
These are observed stage differences, not independently proven cost accounting.
The first complete classification alone exceeds the 32M whole-sequence target.

This gives the accelerated implementation's full cost. PR37's ordinary Arkworks
full cost remains unknown; 32M was its stop limit. No total speedup against that
uncompleted measurement is claimed. The old RISC Zero-wallet-receipt classifier
from PR36 is a different implementation and must not be conflated with it.

## Controls and scope

- Native differential checks verify both original real proofs and compare 28
  public-intent mutations with Arkworks. Field/scalar and G1/G2 coordinate tests
  cover generator, zero, one, u64 maximum and a scalar near the field modulus.
- All five authentication controls abort for the specific expected assertion;
  timeouts/resource/IPC errors cannot count as those outcomes.
- Eight malformed-only guest controls, including an on-curve wrong-subgroup G2
  point, yield outcome 2 and leave the initial balance unchanged under 32M.
- Full ordered commitment, every original native ID, outcomes and state of the
  completed calibration are checked against the old expected fixture by a
  separate software invocation. This is execution-artifact consistency, **not
  receipt verification, a proof of execution or an independent human audit**.
- The pre-execution program identity guard rejects a changed expected identity.
  This is not a substitute for future receipt verification against that identity.

No additional full replay-after-valid or full malformed-then-valid guest run is
qualified at the practical cap: the first valid classification itself is above
that cap. The existing replay/reference checks are retained; the single allowed
larger calibration is not silently expanded into a larger-budget test campaign.
No privacy-note membership/nullifier/encryption, native settlement, testnet
broadcast, funds, signing key or confidential wallet witness is involved.

## Recommendation

Keep this concrete accelerated backend as a compatible research candidate.
The measured 117.47M full execution makes a separately declared **128M-cycle
practical-budget experiment** a concrete next decision, with all full-sequence
adversarial controls and the same one-hour outer-proving cap. Do not report that
future budget as the original 32M success or as an already produced proof.

If 32M remains a firm practical requirement, this implementation fails it; its
cost breakdown shows why accelerating only the final pairing is insufficient.
Do not weaken checked proof decoding or invent curve/subgroup routines to fit.
The full private-note circuit and native settlement remain gated on completing
and separately verifying a real full classification receipt under declared limits.
