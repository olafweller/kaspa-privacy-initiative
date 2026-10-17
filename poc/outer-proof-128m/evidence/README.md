# Approved attempt evidence

The [summary and manifest](comparison.json) and
[public artifact archive](local-outer-proof-artifacts.tar.gz) retain the one
approved outer-proof attempt, all 24 execution controls and the concrete stop.

- Archive: **1,011,185 bytes**, **254** regular members, all read back and hashed.
- SHA-256: `eb39eb23d6dd7da2f55a45711fbcac2acaad844dee94e30e2a91d6f6705a1710`.
- Source snapshot: `7ee1b69` (full revision in the summary).
- Executed host source: `ccd3d51491ca62d3fcebee5cb51c2a48b2b7debd`.
- Predeclared plan: `3fa6a56e0966a40d28cdeb3cedcc2f9af217231b`.
- Unchanged expected image: `397bcdca688462b9573a4b55e3516e1a2511140512c53337eb54da0849a93716`.

Contents include independent expectations, every full/narrow case journal/report
and resource log, qualification summary, proof-job stdout/stderr/sampled memory,
profile/prover-start checkpoints, CPU counters and OS high-water snapshots,
hardware/toolchain/source identities, unchanged program/proofs/operations/keys,
and build/test logs. No proving parameters, wallet secrets or credentials are
included. Old PR37/PR38 archive hashes are retained and unchanged.

The main execution again uses 117,473,222 user cycles / 121 executed segments.
The proof job hits its 3,600-second wall limit and returns **no receipt**. Source
entry points for real succinct receipt production and separate cryptographic
verification are present, but no verifier run on an outer receipt is claimed.
The last confirmed checkpoint is the completed main execution profile; internal
proof-stage completion counts are unavailable. See [results](../RESULTS.md).

[collect_evidence.py](../collect_evidence.py) explicitly whitelists public files
and reads every archived member back against its hash/size. Extract only checked
regular paths. In the pinned build environment, the reused public keys/fixtures
and unchanged program suffice to reproduce qualification through the documented
commands; no large wallet proving key or new setup is needed.

The inherited 12 GiB address-space cap and sampled 12 GiB group-RSS threshold
are distinct from the environment's 16 GiB cgroup cap. Sampled group RSS peaks
at 9.19 GiB. Parent `wait4` accounting after a hard kill omits its unreaped prover;
the independent cumulative `/proc` samples instead observe about 3.92 CPU-hours.
Both raw forms and their limitations are preserved. Environment-wide memory
pressure events are recorded with zero OOM/OOM-kill events. This does not prove
a pure CPU bottleneck or an eventual total proof cost.

All work is local and unfunded. No full private-note relation, native settlement,
new TN10 transaction, independent audit or production feasibility is established.
