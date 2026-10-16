# vProgs wallet provenance and compatibility

Source: `kaspanet/vprogs`, commit
`f9b84a863a7c7c20586a9cf947550475e894f72e`, `l1/wallet/src/`.
The upstream ISC license is retained in [LICENSE](LICENSE).

This is an adapted copy, not an unchanged upstream build. The standalone
[manifest](Cargo.toml) replaces workspace inheritance with explicit dependencies;
the integration lockfile pins all Kaspa dependencies to
`01b532e8b553523216471682649693af92f0fd16` (node release 2.1.0).

The [compatibility patch](compatibility.patch) changes only access to the
post-Toccata block mass limits: `params.block_mass_limits().raw_post()` becomes
`params.block_mass_limits`. The inspected Kaspa revision exposes the latter field.
Activity building, funding search, fee pricing, signing, genesis covenant-ID
calculation and settlement witness preservation remain upstream code. The first
unadapted build failed at these five production call sites. Tests contain the
same API access and receive the same mechanical change.

The KPI bootstrap adapter adds a change output and recalculates/signs the final
transaction. Upstream's single-output bootstrap function spends its entire input;
using it directly with a large fee-wallet UTXO would donate the remainder as a fee.
The provisional bound output and genesis covenant-ID derivation remain upstream.

The integration wrapper checks TN10, funding ownership, maturity, integer-sompi
conservation, fee bounds and actual covenant identity/state. These host checks do
not replace the node's signature, UTXO, script, mass or proof validation.
