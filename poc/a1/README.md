# A1 unfunded falsification harness

Implements ADR-0003 on the separate `poc-a1-successor-state` branch. It has no
funding, RPC submission, wallet or broadcasting API. Do not fund its local
fixtures: the deliberately public recipient fixture key is **1**.

G1 checked integer accounting and canonical contexts have passed the fixed G0
oracles in Rust and a separately written Python implementation. Circuit, script,
native consensus, parameter inspection and recovery tooling are included for
subsequent gate qualification; their presence does not itself close those gates.

Run only the pinned Rust 1.91.0 release toolchain and the locked dependency graph.
The upstream checkout must be clean at
`01b532e8b553523216471682649693af92f0fd16` (v2.1.0).

The reference compiler does not import the production relation or encoder. It
does share the pinned Arkworks SHA256 gadget and field/serialization libraries;
this is independent wiring/parameter inspection, not a second cryptographic
implementation or an audit. Opaque setup keys require source-reviewed setup
observation; hashes or a succeeding proof cannot establish their provenance.

Generated private backups, large proving keys and normalized matrices belong in
an explicitly chosen ignored/local or external directory, not Git. Private
backups are claim secret, recipient recovery key, and any backup-unlock material.
Proving keys are public, not toxic waste. The harness retains no setup trapdoor.

`experiment NEW_DIRECTORY` creates a single-party, unfunded local bundle and
three fresh proofs. `stateful BUNDLE` separately tests actual native temporary
RocksDB/virtual-UTXO consensus, with synthetic genesis and proof-of-work skipped.
`validate-body REQUEST.json` recomputes ID/full hash and runs native Full against
the supplied entry; it does not prove chain acceptance or current spentness.
`fresh-terminal BUNDLE BRANCH SECRET REQUEST OUTPUT` proves terminal spendability
for an authenticated known UTXO, not acceptance-history discovery.

The Python recovery scanner checks independently retained accepted transaction
bodies, lineage and accounting. Synthetic archive/unit tests are not independent
TN10 recovery evidence. G5 requires the separate A/B/C failure-domain topology
and authenticated history prescribed by the ADR. G6 remains unauthorized.
