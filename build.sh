#!/usr/bin/env bash
# Build qr0n/p100-strata (Strata v0.2.2 + 12 P100 patches) as a Docker image for Tesla P100s (sm_60).
#   ./build.sh            -> local/strata-pascal:0.2.2-qr0n
# About 15 minutes of all-core compiling. Works with Docker's legacy builder (no buildx needed).
# Copy it to another machine with: docker save local/strata-pascal:0.2.2-qr0n | zstd | ssh host 'zstd -d | docker load'
set -euo pipefail
cd "$(dirname "$0")"
FORK=8b1b0f5                                               # qr0n/p100-strata commit used for README.md
UPSTREAM=011c9e600a93bbc9fd451c563501b5831c32bbca          # Strata v0.2.2, what the fork's strata/ is based on
[ -d src ] || git clone -q https://github.com/qr0n/p100-strata src
git -C src checkout -q "$FORK"
bash src/tools/verify-source.sh                            # proves strata/ == upstream v0.2.2 + patches/0*.patch
# The fork ships the source without .git, and Strata's packaging step refuses a tree whose commit it can't name.
sed "s#^RUN python3 /src/packaging/package_terminal.py#RUN STRATA_COMMIT=$UPSTREAM python3 /src/packaging/package_terminal.py#" \
  src/strata/Dockerfile > Dockerfile.qr0n
grep -q "STRATA_COMMIT=$UPSTREAM" Dockerfile.qr0n || { echo "build.sh: the Dockerfile patch did not apply" >&2; exit 1; }
# CUDA 12.9 base (CUDA 13 can't compile for Pascal); with an architecture below 75 the Dockerfile turns on
# STRATA_EXPERIMENTAL_SM60 and labels the engine package cuda12 by itself.
DOCKER_BUILDKIT=0 docker build -f Dockerfile.qr0n -t local/strata-pascal:0.2.2-qr0n \
  --build-arg CUDA_IMAGE=nvidia/cuda:12.9.1-devel-ubuntu24.04 --build-arg CUDA_ARCHITECTURES=60 \
  --build-arg BUILD_VISION=0 --build-arg STRATA_VERSION=0.2.2-qr0n-$FORK src/strata
