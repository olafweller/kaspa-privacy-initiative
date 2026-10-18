# Threat Model

**Status:** initial research draft. This document should become more precise as architecture choices are made.

## Assets to protect

1. Native KAS backing the shielded system.
2. The integrity of the shielded supply.
3. User authorization and spend rights.
4. Sender privacy.
5. Recipient privacy.
6. Amount privacy.
7. Balance privacy.
8. Transaction-graph unlinkability.
9. Availability of valid exits.
10. The ability to reconstruct and independently verify protocol state.

## Primary security goals

An attacker must not be able to:

- create unbacked shielded KAS;
- spend the same private value twice;
- withdraw another user's funds;
- alter a valid state transition without detection;
- make an invalid proof accepted;
- make a valid user's funds dependent on one trusted operator;
- silently change the protocol rules through a privileged key.

## Adversaries

The system should consider:

- malicious users;
- blockchain analytics companies;
- large passive observers;
- malicious or compromised provers;
- malicious executors/sequencers;
- compromised RPC/state servers;
- compromised wallet software;
- colluding infrastructure operators;
- attackers seeking denial of service;
- attackers exploiting implementation bugs;
- governance or treasury capture;
- adversaries with exchange/KYC information;
- long-term observers correlating deposits and withdrawals.

## Attack classes

### 1. Inflation

A bug in the circuit, arithmetic, commitment scheme, proof verifier, or state transition allows more shielded value to exist than native KAS locked by the protocol.

**Severity:** catastrophic.

### 2. Double spending

The same note/value can be consumed more than once because nullifiers are not unique, not correctly bound, or not consistently checked.

**Severity:** catastrophic.

### 3. Unauthorized withdrawal

An attacker convinces the settlement mechanism to release native KAS without owning a valid shielded claim.

**Severity:** catastrophic.

### 4. Malicious prover

A prover submits a forged, stale, incomplete, or wrongly-bound transition proof.

Desired property: an invalid proof cannot threaten safety. Loss of a prover may threaten liveness only.

A hosted prover may also learn private notes, amounts, and other witnesses supplied to it. A zero-knowledge proof does not hide those inputs from the prover that handles them. Record local/outsourced proving assumptions and keep spend secrets out of untrusted execution infrastructure.

### 5. Malicious executor/sequencer

An executor censors, reorders, withholds, or selectively includes operations.

Questions:

- Can another executor take over?
- Can censorship be detected?
- Can users still exit safely?
- How long does failover to an independent executor/prover take?
- Can a censored valid operation or exit be resubmitted through independent infrastructure?
- Can censorship and failover be observed and measured externally?

### 6. State availability failure

A server or group disappears with data needed to generate future proofs or withdrawals.

Desired property: critical state is public/reconstructable, replicated, or user-held such that disappearance of common infrastructure does not destroy funds.

Roots alone cannot reconstruct state or witnesses. Recovery must account for L1 pruning, retained public history, encrypted note delivery, wallet backups, and independent proving. A safe halt is not evidence of recoverability.

### 7. Witness corruption

Wallets or provers receive incorrect Merkle paths, state roots, note metadata, or encrypted payloads.

The system should verify rather than trust witness providers wherever practical.

### 8. Timing correlation

A user shields a distinctive amount and soon unshields a similar amount. Even perfect ZK may not prevent a strong statistical link.

Low-activity periods require particular attention, because batching provides less timing anonymity when very few users are active.

### 9. Amount correlation

Unique public deposit/withdrawal values may reduce the practical anonymity set.

### 10. Network metadata

RPC requests, note scanning, transaction submission, IP addresses, and peer connections may reveal relationships that the ledger itself hides.

### 11. Wallet fingerprinting

Wallet-specific transaction construction, timing, fee behavior, note selection, or relay patterns may identify a user or software version.

### 12. Viewing-key leakage

A compromised viewing key may reveal incoming activity or other metadata depending on the final key model.

### 13. Cryptographic failure

A primitive, curve, proof system, hash, PRF, or implementation assumption becomes insecure.

Cryptographic agility must be balanced against upgrade risk.

### 14. Circuit/spec mismatch

The implementation proves a subtly different rule set than the written specification.

Independent test vectors and cross-implementation testing should reduce this risk.

### 15. Upgrade capture

A governance process, multisig, or maintainer group gains the ability to replace the settlement logic with rules that can confiscate or redirect funds.

### 16. Treasury capture

A development funding mechanism becomes technically or socially entangled with user reserves.

The two must remain separate.

### 17. Denial of service

Attackers spam commitments, nullifiers, proofs, or state requests to make proving or verification too expensive.

### 18. Reorg / finality assumptions

An application acts on a Kaspa state transition before the required finality assumptions are satisfied, leading to inconsistent state or invalid settlement.

Define rollback/replay behavior and distinguish executed, proved, settled, and withdrawable state. Historical note anchors must not authorize replay against stale settlement or spent-state roots.

### 19. Unpaid exit liability

A private claim is consumed into an exit entitlement, but the reserve accounting drops that entitlement before the user receives an authorized payout. All pending exits remain user liabilities; proofs and settlement must bind the amount, destination, reserve continuation, and any fees.

### 20. Fee-payment correlation

A private operation may cause a publicly observable Kaspa L1 transaction whose fee is paid by a known or linkable transparent wallet. Even if the private state transition hides sender, recipient, and amount, an observer may correlate the payer, timing, and privacy-system activity.

Desired property: private operations should not require a publicly linkable fee payment from the user's transparent wallet.

Testnet analysis should measure whether a passive observer can correlate a known transparent wallet's L1 fee payment with a specific private operation.

## Initial out of scope for the first cryptographic PoC

The first PoC may not fully solve:

- IP/network privacy;
- mobile light-client privacy;
- economic spam resistance;
- production-grade prover decentralization;
- polished recovery flows;
- legal/operational deployment.

These are not out of scope for the eventual protocol. They are only deferred so the first experiment remains falsifiable and small.

## Principle

**A privacy protocol is not secure merely because transaction contents are encrypted or hidden in a proof.**

The entire path — deposits, state availability, proving, note discovery, transaction broadcast, exits, wallet behavior, and upgrades — belongs in the threat model.

## A0.5 experiment-specific operational boundary

The [A0.5 adapter](docs/poc-a0-tn10-runbook.md) assumes an uncompromised local
host and correct pinned SDK/node binaries. Persisted claim/proving material and
recipient keys are required for liveness; a same-host restricted backup is not
independent recovery. A substituted key cannot spend the original P2SH reserve,
but lost material can strand the test claim. No admin recovery path is added.

The adapter checks exact fields after serialization and accepted-block readback.
A blue-score distance greater than 20 plus a later UTXO recheck are bounded observations,
not a finality guarantee. On uncertain submission/acceptance, stop and inspect
saved IDs; do not automatically refund/rebroadcast. Transparent source, reserve,
recipient, amounts, proof and timing are public and linkable. A0.5 demonstrates
no anonymity or general state availability. Setup remains single-party Groth16
with no independent audit, ceremony or proof of toxic-waste destruction.

During A0.5, the own node can validate network headers while its full UTXO import
is incomplete. Two explicit synchronized native RPC endpoints may then supply
UTXO/acceptance observations after matching locally validated headers and the
independently established TN10 genesis. Their responses remain a trust assumption;
two endpoint URLs do not prove operator independence. Corroborate the accepted
block/body and payout/spentness, fail closed on disagreement, and never describe
this route as local validation of the entire live UTXO set. The original local
full transaction validator and on-chain covenant remain the authorization path.

## Public native-value based-app experiment boundary

The [ADR-0004](docs/adr/0004-public-based-app-native-value.md) experiment exposes
all account balances, public keys, requests, recipients, deposits and payouts.
The prover receives public state only; random signing keys stay on the VPS.
New attack surfaces under test are fabricated/repeated credit, failed-command
side effects, recipient redirection, omission at a fixed authentic lane anchor,
permission replay and reserve/change diversion. Imported runtime actions and
permission scripts enforce different parts of that boundary; see the
[enforcement map](poc/native-value/MAPPING.md). Host checks alone are not proof
of theft prevention. Missing public witnesses can halt progress; there is no
admin bypass or new reserve key. Independent recovery remains untested.

## Recursive public-account adapter boundary

The [recursive follow-up](poc/takeover/README.md) adds a transaction journal and
one coarse SMT resource around the existing public account rules. Its review
must bind the full prior account state, native v1 transaction ID, global merge
index, block context, batch/aggregate images, lane and covenant continuity.
Wrong/missing inner receipts must fail at execution; a changed journal must fail
SDK/native cryptographic verification. Host preparation alone does not establish
these properties. The local script accessor must also be checked against the
fixed captured commitment, since accepting a prover-derived anchor alone cannot
show omission resistance. Lane expiry/reset remains unsupported and rejected in
the batch guest. The experiment retains one owner's historical node/archive
trust and public balances; no independent-operator, pruning-recovery or privacy
claim is added. The [fresh TN10 rehearsal](poc/takeover/LIVE-REHEARSAL.md)
separately confirms actual payout after clean public replay and a 175-score stop
gap; native omission, bridge-diversion and spent-input controls were rejected.
A canonical-chain observation does not establish general reorg recovery; the
runner halts on a detected reorg and never automatically retries broadcasts.

## Privacy work after the Based App checkpoint

The [feasibility conclusion](docs/based-app-feasibility-2026-10-17.md) covers public
ordering/execution/settlement. The next [shielded-KAS specification](docs/shielded-kas-next.md)
must explicitly cover chain observers, executors, hosted provers, RPC providers
and recipient discovery. A prover receiving plaintext witnesses is a privacy
trust dependency; lane payloads, resource access, fee funding, ciphertext retrieval
and timing can leak relationships despite a ZK execution proof. No privacy
requirement is satisfied by the public-account result. Existing fund-safety,
recovery and independent-review requirements remain unchanged.

## Local private-payment model boundary

The [first package](poc/shielded-design/README.md) uses an explicitly ideal proof
registry and reproducible test keys. Its SHA/HMAC IDs and sealed-box demonstration
are not selected production cryptography. A server validity flag cannot replace
a proved predicate. Two valid wallet proofs using one old anchor still need a
current shared nullifier check. Failed operations must change no economic state,
and a funded rejected deposit must retain a proved credit/owner-recovery path.
Uncommitted rent sponsor funds are not backing; the model requires an explicit
funding step before creating an exit rent entitlement. Missing recursive evidence
currently aborts, so deterministic invalidity/no-op handling remains a real
liveness/completeness design blocker. See the [adversarial review](poc/shielded-design/ADVERSARIAL-REVIEW.md).

The [ordinary-verifier experiment](poc/proof-classification/RESULTS.md) checks
canonical submitted proof bytes and reduced field/path encodings in the guest;
local omission/substitution against a fixed expected endpoint aborts. Correct
sequence outcomes were executed, not proved in an outer receipt. Verification
cost and almost-block-sized receipts expose a resource/availability concern:
an invalid seal can fail late and consume nearly the full verification work.
No fee-based denial-of-service protection, arbitrary accepted-lane totality,
real L1 authentication, complete private statement or production safety follows.

The [specialized wallet comparison](poc/groth16-comparison/RESULTS.md) retains
full checked decoding of untrusted curve/subgroup points while loading immutable
prepared constants already checked against the selected VK. Both exact parameter
bytes and program identity must be pinned. Circuit-specific setup introduces a
soundness trust assumption; fresh one-party research entropy is not a production
ceremony. Small real proofs do not establish completed in-guest classification:
that execution still exceeds its 32-million-cycle research cap.

The [accelerated backend experiment](poc/accelerated-bn254/RESULTS.md) subsequently
completes the same full sequence at 117.47M cycles in its labelled 128M calibration,
retaining checked submitted-point decoding before coordinate conversion into
existing library arithmetic. This introduces a pinned backend implementation and
a new expected classifier image, not new host validity authority or setup.
The 32M practical cap still fails; no outer receipt, general replay qualification
at a larger budget, L1 endpoint or production stability claim follows.

The [subsequent approved 128M attempt](poc/outer-proof-128m/RESULTS.md) qualifies
all existing full replay/continuation and malformed/authentication cases. One
actual succinct-proof call is stopped at its one-hour process-group ceiling
without a receipt. No negative control relies on that timeout. Separate real
receipt verification and its wrong-image/journal checks are implemented but
unexecuted without the missing artifact. The fixed synthetic relation, local
ordering source, setup and private-note/native backing limitations remain.

The [follow-up phase diagnostics](poc/proof-phase-diagnostics/RESULTS.md) verify
actual middle-segment, lift and join receipts, including altered seal/claim
rejection in a separate process. Workload association uses the trusted pinned
SDK export and asset hashes. These partial transition proofs do not establish
a cryptographically composed path from the initial image to the full journal;
they cannot replace the full-receipt identity/journal checks or native settlement.

The [remote CUDA preparation](poc/remote-cuda/README.md) sends only these existing
public research fixtures to a candidate rental. An independent CPU comparison
pins all five PR #40 claims; a remote report or transport hash is not enough.
The provider can deny service or falsify telemetry and billing, but cannot make
a different sealed claim pass those checks. The independent watchdog's host,
credentials and provider stop API are availability/cost assumptions, not protocol
authorities. Live CUDA, stop and persistence behavior remain unqualified. Never
send private wallet witnesses through this public-fixture interface without a
separate privacy design. This changes no protocol, circuit or settlement rule.

The disabled [B-host guard](poc/remote-cuda/B-GUARD.md) is installed separately
from the TN10 management gateway. After later activation it keeps its lease,
timer, backups and provider credential on B; Cloud/gateway/laptop availability
is not required by that loop. B-root administrators remain trusted and can read
files or alter the service. The management SSH restrictions and file permissions
do not protect against a malicious administrator. Guard qualification tests use
simulated provider responses. The operator's later successful read-only provider
GET does not establish stop/write permission or live rental/stop qualification.

## Local private-note research boundary (2026-10-18)

The ADR-0011 experiment keeps spend/view keys, note plaintexts and selected
Merkle paths inside the local wallet/proof process. Public payloads contain
commitments, nullifiers, historical anchors, ciphertexts and proofs, not input
notes or paths. The Groth16 setup is one-party experimental; no production
ceremony or toxic-waste guarantee is claimed. SHA/HMAC note composition is a
new experimental protocol adaptation, not a new primitive or inherited Orchard
security result. Native facts are test fixtures, not a trusted rescue authority.

The proof binds ciphertext bytes; it does not prove encryption correctness.
Recipients must decrypt, reconstruct the commitment, verify the expected
owner/incoming key and find the note in accepted data before counting a payment.
Malformed delivery can burn a malicious sender's own output and is never counted
as recipient receipt. Public deposit/exit amounts, timing, tiny tree/low activity,
fixed operation shapes and service/network observation remain linkability risks.
The full state guest, native accepted data/payout verification and independent
service-disappearance recovery are still required before a funded privacy trial.


The subsequent ADR-0012 calibration commits the covenant/config together with
private state and checks deposit fields from native preimages. Its lane anchors
are synthetic until matched by actual canonical native settlement. Untrusted
host balances, locally invented outputs and the mere existence of a proof over
a fixture cannot establish backing. Pending exit permissions remain liabilities;
actual native consumption and exact payout confirmation are still unimplemented.
The 128M full-sequence limit failed; no full receipt or GPU job follows from the
successful single-operation and rejection executions. New test-domain wallet
backups are local-only 0600 files; public parameter retention/loading and local
separate-process recovery do not establish durable independent availability.


A separately owner-approved 160M execution now completes the identical private
sequence and exact aggregate journal. Completion alone is not a genuine receipt,
canonical native deposit acceptance or payout. In the restore path, only the
independently expected VK is enforced; the full parameter-file SHA256 is recorded
but not compared to an independently expected value. Future parameter distribution
must supply/enforce that trusted whole-file hash before use.
