# Specialized comparison evidence

[comparison.json](comparison.json) records wallet/setup metrics, native dimensions,
the incomplete 32-million-cycle profile, negative-control scopes and source pins.
[local-groth16-artifacts.tar.gz](local-groth16-artifacts.tar.gz) contains the actual
wallet proofs, VK/prepared/static parameters, program, fixtures, logs, journals,
source snapshots and per-member SHA-256 manifest. It contains **no outer receipt**.

The 94,702,320-byte public proving parameter file stays in the execution workspace
and is hashed in the report. It contains public group parameters, not a serialized
scalar trapdoor. It is unnecessary to verify the archived wallet proofs. To
regenerate proofs, retain that file locally or repeat a fresh setup, which creates
a new VK/intent/program identity. Synthetic witnesses in the archive are deliberate
public fixtures. No real wallet key, credential or restricted circuit source is
included.

The five authenticating guest failures and eight malformed-only guest cases are
execution evidence. They do not represent a completed three-operation classifier
or an outer proof. Initial checked-constant loading and the optimized static
parameter run both retain their limit failures. Stage cycle logs are executor
diagnostics, not proven resource accounting.
