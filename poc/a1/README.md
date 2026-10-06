# A1 unfunded falsification harness

Implements ADR-0003 on the separate `poc-a1-successor-state` branch. It has no
funding, RPC submission, wallet or broadcasting API. Do not fund its local
fixtures: the deliberately public recipient fixture key is **1**.

G1–G4 have unfunded local qualification evidence in the
[A1 report](../../docs/poc-a1-proof-report.md). All three real proof paths,
native stateful conflicts/reorgs, final SDK decoding and exact fee/resource
checks pass. The [qualification repair](../../docs/poc-a1-proof-report.md#qualification-repair-after-independent-adversarial-review) corrects early-reject supplemental cases and binds fee evidence to final bodies/artifacts. G5 has network-disabled Docker A/B/C rehearsals. [Live attempt 2](../../docs/poc-a1-live-attempt-2.md)
passed physical whole-A loss and autonomous B start but failed at checkpoint
parsing before lineage/proving. Full independent recovery remains open; tool
presence, a container rehearsal or later offline replay does not close it.

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
`native-checkpoint REQUEST.json` imports the synthetic seed UTXO and exports
C's actual native checkpoint with zero accepted fixture transactions. Retain
it and the planned S0 locator before any fixture funding/continuation; later
native paths must match the checkpoint and recovery must reuse those exact
locator bytes. Its request is `{ "initial_outpoint": <native TransactionOutpoint>,
"initial_entry": <native UtxoEntry> }`. This is not a public TN10 checkpoint.
`fresh-terminal BUNDLE BRANCH SECRET REQUEST OUTPUT` proves terminal spendability
for an authenticated known UTXO, not acceptance-history discovery.
Its request is `{ "txid": "<32-byte hex>", "index": "0", "entry": <native UtxoEntry> }`;
`validate-body` instead takes `{ "transaction": <exact file transport>, "entry": <native UtxoEntry> }`.
They are not interchangeable. The independent checker must qualify owner intent,
artifacts and receipt before fresh proving; Full with a supplied entry does not
establish current-chain spentness. `check-backup BUNDLE SECRET RECIPIENT_KEY`
checks both actual private backups locally without printing their bytes.

The Python recovery scanner checks independently retained accepted transaction
bodies, lineage and accounting. Synthetic archive/unit tests are not independent
TN10 recovery evidence. G5 requires the separate A/B/C failure-domain topology
and authenticated history prescribed by the ADR. G6 remains unauthorized.

## Reconstruct without original-host access

Retain public PK/VK/R1CS/context/scripts/manifest/intent/inspection receipts,
source/lock/SDK pins and software independently before any future funding. Git
review fixtures alone deliberately omit the large public PK/R1CS artifacts.
Never regenerate setup to replace a lost key. Keep user private backup separate.

On independent B, obtain this public repository at the recorded source pin and
the official `kaspanet/rusty-kaspa` checkout at the exact revision above in the
sibling `upstream/rusty-kaspa` layout. Install Rust1.91.0 and the native RocksDB
build prerequisites; use locked release builds, not changed dependency versions.
The Cargo lock/source hashes and runtime binaries are recorded in the evidence.
Reconstruction means rebuilding software/reference checks, **not new setup**.

Run `a1_check.py` against separately retained owner intent and receipt with the
independently wired reference binary. Verify private backups with `check-backup`.
For B lineage recovery, use `a1_recovery.py` with the exact S0 locator,
artifact-index hash, complete accepted-body pages, actual historical UTXO
contexts and current UTXOs at a fixed horizon. Do not trust an address-only
match, guessed entry, pruned/gapped history or stale pointer. Reconcile reorgs
before proving. Feed its authenticated outpoint/entry to `fresh-terminal`;
generate a new proof and independently run Full/read back the exact payout.

`a1_recovery_rehearsal.py run --repo ... --bundle ... --retained ... --binary ...
--reference-binary ... --output NEW_DIR` reproduces the **same-host synthetic**
Docker rehearsal. It requires the pinned image identified in its source; an
exported public image may be independently replicated and imported with
`docker load`, then checked by image ID before running. Missing image software
can be rebuilt from pins; missing circuit PK cannot. Containers use read-only
scoped mounts, network none, unprivileged UID, no capabilities, no original
bundle mount in B/C and no saved S1 pointer or exit proof in B.
The chronological v3 rehearsal retains C's checkpoint and planned S0 locator
before A creates a continuation proof or C accepts funding. A late regenerated
locator/checkpoint is rejected rather than credited as pre-loss retention.

The local complete bundle/receipt and image copies under ignored `.local/a1/`
are durable local research records, **not proof of independent host retention**.
Do not recommend G6 until true B/C machine/archive prerequisites and full G5
are completed under separate instructions. Never fund the public-key-1 fixture.

## Replaying repaired qualification evidence

`prepare-body REQUEST.json` is a file-only negative-fixture helper: it recomputes
ID and native storage mass before strict `validate-body`. Preparation is not
validation. The supplemental harness requires the intended script/verifier error;
a stale ID, wrong mass, process failure or unexpected acceptance fails the run.

`scripts/a1_fee_check.py` additionally requires `--bundle DIR --validator BINARY`.
It binds SDK v2 literal bodies, input entries, fees/budgets/IDs/full hashes,
measurements and artifact hashes, then reruns native Full/masses. Legacy unbound
SDK receipts cannot qualify. `--historical-time SECONDS` explicitly replays an
old quote for regression evidence; it is never current fee/funding approval.
The complete invocation and source/binary hashes are reconstructable from the
repair receipt and its listed inputs. Original evidence is retained unchanged.

## Separate live attempt record

[Live attempt 1](../../docs/poc-a1-live-attempt-1.md) demonstrated TN10 S0 → S1
but failed safely at the independent recovery boundary. Its later owner terminal
exit is separate evidence, not successful G5 recovery. Full G5 remains open;
no further live action is authorized. The public fixtures above remain unfunded.

[Live attempt 2](../../docs/poc-a1-live-attempt-2.md) remains permanently
**G5 FAILED — autonomous recovery did not complete during the live run.** Its
later memoized offline replay and separate new-proof terminal owner exit are
distinct evidence. This publication changes no protocol/tooling source and starts
no attempt 3, funding or broadcast. Attempt 1 records remain unchanged.
