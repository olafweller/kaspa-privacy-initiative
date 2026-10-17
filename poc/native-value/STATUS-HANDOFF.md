# Cloud/TN10 public native-value handoff

**Updated 2026-10-17 UTC. The bounded 10/4/6 native cycle is complete.**

Draft [PR32](https://github.com/olafweller/kaspa-privacy-initiative/pull/32), branch
`codex/native-value-cycle`, is stacked on PR31 at `6810058`. PR31's branch is
unchanged; neither PR is merged. The owner explicitly authorized this source
analysis, public native-test-KAS trial, remote execution and separate draft.
Repository documentation remains English; communicate with the owner in Dutch.

## Resume from these facts

- Native deposit 10 test-KAS, zero initial app balance, one proved credit.
- Correct shorter prefix settled; subsequent withdrawal/replay waited as allowed
  by current endpoint rules. No mandatory latest-checkpoint rule was assumed.
- Real partial receipt omitting the valid withdrawal was SDK-verified and then
  actually rejected by TN10 at the same legitimate start/end checkpoints.
- Full withdrawal settlement succeeded, creating the native permission claim.
- Actual payout `772897261ef2b6500a475b616b9636395c901e75ae09150d9403d12caa23239b`
  spent the deposit reserve output, paid 4 principal plus 0.5 sponsor rent refund,
  and left exactly 6 test-KAS in the protocol delegate reserve.
- The paid claim is spent; a distinct replay was rejected by native UTXO
  validation. Receiver/underpayment/reserve mutations were also rejected.
- Three real receipts, no development mode. Public-only re-verification and
  independent native-ID/state/journal/fee/backing audit pass. Ten confirmed
  transactions paid 1.94256 test-KAS in fees, from separate fee funds.

All finite project jobs and Cloud proving have **completed**. There is no proof,
payout or submission to resume. Never rebroadcast a recorded trial. Source and
artifact details are in [runtime metadata](evidence/runtime.json); source-file
hashes identify the delivered tools. Executed guest/host-v1 source is `11906ef`,
host-v2/driver source `c8562c5`, audit/verification baseline `d274b75`, and completed
audit/finish source `a39fbb9`; full rent-entitlement audit `8ea98c2`. Exact full versions are in runtime metadata.

## Connection and retained data

Use the existing root admin WSS terminal to `vmi3633138.contaboserver.net`, using
its configured `TN10_RPC_TOKEN` without printing it. The pinned PR31 client and
`remote.py`/`upload.mjs` remain the route; do not set up external RPC or a VPN.
The VPS node `kpi-tn10` is 2.1.0, synced on `testnet-10`, localhost JSON wRPC
18210, PID 43275 before/after. No restart/configuration change was required.

VPS project `/opt/kpi-pr31-cloud-20261017/native-value`; completed trial
`trial-2026-10-17T00-14-55-563Z-47c6d76b`; detached units used
`kpi-native-prepare-47c6d76b`, `kpi-native-auth-47c6d76b`,
`kpi-native-prefix-47c6d76b`, `kpi-native-finish-47c6d76b`.
Wallet keys remain only in protected VPS files outside the public trial tree.
Do not read, copy, print or package their contents.

Public trial archive, original raw-response captures, all three receipts/journals,
program/raw ELF, costs, test/validation outputs and manifest are in
[evidence](evidence/). Gzip files preserve original bytes; the original-member
manifest and [audit.py](audit.py) verify them. Everything needed for public
verification is retained without either private key. [README](README.md) gives
reproduction commands and [RESULTS](RESULTS.md) distinguishes every rejection layer.

PR31's precision issue is fixed in this follow-up with exact integer handling.
Original RPC members and proof bytes remain unchanged; corrected derived nonces
and six archive derivatives cite original records/prior hashes. The old PoC was
not rerun. Original published bytes remain at commit `6810058`.

## Next gate and material limits

The public user balance remains 6, backed by 6 native test-KAS. **Independent
continued withdrawal after a long idle gap is not established.** The current
fixed guest inherits `MAX_SPAN=100` and lacks the reference runtime's general
long-span/expiry/recursive proof route. Both tested intervals were captured before
proving; no admin upgrade or rescue was added. This is a bounded-adapter limit,
not evidence that Kaspa lacks the necessary primitive. Do not call those six
independently recoverable or production spendable on this evidence.

The smallest next integration is reuse of the upstream per-batch/aggregate and
compatible real recursive proving trajectory in a fresh instance, followed by
independent state reconstruction and continued withdrawal without the original
executor. Do not rebuild lane infrastructure. Mandatory progress, multiple
independent users/provers, pruning/reorg recovery and privacy remain open.
See [MAPPING](MAPPING.md), [adversarial review](ADVERSARIAL-REVIEW.md) and
[ADR-0004](../../docs/adr/0004-public-based-app-native-value.md). RFC-0001 stays Open.
