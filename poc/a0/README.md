# A0 real-proof fixture and A0.5 TN10 adapter

The no-argument executable creates an ephemeral Groth16 BN254 claim and runs the
unmodified pinned Kaspa full validator. Its recipient/claim/setup material is
discarded: **never fund the fixture script**. The separate A0.5 file adapter and
native-RPC orchestrator retain independent test material for a reviewed TN10 run.

From the repository root:

```bash
./scripts/run_poc_a0.sh
./scripts/run_poc_a0.sh test
```

The baseline is one valid fixture, 28 rejected variants and an expected exact
replay accepted against the supplied stateless UTXO. Four original circuit tests
plus three adapter parsing tests pass. See [the report](../../docs/poc-a0.md) for
measurements and the actual live evidence boundary; tests do not prove security.

The [live A0.5 result](../../docs/poc-a0.md#a05-live-tn10-result) records accepted
reserve release, exact payout, replay rejection and two-endpoint/later observations.
It establishes no anonymity, general shielded accounting, independent recovery
or production security.

Follow the [A0.5 runbook](../../docs/poc-a0-tn10-runbook.md) for pinned SDK/node
setup, isolated wallets, reviewed funding, confirmation and replay. File-only
Rust `live` subcommands never access RPC or broadcast. No KasPact checkout is
needed; only an authorized test-KAS source is needed for funding. Do not start A1.

```bash
node --test scripts/a0_tn10.test.mjs scripts/a0_tn10_preflight.test.mjs
python3 scripts/benchmark_poc_a0.py --samples 5
python3 scripts/check_docs.py
```

Install the pinned SDK before the SDK tests. The benchmark uses fresh setup/proof
and verifies all 30 expected outcomes per sample. GNU time maximum RSS covers
the whole harness. The read-only REST preflight remains available through
`node scripts/a0_tn10_preflight.mjs`; exit 2 denotes its recorded compatibility
blocker. It never authorizes funding, even if a later advertised schema passes.
