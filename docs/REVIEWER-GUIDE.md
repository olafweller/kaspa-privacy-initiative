# Review one small part of KPI

KPI asks whether current Kaspa primitives can support optional privacy for native
KAS, with correct backing and exits that survive loss of the usual services.
We are testing assumptions, not launching a privacy pool.

## What exists

- **A0/A0.5:** a real Groth16 proof spent a funded TN10 test reserve and a native
  test-KAS payout was observed. The own node lacked complete UTXO sync; public
  native RPC endpoints supplied live UTXO/acceptance observations. See the
  [report](poc-a0.md) and merged commit
  [`3a1efa8`](https://github.com/olafweller/kaspa-privacy-initiative/commit/3a1efa8db9672025f5282970703cb7256428c1be).
- **A1:** [draft PR #22](https://github.com/olafweller/kaspa-privacy-initiative/pull/22)
  tests S0→S1 plus a partial payout, S0 direct exit, and S1 terminal exit for one
  fixed recipient. Local/native-synthetic G1–G4 evidence exists. Its negative-test
  and fee-receipt qualification defects have a repair under review; use the
  PR's current report for receipts and exact gate status.
- **Not established:** independent G5 machine/archive recovery, live A1 G6,
  private transfers, notes/nullifiers, anonymity, scalable throughput, an audit
  or production safety. Same-host container recovery does not close G5.

Candidate A is the current experimental baseline because it is the smallest
falsifiable use of current L1 primitives. [RFC-0001](rfc/0001-state-architecture.md)
remains open. A0/A1 are evidence, not production architecture acceptance; future
notes/nullifiers/private transfers may require major redesign or another design.
BN254/Groth16 is an experiment-compatible choice, not a final proof system or PQ
security. Per-instance fixed-context setups do not scale into a private pool;
single-party setup provenance remains trusted.

Major blockers: independent artifact/history recovery, fixed-fee exit liveness
([#23](https://github.com/olafweller/kaspa-privacy-initiative/issues/23)), scalable
state/setup design, incomplete [P02 research](../research/existing-kaspa-privacy.md)
and independent human security review. AI-assisted adversarial review has happened;
it is not independent human review.

## Choose one task

### 1. Can a proof authorize a different payout or successor?

Start with A1 `poc/a1/src/script.rs` (about 170 lines) and
`ClaimCircuit::generate_constraints` in `poc/a1/src/circuit.rs` (about 100 lines).
Follow only S0 continuation and S1 terminal first. Compare witness order, raw
selector checks, fixed VK selection and actual output binding with
[ADR-0003](adr/0003-a1-successor-reserve.md). A0 comparison:
`poc/a0/src/main.rs`, proof statement and redeem-script construction in the
merged A0 commit above. No need to review the entire historical evidence tree.

Use A1 repair source commit **9125dc04d4fac49c900e9e56351f27d1b0fac454** in PR #22. On a clean checkout:

```bash
git fetch origin pull/22/head
git switch --detach 9125dc04d4fac49c900e9e56351f27d1b0fac454
# Rust 1.91.0 and native build prerequisites: see docs/CI.md on maintenance PR.
# Place the official upstream checkout in this sibling directory:
git clone --depth 1 --branch v2.1.0 https://github.com/kaspanet/rusty-kaspa.git ../upstream/rusty-kaspa
bash scripts/run_poc_a1.sh build
poc/a1/target/release/kpi-poc-a1 validate-body poc/a1/evidence/fixture-2026-10-03/s0_continue.validate.json
poc/a1/target/release/kpi-poc-a1 validate-body poc/a1/evidence/fixture-2026-10-03/s1_terminal.validate.json
```

The runner requires upstream `01b532e8b553523216471682649693af92f0fd16`.
The commands validate supplied public fixtures; they never fund or submit.
A useful finding supplies a mutated transaction, the intended rejecting layer
and the actual result. An ID/parser rejection alone does not test the covenant.
Never fund these fixtures: their recipient key is deliberately public.

### 2. Can inconsistent fee or mutation evidence qualify?

Review `scripts/a1_extra_negatives.py`, `scripts/a1_fee_check.py` and their
`test_a1_extra_negatives.py` / `test_a1_fee_check.py` regressions at the same
repair commit. Scope: final ID/mass preparation and receipt binding, not a
fee-sponsorship design. Small offline entry tests from that checkout:

```bash
python3 -m unittest discover -s scripts -p 'test_a1_extra_negatives.py'
python3 -m unittest discover -s scripts -p 'test_a1_fee_check.py'
```

A valuable finding makes a test pass for the wrong reason or mixes a manifest,
body, branch, fee, budget, ID, full hash or mass from different fixtures while
still qualifying. Distinguish historical quote replay from current fee approval.

### 3. What exact data can recovery lose?

Review `scripts/a1_recovery.py` (about 310 lines) and ADR-0003's recovery inventory.
Trace one old S0 locator through a continuation and a conflicting DAG reorg.
Start with `python3 -m unittest discover -s scripts -p 'test_a1_recovery.py'`.
This is a source/fixture review, not independent G5 execution. A valuable finding
identifies a missing public artifact, incorrect acceptance/cursor assumption,
or paid entitlement that survives rollback. A current UTXO at the same address
is insufficient lineage evidence; PK hashes cannot recreate lost PK bytes.

## Report a finding

Comment on PR #22 or a linked issue with the exact commit, file, assumption,
small reproduction, expected/actual result and consequence. State what you did
not test. Use [SECURITY.md](../SECURITY.md) for sensitive findings involving
potential deployed funds. No human audit is implied by submitting a review.

[CI scope](CI.md) explains fast/unit/native checks and the manual evidence boundary.
Review does not authorize A2, G5 execution, G6, funding, broadcasting or merging.
