# Completed actual TN10 private/native lifecycle — 2026-10-19

The released test completed **deposit → credit → rejected private transfer → valid
private transfer → Bob's exit → native payout → reconciliation** on actual TN10.
Four fresh outer receipts were verified independently on B and Cloud, and all
four corresponding native settlements were accepted by the running native node.
These are actual-chain inputs and proofs, distinct from PR51's local fixtures.

Bob's confirmed native output is **450,000,000 sompi**: 4 test-KAS principal plus
0.5 test-KAS permission-rent refund. The remaining native delegate reserve is
600,000,000 sompi, matching 600,000,000 sompi private liability. No pending deposit,
unpaid exit or unspent permission remains. The separate state covenant retains
100,000,000 sompi. The final physical outputs and historical accepted checkpoint
are retained in [the physical audit](evidence/native/final-physical.json).

## Results and limits

| Actual batch | User cycles | Proof producer seconds | Whole phase seconds |
| --- | ---: | ---: | ---: |
| Deposit | 1,381,449 | 61.94 | 62.74 |
| Credit, invalid transfer, valid transfer | 142,580,898 | 334.95 | 335.79 |
| Exit | 47,095,440 | 107.73 | 108.44 |
| Native payout reconciliation | 3,278,171 | 126.59 | 127.45 |

The shared elapsed interval, including chain waits and management, was about
**2,038.52 seconds (33m 58.52s)**, within the original 3,600-second limit.
The four active phases total 634.42 seconds. Every batch stayed below its
160,000,000-user-cycle limit. Each phase includes a separate in-container CPU
verification and matching-process CUDA measurements. B and Cloud then independently
verified the returned receipt bytes against their already frozen expectations.
The implementations are shared; they are not independently developed verifiers.

All four receipts passed the existing fifteen cryptographic negatives each:
eleven journal-field mutations, wrong expected image, corrupted seal, malformed
control inclusion and wrong expected control identity. Actual TN10 also rejected
three fully signed payout variants: underpayment, reserve diversion and wrong
recipient. Their sponsor signatures passed the local native engine. A distinct
payout replay with a fresh sponsor input was rejected as an orphan because the
known permission and reserve inputs had already been spent. Resource errors were
not counted as successful negative controls.

The signed transactions, fresh UTXO observations, native engine mass/fee/script
checks and actual native rejection records are in [native evidence](evidence/native).
The final state root is
`4c050dfe1e822f6db96b3237f0b6ba5d8ecc6d037c90ef26b22d5299afc761e8`.
The final settlement is
`236999c339905894da879ab78061e21c202f62fab6f42d8b3dd9314275d4b9b5`;
the payout is `f26e03cade619c68d856dd429733f903add560495a547d0ee083aed34c4c6652`.

## GPU and operational completion

One Secure Cloud L40S was allocated: `jl3e5fcfy32m40`, at USD1.09/hour,
with a 90GB container disk and 10GB `/workspace`. The existing immutable image was
used without rebuilding:

`ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:fa4f72f0e060325a951eac33ea01ef00d3593ffe68531d69cf6a8b09daf41aa1`

The service scope was `STAGED_TN10_PRIVATE_LIFECYCLE_V1`. Its fresh ledger, fixed
policy/trial, provider image/resources and independent guard heartbeat were checked
before the first submission. Each subsequent target was committed, retained
independently on B and approved by hash before upload. No proof was retried and
neither time limit was extended.

The classifier image is
`794cfff4cfa509799ec1f6750678d3fe4bc8623522aa647cc65e6b53955c4bc9`;
the fixed join control is
`7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e`.
The CPU host SHA256 remains
`6b2fa5c0b239854c1c71a4e7d0b7d8ede724209090abda36674bd61055b9e996`;
the CUDA prover remains
`4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb`.
The guest, circuit, VK, public proving parameters, join identity and published
image were unchanged. Per-batch public inputs/journals were new and fixed before
proving. The old preflight/trial authorization booleans remain historical snapshots;
[the later owner release](evidence/release.json) authorized this execution.

The real GPU was an L40S, compute capability 8.9, driver **595.91.07**.
The sampled peak summed process RAM was 793,489,408 bytes and peak matching-process
VRAM was 13,706 MiB. These are sampled measurements, not guaranteed maxima.
Each proof phase used four pinned CPU cores and four compute threads.

The independent B guard stopped the Pod after its verified terminal backup.
Provider `EXITED` was read back. B and Cloud retained and revalidated all four
receipts and the complete GPU archive before deletion. Deletion returned a
subsequent GET404 and absence from the Pod list. Both the 90GB container and 10GB
local volume were removed; no network volume was created. The guard is now
inactive/disabled. Existing B services, old test data, SSH keys and its root-only
account environment file were retained.

Creation was 09:01:03.132 UTC; the guard's confirmed-stop observation was
09:37:12.028 UTC, about 36m 8.90s. This is within 7,200 seconds from actual creation.
The rate/timestamp estimate is **USD0.6654 including storage**, approximately
USD0.67. It is not a final provider invoice. See
[cost calculation](evidence/gpu/cost-estimate.json),
[stop](evidence/gpu/provider-stop-readback.json) and
[deletion](evidence/gpu/provider-deletion.json).

## Native accounting

The fresh sponsor received 1,650,000,000 sompi: principal1,000M, state rent100M,
permission rent50M and fee planning500M. The thirteen accepted trial transactions
spent **199,627,400 sompi in native fees**, below that planning allowance. The
separate source funding transaction cost 703,600 sompi. Rejected transactions
consumed no inputs or fees. Principal, state rent, permission rent and fees were
kept separate throughout. All amounts are integer sompi, and all funds are test KAS.

The exact program's native builder executed every input of the fully signed
positive transactions and checked compute budgets, storage/compute/transient mass
and quoted fees. Before submission the controller refreshed actual UTXOs and
selected-chain context. Receipt endpoints were not rewritten during proof waits.
The actual node's selected-chain acceptance, followed by full capture validation
and current unspent-output checks, completes the native evidence.

## Read-only transport corrections during the run

The native VCC-v2 API caps each response by its batch size. After proof A's native
settlement, the original short capture could not reach its fixed endpoint in one
response. [The paginated collector](capture.mjs) follows successive native pages,
retains every original response, preserves exact u64 values, rejects removed,
empty, duplicate and mismatched pages, and independently rereads the whole interval.
The existing hash-pinned native validator then validates the assembled full body
capture. No checkpoint interval, commitment or operation was omitted or replaced.
The four proven intervals contain 833, 4,863, 4,272 and 2,519 native selected blocks.

Original page bytes and RPC mutation/confirmation transcripts were also streamed
directly from TN10 to B through the existing pinned SSH wrapper. The 138-file,
326,840,320-byte archive has SHA256
`ec336c9b417dcc57347318bb5be41ef76141f2843a0d690e1ff7b71fb0f18a0e`;
its [external preservation record](evidence/native/b-original-native-backup.json)
and [member manifest](evidence/native/original-pages-backup-manifest.json) are retained.
The public compressed assembled captures are bound to the frozen target hashes
in [capture identities](evidence/native/capture-identities.json).

Other finite controller incidents are preserved in the recorded source/history:
- An activation RPC-log filename collided with its earlier query log **after the
  transaction was accepted**. Its existing confirmation was read back; it was not
  resubmitted. Later logs include the action name.
- Large terminal transfers exceeded the command-size boundary. Public transfers
  were changed to bounded chunks or checked public Git downloads.
- A public package download initially lacked its destination directory. Allocation
  followed before that staging copy was corrected. No proof started then: the
  exact A bundle was subsequently SHA-checked and unpacked on B before the fresh
  ledger/guard start checks. There was one Pod and one proof attempt per batch.
- Transient read-only HTTPS failures recovered without re-proving. A stale heartbeat
  observation was followed by an explicitly confirmed fresh heartbeat before
  advancing. The independent absolute stop timer remained active.

These were controller/collection corrections. The proof relation, native scripts,
prover image and experimental limits were not changed.

## Reverification and retained evidence

[The result](evidence/result.json) separates cryptographic, CUDA, native and
operational results. [The evidence manifest](evidence/manifest.json) binds retained
bytes. The GPU archive is independently checked against targets stored before each
submission, rather than against GPU-returned expectations. Trusted CPU executables
are restored from the already retained, hash-bound public package.

```sh
node poc/tn10-live/capture.test.mjs
python3 poc/tn10-live/check_evidence.py
```

These commands perform CPU receipt verification, all sixty cryptographic negatives,
full-journal continuity, exact capture-byte hashes, CUDA sample consistency and
retained native/cleanup record checks. They do not make RPC calls, sign transactions,
prove, rent or mutate a provider. Native acceptance records describe the historical
live execution; this offline checker does not independently replay the entire
consensus engine. The original pinned native validator was actually run on every
capture used for initialization, freezing and accepted checkpoints during execution.

`operator/` contains **recorded one-use drivers and gateway source history**, not
an instruction to rerun this already used trial. The large artifacts remain on B
at `/var/lib/kpi-cuda-guard/tn10-live-20261019`; actual source pages and transcripts
also remain on TN10. Wallet backups and native signing keys are excluded from
these archives and Git. Trusted signing/wallet programs used their own existing
role files locally; no private-key value was printed or copied. The account key
remained on B. Cloud management used the existing TN10 → B route, without new
Cloud domains or secrets. B's guard had no runtime dependency on that route.

## Conclusion and remaining limitations

This demonstrates one complete actual TN10 private/native lifecycle: authenticated
L1 ordering, private wallet proofs, rejected invalid processing, real outer proofs,
accepted native settlements, authorized native payout and reconciled backing.
It closes the gap between the fixed local rehearsal and a real funded testnet run.

The test still uses one owner-operated native node and trusted operator/root roles.
**The existing operator controls logical Bob**, including his wallet and native
recipient; independent user custody or protection from a malicious administrator
is not demonstrated. Separate B/Cloud processes share the reviewed verifier.
The circuit/setup are experimental, the tree is small, and only one pending exit
and a selected reserve greater than the withdrawal are supported. Reserve
combination, concurrent exits and zero reserve change remain outside scope.
This does not establish production privacy, scale, availability, mobile wallet
performance or economic fees for a deployed service. No mainnet work occurred.
