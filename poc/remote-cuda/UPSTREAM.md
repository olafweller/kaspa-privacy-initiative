# Upstream pins and operational findings

Checked 2026-10-17. These are source/build facts, not evidence of live rental behavior.

- RISC Zero [v3.0.3](https://github.com/risc0/risc0/tree/14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6),
  commit `14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6`, committed Cargo.lock,
  `risc0-r0vm` features `cuda,disable-dev-mode`, upstream's
  [Rust 1.89.0 toolchain](https://github.com/risc0/risc0/blob/14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6/rust-toolchain.toml).
  The independent repository CPU verifier still uses Rust 1.91.0.
  [CUDA build support](https://github.com/risc0/risc0/blob/14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6/risc0/build_kernel/src/lib.rs)
  honors `NVCC_APPEND_FLAGS`; `-arch=sm_89` avoids build-time GPU discovery.
- Native C/C++ compilation explicitly uses Clang, following upstream's
  [compiler selection](https://github.com/risc0/risc0/blob/14b5d588dd01cf4f7ba804d8bb0a61264e6ae2c6/.github/actions/sccache/action.yml).
  The image build uses four Cargo workers and records the actual Clang/NVCC
  versions. These build resources are separate from the diagnostic process limits.
  BuildKit keeps source/target caches outside the image layers. The source cache
  is reset/cleaned and checked against the exact commit before every build.
- [Local proving documentation](https://dev.risczero.com/api/generating-proofs/local-proving)
  distinguishes CUDA build toolkit and runtime; first-use compilation can take
  minutes. Compiler success alone does not prove GPU acceleration.
- NVIDIA CUDA 12.8.1 base, Ubuntu 24.04, linux/amd64 manifest
  `sha256:e711c99333fdfe8ae1e677b4972be6c5021f0128a1d31f775c7e58d88921b6a9`.
  The build installs only the required NVCC/development packages rather than
  downloading an entire devel image. Apt package versions and the final binary
  SHA are retained. Apt/Rust bootstrap endpoints remain availability dependencies;
  a later rebuild is not promised byte-identical. Deploy the published image by
  immutable registry digest.
- Public recursion archive:
  `https://risc0-artifacts.s3.us-west-2.amazonaws.com/zkr/744b999f0a35b3c86753311c7efb2a0054be21727095cf105af6ee7d3f4d8849.zip`,
  SHA-256 `744b999f0a35b3c86753311c7efb2a0054be21727095cf105af6ee7d3f4d8849`.
- RunPod CLI [v2.13.0](https://github.com/runpod/runpodctl/tree/3560e35d8900f49a86e6f4e5d814ec1c8bb03c68),
  commit `3560e35d8900f49a86e6f4e5d814ec1c8bb03c68`, confirms REST
  `POST https://rest.runpod.io/v1/pods/{id}/stop` and `GET .../pods/{id}`.
  [PR #330](https://github.com/runpod/runpodctl/pull/330) removed ineffective
  stop-after/terminate-after flags in v2.12.0. Do not use cached instructions
  claiming those flags schedule a reliable provider-side shutdown.
- [RunPod proxy guide](https://www.runpod.io/blog/runpod-proxy-guide): requests
  have a 100-second limit. Start returns immediately; status/artifact requests
  are separate. Transport helpers enforce HTTPS and reject redirects.
- [Storage types](https://docs.runpod.io/pods/storage/types): container disk
  does not survive stop/restart; the Pod volume survives stop and is lost on
  termination. Stopped volume billing continues. Keep artifacts under
  `/workspace/kpi` and back them up off the Pod before deletion.

No fresh provider pricing lookup or deployment quote is asserted. The reference
USD 1.09/hour was supplied in the owner's review; use the actual quote at launch.
