# Megla123's two-card Strata port: how it was run here

[Megla123/qwen3.8-flash-next-2x-p100](https://github.com/Megla123/qwen3.8-flash-next-2x-p100) at `a580ef7`, built
with its own `build.sh` in a CUDA 12.9 container ([Dockerfile.rig](Dockerfile.rig), build context: a clone of that
repo), image `local/fnx-2xp100:megla`. Results: [results/speed/README.md](../results/speed/README.md).

```
# data folder, with links to the serving model so nothing is downloaded or written beside it
sudo mkdir -p /srv/fnx2/models && sudo chown -R $USER: /srv/fnx2
for f in /srv/strata/models/IQ3_S/*.gguf; do ln -sf /models-ro/$(basename $f) /srv/fnx2/models/; done

R="--gpus \"device=1,2\" -u $(id -u):$(id -g) -e HOME=/data -v /srv/fnx2:/data -v /srv/strata/models/IQ3_S:/models-ro:ro"
# once: Strata v0.2.9's server, checksums, tokenizer, the 5.2 GB draft layer, the 64 GB run config (about 8 minutes)
docker run --rm $R local/fnx-2xp100:megla -c \
  "export LD_LIBRARY_PATH=/usr/local/cuda/lib64; bash setup.sh /data --models /data/models --ram 64 --no-pictures"

# run it: the serving container must be stopped first; the memory cap keeps a failed load from taking the rig down
docker stop -t 120 strata
docker run -d --name fnx $R --network host --memory 58g --memory-swap 58g --ulimit memlock=-1:-1 --shm-size 2g \
  local/fnx-2xp100:megla -c "export LD_LIBRARY_PATH=/usr/local/cuda/lib64; exec bash run.sh /data --port 8080 --host 127.0.0.1"
# ready when GET /health says "loaded": true (2 minutes here). No API key. Back to serving:
docker rm -f fnx && docker start strata
```

Inside the container the two cards are 0 and 1, which is what `setup.sh` writes into the config. The load peaked at
55.65 GiB of the container's 58 GiB (4.2 GB of RAM spare on the rig) and settled at 45–47 GiB.

## Three cards

The port is written for two cards. [three-card.patch](three-card.patch) makes it build and run on three (even split,
256 / 192 / 192); [three-card-uneven.patch](three-card-uneven.patch) is the same plus a 256 / 256 / 128 split for a rig
with one slow slot. Apply one to a clone at `a580ef7`, copy [build3.sh](build3.sh) and
[Dockerfile.rig3](Dockerfile.rig3) into it, and build:

```
git apply three-card-uneven.patch
docker build -f Dockerfile.rig3 -t local/fnx-2xp100:megla3u .
```

Run configs are in [profiles/](profiles/): they are `setup.sh`'s `profile.json` with `exe` set to `strata-split-3`,
`gpu` `1,2,0` (the slow-slot card last), `FNX_PF_SP=0`, and `FNX_EXPERT_RAM_GIB` / `FNX_EXPERT_DYN_GIB` of
29 / 13 (`3a`), 22.5 / 13 (`3b`) and 22.5 / 14.5 (`3u`, for the uneven build). Start it as above with
`--gpus all` and `run.sh /data --config /data/profile-3u.json`; [fnx-load.sh](fnx-load.sh) does that and watches
memory, [fnx-quick.sh](fnx-quick.sh) adds the speed set.

What the patches change: two `static_assert(NCARD == 2)` become run-time checks (`prefill.cu`), the FF split works in
units of 64 instead of 32 (`card_split.hpp`), and `FF_CARD_MAX` follows it (`model.hpp`). Nothing in the kernels.
