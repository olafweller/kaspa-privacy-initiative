# A1 source limits and read-only fee observations

Verified on 2026-10-03. Local upstream was clean; official `git ls-remote`
reported both HEAD and tag `v2.1.0` as
`01b532e8b553523216471682649693af92f0fd16`. All links below pin that revision.
These are source facts and external observations, not A1 G2/G4 measurements.
Measured final decoded transactions and native engine traces must be checked
separately; no source estimate establishes acceptance or cryptographic safety.

| Limit / rule | Pinned primary source |
| --- | --- |
| Known SPK version 0; combined main+alternate stacks 244; VM script, individual element and counted-op limits each 1,000,000 | [txscript constants, lines 76–80](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/lib.rs#L76-L80) |
| Combined stack limit is enforced after each opcode | [engine, lines 633–637](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/lib.rs#L633-L637) |
| Signature script ≤250,000 bytes/input | [constant, line 25](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/params.rs#L25), [TN10, line 675](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/params.rs#L675) |
| Output script ≤10,000 bytes; TN10 compute/storage/transient block masses 500,000/500,000/1,000,000 | [TN10 parameters, lines 660–683](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/config/params.rs#L660-L683) |
| 100 script units/gram; 100 grams/compute-budget unit; therefore 10,000 script units/budget unit | [unit constants, lines 4–7](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/units.rs#L4-L7) |
| v1 compute budget is u16; minimum covering budget accounts for 9,999 free script units/input | [free allowance, lines 14–23](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/units.rs#L14-L23), [budget, lines 64–84](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/units.rs#L64-L84) |
| Groth16 tag is raw20; base verifier cost 140,000 grams | [tag/cost, lines 9–34](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/tags.rs#L9-L34) |
| gamma-ABC count must equal public-input count+1; each element adds 250,000 script units =2,500 grams | [VK parsing/metering, lines 18–59](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/zk_precompiles/groth16/mod.rs#L18-L59) |
| OP_ZKPRECOMPILE a6 charges tag, verifies, and only then pushes true | [opcode, lines 759–770](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/opcodes/mod.rs#L759-L770) |
| v1 compute mass includes committed budget×100, serialized-size mass and output-SPK mass; transient mass is serialized size×4 | [native mass calculation, lines 335–369](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/mod.rs#L335-L369), [factor 4, line 31](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/constants.rs#L31) |
| Default minimum relay fee 100,000 sompi/kg =100 sompi/gram | [mempool default, lines 17–20](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/config.rs#L17-L20) |
| Relay fee uses max(compute, normalized transient), excluding storage from this floor; integer floor division, zero-result fallback, MAX_SOMPI cap | [relay checks, lines 67–104](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/mining/src/mempool/check_transaction_standard.rs#L67-L104) |

Five public inputs require **six** gamma-ABC points. The verifier component is
therefore `140000 + 6×2500 = 155000` grams, before surrounding script work.
Compressed BN254 sizes are G1=32 and G2=64 bytes: VK is
`32 + 3×64 + 8 + 6×32 = 424` bytes; two PUSHDATA2 VK literals are
`2×(3+424) = 854` bytes; proof A/B/C is `32+64+32 = 128` bytes.
Artifact parsing and actual measurements must confirm the emitted sizes.

Native counted operations and active execution are different statistics.
[The engine increments non-push counted operations before its conditional
execution test](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/crypto/txscript/src/lib.rs#L582-L597),
so a skipped S0 arm still contributes non-push instructions to the per-script
1,000,000-op limit. `executed_non_push_ops` in A1 metering counts the active arm.
Native opcode logging also prints skipped instructions; its conditional filter
and original log must be reviewed together. Engine script units are hundredths
of a gram, not grams. S0 contains two VKs but must execute one verifier.

For TN10, transient normalization cofactor is `500000/1000000 = 1/2`;
[cofactors derive from the configured block limits](https://github.com/kaspanet/rusty-kaspa/blob/01b532e8b553523216471682649693af92f0fd16/consensus/core/src/mass/mod.rs#L234-L258).
Thus the native default relay fee mass is
`max(compute_mass, ceil(transient_mass/2))`. Storage still must satisfy its
consensus resource limit. A source default is not attestation of a remote node's
configuration; node operator policy may differ.

## Historical read-only observations

The pinned SDK's only quote calls were `getInfo`, `getBlockDagInfo` and
`getFeeEstimate` against these external wRPC endpoints. No local syncing node,
wallet, resolver, submission or funding command was accessed.

| UTC observation | External source | Reported network / software / state | Quoted priority / normal / low rate |
| --- | --- | --- | --- |
| 2026-10-03T21:05:46.783Z | `wss://electron-10.kaspa.blue/kaspa/testnet-10/wrpc/borsh` | testnet-10 / 2.1.0 / synced, indexed; DAA 587288102 | All 100 sompi/gram |
| 2026-10-03T21:05:47.598Z | `wss://vector-10.kaspa.green/kaspa/testnet-10/wrpc/borsh` | testnet-10 / 2.1.0 / synced, indexed; DAA 587288108 | All 100 sompi/gram |

The nodes reported distinct p2p IDs and the same pruning point
`decd97c04aad0ef66f947fdc59446c999b57f3b7452889d9b8727c51421ba460`.
REST `/info/network`, `/info/kaspad` and `/info/fee-estimate` on
`https://api-tn10.kaspa.org` separately corroborated TN10, 2.1.0, synced/indexed
and rate 100, observed by 2026-10-03T21:04:59Z.

At 2026-10-03T21:07:19.200Z and 21:07:19.426Z respectively, separate read-only
genesis-header requests to those two wRPC nodes returned `cannot find header`
for `f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370`.
Those requests are **not** part of the reusable fee-quote script. Network tags
were corroborated; historical genesis retention was not. Indexed/synced status
does not qualify accepted-body archive availability or live G5 recovery.

These quotes are estimates, not inclusion guarantees. G0's 25% quoted-rate
headroom gives 125 sompi/gram for these observations: fixed fee 30,000,000 sompi
covers fee mass ≤240,000. Fee credit 70,000,000 exceeds
`ceil(1.1×max(30000000,30000000+30000000)) = 66000000`.
Final branch masses must be measured independently, and quotes must be refreshed
before any subsequently authorized funding. Rebuild an unfunded instance if
fixed fees cease to qualify; post-funding insufficiency is liveness failure.

## Repeating the observation

Run `node scripts/a1_fee_quote.mjs --sdk-dir /path/to/nodejs/kaspa
--sdk-archive /path/to/kaspa-wasm32-sdk-v2.1.0.zip` (one command).
It verifies the official archive SHA256
`ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124`,
plus extracted JS/WASM/package hashes, before loading SDK2.1.0.
It emits observations and pins on stdout; it does not save files. The
[retained stdout observation](fee-quote-2026-10-03.json) from the reusable
script refreshed both sources at 2026-10-03T21:13:07.407Z and
21:13:07.906Z: both still quoted 100 sompi/gram in every bucket, reported
testnet-10, SDK-compatible server 2.1.0, and synced state. Retained
stdout evidence must preserve failures and timestamps. A changed server version
requires requalification. No alternate endpoint/network argument is provided.
