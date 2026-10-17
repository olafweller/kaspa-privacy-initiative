# ADR-0006: Local shielded-payment design and proof compatibility work package

Status: Accepted for a bounded local design experiment, 2026-10-17. A production
note construction, proof system and funded TN10 privacy trial are not selected.
The owner authorized the specification/model/attack tests and a small real local
composition experiment following PR33 feasibility and PR34 migration requirements.

## Decision

Use the demonstrated Based App path as the first candidate backend. Compare at
most (1) local RISC Zero wallet proofs recursively verified through the existing
RISC Zero transaction/batch/aggregate path and (2) a specialized BN254/Groth16
wallet proof verified inside the outer RISC Zero program. Measure route 1 now;
route 2 remains a cost/setup/licensing comparison, not an implemented circuit.

Use established note, hidden membership, nullifier, encrypted-delivery and
accounting patterns as design requirements. A Python oracle model may model the
cryptographic statement; it must not be represented as a deployed verifier or
privacy protocol. Recipient scanning uses an established sealed-box library
only to exercise role/data separation, not to select the final encryption format.

For the small compatibility experiment use a representative preimage/value
relation, bind its public journal to an actual retained native transaction ID,
and compose through the existing reference batch/aggregate interface. Explicitly
record that this is not a full note circuit, private transfer, client benchmark
or current chain observation. No new cryptographic primitive is introduced.

Test missing/wrong inner evidence and a host-requested skip. If the recursive
route can only halt for invalid evidence, report the invalid-operation no-op
handling as an open blocker; never accept an unproved host verdict. Separately
model deterministic rejection and current nullifier conflicts atomically.

## Boundaries

No funding, keys from earlier experiments, new TN10 broadcast or mainnet action.
No forced migration, new token, reserve-admin key or relaxed invariant. Reject
other statement versions initially; the economic spentness domain must not fork
across later accepted versions. Every funded deposit requires an authenticated
credit or owner recovery path. Native payout, rent and fees remain separate.

The output is a [proposed private-payment specification](../rfc/0002-shielded-payment.md),
executable model, measured compatibility results and one conditional TN10 proposal
for review. Substantial shielded implementation and new funded trials follow
that review, not this local experiment. This records the authorized work scope;
it does not impose additional approval steps on already-authorized local work.
