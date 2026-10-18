# Adversarial preparation review

This is a research-job controller, not a new protocol or a hosted wallet service.
No reserve, spend, nullifier, circuit, guest or settlement rule changes.

| Failure or attack | Binding/check and remaining limitation |
|---|---|
| Mint, double spend, release reserve or substitute recipient | No funds/transactions involved. Only existing public segment assets are processed. Partial receipts are never accepted as a full classifier/settlement receipt. |
| Prover returns a different valid statement | CPU comparison pins all five independent CPU claim digests, checks cryptographic integrity, seal/claim mutations and exact segment composition. Test substitutes another genuinely sealed segment/lift while editing unsigned index metadata; it must fail. |
| Stale image, wrong input, swapped/replayed proof | Existing guest/image and all input hashes fixed; CPU claim pinning rejects valid foreign proofs. One persistent attempt marker prevents retries through restart. This does not add a chain freshness claim to partial proofs. |
| GPU operator sees wallet secrets | Uploaded assets are already-public PR #40 fixtures, not private notes or witnesses. Do not reuse this trust boundary for private proving. Bearer/provider credentials are excluded from proof child environments and artifact selection. |
| Arbitrary command service or credential forwarding | Fixed endpoints and fixed five-phase commands; authenticated short requests, no uploads, redirects or client-selected paths. Account key only on independent guard host. Transport/service token is still a privileged control credential. |
| Controller disappears and compute keeps billing | Independent guard with restartable systemd unit and a timer separate from status/download requests stops the precise lease; process groups also have local deadlines. Provider/read-back failure is retried and never reported as confirmed stop. Both guard and provider availability are operational trust assumptions. |
| Wrong Pod stopped or budget silently expanded | Pod identity/creation time, one L40S, quote/resources and absolute deadline checked. No create/start/delete provider API is implemented. Lease includes stopped-storage retention; actual billing remains a provider fact. |
| Restart repeats paid work | Attempt marker and interrupted-state recovery; restart does not prove again. New lease cannot overwrite a configured lease. |
| Host memory cap incompatible with CUDA | Explicit RSS policy, no CUDA virtual-address-space limit; sampled peaks may be missed, shared RSS double-counted. Host must have spare RAM. Limits and actual values are reported. |
| CPU fallback or unrelated GPU activity counted as acceleration | CUDA-only upstream build, fixed binary hash; matching process-group PID, GPU UUID and utilization required per phase. Container/host PID mismatch remains a live qualification gate. |
| Missing dependency or malformed archive | Exact source/archive hashes and safe bounded extraction. Missing build/runtime/provider services stop this attempt; no weakened verifier or automatic budget increase. |
| Download race, interrupted external write, or stop loses results | External archives use same-filesystem temporary writes, file fsync, atomic replace and directory fsync. Size/hash verification of the saved copy precedes completion records, including on reuse after restart; stale completion for a damaged copy is discarded before repair. Truncated and same-size damaged copies are tested. A failed backup cannot delay the independent absolute rental-stop timer; the Pod volume remains the fallback. A checkpoint can advance between status/fetch: retry a mismatch. CPU verification remains separate. |

Local HTTP/provider tests use explicit mocks and cannot establish live HTTPS,
provider schema, persistence, CUDA use, shutdown reliability or production security.
The former B recovery VPS now hosts the disabled guard; see [B-GUARD.md](B-GUARD.md).
This is not a new independent operator network. The management gateway is not a
runtime dependency: lease, code, timer, backups and later credentials reside on B.
B-root administrators remain trusted and can read files or change the service;
SSH restrictions do not provide privacy from them. Old recovery secrets were not
inspected and old services were not restarted. Live rental deployment still
requires credentials, quote, real lease, direct HTTPS and provider read-back.

The later `qualify_guard.py` host rehearsal supplies explicit fake provider and
artifact callbacks to every guard instance. It uses a fresh output directory and
separate Python processes, records source hashes and labels both simulated time
and provider stop. A subprocess failure prevents the final success report. It
does not read credentials, reboot the host or establish live rental protection.
The clean-runner packaging fix creates missing parents only; it retains refusal
to reuse an existing output directory and all fixture/hash/CPU-receipt checks.

The application User-Agent maintenance adds only honest client identification
and a JSON Accept header; it preserves authentication, TLS-only URLs, redirect
refusal and time/size bounds. The focused regression checks the request object
with a mocked opener, never the real account credential. Current B source is
bound to its new hash; the prior published image remains bound to its original
source and digest. Its unused outbound-request helper is not a reason to rebuild
or weaken image/source checks. The owner's real read-only GET result is recorded
as owner-reported evidence and does not qualify provider stop/write privileges.
