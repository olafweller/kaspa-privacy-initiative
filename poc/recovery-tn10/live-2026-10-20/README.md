# Actual TN10 recovery and full withdrawal — 2026-10-20

The fresh trial completed on TN10: an accepted 10 test-KAS deposit, an
owner-local private credit/transfer, recovery after the original application
controller became unavailable, Bob's 4-KAS withdrawal, and Alice's final 6-KAS
withdrawal. Six new outer receipts were independently verified on B and all six
settlements were accepted by TN10. Both native payouts were subsequently found
as unspent outputs belonging to the owner-held recipient keys.

This closes this bounded live recovery/full-withdrawal milestone. It is testnet
research evidence, not a production-security or anonymity claim.

## Retained evidence and reproduction

[result.json](evidence/result.json) records the frozen identities, receipt hashes,
accepted transaction/block IDs, recovery observations, native UTXO readback,
resource measurements, preservation, stop/deletion and estimated costs.
[manifest.json](evidence/manifest.json) binds every published evidence file.
The six original targets, actual receipt bytes and B CPU verification reports
are included. Targets were fixed on trusted B before each upload; expectations
were not obtained from the returned GPU metadata.
Their pre-proof `proofStarted`/`networkAcceptance` flags remain unchanged as
historical target descriptors; actual completion/acceptance is recorded in the
separate result. Cloud subsequently reran all six real CPU verifications and 90
mutations and obtained reports identical to B's retained results.

Run the standalone CPU check from a checkout:

```bash
python3 poc/recovery-tn10/live-2026-10-20/check_evidence.py
```

It restores the existing hash-pinned public verifier package and verifies all six
actual seals, exact 352-byte journals, fixed guest/Join identities, absence of
development mode/unresolved assumptions, and 15 cryptographic mutations per
receipt. It does not prove, access wallets, call a provider, fund or broadcast.
Native acceptance and recovery observations are retained historical evidence;
this CPU check does not independently select the current canonical TN10 chain.

Owner-specific receive files, public-input bodies, full native captures, local
Mint instructions, wallet backups and keys are not published here. Complete
public history and inputs remain preserved on the external B host, with hashes
in the retained records. The final GPU archive is 6,830,556 bytes, SHA256
`e15220bd18bca949754888457a5ccdc2790df52ae1c556caaa33f4e2006eec23`.

## Actual cycle and recovery

The reviewed preparation was PR #60, head
`f02e98d5918af3f53985b77809c7e930d888231f`, merged as
`3bd363a85169f887f9ad1f155c63c5e9da34447c`. The immutable CUDA image remained
`ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:cd42221a752ac0469e2b78254ab48aa8da0dedd8b491355e4a184cacd142f468`.
Guest, wallet circuit/VK, parameters, Join identity and native policies were
unchanged during execution. The historical PR54 pool was not spent by this run.

The original controller consisted of real finite application CLI jobs on TN10,
not an always-on application daemon. After the accepted credit-transfer
settlement, their completion/PIDs were recorded and the original entry point was
made non-executable; an actual execution attempt returned permission denied.
The original cache was retained. No shared native node, gateway, history service,
B guard or prover was stopped as part of this interruption.

B reconstructed the exact accepted state in a fresh directory from the first
two public inputs. The replay process had no network, could not access the
materialized public state-cache directory, and had no original-controller cache
on its machine. Its entire serialized state matched the accepted checkpoint.
B then performed the remaining application work.

The owner separately reported that Mint restored **both** wallets afresh from
T7, reconstructed the public history, and found Bob's single 4-KAS note. Before
Alice's exit, Mint reconstructed all four available batch inputs and found her
single 6-KAS note. Each wallet proof was produced locally with the restored
wallet. Cloud did not inspect the Mint filesystem or secrets; these local
restore/scan observations are explicitly owner-reported. Returned public
operations were then verified through the actual outer-proof/native route.

## Native money movement and final state

| Item | Actual outcome |
| --- | --- |
| Bob | 400,000,000 sompi principal + 50,000,000 permission-rent refund |
| Alice | 600,000,000 sompi principal + 50,000,000 permission-rent refund |
| Remaining user reserve/private liability | 0 / 0 |
| Pending deposits/unpaid exits/permission rent | 0 / 0 / 0 |
| Separate state rent | 100,000,000 sompi remains in the state covenant |

The two permission rents were sponsor-funded, separate from the 10-KAS user
principal. A fresh native UTXO query confirmed both recipient outputs, both spent
permissions, the spent initial/remaining reserve, all spent prior state outputs
and the final 1-KAS state output. Actual signed transactions passed the pinned
native script engine and size/mass/compute/fee checks before broadcast; the
qualification metrics are retained alongside the accepted transaction IDs.
Their offline `networkAcceptance: false` fields are original build-time
descriptors; actual acceptance is recorded separately against those exact IDs.

Each receipt settlement was estimated at 224,096–224,240 serialized bytes.
At the selected 100 sompi/priority-gram rate, the six settlement transactions
cost 285,598,400 sompi (2.855984 test-KAS) in native fees. Other trial transactions
and funding cost another 10,230,800 sompi. These are sponsor-paid test-KAS fees,
separate from both user principal and the GPU's USD rental estimate. This small
trial does not establish production fees, amortization or throughput.

Final native settlement:
`30d30f7ba9cb6dc02306dec2b463f7b5fd1991c309dfbe053e99c8fe9ca4e1f9`.
Final state root:
`ba8603dcb5569a782a6d471ac197f1ce2592dd734e1718ff4606640755d95f3f`.

## GPU execution and operational closure

| Batch | User cycles | Segments | Segment po2 | Producer process seconds |
| --- | ---: | ---: | ---: | ---: |
| Deposit | 1,883,109 | 93 | 16 | 60.68 |
| Credit-transfer | 97,957,741 | 101 | 20 | 172.85 |
| Bob exit | 47,613,695 | 50 | 20 | 85.88 |
| Bob reconciliation | 3,178,895 | 147 | 16 | 97.30 |
| Alice exit | 47,386,717 | 50 | 20 | 91.47 |
| Alice reconciliation | 3,155,174 | 146 | 16 | 111.16 |

All batches used the same one L40S (driver 595.91.07, compute capability 8.9),
four pinned CPU cores/compute threads and the declared 160M-cycle bound. Raw
samples were rechecked against their process groups and GPU identity: every
batch had matching active CUDA processes. Sampled peaks were approximately
730 MiB summed process RSS and 13.38 GiB GPU process memory. Samples may miss
instantaneous peaks; summed RSS can double-count shared memory.

The six producer process groups took 619.34 seconds in total. The shared run,
including intervening wallet/chain/management waits, took approximately
3,440.54 seconds to the last proof process completion, within the original
3,600-second deadline. This is one attempt, not an automatic retry. The last
private-controller admission threshold used a declared minimum 240 seconds,
based on the measured 97.3-second preceding reconciliation plus margin; the
immutable image's original hard deadline and proof statement were unchanged.
Final native checkpoint validation, preservation and deletion are separate
postprocessing, not additional proving time.

B durably preserved and revalidated the final archive and 164 public history
files before deletion. The independent guard stopped the Pod and separately
read back provider `EXITED`; a subsequent API observation confirmed it. Deletion
then returned 404 on GET and absence from the Pod list. The 90-GB container and
10-GB local volume were removed; no network volume was created. The guard ended
disabled/inactive. Original entry-point permissions were restored without
restarting original jobs; the shared TN10 services retained their original PIDs.

Approximate compute rental was 3,549.18 seconds at USD1.09/hour. Compute plus
conservative active/stopped storage estimates total **USD1.08854**. This is a
rate/timestamp estimate, not an itemized invoice; tax/top-ups are excluded.
The original 7,200-second rental limit and USD5 planning allowance were retained.

## Scope and remaining limits

- Both logical users are managed by the same owner; independent human custody
  was not tested. B-root remains a trusted administration role.
- Recovery used retained complete public history and independently checked
  checkpoints while the native node/gateway/history/prover remained available.
  This does not establish indefinite recovery with missing data or an expired
  lane, or operation without an available replacement prover.
- This was one initial reserve, two notes and sequential exits. General reserve
  selection/combining, concurrent exits and a production operator network remain
  outside the result.
- Live wallet publications were credit, transfer, Bob exit and Alice exit. No
  extra intentionally invalid live wallet operation was broadcast. The 90
  receipt mutations are cryptographic negative controls, not live invalid-wallet
  or network-reorg trials. Existing local native-policy regressions remain
  separate historical evidence.
- Independent verification used separate trusted CPU processes with the same
  reviewed implementation, not two independently developed verifiers. This is
  not a mainnet, production cryptography, anonymity-set or mobile-wallet result.
