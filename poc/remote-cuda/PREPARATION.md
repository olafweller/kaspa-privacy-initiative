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
- Thirteen Python tests cover lease cost/duration/host constraints, archive traversal
  and duplicate entries, Pod-bound one-time configuration, HTTP authentication,
  guard requirement, duplicate starts, disconnect/restart behavior, independent
  mocked stop/read-back, false stop acknowledgment and real process-group timeout
  with credential stripping, and durable terminal backup before stop after
  controller loss. Empty provider stop responses and already-exited Pods are
  covered as well. The rental-stop timer is separately tested while the simulated
  GPU request remains blocked. HTTP/provider simulation is not rental evidence.
- The review's pre-existing truncated-archive case is reproduced and repaired.
  Existing copies require both size and SHA-256 checks. New copies use a
  same-filesystem temporary file, file fsync, atomic replacement, saved-byte
  verification and directory fsync before completion metadata. A stale completion
  marker is discarded before repair; restart rechecks the copy and preserves the
  retrieval grace. Same-size corruption and failed rename are covered, as is an
  absolute rental stop despite repeated backup failures. These tests simulate
  provider responses; no actual VPS restart or provider stop is claimed.
- The public source archive is checked against SHA-256
  `01107d542cb0c333ec509362de59bbb6c402a4d243c13f13954f485e3c256cfc` and
  all 107 original manifest entries before preparing the small fixed workload.
- Repository fast checks pass: Markdown paths, Python syntax, the two existing
  phase-control tests, thirteen new remote-control tests, 81 script tests (two
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

## CUDA build and CPU-only container validation

The image was successfully built with upstream source unchanged, Rust 1.89.0,
Clang 18.1.3, NVCC 12.8.93, `sm_89` and `cuda,disable-dev-mode`. The build recipe
is recorded at `40198bcc556bca3761499ed35c766885a611c355`. Four build workers
were used; this is separate from the later diagnostic process limits. The
successful builder step took 1,160.6 seconds, including its setup; Cargo reports
17 minutes 52 seconds. No GPU was present or used.

- Local image ID:
  `sha256:8d0c70c2e5fdfd3c571a5bb6a96de821b58b3a88333fa5401e750623b82fa712`.
- Image size: 525,986,230 bytes. This is a local image identity, **not** a
  published registry digest or an actual rental pull measurement.
- CUDA prover binary SHA-256:
  `5ff8e229363d67a473af217b94d5c393d65b21edfbcd7c5a924da0cc0e6634ac`.
- The image build actually ran the independent five-receipt CPU comparison
  inside the runtime image; it passed. CPU baseline receipts are not copied into
  the final service image.
- `check_image.py` passed actual image startup, Python compilation, source and
  binary hash checks, HTTP authentication, Pod/lease binding and refusal to
  start proof work without an independent guard. No proof job was started.
- All non-driver shared libraries resolve. `libcuda.so.1` is absent on this
  CPU-only host and must be supplied by the real NVIDIA container runtime.
  Accordingly, `proverVersion` is null: the CUDA executable could not be launched
  locally. Source SDK version 3.0.3 is recorded by the successful build. No driver
  stub or CPU fallback was substituted; GPU execution remains unqualified.

See `evidence/container-smoke.json`, `cuda-build.json`, `cuda-build.log` and
`build-packages.txt`. The successful build follows two preparation findings:
the initial GCC build was abandoned after about 40 minutes with a generated
CPU kernel still compiling; upstream explicitly selects Clang. The Clang build
with Rust 1.91 then hit two upstream warnings treated as errors. Using the tag's
declared Rust 1.89 resolved them while preserving the upstream warning policy.
These were compiler/build attempts, not GPU proof attempts or cryptographic
rejections. The independent repository CPU verifier remains on Rust 1.91.

The public package and image can be regenerated with [START.md](START.md).
The image still requires reviewed registry publication and a pull check before
rental. BuildKit's source/target caches and the local image are preparation
artifacts, not a connection to a GPU provider.

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
