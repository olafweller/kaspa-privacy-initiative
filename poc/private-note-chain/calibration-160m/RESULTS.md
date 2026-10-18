# Single approved 160M execution calibration — 2026-10-18

**The frozen PR45 valid-invalid-valid scenario completes at 139,763,284 user
cycles. Its entire 352-byte aggregate journal equals the original reference.**
One execution-only run was performed; the other 21 guest scenarios were not
repeated. No setup, wallet proof or guest was regenerated/modified. No outer
receipt, GPU rental, provider action or TN10 broadcast occurred.

| Measurement | Observed result |
|---|---:|
| Approved cycle / whole-process-group wall limit | 160,000,000 / 900s |
| Completed user cycles | **139,763,284** |
| Segments | **143** |
| Every segment po2 / padded cycle slots | **20 / 1,048,576** |
| Total padded trace cycle slots | **149,946,368** |
| Executor wall time | **3.535s** |
| Whole measured process-group job | **3.799s** |
| Sampled peak process-group RSS | **78,643,200 bytes (75 MiB)** |
| wait4 maximum RSS | **120,324,096 bytes (114.75 MiB)** |
| CPU affinity / compute threads | **0–3 / 4** |
| Original environment memory limit / RLIMIT_AS | **16 GiB / unlimited** |

Padded trace size is reported in cycle slots, computed as the sum of `2^po2`
for all segments. It is not a measurement of serialized trace bytes, proving
memory, GPU VRAM or proof time. RSS sampling can miss short peaks; wait4 includes
process startup/fork effects and is not summed simultaneous process-group RSS.
The actual raw resources/segment arrays are retained separately.

This run starts **after synthetic deposit registration**, then processes credit
of Alice's 10 note, a canonical but cryptographically false transfer, and the
valid Bob4/change6 transfer. Expected outcomes are `[0,1,0]`. The fixed guest
computes those outcomes; the native 352-byte ABI commits resulting state and
complete lane endpoint, not a separate verdict array. The entire journal matches
byte-for-byte. Bob's exit, original native funding acceptance and a native
payout are outside this scenario; permission and deposit hash slots are zero.

The previous stage estimate is now replaced by a complete measurement. The
third pairing finishes at 139,172,006 cycles; state/journal work brings the total
to 139,763,284. The old 128M stop remains an actual failed run and is not relabelled
as success. No further cycle increase or repeated attempt was needed.

## Identity and validation

Guest image remains
`20d8431e18f42c6e337ab726f166914516e3ebcd70577e67d49e687737901f8b`;
VK remains `d3c179aae5c2c6c013b1de1da5ad4412e4b2c8bae7288c0b9d85e0c986b5a3ec`.
Expected/actual journal SHA256 is
`88ba872f3aca413a41b83e91ba40c4eb0b27eb9db31150b7af3d133bb6ccf22e`.

All original 174 evidence hashes and selected Git blobs were checked unchanged
before execution. The host command/runner flag explicitly select only this
approved calibration, leaving original `profile` at 128M. Updated executable,
host source and runner hashes were frozen before starting. The two focused host
unit tests pass: explicit budget selection and rejection of resource/IPC errors
as authentication evidence. No expensive unrelated tests were repeated locally.

See [frozen artifacts](evidence/frozen-artifacts.json),
[updated host identity](evidence/host-identity.json),
[run report](evidence/report.json), [process resources](evidence/valid-invalid-valid.resources.json),
[stage log](evidence/valid-invalid-valid.stdout.log),
[exact journal](evidence/journal.bin) and [artifact manifest](evidence/manifest.json).

## Parameter-integrity wording

The earlier restore process records the full public-parameter SHA256 and
**enforces the independently expected VK** after checked parameter decoding.
It does not yet compare the complete parameter file with an independently
expected file hash. Existing observations remain unchanged; no new parameter
loader or distribution security is claimed. A future distributed parameter
loader must enforce a trusted whole-file hash before use.

## Next task

The completed execution supports preparing one real Succinct proof for this
exact monolithic claim, followed by separate CPU verification and native local
script checks with the genuine receipt. [NEXT-PROOF.md](../NEXT-PROOF.md) and
[next-proof-target.json](next-proof-target.json) fix its identities and boundaries.
They do not authorize rental/proving, close native deposit/exit/payout gates or
supply separate transaction/batch/aggregate proof identities.
