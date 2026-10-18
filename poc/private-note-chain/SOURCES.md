# Source/reuse review — 2026-10-18

Current upstream heads were checked again before integration; the ten monitored
Kaspa/privacy repositories match the PR44 review. Nineteen retained pinned
primary files were reread/hash-checked. See [source-refresh.json](evidence/source-refresh.json),
[integration source hashes](evidence/integration-source-review.json) and the
[previous detailed review](../private-note-wallet/SOURCES.md).

- Kaspa docs and research: retain the split between native lane acceptance,
  off-chain execution and proof-based settlement. A fixture endpoint is not an
  accepted native event. The pinned rusty-kaspa testnet genesis supplies the
  explicit domain descriptor; no network/node behavior is inferred from a label.
- vProgs pinned at f9b84a8: inspect the current deposit-policy source, native
  StateTransition layout, StandardSpk encoding and permission scripts/accumulator.
  The covenant belongs in committed configuration; actual deposit output value,
  exact delegate-entry script and unbound flag are checked from native preimages.
  Reuse canonical native v1 hashing/lane-context/seqcommit and 352-byte ABI.
  Permission finalization returns its actual P2SH script hash, not a bare tree
  root. A granted permission is not a confirmed native payout.
- Orchard/Aztec/RAILGUN: retain hidden authorization/membership separately from
  current spentness, actual constrained nullifiers and validation of delivery
  before accepting receipt. No restricted circuit code or curve construction is
  copied; no mature protocol's security theorem is claimed for this composition.
- Monero/MWEB: retain separate range/conservation/authorization checks and the
  requirement for recoverable scan data. Local key recovery does not establish
  durable independent public data availability or anonymity.
- RISC Zero/backend: preserve SDK/r0vm 3.0.3, v1compat 2.2.2 and the qualified
  substrate-bn commit 22108fe8. Add only a thin generic public-input adapter using
  the same established group/pairing equation and checked submitted-proof decode.
  Dynamic guest pprof confirms bigint2 execution for this new key/input vector.

The existing experimental SHA/HMAC note relation is reused under a new explicitly
selected economic domain. Constants change the compiled circuit/VK, so the old
local artifacts are preserved rather than re-labelled. Public parameters and
secret backup APIs are local wallet facilities, not new primitives or remote
witness delivery. Setup remains a one-party unfunded experiment.
