# Second pass — fixed six-receipt producer and orchestration

- Inflation/withdrawal: no guest, wallet proof, native script or accounting
  change. The producer/verifier compiles the reviewed exact expectations; the
  issued permission and payout must retain the corrected captured transaction
  IDs. Genuine permission issuance requires a new verified exit receipt first.
  Synthetic native startup tests are not evidence of that positive receipt path.
- Double spending/state binding: PR56's 13 transactions and 22 unique inputs
  remain unchanged. Fixed six-case order, full journal/root/tip/covenant/lane
  continuity and per-case segment profiles cannot be chosen by the remote client.
  No old receipt, fake receipt, dev mode, unresolved assumption or different
  decoded Join identity can satisfy the reused strict receipt verifier.
- Untrusted prover: candidates are saved before checks. Each receipt is checked
  in a separate CPU process and independently again on B using trusted local
  executables. Downloaded executables and metadata do not set expectations.
  Fifteen real cryptographic mutations are required per genuine receipt;
  native attacks must fail semantically, never via resource errors. Partial and
  candidate-only results remain explicitly distinct from six final receipts.
- Native context availability: embedding the reviewed public corpus avoids
  accidental dependence on the build machine's old PR55 filesystem. Rust tests
  compare it with the original generator and both native contexts run inside
  the CPU-smoked container. Real new-receipt issuance remains pending. These are
  synthetic UTXOs/anchors, not complete signed canonical TN10 validation.
- Time/process failure: all fourteen sequential stages inherit one externally
  watched process group. A controller death does not remove the GNU timeout.
  Tests use real descendants and nonrecursive directory creation; prior results
  survive later failure. B's unchanged guard remains the absolute lease stop and
  backup authority without Cloud/gateway/laptop runtime dependencies. No retries.
- Privacy/operator role: only fixed public operations, templates and code enter
  this package; no wallet backup, native user key, setup parameters or RunPod
  account key. Existing B-root administration remains trusted. Service secrets
  do not enter prover or CPU verifier child environments. Correlation, independent
  custody, public-state freshness and shutdown recovery are not solved here.
- Reorg/dependency loss: this fixed local workload cannot be relabelled as actual
  chain inputs. A new funded instance and accepted captures require fresh proofs.
  Missing history/prover reduces liveness rather than authorizing value release.
  No upgrade, admin withdrawal or modification of the old PR54 reserve is added.

Reuse: PR56 relation/fixtures/native engine/receipt helpers and prior qualified
RISC Zero producer APIs, four-batch worker, watchdog, service and archive checks.
The reviewed source decisions in [PR56](../recovery-native/SOURCES.md) remain
applicable; no new note/nullifier/circuit/curve or privacy subsystem is designed.
The operational additions implement ADR-0017's already selected bounded proof
step. Native public contexts are compiled instead of read from build paths.
The same implementation is reused on GPU/CPU/B, not independently implemented.

## Focused B result-archive repair

The first B extraction route called a generic archive helper whose visible-file
limits did not cover hidden PAX/GNU metadata processed by tarfile. The existing
staged helper now bounds both compressed reads and total gzip expansion before
tar parsing. A matching digest cannot substitute for this resource bound.
Tests cover a one-byte normal file with 64 KiB metadata, parser-not-called
assertions through both the function and real CLI, and preservation of path,
regular-file, duplicate, count and file/content limits. A fresh isolated B-client
installation includes the pinned helper. The change is limited to B extraction
and qualification: no guest, proof/native verifier or GPU image change is made.
