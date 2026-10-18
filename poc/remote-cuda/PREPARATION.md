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
The original image above is a local preparation build. The separately rebuilt
and published image is identified below. BuildKit's source/target caches and the
local image are preparation artifacts, not a connection to a GPU provider.

## Current Cloud and independent host

The managed environment reports current observations, enforced restricted HTTP
policy, package registry presets, one configured TN10 host and ready
`TN10_RPC_TOKEN` for that host. It has no RunPod destination/service token,
provider account identity or GPU device. None was added for this preparation.
The official environment skill documents proxy credential injection; use the
configured scoped variable normally even if its value is a proxy placeholder.

On 2026-10-17 the former role-B VPS was only an owner-proposed candidate.
On 2026-10-18 its separate identity, Cloud management route, installation and
focused host qualifications were established as recorded below.

After PR #41 merged at `c2037893936508d6d61dcb9ee78aea6ba4515aab`, the
explicit `cuda-qualification-20261017-pr41` tag started
[publication run 39067028926](https://github.com/olafweller/kaspa-privacy-initiative/actions/runs/39067028926).
That first run stopped before the CUDA build because the clean runner lacked
the public package output's parent directory. The CPU build and actual five-seal
comparison had passed. `package.py` now creates missing parent directories while
still refusing to overwrite an existing output directory. Its full local run
against a fresh nested output succeeded. The initial tag is retained unchanged;
publication must use a new explicit tag for this correction. Starting a build is
not evidence of publication by itself.

## Published image and independent Cloud pull

The replacement [run 39067230794](https://github.com/olafweller/kaspa-privacy-initiative/actions/runs/39067230794)
completed successfully from revision `81f2b90c7bc3aaddd44fecda222bb5d6de731616`,
tagged `cuda-qualification-20261017-pr41-r2`. The immutable deployment reference is:

```text
ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:df8e68263f85a8d89a8fb2365d78c795b0010d35cb35d6ddc1f740d3020b7743
```

This rebuild preserves the pinned RISC Zero source/configuration, three service
source hashes, classifier image, fixture bytes and expected CPU claims. Its
actual prover binary SHA-256 is
`4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb`,
and its image ID is
`sha256:416b30c4f57156016f46568a0ebcb2f73a2fc4af30b1868131a3511fce9c9912`.
These are the published build's identities, distinct from the earlier local
build. The builder step took 1,086.2 seconds; Cargo reports 17 minutes 15 seconds.

The publication job pulled this exact digest back and repeated the CPU-only
container checks. Cloud independently confirmed anonymous registry access and
the returned digest, downloaded the image and repeated those checks. Source and
binary hashes, authentication, lease binding, unguarded-start refusal and
non-driver libraries passed. The real five retained CPU receipts were verified
during packaging and image construction. See `evidence/publication.json`,
`published-image-smoke.json`, `cloud-registry-access.json` and
`cloud-published-image-smoke.json`. `published-policy-comparison.json` also
checks the image's actual input files against the original package's hashes
and confirms the independently expected program and claims are unchanged.
These are build/transport/CPU results;
`gpuExecutionQualified` remains false and no proof job was started.

## Guard source versus published image

The operator's B-side application-header fix is now preserved in Git:
`common.py` has SHA-256
`5ed5815ae1177f5915852477d270110f3768bd6b61ff5ebd5833b62526e549c3`.
Only `User-Agent: kpi-remote-cuda/1.0` and `Accept: application/json` were added
to requests. TLS-only URLs, Authorization, Content-Type, redirect refusal,
timeouts and response limits are unchanged. B's runtime was already patched;
Codex checked its bytes/hash and did not overwrite it or open the credential
file. The original B backup remains available.

The published image is an **unchanged, separately established artefact** from
`81f2b90c7bc3aaddd44fecda222bb5d6de731616`. Its `common.py` correctly retains
`841a0670ec027616cab4d6c0c9cd2a7ce842322489319dfde5062b6638da0a83`.
Its service imports only `atomic`/`lease_check`, and its worker imports only
`atomic`/`sha`; neither uses `request`/`json_request` to access RunPod. The actual
provider client is on B. Service/worker sources, classifier/fixture/claim
bindings, prover identity and all prior image manifests/evidence remain intact.
No image rebuild, tag movement or republication was performed for this fix.

`check_image.py` remains strict: by default it compares against source files
beside the checker. Running the current checker/source bundle on the earlier
image will therefore reject its old `common.py`. That is an expected source
version mismatch, not permission to waive checks or relabel the old manifest.
If another CPU-only check of the published image is needed, use the matching
historical source bundle, for example:

```bash
task_image_sources=$(mktemp -d .local/published-image-source.XXXXXX)
git archive 81f2b90c7bc3aaddd44fecda222bb5d6de731616 poc/remote-cuda/check_image.py poc/remote-cuda/common.py poc/remote-cuda/service.py poc/remote-cuda/worker.py | tar -x -C "$task_image_sources"
python3 "$task_image_sources/poc/remote-cuda/check_image.py" ghcr.io/olafweller/kaspa-privacy-initiative/cuda-qualification@sha256:df8e68263f85a8d89a8fb2365d78c795b0010d35cb35d6ddc1f740d3020b7743
```

This recipe uses reviewed Git source, not an untrusted result archive. A future
new image built from current source needs its own new identities/evidence;
it must not silently replace the existing digest. The maintenance's
[binding audit](evidence/b-header-maintenance-2026-10-18/artifact-bindings.json)
checks these distinctions without running/rebuilding an image.

## Independent host preparation

A new read-only check reached the already configured Contabo host: Python
3.12.3, systemd 255, synchronized time, approximately 826.7 GB available under
`/var/lib`, and the existing `kpi-tn10` service active. No guard was installed,
no existing service was restarted and no trial credentials were inspected.
This was the TN10/gateway, not B. The owner subsequently confirmed the separate
B identity and supplied its existing pinned SSH management wrapper on TN10.

`qualify_guard.py` provides a credential-free, simulated-provider recovery test
across three separate Python processes on the selected filesystem. Its Cloud
run passed, as recorded in `evidence/cloud-process-restart.json`; this is not a
B-VPS run, a host reboot, a live provider stop or a CUDA result.

On 2026-10-18 the Cloud -> TN10 HTTPS/WSS -> `kpi-b-ssh` route returned exit 0
and `vmi3641034.contaboserver.net`. B was inspected before installation: Python
3.12.3, systemd 255, synchronized time and 85,807,165,440 free bytes on local
ext4. The eight Python files and separate systemd unit were installed from
`0ed4cb0b465f863f03b06ab3ef102234528996bc`; unit validation passed. No private-key
contents or old wallet/credential files were inspected or copied.

The recovery rehearsal and thirteen control tests then passed on B as
`kpi-cuda-guard` (UID 995/GID 986), with new temporary/test directories on the
actual `/var/lib` device. The repaired archive has the correct 51-byte size and
SHA-256; restart/grace reuse, same-size corruption, rename failure, backup-failure
deadlines and stalled-request deadlines passed. All provider/job responses were
simulated. The unit is loaded but **disabled/inactive**, PID 0; no production
lease exists and the root-only environment file contains no credentials supplied
by this task. All 38 prior B KPI unit states/PIDs and the gateway's active TN10
PID 43275 are unchanged. See [B-GUARD.md](B-GUARD.md) and
`evidence/b-guard-2026-10-18/` for the installation, hashes, permissions, test logs
and before/after snapshots. The published CUDA image is unchanged.

The later operator header fix and reported real read-only GET are documented in
[B-GUARD.md](B-GUARD.md#application-header-maintenance). Codex then confirmed B's
patched source, retained the original backup, added a targeted transport regression
and repeated **14/14 tests plus recovery** as the service user on B's state
filesystem. The account-key file was not opened; the test environment contained
no account key. The HTTP 200/zero-Pods result is owner-reported and was not
repeated by Codex. Current maintenance evidence is separate from the initial
installation snapshots; the unit remains disabled/inactive with no real lease.

## Not established

No paid resource, real lease, provider mutation, GPU driver test, CUDA kernel
execution, GPU speedup, actual VRAM peak, provider stop/persistence test or bill
exists for this package. The owner reports an account key stored only on B and a
successful read-only Pods-list request, which does not establish stop/write
rights. No full classifier receipt was attempted. Actual Pod-specific REST/proxy
checks, scoped-token configuration, real-lease activation and live provider
stop/read-back remain deployment gates. Research receipts alone do not
establish a financial privacy protocol or production readiness.
