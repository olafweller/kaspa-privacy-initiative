# Source provenance and compatibility

Copied `build.rs` and the complete `src/` of `kaspanet/vprogs`
`zk/backend/risc0/covenant` at `f9b84a863a7c7c20586a9cf947550475e894f72e`.
ISC license retained. `compatibility.patch` records every Rust source change.
Four production references (and two retained test references) to the removed
`EngineFlags.covenants_enabled` field are replaced with `EngineFlags::default()`.
At Rusty Kaspa `01b532e8`, EngineFlags only carries
sigop pricing; covenant context and the seqcommit accessor enable their opcodes.
The fixed succinct control pin changes from `resolve.zkr` to the official
`lift_rv32im_v2_20.zkr` ID `34530b42028fb631c90e1226bb0e750d4b9b593840d45216f75dca449dac7734`.
The monolithic guest has no recursive assumptions; its receipt ends at the lift
step. The unadapted pin rejects its real receipt, with retained failure evidence.
The pin remains exact, and native verification still checks inclusion under
Kaspa's allowed control root, the fixed guest image, empty assumptions and the
exact journal. No proof, journal, SMT, state, output, fee or anchor check has been
removed. Other segment shapes remain unsupported; this is an experiment covenant,
not the unmodified upstream runtime covenant. Comments and the retained control-ID
cross-check are updated to name the monolithic lift circuit.

The standalone manifest specifies upstream dependencies explicitly and omits
unused `vprogs-l1-types` and the ABI `host` feature. This avoids pulling in the
runtime/scheduler/storage stack, which is unnecessary for building the covenant.
The experiment uses only the production succinct branch. Development helpers
remain in the copied upstream source for provenance but are never called.

The main workspace lockfile pins every Kaspa crate to `01b532e8` and every
remote vProgs crate to `f9b84a8`. Compile/reproduction uses `--locked` and verifies
those sources before running. Upstream tests are retained, but their separate
test dependencies are not installed by this adaptation; tested use is the host
experiment's real-proof native script suite. This is not an upstream test run.
