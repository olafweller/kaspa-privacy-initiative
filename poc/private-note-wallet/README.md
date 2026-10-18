# Local private-note wallet experiment

This package produces real Groth16 wallet proofs of hidden note ownership,
Merkle membership, economic nullifier derivation, u64 ranges and conservation.
It also implements recipient discovery and a local atomic state kernel that
verifies those proofs. It does **not** prove that kernel in the zkVM or implement
native deposit/payout authentication. No TN10 transaction or rental ran here.

The measured example is deposit-fixture 10 -> Alice credit -> Bob 4 + change 6 ->
Bob's own exit proof 4 -> payout-fixture 4. Amounts use integer sompi throughout.
Five real proofs include an independently valid competing spend and pending
recovery, which the current state rejects after their shared input is consumed.
See [results](RESULTS.md), [encoding/relation](SPEC.md), [source review](SOURCES.md),
[ADR-0011](../../docs/adr/0011-local-private-note-wallet.md),
[adversarial review](ADVERSARIAL-REVIEW.md) and [next integration gates](NEXT-CHAIN.md).

## Reproduce without creating new parameters

From the repository root, using Rust 1.91.0:

```sh
RAYON_NUM_THREADS=4 cargo +1.91.0 test --locked --release   --manifest-path poc/private-note-wallet/Cargo.toml -- --test-threads=1
cargo +1.91.0 run --locked --release   --manifest-path poc/private-note-wallet/Cargo.toml -- verify   poc/private-note-wallet/evidence/public   d45e8248eda25a6f6ec85b5074d0f7d217d29741c820c4d8ddfb2667675a5bf2
```

`verify` checks the archived five actual proofs in its own process against the
independently specified key identity, then exercises state and malformed-proof
controls. It writes `separate-verification.json` in the supplied directory;
use a disposable copy to preserve the committed measurement. CI uses a temporary
copy and does not generate a new setup or upload wallet secrets.

To generate a new local experiment, replace `verify ... EXPECTED_ID` with
`demo /path/to/new-directory` (the directory must not exist). This creates a new
experimental one-party Groth16 setup and random wallets. Record its new VK identity;
do not substitute it into the archived comparison. The setup toxic waste is not
ceremonially destroyed or independently validated. No production use is implied.
Public proving parameters are not retained in Git; remote wallet proving with
this setup and independent recovery/parameter availability remain untested.
Wallet secrets, note openings and Merkle witnesses are never serialized to the
public artifacts. Logical Alice/Bob roles share the local test process, although
Bob's discovery API receives only his keys and accepted public records.

## Boundaries

This tree has four leaves, one input, two output slots, whole-note exits and zero
application fees. Encrypted delivery is bound to the proof but encryption
correctness is validated by the recipient, not proved by the circuit. Address
authentication is assumed. The SHA/HMAC protocol composition is experimental;
using established primitives is not an inherited security proof or an audit.
The deposit and payout APIs explicitly accept authenticated **test fixtures**.
A native adapter, new outer identity/receipt, accepted-lane integration, actual
native payout, retained scan data and independent recovery must still be tested.
The earlier PR43 outer receipt proves its earlier test relation, not this one.
