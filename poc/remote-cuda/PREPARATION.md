# Preparation evidence — 2026-10-17

This records preparation, not a GPU experiment. PR #40 is merged at
`e7ea15e8009b8f6ef3aaa34b3cec17fbfc3eb5cd`.

## Checked locally

- New independent CPU comparison actually verifies PR #40's retained five
  receipts and checks seal/claim mutation rejection. A genuinely sealed but
  substituted segment/lift, with adjusted unsigned metadata, is rejected against
  the pinned CPU expectations. Altering a join seal is rejected as well.
  An explicit incomplete-run command verifies a single retained segment and
  reports one receipt, not five; the strict command rejects that incomplete
  set, and mutating the single seal is rejected. Signal/timeout failures cannot
  count as rejection evidence.
- Nine Python tests cover lease cost/duration/host constraints, archive traversal
  and duplicate entries, Pod-bound one-time configuration, HTTP authentication,
  guard requirement, duplicate starts, disconnect/restart behavior, independent
  mocked stop/read-back, false stop acknowledgment and real process-group timeout
  with credential stripping, and durable terminal backup before stop after
  controller loss. HTTP/provider simulation is not rental evidence.
- The public source archive is checked against SHA-256
  `01107d542cb0c333ec509362de59bbb6c402a4d243c13f13954f485e3c256cfc` and
  all 107 original manifest entries before preparing the small fixed workload.
- Repository fast checks pass: Markdown paths, Python syntax, the two existing
  phase-control tests, nine new remote-control tests, 81 script tests (two
  optional cases skipped), 13 Node tests and 24 private-payment model tests.
  Locked release takeover tests pass (13 tests), as does Rust formatting.

The retained public bundle is `evidence/public-package.tar.gz`, 9,288,223 bytes,
SHA-256 `323efa23bf042895ddac7b2531a7628c72664849aec26c3f528cadb93d964805`.
It records host-source revision `b5be7e8083f765124042e8c45f58ac2fd363c66d` and
CPU verifier SHA-256
`ee60c3fb5ff9fc6c125ad41019e74188d68814f1b1a2fc6bc101ddab184202a7`.
Input and claim identities remain those of PR #40. The evidence manifest lists
the retained files and their hashes. Verification of real CPU receipts does not
claim that simulated GPU/controller transport produced those receipts.

Build result and exact generated artifact identities are recorded in this file
and `evidence/` once local image validation completes. The public package can be
regenerated with the commands in [START.md](START.md); generated `.local` output
is not a remotely published container image.

## Current Cloud and independent host

The managed environment reports current observations, enforced restricted HTTP
policy, package registry presets, one configured TN10 host and ready
`TN10_RPC_TOKEN` for that host. It has no RunPod destination/service token,
provider account identity or GPU device. None was added for this preparation.
The official environment skill documents proxy credential injection; use the
configured scoped variable normally even if its value is a proxy placeholder.

The owner identified the former A1 role-B Linux VPS as the proposed independent
guard host. Its availability was reported by the owner, not established through
a new login or installation. This preparation leaves it unchanged.

## Not established

No paid resource, provider key, live RunPod API/proxy request, GPU driver test,
CUDA kernel execution, GPU speedup, actual VRAM peak, provider stop/persistence
test or bill exists for this package. No full classifier receipt was attempted.
The image still needs publication by digest and a pull check before rental.
Connection/credential checks, independent guard installation and live provider
schema/read-back remain deployment gates. Research receipts alone do not
establish a financial privacy protocol or production readiness.
