# Later deployment checklist and commands

Preparation only. Do not rent until the image is pullable and the independent
guard host and credential/network paths are ready. No command below is run by
creating or reviewing this PR.

## Before the rental clock starts

1. Review this package, build evidence and the public fixture provenance. Confirm
   the one-GPU, one-attempt scope, two-hour rental envelope, one-hour diagnostics,
   USD 5 planning ceiling and storage cleanup responsibility with the owner.
2. Build/publish the reviewed image **before renting**. The manually dispatched
   `Prepare CUDA qualification image` GitHub workflow builds on CPU; `publish`
   defaults false. After this workflow reaches the default branch, it can publish
   a reviewed revision to GHCR using GitHub's job token. Record its registry
   digest, not just a mutable tag. Make it publicly pullable or configure a
   read-only registry pull credential in RunPod. Do not assume package visibility.
   This preparation has not published a registry image.
   Alternatively, push an explicit `cuda-qualification-*` tag on the reviewed
   revision to run the same build/publication. Publication pulls the immutable
   digest back from GHCR and repeats the CPU-only container checks. An
   authenticated CI pull does not establish anonymous/public package access.
3. Inspect the owner's existing Linux VPS that held A1 recovery role B. It needs
   Python 3.10+, systemd, synchronized time, durable free space for checkpoints
   and outbound HTTPS to `rest.runpod.io` and the eventual exact Pod proxy host.
   It needs no GPU or CUDA. Keep old trial data, keys and services unchanged.
4. Copy `common.py`, `watchdog.py`, `make_lease.py` to `/opt/kpi-remote-cuda` on
   that VPS; create a dedicated `kpi-cuda-guard` service user and
   `/var/lib/kpi-cuda-guard`. Install `kpi-cuda-guard.service`. A root-owned
   mode-0600 `/etc/kpi-cuda-guard.env` supplies `RUNPOD_API_KEY` and
   `KPI_GPU_TOKEN` through the operator's credential mechanism. Never paste their
   values into a chat, Git, a unit file, command arguments or uploaded artifacts.
   Enable service startup/restart after the real lease is written. A missing
   lease must not be replaced by a guessed Pod identity.
5. Generate a fresh scoped service token through a secret manager (32+ ASCII
   characters). Inject the same `KPI_GPU_TOKEN` into the Pod and guard; configure
   Codex's scoped credential separately. Keep the RunPod account API key only
   on the guard host. Choose the narrowest provider permissions that support
   reading/stopping this Pod; the helper never creates paid resources.
6. Confirm actual L40S availability/quote and host resources: one 48 GB L40S,
   at least four vCPUs, 32 GB RAM, 90 GB container disk and 10 GB persistent
   volume mounted at `/workspace`. Include active/stopped storage charges and
   24-hour retention in the USD 5 check. Account top-up is not experiment usage.

The current Codex environment has no RunPod allowlist entry or GPU token. Later,
allow only `https://POD_ID-8080.proxy.runpod.net` for its control API and bind
`KPI_GPU_TOKEN` there as an environment-variable secret using the environment's
supported configuration workflow. Do not send the account API key to Codex or
the GPU service. The official Cloud runtime skill describes proxy credential
injection: the configured variable may contain a proxy placeholder. Use it
normally in `control.py`'s bearer header and preserve the inherited proxy and CA
configuration; never inspect or replace that placeholder with an invented token.
Require fresh `ready` observations and a successful authenticated status request.
That live credential check remains pending until the exact host/token exist.

CPU image building uses Docker Hub/NVIDIA image endpoints, GitHub, Rust static
downloads, crates.io, Ubuntu/NVIDIA apt repositories and the public RISC Zero S3
artifact URL. Use the existing managed proxy and supplied CA bundle; never disable
TLS or bypass a network restriction. The local build used the already-cached
public recursion archive. Runtime proof work uses the packaged inputs; it should
not fetch wallet data or setup material.

## Configure and run the single paid qualification later

1. Manually deploy the reviewed image **by digest** with the settings in
   `pod-template.example.json`, replacing placeholders via provider UI/secret
   mechanisms. Expose only `8080/http` through the HTTPS proxy. The process boots
   unconfigured and cannot start proof work without a lease and guard heartbeat.
   RunPod's NVIDIA runtime must inject `libcuda.so.1`, NVML and `nvidia-smi`;
   retain `NVIDIA_DRIVER_CAPABILITIES=compute,utility`. CPU-only image validation
   records the absent driver and cannot start the CUDA prover. Do not substitute
   a driver stub or count a CPU fallback as GPU qualification.
2. On the independent VPS, with provider/service secrets supplied securely, run:

   ```bash
   python3 /opt/kpi-remote-cuda/make_lease.py POD_ID ACTIVE_STORAGE_USD_PER_HOUR STOPPED_STORAGE_USD_PER_HOUR /var/lib/kpi-cuda-guard/lease.json
   ```

   This performs a read-only lookup and records the provider's creation time,
   actual hourly quote and resources. The deadline is creation plus 7,200 seconds.
   The storage arguments must come from the actual allocation/pricing. Verify
   the filtered lease, ownership/read permissions and system clock. Save a
   secret-free copy for Codex. The guard service user must be able to read it.
3. Start/enable the guard systemd unit. Check its `guard.json`, lease digest,
   heartbeat and deadline. It configures the Pod, arms the job, backs up results
   and requests stop even if Codex vanishes. Check actual API behavior before
   starting diagnostics. A provider schema/stop mismatch blocks qualification;
   stop manually in the provider UI if the helper cannot confirm stop.
4. Complete an authenticated HTTPS connection check from Codex. With the scoped
   token delivered through the supported runtime mechanism:

   ```bash
   python3 poc/remote-cuda/control.py status LEASE.json
   python3 poc/remote-cuda/control.py start LEASE.json
   python3 poc/remote-cuda/control.py status LEASE.json
   ```

   Start returns immediately with the fixed job ID. Require a fresh guard
   heartbeat and more than 3,660 seconds remaining; otherwise do not start.
   Poll short requests; never issue a synchronous hour-long HTTP request.
   Duplicate start returns the existing attempt; restart does not rerun it.
5. Fetch a checkpoint/final archive into a **fresh** directory, then verify it
   using the trusted, locally generated CPU package:

   ```bash
   python3 poc/remote-cuda/control.py fetch LEASE.json .local/gpu-download
   python3 poc/remote-cuda/control.py verify .local/remote-cuda-preparation/dist .local/gpu-download
   ```

   A checkpoint may advance between status/download. Retry a size/hash mismatch;
   never accept it. Final `verify` requires all five receipts. For an interrupted
   run, retain all partial receipts and stage logs. Use `verify-partial` in place
   of `verify` to cryptographically check every available receipt against its
   pinned CPU claim; it reports the verified count and `allFiveSealsVerified=false`
   unless all five exist. No receipts is an error. This does not make an incomplete
   qualification successful. The guard's durable hash-named archive survives Pod stop and can
   be copied back if the proxy is already unavailable. With the archive and
   expected hash from the guard's durable `latest-artifact.json`, use:

   ```bash
   python3 poc/remote-cuda/control.py unpack SAVED.tar.gz EXPECTED_SHA256 .local/gpu-recovered
   python3 poc/remote-cuda/control.py verify .local/remote-cuda-preparation/dist .local/gpu-recovered
   ```

   This uses bounded, path-checked extraction rather than unrestricted shell tar.
6. Inspect the final CPU comparison, every phase's actual GPU process evidence,
   wall/CPU time, sampled RSS/VRAM and build identity. A hash-checked download or
   a Pod-written report alone is not independent verification. Missing CUDA/PID
   evidence is inconclusive, even if all proofs verify.
7. Confirm `stop.json` and provider `desiredStatus=EXITED`. The guard grants only
   60 seconds after terminal backup before stopping compute; if retrieval fails,
   it still stops at the absolute deadline and preserves the Pod volume.
   After external backup and CPU verification, manually remove the Pod and its
   volume, ideally immediately and within the budgeted 24-hour storage window.
   Record provider billing/retention; stop acknowledgment alone is not a bill.

Do not start a full-classifier proof as part of this qualification. A later
decision uses measured per-phase CUDA costs and the remaining uncertainties.

## Rebuild the public package locally

Use Rust 1.91.0 and the repository's pinned sibling `upstream/rusty-kaspa`
checkout, as in `.github/workflows/cuda-image.yml`:

```bash
cargo +1.91.0 build --locked --release --manifest-path poc/takeover/Cargo.toml --bin kpi-takeover-host
python3 poc/remote-cuda/check_cpu_compare.py .local/ci-target/release/kpi-takeover-host
python3 poc/remote-cuda/package.py .local/ci-target/release/kpi-takeover-host .local/remote-cuda-preparation/dist
bash poc/remote-cuda/build_image.sh .local/cuda-build-context kpi-cuda-qualification:prepare
```

Set `CARGO_TARGET_DIR` to `.local/ci-target` before building. Both output/context
directories must be new. Commit the reviewed source first: `workload.json` records
the checked-out revision and verifier hash. The prepared bundle contains public
inputs/CPU baseline/verifier only; never add wallet keys or service secrets.
