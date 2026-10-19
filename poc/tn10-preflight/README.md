# Concrete TN10 private/native preflight — 2026-10-19

PR53 was merged as `da84afbb7daf993f805859ceb40a3fc9f0dabf15`, after checking
Astra's reviewed head `4864924…` and successful CI. This package records actual
host/chain/provider observations and the [execution manifest](runmanifest.json).
It does not release funding, broadcasting, new proving or GPU rental.

## Results

| Check | Actual result |
| --- | --- |
| Cloud → gateway → B | Correct B FQDN, root administration through existing pinned wrapper |
| B clock/storage | NTP synchronized; about 79.7 GiB free on the state filesystem |
| B trusted package | Installed separately at `/opt/kpi-staged-tn10` from the merged commit; 14 downloaded file hashes and four public package files checked |
| Guard | Existing code hashes unchanged; sole systemd guard disabled/inactive, PID 0 |
| Guard host qualification | Separate-process durable recovery passed; all 15 existing guard controls passed as `kpi-cuda-guard`, on the real state partition with cleared environment |
| Trusted B verification | All four **retained fixture** receipts cryptographically verified, with existing negative controls, as the service user |
| Permissions | Guard user can read the public package/write state; cannot modify code or read root-only account envfile |
| Image availability | Anonymous registry manifest verified on B at the exact published digest and expected config ID |
| TN10 | v2.1.0, synchronized, UTXO index enabled; reviewed native binary hash retained; PID 951 unchanged during this preflight |
| Lane | Fixed lane inactive; full 20-block capture reconstructed by pinned native validator, zero accepted KPI-lane transactions |
| Funding snapshot | Known source has 995,388,210,600 sompi; fresh sponsor and Bob addresses have zero UTXOs |
| Fees snapshot | 100 sompi/gram; every later fully signed transaction still needs fresh mass/budget/fee checks |
| RunPod | Read-only authenticated list found zero Pods; Secure Cloud L40S lowest noninterruptible quote $1.09/h |
| Custody | Role files exist with 0700 directories/0600 files; no secret contents read or copied. Owner explicitly assigned Bob to the existing trusted operator for this test |

The exact GPU image remains:

```text
ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:fa4f72f0e060325a951eac33ea01ef00d3593ffe68531d69cf6a8b09daf41aa1
```

The original B guard and `/etc/kpi-cuda-guard.env` were not modified. The envfile
was used only through systemd's normal EnvironmentFile mechanism for read-only
provider requests; no account key reached Cloud, arguments, logs or the image.
An **old lease file remains**. Never arm the guard with it: preserve it and bind
a fresh lease to the actual new Pod/creation time only after live release.

## Native RPC compatibility found during preflight

The historical `private-native-tn10/read-only.mjs` sends a string request ID and
waited until timeout against the actual native endpoint. A numeric ID received
an immediate valid native response. [rpc.mjs](rpc.mjs) reuses the historical
method/endpoint allowlist, sends native numeric ID 1 and preserves raw response
bytes, including u64 values. [The focused test](rpc.test.mjs) checks numeric ID,
exact u64 preservation and refusal of mutation/another endpoint before connection.
The historical source binding, trusted host, guest and GPU image are unchanged.

The actual numeric client and [collector](collect.mjs) ran on the gateway in
`/opt/kpi-tn10-preflight-20261019`, using the existing Node binary at
`/opt/kpi-cloud-https/bin/node`. This is a one-shot read-only client, not another
chain executor. The collector is fixed to this public trial's addresses/lane.

```text
node poc/tn10-preflight/rpc.test.mjs
# ON THE GATEWAY, with a fresh directory already created:
/opt/kpi-cloud-https/bin/node tn10-preflight/collect.mjs NEW_RPC_DIRECTORY
```

The existing capture tool collected complete accepted bodies, confirmed endpoints
and a recheck. The Cloud verifier used the trusted validator SHA
`a7414677…`, not the differently hashed historical executable on the gateway.
Native reconstruction succeeds for the inactive lane. Omit/reorder/substitution
controls had **no applicable lane activity**, so were not exercised. This is
actual L1 preflight evidence, not a new ZK proof or settlement.

## Concrete next execution

The manifest fixes the current public trial and recipients, source UTXO snapshot,
image, B installation, custody status, fee allocation and each checkpoint:

1. After full live release, refresh source/fees/UTXOs and allocate
   **16.5 test-KAS** to the fresh sponsor: 10 principal, 1 state rent, 0.5 permission
   rent and 5 fee planning. The source separately pays the actual funding fee.
2. Activate the inactive lane, capture/verify a fresh active seed, then confirm
   bootstrap and initialization before depositing principal. Capture/freeze A.
3. Rent only when A is prepared. Read back the actual quote/resources/image and
   creation time; bind and arm the existing B guard with the exact 13-field lease.
4. Execute A → B → C → D with intermediate actual native acceptance, independent
   B CPU checks, fresh lane captures and exact targets approved on B before upload.
   C's genuine receipt issues permission; Bob's actual payout feeds D.
5. Preserve and verify results on B, confirm provider EXITED on every outcome,
   then delete the attempt's Pod/storage after external preservation and confirm
   deletion. Separate cryptographic, CUDA, native and operational outcomes.

One L40S, one attempt, 160M cycles per batch, **one shared 3,600-second proof hour
including chain waits**, and 7,200 seconds rental from creation remain unchanged.
The service reserves 300 seconds before lease end for transfer; B begins stopping
60 seconds before the absolute deadline. Start with over 3,960 seconds left.
No retry, extension, historical trial runner or unverified replacement input.

At the observed Secure quote, two hours GPU plus 100 GB running storage and up to
24 hours retention of the 10 GB stopped volume is about **$2.27**, assuming a
720-hour pricing month. This is planning under the existing $5 allowance, not a
reservation, guaranteed bill cap or permission to rent. Actual quote and fees
must be checked at their respective execution points.

## Release status and evidence

Preparation, B qualification, native connectivity and funding availability pass.
Bob custody is confirmed by the [owner decision](evidence/custody-decision.json):
the existing trusted operator manages Bob's backup and native recipient key for
this test. This is a logical Bob role, not independent user custody or isolation
from a malicious operator/root. No key was read or copied to record the decision.

**Funding/broadcast/rental remain NO-GO until the owner releases this complete
execution.** Inactive-lane activation and fresh chain
inputs are planned execution steps; the current capture is not a future seed.
Actual signed native transactions and four actual-input receipts do not exist yet.

Evidence is in [evidence](evidence/final-host-check.json), including
[B qualification](evidence/b-qualification.json), [native RPC](evidence/tn10-rpc.json),
[capture reconstruction](evidence/capture-verification.json),
[capture identity](evidence/capture-identity.json), [provider quote](evidence/provider-quote.json)
and [RPC compatibility](evidence/rpc-compatibility.json). The compressed capture
contains only public native transactions; role backups, keys and parameter
contents were not copied into evidence.
