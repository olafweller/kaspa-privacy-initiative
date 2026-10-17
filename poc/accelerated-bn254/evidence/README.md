# Retained backend qualification evidence

The [summary and manifest](comparison.json) and
[public artifact archive](local-backend-artifacts.tar.gz) retain the complete
calibration, practical-budget failures, 13 narrow guest controls, actual proofs
and operations reused from PR37, dynamic smoke pprof, native reference checks,
programs, exact sources, locks, toolchain identity and validation logs.

- Source snapshot: `4a68ff05bc4dacf1012949ed1c0c9a69b62599ac`.
- Runtime implementation source: `76215dd537f1bec68439c502ffc40fd8c45b34ef`.
- Predeclared limits: `bcc719d8b1f4f7d532a3c10bb93b6176622f7224`.
- Archive: **1,460,679 bytes**, **189** regular members.
- SHA-256: `16c6ab7ae1b9b5549f76743dfe12e2de38b2f81bd4972553a86625b3643ea3a2`.
- Classifier image: `397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.

[collect_evidence.py](../collect_evidence.py) uses an explicit public-artifact
whitelist and reads back each member's length/hash. No public proving parameters,
signing keys, credential values or confidential witnesses are included.
Both smoke and classifier programs rebuild byte-identically. Thirty-two retained
key/proof/operation/fixture files match the previously published PR37 archive.

Extract with safe regular-file/path checks. In the existing pinned SDK build
environment, [verify_execution.py](../verify_execution.py) can check
`local/programs-final`, `local/calibration-result` and `reused-pr37`, supplying the
expected classifier image above as a separate argument. It recomputes that image
through the SDK and checks the original ordered root, every native ID, outcomes
and state. [inspect_profile.py](../inspect_profile.py) can inspect
`local/smoke-profile-result/accelerated-path.pprof` for dynamically sampled bigint2
syscall stacks. The underlying classifier uses the same target-specific library
path; no Arkworks pairing fallback is present in the adapter.

These are execution-artifact and diagnostic checks, **not outer receipt
verification**. The main sequence finishes in the separate 128M calibration at
117,473,222 cycles / 121 segments, while the 32M practical cap still fails.
No full larger-budget replay campaign, outer proof, funding, private payment or
new TN10 settlement is claimed. See [results and limitations](../RESULTS.md).
