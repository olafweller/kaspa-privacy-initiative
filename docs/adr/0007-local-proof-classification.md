# ADR-0007: bounded local proof-byte classification experiment

Status: Accepted for this local, unfunded experiment only, 2026-10-17.

## Problem and decision

PR35 established positive recursion but not a proven invalid-operation no-op.
Test the existing RISC Zero 3.0.3 succinct receipt verifier as ordinary guest
computation, without `env::verify`, host verdicts or optional assumptions. Its
actual result decides whether the small proxy operation changes state. Pin the
wallet image and verifier context; accept only a bounded canonical succinct
receipt format, with development mode disabled. Retain a canonical proof-excluding
intent, full submitted proof bytes, recipient-delivery fields and native v1 IDs.

The local sequence commitment is a public, verifier-checked fixture. It is NOT
a new authenticated TN10 acceptance endpoint. Substituting or omitting bytes
must fail against that fixed commitment, rather than become a rejected payment.
Unavailable fixture data halts. Malformed submitted proof data is classified.

## Research and alternatives

Reuse the PR35 mature-protocol and Kaspa source review. RISC Zero's ordinary
`Receipt::verify_with_context` verifies a seal and successful expected claim;
the recursive syscall only adds an assumption. Review the pinned verifier's
parser, field, cycle-exponent and control-path bounds before execution.
Current upstream heads are refreshed in the result evidence. Do not copy
restricted circuit sources. No note construction, privacy circuit or migration
scheme is selected here. Specialized BN254/Groth16 remains one comparison if
this route is impractical; no performance advantage is presumed.

## Acceptance and stop criteria

Attempt valid-invalid-valid with actual wallet proofs and actual ordinary
verification in the guest. Both valid operations must affect the proxy state;
the bad operation must have an explicit outcome and no economic effect. Prove
the resulting journal if practical, and test withheld/substituted evidence,
host verdicts, malformed encodings, domain binding and replay. Measure actual
execution/proof cost, memory and complete proxy operation/native masses.

If deterministic classification, bounded execution or practical proof production
cannot be achieved, retain the reproduction and state the concrete blocker.
Do not exclude bad operations, relabel an execution profile as a proof, weaken
invariants or fund TN10. Full private economics, real accepted-lane integration,
native payout, data availability and independent recovery remain later gates.
