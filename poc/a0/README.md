# A0 local real-proof fixture

This executable generates a real Groth16 BN254 proof and runs the actual pinned
Kaspa transaction validator. It is **not a wallet or live TN10 deployment tool**.
Its generated recipient key and claim/setup material are discarded. Never fund
the fixture script. A0 remains incomplete pending live-network evidence.

From the repository root:

```bash
./scripts/run_poc_a0.sh
./scripts/run_poc_a0.sh test
```

The first command exercises the real consensus path and 28 invalid variants,
plus an expected exact-replay acceptance with a supplied UTXO. The second runs
four circuit constraint tests. See [the report](../../docs/poc-a0.md) for build
requirements, pins, single-run benchmarks and the evidence boundary.

For the next local session, follow the [A0.5 TN10 handoff](../../docs/poc-a0-live-tn10-handoff.md).
Implement the missing persistence/RPC adapter and verify the test-only network
and recipient control before funding. Do not start A1 as part of this handoff.
