# Adversarial second pass

This is an AI-assisted implementation review, not independent security review.
No production architecture is selected. RFC-0001 remains open.
The original table below describes the 2026-10-13 offline checkpoint.
The remote-integration review at the end scopes the later live adapter.

| Attack / assumption | Enforced boundary / remaining risk |
| --- | --- |
| Omit three operations, recompute state and generate a valid proof | Guest derives a different lane tip and seqcommit. Production covenant reconstructs its journal with the external canonical end seqcommit. Same-interval settlement must reject despite valid off-chain receipt. |
| Feed a fake endpoint to the executor or verifier | Positive attack control intentionally accepts a partial receipt when the harness accessor is replaced with its fabricated endpoint. Only a real node supplies a canonical chain accessor. Fixture authenticity is the explicit offline trust boundary. |
| Carry the full lane tip while omitting execution | The image pins one monolithic program that applies every recognized operation while constructing activity from the same authenticated bodies. A partial receipt has a different journal and cannot authorize full-tip settlement. |
| Change payloads but keep original transaction IDs | Guest recomputes v1 ID from payload and strictly parsed rest preimage; activity commits it. Altered payload changes the endpoint. |
| Count to ten, renumber, duplicate or reorder to disguise omissions | The proving relation has no expected count and no expected operation sequence. State fold is order-sensitive. Activity uses version, ID and strictly ascending block-local `merge_idx`; canonical endpoint detects alternate sequences. |
| Wrong old/new state, lane, covenant or guest image | P2SH pins the old state/tip, lane and program; journal includes covenant ID and state continuation. Native negatives exercise the applicable bindings. |
| Forge SMT siblings or block context | Final inclusion and per-touch context are inside the authenticated seqcommit path. Start inclusion is checked, but a production start tip must come from bootstrap/prior settlement, not a prover assertion. |
| Skip an empty chain block | A continuously active app lane does not change during an empty block. The protocol intentionally compresses inactivity. Block context and miner data not used by the app remain opaque anchored digests; this PoC does not prove whole-DAG history or miner semantics. |
| Settle a shorter prefix or stop advancing | Completeness is relative to the claimed authenticated interval. This test does not force the executor to choose the latest anchor, settle on time, or get submitted operations accepted by miners. Independent execution is a recovery capability, not censorship resistance or guaranteed progress. |
| Lane expiry/reactivation | Guest only supports a continuously active, short span; no reset path. Missing inactivity/non-inclusion proofs are an explicit live gate. |
| Reorg, stale or unknown anchor | Actual opcode rejects a block invisible from validation or outside accessor depth. Offline accessor tests represent these cases; no live rollback or canonical-chain validation is implemented. |
| Replay | Proof binds state/tip/covenant. Replaying against the successor script fails. Replaying against the same synthetic unspent UTXO could pass the stateless script; L1 UTXO spentness supplies single-spend enforcement and is not simulated as a security guarantee here. |
| Mint, divert or release funds | No shielded liabilities, transfers, reserves or exits exist. Synthetic covenant continuation preserves value and output script. Fee inputs and economic transaction validation are not implemented. |
| Privacy leakage | All operations and state are public. No privacy or anonymity claim; a ZK-capable prover does not make this workload private. |
| Dependency / executor loss | Retained public fixture and guest/program binaries allow reconstruction and verification. Real Kaspa pruning, archive loss and witness availability remain open; a root alone is insufficient to recover bodies. |
| Malformed / underbudget proof | Real succinct receipts are required. Native verification rejects corrupted seals; bounded execution and insufficient budget are measured. |
| Control circuit / receipt format | An exact official monolithic lift control-ID pin replaces the upstream recursive resolve pin. Native verification still checks the allowed-control root, program image and empty-assumptions claim. Other segment shapes are unsupported; changing workload size can require a separately reviewed covenant instance. |

The cryptographic interpretation assumes RISC Zero soundness and SHA-256/BLAKE3
binding, correct image/covenant pins, correct bootstrap and a canonical external
seqcommit accessor. Tests exercise this implementation; they are not a proof of
cryptographic correctness, censorship resistance, data availability or recovery
of shielded native KAS.


## Remote TN10 integration second pass — 2026-10-17

- **Inflation / reserve release:** no shielded liabilities or exit mechanism is
  introduced. Bootstrap locks one test-KAS; settlement must preserve that exact
  covenant amount and identity. The native node validates the funded transaction,
  signatures, mass and live UTXO spentness. The builder uses checked integer-sompi
  accounting and excludes covenant-bearing entries from fee selection.
- **Fee handling:** preserve upstream activity/settlement funding logic with only
  the recorded mass-limit API access change. Add a normal change output before
  re-signing the bootstrap: the upstream single-output template otherwise gives
  the entire large input remainder to miners. A fee-wallet key cannot substitute
  for the covenant proof or change a bound successor.
- **Wrong state / proof replay:** the existing guest image and covenant pins are
  retained. The builder checks the real UTXO's script against the expected old
  state/tip and verifies the receipt's exact journal before funding. The negative
  variant intentionally signs a different successor state with the same valid
  receipt; only a proof-verification rejection counts. A spent bootstrap outpoint
  cannot be reused after confirmed continuation. No stronger unexecuted replay
  experiment is inferred from that spentness observation.
- **Wrong input / lane:** native decoding and transaction-ID reconstruction precede
  global-index lane filtering. Omission and ID-substitution controls keep the
  actual end anchor fixed. Python independently verifies the same raw capture.
  This is independent implementation, not independent data retrieval or a second
  node. A three-operation success is not represented as ten live operations.
- **Bootstrap / stale state:** the lane is preactivated with a seed outside the
  interval; the covenant explicitly starts at that known active tip and initial
  public app state. Execution-only profiling chooses the official fixed lift-19 or lift-20
  identity before funding bootstrap; it cannot authorize settlement. The old guest's
  100-score bound and supported SMT terminal
  remain unchanged. First-touch, expiry and general bootstrap history are absent.
- **Reorgs:** broadcast observations start behind the volatile sink. Capture
  rechecks selected-chain endpoints and the full accepted interval. Lost
  checkpoints preserve an unsuccessful trial; nothing automatically rebroadcasts
  a used identity. No continuously reorg-aware runtime is claimed. The actual
  settlement opcode remains responsible for consensus-visible end-anchor checks.
- **Privacy:** operation payloads, state and the test-fee wallet are public. The
  real zk proof authenticates computation; this workload offers no confidentiality
  or sender/receiver anonymity. Keys are only read inside the remote signer;
  repository evidence contains signed transactions and public data, never keys.
- **Operator / dependency loss:** Cloud builds/proves; finite VPS systemd jobs run
  independently of the terminal and laptop. Retain public captures, exact program,
  receipts and failed trials. Loss of the VPS wallet or all archives is not solved
  by a state root. Long downtime, pruned history and alternate-prover recovery
  remain separate experiments.
- **Hidden trust:** root host integrity, existing authenticated terminal/proxy,
  one owner-operated consensus-validating TN10 node, upstream software, RISC Zero
  soundness and hash binding remain assumptions. This AI second pass and passing
  tests do not constitute independent cryptographic/security review.


The retained failed lift-19/lift-20 combinations demonstrate a liveness and
compatibility risk, not a reason to remove a verifier pin. Final input is profiled
before bootstrap and checked again after inserting the real covenant identity.
The node still requires a real proof of the pinned guest and journal. The
catch-up bootstrap intentionally occurs after public input capture; it fixes a
known earlier lane tip and explicit initial app state. It does not establish the
authenticity of arbitrary past private state or bridge deposits.
