# Preparation second pass — 2026-10-19

This is a source/local-test review, not an independent audit or live rehearsal.
No model reviewer or Astra was invoked; the owner retains that review step.

| Question | Enforcement/evidence | Remaining boundary |
| --- | --- | --- |
| Can a different genesis script/ID be substituted? | Native ID is derived from the actual rent-only genesis output; initializer derives the successor root from `OpInputCovenantId`. Actual engine tests accept the exact successor and reject wrong root/lane/rent/output authorization/shape. | New initializer needs owner/source review and actual native genesis acceptance. |
| Can initialization release user funds? | No deposit is admitted before the accepted initialized checkpoint. Initializer handles only unchanged 100M rent and one unbound sponsor. It has no withdrawal key or arbitrary successor. | The controller must recheck the actual initialized UTXO before depositing. |
| Can a GPU choose an easier statement? | Frozen input/program/journal hashes and target SHA retained independently on trusted B. Receipt verification pins guest/join, full journal, no assumptions and real mode. Four genuine retained receipts plus 60 existing crypto negatives rechecked. | A malicious controller choosing its own expectations is outside this trust boundary; old fixtures are only regressions. |
| Can proof waiting omit accepted activity? | Use the full native `verify`, mapping canonical bodies and merge indices without the old short-export execution. Prior tip/last-touch/checkpoint start must match; long-gap conversion preserves exact retained input/journal. | Actual fresh captures must be collected after release. Native lane expiry is unsupported. |
| Can a stale endpoint be replaced after proving? | Signed settlement preparation checks the exact proven end block/seq, selected-chain flag and strict native finality-depth eligibility. Native accessor remains the actual on-chain authority. | Historical RPC files can become stale; refresh before a later broadcast. Orphans halt. |
| Could signing invalidate measured budgets? | The generic native signer was found to reset proof-input budgets to 10. The adapter now uses the existing single-input fee signer after budget measurement. Genuine receipt integration requires proof budget >=2500 and rechecks all final scripts/budgets/masses/fees. | Live node policy/version and current fee estimates remain to be confirmed. No historical fixture evidence was rewritten. |
| Can an accepted payout become an economic no-op? | Reviewed relation/native restrictions unchanged. Actual receipt creates a new permission outpoint; payout builder verifies actual permission/selected reserve and previews authenticated accounting. Signed native underpay/reserve/recipient/lane mutations require specific semantic script errors, not resource failures. | Actual TN10 acceptance, spentness and distinct replay rejection are still unperformed. |
| Can a second stage get a fresh hour or repeat after failure? | Persistent ordered attempt ledger, fixed original deadline/lease identity, stage marked attempted before spawn. GNU timeout wraps prover + separate CPU invocation; existing qualified sampler/process-group code reused. Synthetic deadline/order/restart tests pass. | Staged transport/image binding and actual GPU execution remain unqualified; no live service is deployed here. |
| Can keys or witnesses leak in upload? | Fresh 0600 role files stay outside the four-file public allowlist. Public bundle hashes all assets and tests exclude an extra key file. Outer input contains public wallet proofs, not witnesses. | Host root can access local roles; Bob custody must be established. Metadata/traffic analysis and production privacy are not solved. |
| What if Cloud/gateway/prover disappears? | Receipts/candidates remain create-only; checkpoint and target hashes preserved. No automatic retry/rebroadcast or accounting rewrite. Reuse independent B backup/absolute lease-stop guard. | B guard/package, quote and new service compatibility must be checked before any future rental. No provider call was made here. |

The concrete blockers are in [runmanifest.json](runmanifest.json). In particular,
this PR does not describe the PR51 fixed image as accepting staged inputs and
does not manufacture an image digest for a service that has not been deployed.
The owner-approved preparatory phase ends with these tools/tests/manifest for
review; funding, new actual-input proofs, rental and broadcasting remain unreleased.
