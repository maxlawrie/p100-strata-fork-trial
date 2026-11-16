# To do

Open work on the 3× P100 rig, in rough order. The rig is back in service; the model tests below need the desk
fan on until the duct works on its own.

## Hardware first

- [x] **SSD swap:** done 14 Nov. The rig runs from the 1 TB drive and the filesystem spans it (936 GB).
- [ ] **Restore serving:** `strata` is back up on the rig (IQ3_S, restarted 16 Nov 20:20 after the llama.cpp 1.0 runs).
      The batch worker that uses the rig is still stopped; start it once the cooling is settled.
- [x] **New cooling duct** (3D-printed): fitted 15 Nov. On the case fans alone it is worse than the old shrouds
      (GPU 0 throttles); with the desk fan on it ran 12 minutes with no throttling (peaks 70 / 65 / 79 °C). Runs and
      notes are in [results/cooling/](results/cooling/README.md).
- [ ] **Cooling follow-ups:**
  - [ ] Find why GPU 0 gets so little air from the duct alone: check its rear bracket against the old PSU-hole
        plate, and the bottom of the plenum outlet where its power cable sits.
  - [x] Fan speed: the front fans are wired straight to 12 V, so they already run flat out. Speed control
        would only make the rig quieter at idle.
  - [ ] Try higher-pressure front fans, so the duct does not depend on the desk fan.
  - [ ] A longer sustained run on the desk-fan setup: GPU 2 was at 79 °C and still rising after 12 minutes.

## Models on disk for later tests

`fetch-models.sh` downloads model files at Strata's pinned revisions and checks their hashes, without starting an
engine. All of these were downloaded and hash-checked on 14 Nov; 368 GB is free afterwards. Strata prepares each
pack at that model's first start (roughly the size of the experts: up to about 43 GB for IQ3_XXS).

| Folder | Model | Size on disk |
|---|---|---|
| `/srv/strata/models/IQ3_S` | Flash-Next IQ3_S (serving) | 78 GB |
| `/srv/strata/models/IQ3_XXS` | Flash-Next IQ3_XXS | 71 GB |
| `/srv/strata/models/IQ2_XS` | Flash-Next IQ2_XS | 64 GB |
| `/srv/strata/models/coder-IQ1_M` | Flash-Next Coder IQ1_M | 55 GB |
| `/srv/strata/models/gyro-Gyro-S` | Flash-Next Gyro-S | 55 GB |
| `/srv/strata/models/gyro-Gyro-M` | Flash-Next Gyro-M | 86 GB |
| `/srv/strata/models/qwen36-UD-Q4_K_XL` | Qwen3.6-35B-A3B UD-Q4_K_XL (one card only in Strata 0.2.2) | 22 GB |
| `/srv/models/bonsai-2-27b` | Ternary Bonsai 2 27B, PQ2_0 and PTQ1_0 | 13 GB |

## Tests

Run overnight on 15–16 Nov; results in [results/night/](results/night/README.md).

- [x] **Gyro-M on three cards:** same quality as serving, about 15% slower. Not adopted.
- [x] **IQ2_XS on three cards:** 8–11% faster and cooler, but 32 of 63 on coding. Not adopted.
- [x] **IQ3_XXS on two cards:** matches serving on quality and speed; the primary card throttles at 80 °C.
- [x] **Coder IQ1_M on two cards:** 38 of 63 on coding, no better than IQ3_XXS.
- [x] **Ternary Bonsai 2 27B on one card (GPU 0)**, Kindi 0.4.0 and PrismML's llama.cpp fork: both run, both
      throttle (19.8 and 15.7 tok/s sustained). Kindi on two cards: 34.5 tok/s.
- [x] **Gyro-S 1card arm, the missing parts:** still aborts at 80 °C on GPU 0.
- [x] **tensorless (Qwen3.8-27B PN3) on GPU 0:** runs, throttles, 14.1 tok/s sustained.
- [x] **Settings from other P100 repos:** only `prefill-pipe=768` helped (+7–10% prompt reading up to 16K).

Speed attempts on 16 Nov with the stronger desk fan; results in [results/speed/](results/speed/README.md).

- [x] **Qwen3.6-35B-A3B on llama.cpp, two cards:** 62.9 tok/s sustained and 691 / 733 / 686 tok/s reading, the
      fastest run on the rig. Quality not measured yet.
- [x] **Power limit on serving:** 220 W with `prefill-pipe=768` reads 13–17% faster; writing unchanged; GPU 2 at 75 °C.
- [x] **One-card engines on GPU 1:** none throttles. Gyro-S 40.0, Kindi 27.9, tensorless 25.3, llama.cpp 25.0 tok/s.
- [x] **Layer split 12,36:** no gain.

- [x] **Stock llama.cpp v1.0.0:** builds for the P100. Qwen3.6 reads 8–26% faster than on the fork and writes 40%
      slower; it loads Flash-Next IQ3_S but runs it at 20 tok/s untuned.

Still open:

- [x] **Qwen3.6-35B-A3B quality:** 39 of 63 coding, 117 of 120 arithmetic; Megla's port with IQ3_S: 42 and 120.
      Both are deterministic, so this is one sample each.
- [ ] **A benchmark that can separate these:** more coding tasks, or a real workload (my own pairs and
      specs jobs), since 21 tasks at temperature 0 cannot rank deterministic engines.
- [x] **Megla123/qwen3.8-flash-next-2x-p100** (two-card Strata port): runs on the rig. Reading 678 / 896 / 891
      tok/s, sustained writing 53.8 tok/s (GPU 2 throttling), code replies slower than serving. See
      [megla/README.md](megla/README.md).
- [x] **The port on three cards:** runs and is correct with a small patch. An uneven 256 / 256 / 128 split matches the
      two-card port on writing (48–55 tok/s stories, 50 code) and reads at 613 tok/s against 896.
- [ ] **Three-card port, next:** (sustained 53.1 tok/s without throttling and 48 of 63 coding are done) more uneven splits
      (320 / 256 / 64); GPU 0 first; why reading is a third slower than on two cards; tell the author.
- [ ] **Two-card port follow-ups:** a run with GPU 2 not throttling; its `--route-prior 0.15` mode (faster, lossy).
- [ ] **Decide the power limit:** 220 W costs 6–7 °C on GPU 2 and needs the stronger desk fan.
- [ ] **`prefill-pipe=768`:** a quality run, since it changes answers; adopt if coding holds.
- [ ] **One-card engines above 140 W**, to see how much of the gap to their published speeds is the limit.
- [ ] **Kindi's coding score:** rerun `quality.py` on GPU 1 now that it does not throttle.
- [ ] **`spec-min-p=0.65 suffix-draft=0`:** more stories, to see whether the +4% is real.
- [ ] **Two models at once:** Qwen3.6 or IQ3_XXS on GPUs 1 and 2 plus a one-card model on GPU 0.
- [ ] **Batch worker pilot against Gyro-S**, and **a small model on the workstation's RTX 5050** for the
      pairs job.
