# Reuse review — 2026-10-18

Ten upstream heads were checked before implementation and still match the
previous pinned review: [source-refresh.json](evidence/source-refresh.json).
The detailed [private-note source review](../private-note-chain/SOURCES.md),
[native integration map](../native-value/MAPPING.md) and
[takeover rehearsal](../takeover/LIVE-REHEARSAL.md) are the implementation basis.

Inspected current pinned vProgs `tx_inputs.rs`, batch verifier/aggregator,
permission tree/redeem script, delegate constants and the vendored settlement
builder. Reuse their transaction ID, native v1 encoding, active-lane hashing,
permission amount/destination/refund and reserve-change enforcement. The pinned
upstream/vendor files stay unchanged. The PR49 correction adds native lane/shape/
reserve restrictions to issued permissions and a lane guard to state covenant
continuation through a separate adapter; see [the alignment review](REVIEW-FIX.md).
Use accepted output covenant binding and exact outpoints rather than a separately
asserted native-success flag.

The existing Orchard, Aztec, RAILGUN, Monero and MWEB reviews were revisited for
the private/public boundary: hidden membership does not replace current
spentness; encryption does not replace recipient validation; an exit obligation
does not disappear until its authorized native payment. Their proof systems,
curve arithmetic, restricted circuit code, governance and monetary models are
not imported. The existing wallet Groth16 relation, SHA/HMAC nullifiers and
sealed-box discovery remain unchanged. Public parameter file identity must be
checked independently before loading it in Bob's separate local wallet process.

The active gap adapter reuses Kaspa's canonical activity and lane-tip functions
and the previously exercised unchanged-active-leaf anchor. It does not implement
expiry transitions, trust wall-clock gaps, enlarge a stale interval by relabeling
its starting blue score, or claim a fixture anchor is selected by TN10.
