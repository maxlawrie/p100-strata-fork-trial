# qr0n's P100 fork of Strata, measured on a 3× Tesla P100 rig

Results from trying [qr0n/p100-strata](https://github.com/qr0n/p100-strata) (Strata v0.2.2 plus 12 patches with
faster Pascal kernels) against the stock Strata 0.2.1 my rig was running, with the same model
(Qwen3.8-Flash-Next GSQ-RCO IQ3_S), the same three cards and the same settings. Write-up with more of the story:
[A third more speed from the same three P100s](https://lawrie.co.nz/posts/p100-strata-fork.html).

**Short version:** about **30% faster writing** (stories 32–36 → 41–45 tok/s, code 42–55 → 52–74 tok/s), prompt
reading unchanged, no extra heat, and no difference I can measure in a coding test. It works in Strata's low-RAM
mode on 64 GB and across three cards. I switched the rig to it. The opt-in Q8 kernel added only a few percent more
here and wasn't worth its cost.

A second round of experiments (layer splits, sustained load, power limit, peer mode, two other models, thinking
on and off) is under [Follow-up experiments](#follow-up-experiments). None of them changed the config.

## Hardware

- 3× Tesla P100-PCIE-16GB, 140 W power limit each, passive cards in fan shrouds. Two on PCIe 3.0 x8 (CPU lanes),
  one on the chipset's PCIe 2.0 x4
- ASUS Prime X370-Pro, Ryzen 5 2600, 64 GB DDR4 (60.7 GiB usable), 250 GB NVMe
- Ubuntu 26.04, Linux 7.0, driver 580, Docker, CUDA 12.9.1 (CUDA 13 can't build for Pascal), `iommu=pt`
- Model: Qwen3.8-Flash-Next GSQ-RCO IQ3_S, 256K context, int8 KV, MTP on (`--spec 4 --spec-min-p 0.5`), one slot

## Results

Measured 10 Nov 2026. One run each, started from resting temperatures (54–57 °C with the model loaded), thinking
off, temperature 0, with [`bench/bench.sh`](bench/bench.sh). Speeds are the engine's own timings. Raw output of
every run is in [`results/`](results/).

Every column uses `resident-experts kv-resident=32768 layer-split=12,34 conversation-cache-mib=8192`. "Flags" are
the fork's kernels, `STRATA_GU_F16=2 STRATA_SM60_D20_SUB=1 STRATA_DOWN_F16=1 STRATA_B6_F16=1`, plus
`STRATA_ROUTE_TAIL_SKIP=0`.

| | Stock Strata 0.2.1 | Fork + flags | Fork + flags + `trim-stage-weights` | … + `STRATA_Q8_SM60=1` |
|---|---|---|---|---|
| Reading a 4K / 16K / 32K prompt, tok/s | 233 / 366 / 456 | 231 / 365 / 455 | 232 / 366 / 455 | 237 / 369 / 459 |
| 300-token stories, tok/s | 31.8–35.8 | 39.3–43.0 | **41.2–44.9** | 42.4–50.7 |
| Code replies, easy set, tok/s | 42–55 | 45–67 | **52–74** | 48–73 |
| Code replies, hard set, tok/s | 43–55 | 54–68 | **59–71** | 61–74 |
| Easy coding set (8 tasks) | 8/8, 76 s | 7/8, 68 s | **8/8, 63 s** | 8/8, 59 s |
| Hard coding set (8 tasks) | 4/8, 254 s; rerun 6/8, 230 s | 5/8, 194 s | **7/8, 170 s** | 4/8, 173 s |
| Experts held in VRAM | not logged | 16,491 | **18,707** | 16,883 |
| Decode expert-cache hit rate | not logged | 94.8–98.0% | 95.7–98.8% | 94.7–97.9% |
| Hottest card, easy run | 74 °C | 74 °C | 74 °C | 75 °C |

The third column is what the rig serves now ([`compose.yaml`](compose.yaml)). A repeat of the easy run on the
serving container gave the same speeds (stories 41–46 tok/s, code 51–70) and 7/8.

### What each step does

- **The fork's fp16 kernels: about +22%.** They are off unless the flags are set. Prompt reading doesn't change,
  because the patches are decode kernels.
- **`trim-stage-weights`: the rest.** This is an upstream Strata flag, not the fork's. With an explicit layer split,
  each card loads only its own layers' dense weights. That freed room for about 2,200 more experts on GPU1 and
  GPU2 (6,630 and 5,933 instead of 5,631 and 4,716). GPU0 stays at 6,144 with ~3 GB of VRAM unused.
- **`STRATA_Q8_SM60=1`: a few percent, at a price.** Stories about +8%, code about +3–4%. The kernel's packed
  copies took 3.5 GiB of VRAM (737 + 1,355 + 856 MiB over the three stages, 644 MiB for the head), which pushed
  about 1,800 experts back off GPU1 and GPU2 and gave back most of what the kernel won. It also needs a second copy
  of the model's first shard with the dense matrices requantized to Q8_0: `tools/q8_dense_gguf.py` wrote a 58.6 GB
  file in about 6 minutes (the docs' "+3.5 GiB" is on top of a full copy), and Strata's launcher has to be bypassed
  to load it. Not adopted. On two cards with every expert in VRAM the trade may be different.

### The hard coding set is noisy

| Task | Stock, run 1 | Stock, run 2 | Fork + flags | Fork + flags + trim | Fork + Q8 |
|---|---|---|---|---|---|
| semver_sort | PASS | PASS | PASS | PASS | PASS |
| cron_next | FAIL | PASS | FAIL | PASS | FAIL |
| json_parse | PASS | PASS | PASS | PASS | PASS |
| regex_match | FAIL | PASS | PASS | PASS | FAIL |
| osa_distance | PASS | PASS | PASS | PASS | PASS |
| parse_csv | FAIL | FAIL | FAIL | FAIL | FAIL |
| run_limited | FAIL | FAIL | FAIL | PASS | FAIL |
| lex_shortest_path | PASS | PASS | PASS | PASS | PASS |
| **Total** | **4/8** | **6/8** | **5/8** | **7/8** | **4/8** |

The same stock server, an hour apart, scored 4/8 and 6/8 (and 7/8 three weeks earlier). Temperature 0 doesn't make
the engine deterministic: experts computed on a GPU round differently from the CPU, and which experts are cached
changes between runs. So this set can't rank these builds. All it says is that none of them is obviously broken. A
single run of eight tasks was too little to support the 7/8 against 5/8 comparison in my
[earlier trial](https://github.com/maxlawrie/p100-llamacpp-fork-trial) as firmly as I wrote it up.

## Follow-up experiments

Same day, same rig. Everything below is the serving build (third column above) unless it says otherwise. Raw output
is in [`results/followup/`](results/followup/). Write-up:
[Nine experiments on the P100 rig, and the one that mattered](https://lawrie.co.nz/posts/p100-experiments.html).

**Short version:** no setting, mode or other model beat the serving config. Turning thinking on raised the coding
score more than anything else, at more than ten times the time per answer.

### A repeated benchmark

[`bench/quality.py`](bench/quality.py) asks 21 coding tasks (the 8 hard ones above plus 13 in
[`coding_tasks_v2.py`](bench/coding_tasks_v2.py), graded by unit tests in a container with no network) and 40
arithmetic word problems with exact answers ([`arith.py`](bench/arith.py)), three rounds each, temperature 0.

| | Coding, of 21 per round | Arithmetic, of 120 | Code speed, tok/s | Time per coding round |
|---|---|---|---|---|
| Serving build, thinking off | 13 / 15 / 16 | 120 | 64.7 mean | about 6 min |
| `STRATA_ROUTE_TAIL_SKIP` left at its default (7) | 16 / 15 / 15 | 120 | 64.6 mean | about 6 min |
| Serving build, thinking on, arithmetic only | not run | 120 | | |
| Serving build, thinking on, coding (1 round) | 18 | not run | 49–78 | 81 min |
| Ornith 1.5 35B-A3B, thinking off | 6 / 6 / 6 | 120 | 55.4 mean | about 4 min |
| Ornith 1.5 35B-A3B, thinking on (1 round) | 12 | not run | 46–58 | 85 min |
| Qwen3.5-122B-A10B, thinking off (1 round) | 13 | not run | 17.5 | about 25 min |

- **Tail-skip:** no difference in speed or score beyond the spread between rounds.
- **Arithmetic:** every arm scored 120/120, so this set is too easy to separate anything. It did not reproduce the
  wrong payment totals Junk GPU Lab reported for Strata; his problems are not mine.
- **Thinking on** allows 22,000 tokens per answer. Flash-Next never ran out: 11 of its answers used 16,700–18,500
  tokens, so its thinking appears to stop at a budget. Ornith spent the whole allowance thinking on 8 tasks and
  returned no code; only 1 of its 9 failures was wrong code. The thinking-on rows are one round each. Ornith's second
  round began with identical token counts and was stopped; Flash-Next's rounds vary.
- **Three tasks rarely pass** (`parse_csv`, `glob_match`, `knapsack_pick`). I re-ran the failing answers: the prompts
  state what the tests check and the answers have real bugs. `knapsack_pick` was passed by no model in 12 attempts;
  its tie-break rule (lexicographically smallest index list) makes it more of a puzzle than a coding task.

### Settings that changed nothing

**Layer split.** One speed run per arm.

| `layer-split` | Stories, tok/s | Code mean, tok/s | Experts in VRAM |
|---|---|---|---|
| 12,34 (serving) | 41–46 | 64.9 | 18,707 |
| 14,34 | 43.0–47.5 | 66.1 | 19,662 |
| 14,36 | 39.8–45.5 | 64.0 | 19,620 |
| 15,35 | 39.6–47.2 | 64.4 | 20,180 |

**Sustained load.** [`bench/sustain.sh`](bench/sustain.sh): 12 minutes of back-to-back 300-token stories. Speed
drops about 1% after 7 minutes. No run hit the 80 °C stop.

| `layer-split` | Mean tok/s | GPU peaks, °C | Throttled samples on the hottest card |
|---|---|---|---|
| 12,34 | 45.1 | 61 / 78 / 79 | 33 of 360 |
| 14,34 | 45.4 | 63 / 73 / 80 | 36 of 358 |
| 14,36 | 45.5 | 63 / 79 / 80 | 11 of 360 |

**180 W power limit against 140 W.** Prompts 248 / 398 / 496 tok/s against 234 / 366 / 456 (+6–9%). Writing no
faster. One card reached 79 °C with 2 throttled samples in a 4-minute run (75 °C and none at 140 W).

### Two-card peer mode

`--peer-device 1` on the two PCIe 3.0 x8 cards, with the same IQ3_S files and no new download:

```
GPUS=1,2
STRATA_SET="resident-experts kv-resident=32768 conversation-cache-mib=8192 peer-device=1 peer-reserve-mib=2000
            STRATA_GU_F16=2 STRATA_SM60_D20_SUB=1 STRATA_DOWN_F16=1 STRATA_B6_F16=1 STRATA_ROUTE_TAIL_SKIP=0"
```

| | Three-card layer split | Two-card peer mode |
|---|---|---|
| Reading a 4K / 16K / 32K prompt, tok/s | 234 / 366 / 456 | 325 / 355 / 342 |
| 300-token stories, tok/s | 40–46 | 35–48 |
| Code replies, tok/s | 52–74 | 37–55 |
| Experts held in VRAM | 18,707 | 11,804 (4,645 + 7,159) |
| Decode expert-cache hit rate | 96–99% | 83–86% |
| Hottest card | 75 °C | 80 °C after 4 minutes; the peer card 57 °C |

- It runs in low-RAM mode (`resident-experts`) on 64 GB, with 41.7 GiB of experts in RAM.
- The primary card does all the dense work alone. It reached the benchmark's 80 °C stop after 5 of the 8 easy
  coding tasks (all 5 passed).
- The engine refuses `--peer-device` together with `--layer-split`. Strata's Docker launcher keeps earlier
  `STRATA_SET` values in its `/data` folder, so a container that has run with a layer split needs a fresh `/data`.
- qr0n's IQ3_XXS weights, which would fit more experts on two cards, were not tried.

### Two other models

Both on [Junk GPU Lab's P100 llama.cpp fork](https://github.com/junkgpulab/llama.cpp-p100) at `c89a8dc`.

| | Flash-Next on Strata | Ornith 1.5 35B-A3B Q4_K_M | Qwen3.5-122B-A10B Q4_K_M |
|---|---|---|---|
| Cards | 3 | 2, tensor split, MTP 4 drafts | 3 plus CPU (6 threads) |
| Reading a 4K / 16K / 32K prompt, tok/s | 234 / 366 / 456 | 812 / 958 / 878 | 31 / 32 / 32 |
| 300-token stories, tok/s | 40–46 | 38.6–39.6 | 17.2–17.6 |
| Easy coding set | 8/8, 65 s | 8/8, 48 s | 8/8, 301 s |
| Hottest card | 75 °C | 74 °C | 64 °C |

- **Ornith** used 12.7 GB on each card at 128K context. Its MTP draft acceptance was low: about 15% in stories and
  32% in code.
- **The 122B** is 76.5 GB against 48 GB of VRAM. `-ngl 99 --n-cpu-moe N -sm layer` failed to load at every N from
  14 to 32, because the layer split puts every layer that keeps its experts on the last card. Leaving out `-ngl`
  and `--n-cpu-moe` lets the server fit itself: about 15 GB per card, roughly half the layers' experts on the CPU.

### Still not covered

- More than one round of the thinking-on coding runs.
- qr0n's IQ3_XXS weights in peer mode.
- An arithmetic set hard enough to separate engines.

## Reproduce

```
./build.sh                                   # ~15 min of all-core compiling; see the note below
docker compose up -d                         # needs STRATA_API_KEY in .env; edit the two volume paths
./bench/bench.sh fork http://127.0.0.1:8080 "$STRATA_API_KEY"
CODING_SET=hard ONLY_CODE=1 ./bench/bench.sh fork http://127.0.0.1:8080 "$STRATA_API_KEY"
```

- `build.sh` clones the fork at commit `8b1b0f5`, runs its `verify-source.sh` (which proves the bundled source is
  upstream v0.2.2 plus the 12 patches and nothing else), and builds Strata's own source Dockerfile for sm_60 on a
  CUDA 12.9 base.
- The fork ships its source without `.git`, and Strata's packaging step stops with "the commit of these sources is
  unknown". `build.sh` passes upstream's commit through `STRATA_COMMIT`.
- My rig's Ryzen 5 2600 has hard-reset under an all-core CUDA compile before, so I built on another machine and
  copied the image across: `docker save local/strata-pascal:0.2.2-qr0n | zstd | ssh rig 'zstd -d | docker load'`.
- Coming from stock 0.2.1, the fork reused the existing model files, pack and MTP layer. Nothing was downloaded or
  rebuilt, and it ran with the model folder mounted read-only.
- Flags go in `STRATA_SET` (they end up in the launch config's `env`). Without them the fork's kernels stay off.

## Credits

- [qr0n](https://github.com/qr0n/p100-strata) for the patches, and for measuring each one.
- [Niko1221 and contributors](https://github.com/Niko1221/Strata) for Strata.
- [Junk GPU Lab](https://www.youtube.com/@junkgpulab), whose
  [video](https://www.youtube.com/watch?v=zT09gR54e9w) on Strata and these patches is where I found them.

MIT licence.
