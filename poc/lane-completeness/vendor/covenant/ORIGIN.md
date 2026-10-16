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


## Live integration extension — 2026-10-17

[Live pin patch](live19.patch) is relative to PR31 commit `902cbe9`, separate from
the original upstream compatibility patch. `monolithic-lift19` is an optional
feature selecting the exact official `lift_rv32im_v2_19.zkr` identity for the
shorter live workload. The integration enables it; the original offline host
workspace does not, preserving its lift-20 behavior. A new script/SPK/covenant
is bootstrapped for this choice. It cannot upgrade any previously funded UTXO.

The guest, proof relation, ABI, allowed-control root, image and empty-assumptions
checks are unchanged. A valid lift-19 receipt rejected under a lift-20 deployment
is retained as a failed compatibility trial. Segment shapes outside the selected
fixed circuit remain unsupported. The historical source manifest now differs
only at this crate's manifest and script source; its 25 evidence files and all
other recorded sources remain unchanged, with the original sources in `902cbe9`.
