# Upstream encoder provenance

`src/actions.rs` is copied from
`kaspanet/vprogs/examples/tn10-runtime/src/actions.rs` at
`f9b84a863a7c7c20586a9cf947550475e894f72e`, SHA-256
`1cfb55ad3ceadb03e8f1669b211f1d92ce227edc141e5f9e6af19e113a22f253`.
The executed adapter uses rustfmt formatting only (SHA-256
`fcc56ff3729bccf9472280bc31f1c481c50a87faefab8d37746be4da4da4af53`);
see `actions-format.patch`. ISC license retained as `UPSTREAM-LICENSE`. Unused reference helpers remain.
The actual experiment uses a random VPS-only key, never the reference genesis
scalar or TestSigner. Its withdrawal builder reuses the encoder's existing
prev-tx witness format for owner-authorized native inputs.

All runtime, ABI and permission-script code is imported from the same pinned git
revision, with no modifications. The earlier wallet/covenant API and monolithic
verifier adaptations are reused from PR31; they are not unmodified upstream code.
