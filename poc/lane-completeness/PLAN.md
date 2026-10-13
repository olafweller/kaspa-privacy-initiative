# KIP-21 lane completeness experiment

2026-10-13. Research only; no shielded funds, notes, funding, signing keys or broadcasts.
KPI baseline `ccbdfbc7b5d2f601089e9dc5254719c523a64010` matches origin/main.
RFC-0001 remains open. A1, invariants and historical evidence are untouched.

## Source inspection before implementation

| Source | Pinned head | Inspected components |
| --- | --- | --- |
| kaspanet/docs | `0ac77d043a802fc8196abfd5812ac2afbd97a2b9` | `content/docs/toccata/based-apps.mdx` |
| kaspanet/kips | `e4ae2332117b5cb68bd6188e065ef885b6d17939` | KIP-21 and companion proving/accessor specs |
| kaspanet/rusty-kaspa | `01b532e8b553523216471682649693af92f0fd16` | seq-commit hashing/tests, SMT proofs, v1 TxID/preimages, lane validation, RPC, script accessor |
| kaspanet/vprogs | `f9b84a863a7c7c20586a9cf947550475e894f72e` | batch/aggregate verifiers, L1 bridge, activity builder, production/development settlement, receipt witnesses, TN10 runbook |

Existing KPI A0/A1 and mature-protocol review notes were inspected. No private protocol
components are required. The Sutton discussion was not supplied or found in KPI;
no statement is attributed to it without the primary transcript.

## Smallest experiment

1. Synthetic, explicitly labelled Kaspa accepted-order fixture: ten numbered v1
   operations in a valid user lane, unrelated accepted traffic, several chain
   blocks, lane SMT and start/end sequencing anchors. Application state is a
   domain-separated SHA-256 fold over operations; order changes the state.
2. Reuse native `kaspa-seq-commit`, `kaspa-smt`, transaction preimage/ID APIs and
   `vprogs-l1-utils`; write a small RISC Zero guest executing the fold and lane
   recurrence. Reuse the production vProgs settlement covenant and real succinct
   verifier in the Kaspa script engine. No development receipt or covenant.
3. Bind old state/tip, app/lane identity, new state/tip, final SMT inclusion and
   final seqcommit. Settlement reads the externally fixed anchor through
   `OpChainblockSeqCommit`, not a value supplied by the executor.
4. Generate full and seven-operation receipts, omitting operations 3/6/9. Verify
   that the partial receipt is real, then demand settlement against the same
   full fixture interval. Also attempt wrong state/lane/order/anchor/SMT/payload
   and malformed proofs. A host length/count check is not decisive evidence.
5. A separate Python executor reconstructs order from the accepted transaction
   records, verifies IDs/commitments and folds all public operations.
6. Retain fixtures, receipt/transaction bytes, verifier errors, timings, memory,
   sizes, native script costs and exact reproduction commands.

## Publication and limitations

User operations use ordinary v1 transactions: four namespace bytes followed by
16 zero bytes, with at least one nonzero namespace byte after byte zero. Use normal
fee-funded inputs/change, payload and supported lane gas. Reuse vProgs
`l1/wallet/src/build/activity.rs` when a live trial is authorized. Reconstruct from
accepted order (`merge_idx` including selected-parent coinbase), not arrival order,
txid sorting or transaction timestamps. Fetch full bodies, selected-parent context
and `GetSeqCommitLaneProof` for the end anchor. Retain rollback/removed-chain data.

Missing/unsupported: companion proving spec is reserved; no stable lane SDK;
long-term payload/witness retention, expiry/reactivation and live reorg handling
need separate validation. TN10 connectivity/activation/relay/witness serving are
not established by offline results. Based-app docs say 320-byte journal; pinned
code uses 352 bytes including `deposit_spk_hash`. Follow code. vProgs demo defaults
to development mode, which is unsuitable evidence here. CPU succinct proving is
attempted; toolchain/artifact/network failures must be reported as failures.

Offline success can demonstrate cryptographic rejection against fixture anchors
using the actual L1 verifier. It cannot establish an observed canonical TN10
interval, censorship resistance, privacy, availability, production soundness or
RFC acceptance. No broadcast functionality is needed for this stage.

Implementation findings: upstream EngineFlags is incompatible with the current
node API, so a recorded compatibility adapter is required. Its recursive
`resolve.zkr` pin also rejects an assumption-free monolithic receipt. The local
experiment retains all verification and uses an exact official monolithic lift
control ID; other proof segment shapes are unsupported. A raw guest ELF must be
packaged with the trusted v1compat kernel using the upstream ProgramBinary API.
