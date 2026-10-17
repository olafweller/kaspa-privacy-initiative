# Reference resolve covenant provenance

Source: kaspanet/vprogs at `f9b84a863a7c7c20586a9cf947550475e894f72e`,
`zk/backend/risc0/covenant`. ISC license retained. Complete source files remain;
[compatibility.patch](compatibility.patch) records all Rust-source differences,
and [source-sha256.json](source-sha256.json) records original/adapted hashes.

Only four production and two test uses of removed `EngineFlags.covenants_enabled`
become `EngineFlags::default()`. Compatible Kaspa 2.1.0 has no such flag; its
covenant context/accessor supply validation. Script constants, proof checks,
journal, continuation, deposit binding and permission rules are unchanged.
The original fixed `resolve.zkr` identity is retained, unlike the separate PR31
monolithic lift adaptation. Existing funded instances are untouched.

The standalone manifest uses explicit dependencies, omits unused l1-types/ABI
host dependencies, and pins the tested RISC Zero/build dependencies. Only the
production succinct path is exercised. Retained development helpers are never
called. This is an isolated source adaptation, not an upstream test-suite run.
