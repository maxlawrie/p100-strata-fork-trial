# Stock llama.cpp v1.0.0 (13 Nov 2026, github.com/ggml-org/llama.cpp) built for the Tesla P100: CUDA 12.9 (CUDA 13
# dropped Pascal), sm_60 only.   docker build -t local/llama-cpp:v1.0.0-sm60 llama1
ARG CUDA_VERSION=12.9.1

FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu24.04 AS build
ARG TAG=v1.0.0
ARG JOBS=8
RUN apt-get update && apt-get install -y --no-install-recommends \
        git cmake build-essential ca-certificates libssl-dev \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${TAG} https://github.com/ggml-org/llama.cpp /src && git -C /src log --oneline -1
WORKDIR /src
RUN cmake -B build \
        -DGGML_CUDA=ON \
        -DCMAKE_CUDA_ARCHITECTURES=60 \
        -DGGML_NATIVE=OFF \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLAMA_BUILD_TESTS=OFF \
        -DCMAKE_EXE_LINKER_FLAGS=-Wl,--allow-shlib-undefined \
    && cmake --build build --target llama-server llama-bench -j${JOBS}

FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 libssl3 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/build/bin/ /app/
ENV LD_LIBRARY_PATH=/app
ENTRYPOINT ["/app/llama-server"]
