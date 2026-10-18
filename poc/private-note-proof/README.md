# Fixed private-note proof package

Completed follow-up: the owner reviewed and released one bounded GPU attempt.
The [actual result](gpu-2026-10-18/RESULTS.md) records the genuine receipt,
independent CPU/native verification and confirmed provider stop/deletion.
The software-preparation authorization and future-run instructions below are
retained as the original scope; they do not authorize additional attempts.

Owner-authorized software preparation, 2026-10-18. The owner performs the Astra
review in Chat. No internal Astra reviewer is part of this package. No rental,
proof job, wallet setup, extra calibration or TN10 broadcast is authorized here.

## Exact target and reused work

[target.json](target.json) adds the explicit `join.zkr` / Poseidon2 control pin
to PR46's frozen target. Guest image, VK, wallet proof bytes, public input and
352-byte expected journal are unchanged. The original 128M failure and 160M
calibration remain intact. No guest is rebuilt.

The circuit/privacy-design reuse review remains ADR0011/0012. This package adds
no note relation, curve arithmetic, proof system, wallet keys or parameter setup.
It reuses RISC Zero 3.0.3's Succinct producer and official STARK verifier,
the pinned Kaspa script engine, the vendored settlement builder, and the existing
authenticated fixed-job service, process deadline, snapshots and independent B
guard. Public fixtures only enter the prover; wallet secrets and proving
parameters do not. The ancestor state/deposit is synthetic, as before.

The new `SuccinctJoin` covenant variant pins
`7a8f24092c34ed3eb81b3d0a0b796c588c615d3488ef9e61c21dbd1e4b83ea6e`.
Existing `Succinct` fixtures still pin `resolve.zkr`. The helper does not accept
a caller-selected arbitrary control identity. Allowed-control-root inclusion,
seal/control equality, image, successful exit, assumptions and journal checks
remain required. The allowed root is
`a54dc85ac99f851c92d7c96d7318af41dbe7c0194edfcc37eb4d422a998c1f56`.

An additional SDK nuance is explicit in `src/lib.rs`: SDK 3.0.3's verifier
authenticates the control decoded from the seal, but its callback does not equate
that decoded value to the receipt's metadata. The independent verifier therefore
uses the official STARK-verification callback to require decoded control = pinned
join = metadata, and verifies inclusion against the official allowed root. This
is the same equality enforced by the pinned Kaspa precompile, without custom
cryptographic arithmetic.

## Executables and independent checks

- `kpi-private-note-producer check-target PACKAGE/inputs`: checks hashes, image and
  expected journal, without executing or proving the guest.
- `kpi-private-note-producer prove PACKAGE/inputs NEW_PROOF`: exactly one fixed
  Succinct receipt, <=160M execution cycles, segment po2=20, no assumptions.
  The remote process-group timer covers the entire <=3,600s invocation, including
  proving, compression, save and producer verification. A returned candidate is
  durably saved before further checks. There is no automatic retry.
- `kpi-private-note-verifier verify-receipt RECEIPT NEW_OUTPUT`: a separate local
  CPU executable/process with independently compiled image, control and complete
  journal expectations. Rejects Fake/Composite, non-success/unresolved claims,
  wrong image/control, changed journal, seal and control-inclusion mutations.
- `kpi-private-note-native verify-receipt RECEIPT NEW_OUTPUT`: actual native
  settlement script execution with fixed state/lane/relation slots and
  **1,000,000,000 sompi** reserve principal. Tests fifteen negative variants of
  state, tip, endpoint, covenant, relation/image/control pins, seal/inclusion and
  reserve diversion with the unchanged genuine receipt. This fixture has no
  permission output, native fee/rent acceptance or payout; sponsor/rent costs
  are separate and not deducted from backing.
- `kpi-private-note-native archived-join OLD_RECEIPT NEW_OUTPUT`: actual
  precompile-only compatibility check with the SHA-pinned genuine PR43 receipt.
  It cannot demonstrate the new private-note claim or a 352-byte settlement.

Development mode is rejected by the CLIs and disabled in verification. Timeouts,
build failures, resource errors and panics never count as successful negative
native controls. Only explicitly allowed verifier/semantic script errors count.

## Public package and binary/source binding

[evidence/package-identity.json](evidence/package-identity.json) records the three
separately built executables, their reviewed source/lock hashes, public inputs,
archive and policy hashes. The build used Rust 1.91.0, separate `cargo build`
invocations and the pinned lockfile. Both verifiers are trusted local artifacts,
not downloaded executables selected by the GPU. There is no claim that the
recorded hashes alone prove compilation correctness or a reproducible compiler.

The whitelist-built archive contains exactly three public input files, three
executables and the workload manifest. `private_package.py restore` checks the
archive and current source bindings before extracting it into a fresh directory.
There is no recursive wallet-directory copy. For a fresh source build:

```bash
cargo +1.91.0 build --locked --release --manifest-path poc/private-note-proof/Cargo.toml --features native --bin kpi-private-note-producer
cargo +1.91.0 build --locked --release --manifest-path poc/private-note-proof/Cargo.toml --features native --bin kpi-private-note-verifier
cargo +1.91.0 build --locked --release --manifest-path poc/private-note-proof/Cargo.toml --features native --bin kpi-private-note-native
```

The binaries run without wallet/circuit/parameter modules. Later source changes
must rebuild and re-freeze affected artifacts; do not relabel old binaries.

## Fixed image and CPU-only preparation

`poc/remote-cuda/Dockerfile.private` derives from the already published immutable
PR43 image; the CUDA prover remains SHA256
`4447bbfa89b450611deda80825387d48cce6d23b428310ac45662f5c65f1cbcb`.
It installs the new package under `/opt/kpi/private-note` and uses a new durable
volume identity `/workspace/kpi-private-note`. The old proxy-classifier workload
and image identity remain separate historical artifacts.

```bash
python3 poc/remote-cuda/private_package.py restore .local/private-image/private-dist
cp poc/remote-cuda/{Dockerfile.private,common.py,worker.py,service.py,package.py,private_package.py,private_worker.py,private_service.py} .local/private-image/
docker build -f .local/private-image/Dockerfile.private -t kpi-cuda-private:checked .local/private-image
python3 poc/remote-cuda/check_private_image.py kpi-cuda-private:checked
```

The publishing workflow is `.github/workflows/cuda-private-image.yml`, triggered
only by a `cuda-private-note-*` tag. It validates source/package binding, runs
the control tests, builds, checks authentication/lease binding without a proof,
publishes and rechecks the immutable digest. See [RESULTS.md](RESULTS.md) for the
actual published identity and tests. Docker platform proxy/CA settings remain
required where applicable; no TLS weakening or new Cloud secrets/domains.
The immutable image and exact proposed disk/port/start settings are also recorded
in [deployment.json](deployment.json); it explicitly authorizes no rental.

## Owner/Astra review and a later one-attempt GPU release

Software review comes first. Before a later rental, record the actual available
L40S + disk quote, independently confirm B's time, storage and installed guard,
and obtain the owner's release. No Pod or account mutation is performed by
preparation. Preserve B-only account credentials and the existing management
route Cloud -> TN10 -> B; no Cloud/GPU account key and no runtime dependency on
Cloud, the gateway or the laptop.

The proposed run uses one L40S 48GB, >=4 vCPUs, >=32GB host RAM, 90GB container
disk + 10GB `/workspace`; one attempt, <=1h entire proof group, <=2h rental from
actual creation. The inherited runner uses four compute threads and a sampled
12GiB process-group RSS stop. B's fresh lease/guard independently handles backup
and provider stop even when the controller disappears. Reuse the existing
runbook's lease procedure; never reset old attempt markers. The USD5 planning
limit must include the actual GPU/storage/retention quote and is not a guaranteed
provider-invoice cap. No current price/availability is claimed by this package.

Require >3,660 seconds lease time and a fresh B heartbeat before starting. B uses
its existing service token to call this service. Commands below are for the
later authorized run, not actions performed during this preparation:

```bash
# On B through its existing credential-loading operator path:
python3 /opt/kpi-remote-cuda/control.py status NEW_LEASE.json
python3 /opt/kpi-remote-cuda/control.py start NEW_LEASE.json
python3 /opt/kpi-remote-cuda/control.py fetch NEW_LEASE.json NEW_DOWNLOAD
```

Keep results durably on B. Restore the trusted package from this reviewed commit
on the verification host and run the separate verifiers, never a GPU-supplied
binary. On the local CPU host, after safe archive retrieval/unpacking:

```bash
python3 poc/remote-cuda/private_control.py verify TRUSTED_PACKAGE DOWNLOADED NEW_VERIFICATION
```

Verify actual matching-process CUDA activity, exact claims, CPU/native outcomes
and backup hash/size. A missing GPU-activity observation is inconclusive even if
the receipt verifies. Confirm provider EXITED by readback; archive recovery must
work after stop. Delete rented storage only after verified external preservation
and under the later release. Provider stop acknowledgment alone is insufficient.

## Self-review and limits

I-1/I-2: no economic relation changed; the fixture backs all 10 KAS and rejects
shrinking the continuation. I-3/I-4: unchanged wallet authorization and nullifier
checks execute inside the frozen guest. I-5/I-6: real seal, exact image/control/
journal and prior-state/lane/endpoint pins; GPU JSON never authorizes state.
I-7/I-8/I-12: no payout or administrative withdrawal is introduced. I-9: failures
stop the single attempt without a weaker statement. I-10/I-16: no wallet secrets
leave the owner; public-state and proving-parameter durability, anonymity,
canonical reorg handling and permissionless recovery remain unproven. Compilers,
reviewed binaries, B root and the existing experimental one-party setup retain
their previously stated trust roles.

Successful later CPU/native verification would prove this **monolithic**
credit -> invalid transfer -> valid transfer, beginning after synthetic deposit
registration. It would not prove original deposit lineage, Bob's exit/payout,
canonical TN10 settlement, independently operated recursive stages or a complete
privacy protocol. A genuinely proved omitted-operation variant needs a separate
proof. The private 352-byte positive/negative fixture checks remain pending until
the new real receipt exists; archived PR43 checks are labelled separately.
