# Security Invariants

These invariants should hold regardless of which candidate architecture is selected.

Where possible, they should later become executable tests, property tests, fuzz targets, formal statements, or proof obligations.

## I-1: Backing

At every valid protocol state:

```text
total spendable shielded value <= native KAS controlled by the protocol for users
```

Development treasury funds must not be counted as user backing.

## I-2: Value conservation

For every valid private state transition:

```text
sum(private inputs) = sum(private outputs) + explicit allowed fees
```

No hidden inflation, rounding creation, or negative-value behavior is permitted.

## I-3: Authorization

A private note or claim may only be consumed by a party satisfying its cryptographic spend conditions.

Knowledge of public commitments alone must never authorize spending.

## I-4: Single spend

A spendable private resource may be consumed at most once.

The protocol must deterministically detect duplicate consumption without publicly revealing which commitment was consumed, except where the chosen design explicitly differs.

## I-5: Proof soundness

No invalid state transition may be accepted solely because a prover or executor asserts it is valid.

Consensus/settlement accepts only transitions satisfying the protocol's verifiable proof conditions.

## I-6: Binding to the correct state

A valid proof must be bound to the intended prior state and relevant ordered Kaspa activity.

A proof for one state, lane, sequence commitment, or transition set must not be replayable against another.

## I-7: Withdrawal safety

Native KAS may leave the shielded reserve only when a valid protocol condition proves authorization and value conservation.

No operator signature alone should be sufficient in the production design.

## I-8: No privileged confiscation

No permanent maintainer, foundation, founder, frontend, prover, or executor should be able to arbitrarily confiscate, freeze, or redirect valid user funds.

## I-9: Safety before liveness

Loss, censorship, or corruption of a prover/executor should not enable theft or inflation.

If the system cannot safely proceed, it should halt, delay, or switch infrastructure rather than accept unverifiable transitions.

## I-10: Recoverability

A valid user should not lose access merely because a specific hosted service disappears.

The final design must identify which combination of:

- Kaspa data;
- public protocol state;
- user-held keys/secrets;
- replicated witnesses;
- independent software

is sufficient to recover and spend.

## I-11: State reproducibility

Independent honest implementations starting from the same accepted public inputs should derive the same consensus-relevant state.

## I-12: Reserve isolation

User reserve KAS and protocol-development treasury assets are separate accounting and control domains.

A governance decision about funding must never create an alternate path to spend the user reserve.

## I-13: Explicit upgrade authority

If an upgrade mechanism exists, its authority and limits must be explicit.

An upgrade mechanism must not quietly become a permanent withdrawal key.

## I-14: Note recipient spendability

A sender must not be able to create a note that appears valid to a recipient but cannot actually be spent under the protocol rules, unless the wallet can deterministically detect and reject it before acceptance.

## I-15: Deterministic rejection

Malformed proofs, duplicate nullifiers, invalid state roots, invalid commitments, and unauthorized withdrawals should fail deterministically across implementations.

## I-16: Privacy claims are scoped

Documentation must distinguish cryptographic confidentiality from anonymity against timing, amount, network, and external-data correlation.

The protocol must never promise stronger privacy than it can substantiate.

## Review rule

Any architecture proposal that violates one of these invariants must either:

1. be rejected; or
2. explicitly propose a change to this document and survive independent security review before implementation.
