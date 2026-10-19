# RFC-0002: Minimal shielded native-KAS payment relation

Status: Proposed, 2026-10-17. Local work under
[ADR-0006](../adr/0006-shielded-design-local-work-package.md). This is the proposed
statement and interface, not an accepted production note construction or funded
privacy trial. [RFC-0001](0001-state-architecture.md), all security invariants and
the common N-user shutdown/exit gate stay open. PR34's migration requirements
apply. Native KAS is the backing asset; private notes are claims, not a new token.

## Current experimental checkpoint — 2026-10-18

The [completed classifier receipt](../../poc/remote-cuda/FULL-RESULTS.md) resolves
the bounded outer-proof blocker for the previous small test relation. The new
[ADR-0011](../adr/0011-local-private-note-wallet.md) chooses a bounded local
private-note circuit/kernel experiment, not production cryptography. Earlier
implementation-status paragraphs below describe the original model package;
the new package keeps actual wallet proofs separate from its unproved native-
fact fixture/kernel and the pending outer/native integration.

The later [ADR-0012](../adr/0012-private-note-state-integration.md) calibration
integrates real private state and native preimage checks in a new guest, with
21 passed cases and a 128M incomplete full-sequence result. This is execution
only, not a new receipt or native acceptance. The
[binding map](../../poc/private-note-chain/BINDINGS.md) lists actual remaining
settlement/recovery obligations. Earlier historical status rows are not claims
that these new native obligations are closed.

The [separate owner-approved 160M measurement](../../poc/private-note-chain/calibration-160m/RESULTS.md)
now completes that identical frozen sequence at 139,763,284 cycles. It preserves
the original 128M failure and produces no receipt. The exact next monolithic
proof/native-fixture target is specified separately; actual deposit lineage and
exit/payout/native acceptance remain open.

## Scope and economic state

Target lifecycle: authenticated native deposit -> one private claim -> private
payment and sender change -> current-state nullifier update -> pending exit ->
confirmed native payout. Alice/Bob is the first proposed workload, not an anonymity
claim. New funding waits for the [review decisions](../../poc/shielded-design/TN10-PROPOSAL.md).

Use integer sompi `0 <= v <= 2^64-1`, rejecting booleans/floats, noncanonical
encodings and overflowing sums. Positive spendable outputs are range constrained;
padding/dummy semantics require a separate explicit encoding. Do not perform
conservation merely modulo a proof field.

Logical state contains accepted note commitments `C`, permitted membership anchors
`A`, current spent nullifiers `N`, deposit states `D`, unpaid exits `W`, authorized
unpaid fee claims `F`, and the canonical native reserve/permission bindings. One
logical note universe is the initial experiment; physical tree/storage layout is
not selected. A model hash of the commitment list is not a production Merkle tree.

At every canonical state:

```text
private spendable liabilities + funded-but-uncredited deposit liabilities
+ unpaid exit principal + unpaid authorized fee claims <= reserved native principal
unpaid permission-rent refunds <= native permission rent already locked for them
```

State-covenant rent and uncommitted sponsor/treasury assets are excluded from user
backing. A sponsor paying native submission costs does not reduce user principal.
If fees are charged privately they are proof-authorized debits and remain backed
fee claims until their exact payout; they are not free treasury assets. Native
fees, app fees, rent and refunds have distinct ledger entries.

| Transition | Required accounting |
| --- | --- |
| Native deposit accepted | Reserve and pending-deposit liability both increase by actual output value; no private credit yet. |
| Deposit credited once | Pending liability becomes equal private value; actual native ID/output, pool script and amount are authenticated. |
| Private transfer | Sum input values = sum output values + authorized private fee. Sender change is an output; no hidden loss/inflation. |
| Exit requested | Sum inputs = private change + exit principal + authorized fee. Private debit creates an equal unpaid principal liability. |
| Native payout | Only confirmed permission consumption/exact recipient output removes exit liability and reserve principal; refund separately locked rent. |
| Deposit recovery | Consume a still-pending deposit claim once, prove owner authorization and current state, then credit or emit the exactly backed refund permission. A plain owner/admin signature cannot bypass current credited/spent state. |

The model implements the pending-deposit/refund state machine. This path is **not
implemented by the old funded delegate script**. The first private trial needs
an authenticated deposit descriptor and proved pending-credit/recovery semantics;
reusing a public deposit helper alone is insufficient. A stable outer descriptor
must retain recovery authority even when the inner proof/version is rejected.
The native meaning of malformed unsolicited transfers must be specified before
wallet funding is enabled; no claim is inferred from an arbitrary payment alone.

## Proposed wallet statement

Conceptual note fields are native value, spending condition, fresh randomness
and the chosen note/nullifier derivation inputs. Reuse established constructions
after [source and rights review](../../poc/shielded-design/SOURCES.md); do not copy
the executable model's SHA/HMAC identifiers as a reviewed protocol.

The wallet proves, without publishing the selected leaves/path, values or keys:

1. Every real input is a note under an allowed commitment anchor, with correctly
   derived note commitment and a satisfied spending condition.
2. Every nullifier is derived from that economic note and rightful authority in
   the correct immutable network/pool/spend domain; the user cannot choose a fresh
   marker for the same claim.
3. All amounts and intermediate sums satisfy integer bounds and conservation.
4. New commitments bind the authorized recipients, amounts and change. The
   delivery data/commitment relationship and recipient validation requirements
   are explicit; a corrupt ciphertext cannot be counted as a received payment.
5. The complete public intent, including outputs, ciphertext digest, fee terms,
   exit destination/principal and deposit reference where relevant, is bound to
   the proof and its spending authorization.

Public statement fields: network/genesis, pool/lane identity, statement and
verifier identities, allowed anchor, nullifiers, output commitments, delivery
ciphertexts or authenticated availability commitment, fee recipient/value and
public exit/deposit fields. Fixed arities/padding and the final note/encryption
formats remain review decisions; the model's variable operation shapes leak shape.

**Avoid a proof/payload circularity:** a wallet proof that is itself carried in
an L1 payload cannot bind its journal to the final native transaction ID that
includes those proof bytes. Instead define a canonical intent digest excluding
the proof serialization. The transaction adapter recomputes that intent, checks
the wallet journal, and commits the actual native ID/context into the outer lane
journal. The local compatibility fixture binds to an already-existing native
ID with no embedded wallet proof; it does not implement this new payload format.

## Enforcing layers and implementation status

| Obligation | Enforcing layer | Status in this work package |
| --- | --- | --- |
| Ownership, hidden membership, note/nullifier derivation, ranges/conservation, output intent | Local wallet proof and spending authorization | Ideal predicate in model; small preimage/sum relation only in measured proof; complete private circuit unimplemented. |
| Wallet verifier/program pins and public-intent binding | Proven transaction adapter and fixed outer image/config | Real composition/pinning measured, binding a retained public transaction ID. New intent/receipt payload and full monetary bindings remain unimplemented. |
| Allowed historical root and current unspent nullifiers | Proven canonical ordered application transition | Modelled, including two valid proofs from the same old root competing for one nullifier. Not proved by membership alone. |
| Every accepted lane input gets a deterministic outcome | Proven transaction/batch processing and native end commitment | Public backend established. Private invalid-proof classification is an explicit blocker below. |
| Atomic note/nullifier/claim updates | Proven application transition | Model checks before commit; failed spends change only rejection records. Complete shielded guest not implemented. |
| Actual deposit existence, covenant/state continuity, native reserve and payout | Native accepted input/seqcommit plus proved app relation and covenant/permission scripts | Public backend previously demonstrated. Private credit/recovery relation and payout integration require implementation and full fresh rehearsal. |
| Ciphertext authentication, complete local discovery, recipient spendability | Wallet, proof-bound delivery format, authenticated retained public data | Separate-key sealed-box model with commitment/owner checks and signed receiving addresses; not the chosen production format or a proof of encryption correctness. |
| Legacy version spending and migration single-consumption | Shared economic spentness or a proved one-way migration rule | Other versions rejected in model. Migration unimplemented; PR34 requirements remain open. |

## Invalid proofs and deterministic ordering

A rejected operation remains part of the accepted L1 lane input sequence. The
executor cannot remove it or assert a valid operation is invalid. Reject without
partial note append, nullifier insertion, fee debit or exit liability; process
later valid operations against the resulting current state. Repeated nullifiers
are checked both within an operation and across earlier accepted operations and
batches, even if all wallet proofs use the same still-allowed old root.

The RISC Zero 3.0.3 `env::verify` composition call requires the existence of a
valid matching claim and returns `Result<(), Infallible>`. It is not an ordinary
cryptographic verifier returning `false` for arbitrary bad proof bytes. The local
experiment observes missing/wrong evidence aborting execution; it does **not**
prove an invalid-operation no-op. A catch, host flag, unresolved assumption or
whole-batch abort does not close this requirement.

Before a funded private trial choose and measure a cryptographically enforced
validity/invalidity path. One candidate is an ordinary bounded proof verifier
executed inside the outer guest, whose actual result selects success/no-op; it
must agree with the permitted proof format and verifier identity. Another
admission/envelope design needs its own authenticated inclusion, authorization,
availability and censorship analysis. Neither is implemented or accepted here.
If no practical path is found, report a blocker rather than weakening ordering
or silently excluding malformed private operations.

Follow-up: [ADR-0007](../adr/0007-local-proof-classification.md) and the
[classification results](../../poc/proof-classification/RESULTS.md) implement and
execute a bounded canonical receipt verifier with valid-invalid-valid outcomes.
The operation excludes proof bytes from the wallet intent but includes them in
the computed native v1 ID. The endpoint is a local fixed ordered fixture, not
a new accepted-lane proof. Actual ordinary verification requires 870,829,938
user cycles / 880 segments; no outer receipt was generated. This leaves a
concrete proof-cost and real-lane integration blocker rather than closing the
invalid-operation requirement. The specialized route remains an unmeasured
comparison and no production format/construction is selected.

The [specialized comparison](../../poc/groth16-comparison/RESULTS.md) now implements
the second candidate directly (not receipt compression). Same hashes/ranges and
96-byte statement, 128-byte proofs, 702-byte operations; the ordinary verifier
still exceeds the declared 32-million-cycle budget. Its one-party test setup is
not a production ceremony. No completed outer receipt or funded trial follows;
keep full note construction and native integration gated.

The [accelerated candidate qualification](../../poc/accelerated-bn254/RESULTS.md)
demonstrates pinned-VM compatibility and full valid-invalid-valid execution at
117.47M cycles under the separately labelled 128M calibration, preserving proof
format and validation. It still misses the predeclared 32M practical target;
there is no outer receipt. A new explicit practical-budget experiment, full
adversarial qualification and actual one-hour-bounded proving remain prerequisites.

The [explicitly approved 128M successor](../../poc/outer-proof-128m/RESULTS.md)
qualifies all 24 existing adversarial executions and makes exactly one real
succinct-proof attempt. The whole process group is stopped at one hour with no
returned receipt. Full replay/continuation execution is now measured, but real
outer-proof completion and separate seal verification remain unqualified. No
private-note circuit, setup or native/TN10 integration is added.

The [subsequent phase diagnostics](../../poc/proof-phase-diagnostics/RESULTS.md)
produce and independently verify two actual segment receipts, their lifts and a
valid join, preserving this small wallet relation and classifier. They identify
measured phase costs without a complete classifier receipt. Full-session
image/journal verification and all private-note/native-integration gates stay open.

## Witness boundary, recipient and recovery

The initial design assumes local wallet proving. Raw private note contents,
spending/nullifying secrets, selected leaf indices and membership paths must not
be sent to executors, hosted batch provers, RPC services, logs or journals. The
outer prover receives only the public intent, wallet proof and public protocol
state/witnesses. The local measured Cloud process represents the wallet for a
synthetic fixture; it is not a benchmark on an independent user device.

Bob uses his own incoming key to trial-decrypt **authenticated accepted** output
records, checks exact note encoding/commitment and his spending condition, and
rebuilds the selected membership witness locally. A signed receiving-address
binding is exercised in the model to catch key substitution; final key/address
construction and ciphertext binding require review. Receiver validation must
fail before a note is counted as received. Seeing a root or an unconfirmed
ciphertext alone does not establish a spendable balance.

Retain: canonical L1 acceptance/settlement lineage, complete ordered commitments,
spentness updates, permitted anchors, full ciphertexts and required delivery
metadata, verifier/encoding artifacts and any proved snapshots. User backups
include spending and incoming-view material plus owned note metadata as required
by the selected scheme. No seed-only or root-only recovery claim is made.
Downloading/scanning complete public updates avoids a direct selected-note query
but not network/timing correlation. Missing history can prevent discovery or
exit; the model detects missing delivery, not independent archive availability.
Reorgs invalidate unfinalized outcomes/anchors and require specified rollback;
the current model is monotonic and does not implement general reorg recovery.

## Version boundary and review outcome

The public proof statement includes the exact network/genesis, pool and statement
version. Current nullifier spentness must refer to one economic consumption
domain across **all** simultaneously allowed versions/routes. Adding a verifier
version to a nullifier PRF and maintaining unrelated spent sets is unsafe unless
a separately proved migration consumes the old claim exactly once.

The first model permits only version 1, rejecting other networks, pools, integer
versions, booleans and float aliases. It does not implement migration. Before
later changes address voluntary privacy-preserving migration, legacy verifier/
data/fee availability, dormant users, anonymity fragmentation and stranded
liabilities, without an administrator withdrawal or forced migration key.

The [results and TN10 proposal](../../poc/shielded-design/TN10-PROPOSAL.md) name the
open decisions. Passing the model or small composition experiment does not
select a production construction or authorize the funded trial.

## Actual-chain preparation checkpoint — 2026-10-19

The [completed local four-receipt rehearsal](../../poc/private-native-proof/gpu-2026-10-18-02/README.md)
does not establish a TN10 private payout. The [staged preparation](../../poc/private-native-tn10/README.md)
now separates actual deposit references, accepted native lineage, complete lane
captures and per-batch trusted targets from the fixed fixtures. The reviewed
guest and wallet relation are unchanged. [ADR-0015](../adr/0015-tn10-private-native-preparation.md)
records the proposed deterministic rent-only initialization step needed by the
native genesis-ID rule. Its new script and subsequent live release need review.
Multiple outstanding exits/reserve aggregation, tree scaling, production wallet
custody and financial-privacy assessment remain open; this work does not close them.

## User-held recovery and terminal withdrawal package — 2026-10-19

[ADR-0016](../adr/0016-user-held-recovery-and-terminal-exit.md) and the
[executable local package](../../poc/user-recovery/README.md) make backup/data
requirements, public-history replay and an exact-reserve terminal native policy
testable. The old live program is unchanged. The new local policy requires later
guest integration and genuine outer-proof/native issuance qualification. Separate
local user processes are not independent custody. Independently administered
users and replacement services must still demonstrate actual canonical payouts
for all users, including the last, before the N-user recovery gate passes.

## Integrated full-reserve guest qualification

[ADR-0017](../adr/0017-integrated-recovery-native-guest.md) adds a separate
[guest and six linked local batches](../../poc/recovery-native/README.md) for
both the first user's partial and the final user's exact-reserve withdrawal.
Exit liabilities remain until native payout reconciliation. Native script and
accounting shapes agree; old program/state identities remain unchanged. A local
CPU qualification is not a new outer receipt or proof-authorized issuance. The
next bounded software package must qualify those genuine receipts before any
separately released fresh-instance TN10 test or N-user shutdown milestone.
