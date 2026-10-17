# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.8.1-base-ubuntu24.04@sha256:e711c99333fdfe8ae1e677b4972be6c5021f0128a1d31f775c7e58d88921b6a9 AS builder
ENV CARGO_HOME=/opt/cargo RUSTUP_HOME=/opt/rustup
ENV PATH=/opt/cargo/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
COPY recursion_zkr.zip /opt/build/recursion_zkr.zip
COPY build_cuda.sh /opt/build/build_cuda.sh
RUN --mount=type=secret,id=system_ca,mode=0444 \
    --mount=type=cache,id=kpi-risc0-303-source,target=/tmp/risc0,sharing=locked \
    --mount=type=cache,id=kpi-risc0-303-clang-rust189-target,target=/opt/cuda-target,sharing=locked \
    bash /opt/build/build_cuda.sh

FROM nvidia/cuda:12.8.1-base-ubuntu24.04@sha256:e711c99333fdfe8ae1e677b4972be6c5021f0128a1d31f775c7e58d88921b6a9
RUN --mount=type=secret,id=system_ca,mode=0444 \
    set -e; if test -f /run/secrets/system_ca; then \
      apt-get -o Acquire::https::CaInfo=/run/secrets/system_ca update; \
      apt-get -o Acquire::https::CaInfo=/run/secrets/system_ca install -y --no-install-recommends python3 ca-certificates util-linux; \
    else apt-get update && apt-get install -y --no-install-recommends python3 ca-certificates util-linux; fi; \
    rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/kpi/bin/r0vm-cuda /opt/kpi/bin/r0vm-cuda
COPY --from=builder /opt/kpi/cuda-build.json /opt/kpi/package/cuda-build.json
COPY --from=builder /opt/kpi/build-packages.txt /opt/kpi/package/build-packages.txt
COPY dist/bin /opt/kpi/package/bin
COPY dist/inputs /opt/kpi/package/inputs
COPY dist/workload.json /opt/kpi/package/workload.json
COPY common.py worker.py service.py /opt/kpi/app/
RUN --mount=type=bind,source=dist/baseline,target=/baseline,readonly \
    cp -a /baseline /tmp/cpu-check && rm /tmp/cpu-check/cpu-comparison.json && \
    RISC0_PROVER=ipc /opt/kpi/package/bin/kpi-takeover-host phase-diagnostics compare /tmp/cpu-check && \
    rm -rf /tmp/cpu-check
ENV RISC0_PROVER=ipc RISC0_SERVER_PATH=/opt/kpi/bin/r0vm-cuda RISC0_DEFAULT_PROVER_NUM_GPUS=1
EXPOSE 8080
WORKDIR /opt/kpi/app
CMD ["python3", "service.py"]
