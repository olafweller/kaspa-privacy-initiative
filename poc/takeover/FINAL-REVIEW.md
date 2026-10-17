# Final review of PR33

Date: 2026-10-17. Reviewed live source checkpoint: `38b8537`. Read-only review
utilities: `96be082`. This is an AI-assisted second-pass review of this isolated
public-account experiment, not an independent audit or approval by an external
reviewer. No human review submissions or unresolved inline threads existed when
review began. Original-head GitHub code and documentation checks passed.

**Disposition: no blocking finding for the documented TN10 public-account scope.**
All five [Based App acceptance criteria](../../docs/based-app-feasibility-2026-10-17.md)
have matching evidence. No invariant is weakened, no further funding or broadcast
is needed to close those criteria, and no production/privacy/recovery claim is
inferred. The new review tools do not alter the guest, covenant or existing
proof artifacts; original executed source hashes remain historical provenance.

## Inspected enforcement

| Question | Source and review result |
| --- | --- |
| Can a host invent a deposit or redirect credit? | `common::execute` checks native v1 preimages and emits exact IDs/context; reused native `apply_transaction` authenticates deposit outputs and owner resources. Reference batch verification authenticates the whole previous public state through one SMT leaf. Native endpoint commitment binds accepted activity. Repeated credit, malformed/foreign outputs and overflow are rejected/no-ops in tests. |
| Can execution silently drop failed commands? | The native relation returns an error journal with unchanged state; the reference batch still adds its ID to lane activity. PR32's four-command history includes unauthorized and copied commands. Reconstructed accepted order is distinct from broadcast order. |
| Can recursive assumptions or continuity be substituted? | The batch verifies transaction-image journals, strictly increasing merge indices, block context and resource hashes. The aggregator checks state/tip/score/lane/covenant/image continuity. Real receipts resolve assumptions; missing/wrong-image execution controls are retained. All eight live receipts reverify with the pinned SDK; changed journals/wrong images fail. |
| Can omission settle at the same endpoint? | The native covenant reads the actual selected-chain commitment. Both live experiments reject the partial-computation receipt at the unchanged endpoint. Final review checks the same old covenant input, endpoint, different derived commitment and actual native ZK-integrity rejection. Local derived-anchor acceptance alone is not sufficient evidence. |
| Can an operator use a stale state or replace a verifier? | Bootstrap pins program/inner images, lane and state. The builder checks the actual prior covenant UTXO script before submission. The native script binds continuation and actual covenant identity. No upgrade, init/config action or reserve-admin key is enabled. Local negative tests cover wrong state/lane/image/continuity. |
| Can a debit be reported as a paid exit? | Exact permission recipient/principal and separate rent are committed; native payout consumes the real deposit reserve and permission. Final accounting checks actual recipient/reserve UTXOs and zero remaining claim. Balanced underpayment/reserve/recipient controls fail scripts; replay fails spent-input validation. |
| Can fees or rent mask insolvency? | Python recomputes actual transaction IDs, input/output fees, complete account state hashes, SMT roots and native backing. All nine fresh fees and all ending asset domains reconcile; unpaid permission rent is a distinct backed entitlement. Treasury and state rent are excluded from principal backing. |
| What if infrastructure fails or reorgs? | Missing proof/data and detected reorg halt execution. Write-once intents and fresh-identity retries prevent blind rebroadcast. The normal node is unchanged. No general reorg, expiry, pruning or independent recovery claim is made. |
| What information is private? | None of the financial app state in this experiment. Public account data, payloads and recipients remain observable. Actual signing keys remain outside archived public trial files. |

## Additional review validation

The [review JSON](evidence/final-review.json) retains the exact tool source and
binary hashes, archive identities, re-verification reports and audit results.
Python rehashes 127 outer members and 89 nested public VPS members, reconstructs
both live intervals from raw captures, verifies merge positions/contexts and
complete state roots, and recalculates all fees/backing. It also repeats the
older PR32 audit over 120 original files and PR31's three-input reconstruction.

The SDK tool verifies eight existing succinct receipts and their saved journals;
each also rejects a changed journal and a wrong program, giving sixteen explicit
negative SDK checks. It invokes no executor/prover, signing key or RPC. The
seven existing Rust adapter tests pass again. Fast CI checks cover the new tool's
syntax/build/formatting; receipt and public-archive replay remain explicit manual
checks rather than implicit CI claims.

The review audit needed the documented `blake3==1.0.8` Python dependency and the
native run-length parent-header encoding, with exclusive end levels, to compare
RPC representations. These review-tool development issues did not change the
historical captures or cause a repeated trial. They are distinct from the
retained earlier final accounting response-shape correction.

## Reproduce without funding or proving

After the Rust build prerequisites and official SDK setup in [CI](../../docs/CI.md):

```bash
python3 -m pip install --target .local/feasibility/python blake3==1.0.8
PYTHONPATH=.local/feasibility/python python3 poc/takeover/audit.py poc/takeover/evidence
PYTHONPATH=.local/feasibility/python python3 poc/native-value/audit.py poc/native-value/evidence
cargo +1.91.0 build --locked --release --manifest-path poc/takeover/Cargo.toml --bin kpi-takeover-verify
```

For SDK checks, extract the hash-checked public artifact archive to a **new**
directory, retaining its `programs` and the three `*-proof` directories. Never
execute programs or remote runners from an evidence archive. For each directory:

```bash
.local/ci-target/release/kpi-takeover-verify NEW_DIRECTORY/programs NEW_DIRECTORY/prefix-proof
.local/ci-target/release/kpi-takeover-verify NEW_DIRECTORY/programs NEW_DIRECTORY/omission-proof
.local/ci-target/release/kpi-takeover-verify NEW_DIRECTORY/programs NEW_DIRECTORY/final-proof
```

Use the actual Cargo target path when different from this Cloud setup. The
SDK checker verifies what is present; the review report records the expected
three/two/three receipt counts. The omitted-input receipt is a valid proof of a
partial computation, so SDK acceptance is expected. Its rejection at the fixed
real endpoint is a separate recorded native result.

## Boundaries retained

This is not a new current-chain observation, upstream runtime audit or
independent human review. Same-owner/node public replay remains narrower than
I-10/I-11 for a future private protocol. The five-criterion feasibility outcome
does not close the N-user shutdown gate, fee-liveness issue #23, privacy issues
or RFC-0001. Neither the existence of a proof nor a passed test justifies calling
this unreviewed research code secure.
