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

A third round on 14–16 Nov (other quantizations, one-card and two-card engines, a new cooling duct, and a two-card
port of this engine built for three cards) is under [More experiments, 14–16 Nov](#more-experiments-1416-nov). The
rig still serves the same config, but three other setups now write prose and read prompts faster than it does.

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

## More experiments, 14–16 Nov

Each part has its own notes with the full tables, and the raw output beside them. Write-up:
[Two P100s now beat three, on paper](https://lawrie.co.nz/posts/p100-two-cards.html).

| Part | Notes | Raw output |
|---|---|---|
| Gyro-S on one, two and three cards (14 Nov) | [gyro/RESULTS.md](gyro/RESULTS.md) | [results/gyro/](results/gyro/) |
| A 3D-printed cooling duct, and two desk fans (15–16 Nov) | [results/cooling/README.md](results/cooling/README.md) | [results/cooling/](results/cooling/) |
| Overnight: other quantizations, one-card engines, settings (15–16 Nov) | [results/night/README.md](results/night/README.md) | [results/night/](results/night/) |
| Two-card engines, power limit, the port on three cards (16 Nov) | [results/speed/README.md](results/speed/README.md), [megla/README.md](megla/README.md) | [results/speed/](results/speed/) |

**Short version:** heat decided most of these results until the cooling was fixed. Once it was, two setups on two
cards beat the serving config on prose and on prompt reading: Qwen3.6-35B-A3B on llama.cpp, and the serving model
itself on Megla123's two-card port of Strata. Both push one card to its 80 °C throttle point. The port, patched
here to run on three cards, holds the same writing speed without throttling. My benchmark can't separate any of
them from serving on quality, so nothing has been switched yet.

### The candidates against serving

All at a 140 W limit with the duct and the stronger desk fan. "Sustained" is the mean of 12 minutes of back-to-back
300-token stories ([`bench/sustain.sh`](bench/sustain.sh)). Coding and arithmetic are three rounds of
[`bench/quality.py`](bench/quality.py), thinking off, temperature 0.

| | Serving: IQ3_S, qr0n Strata, 3 cards | IQ3_S, Megla's port, 2 cards | IQ3_S, Megla's port patched for 3 cards (256 / 256 / 128) | Qwen3.6-35B-A3B UD-Q4_K_XL, llama.cpp fork, 2 cards |
|---|---|---|---|---|
| Sustained writing, tok/s | 45.7 | 53.8 | 53.1 | **62.9** |
| Code replies, easy set, mean tok/s | 64 | 56 | 50 | **115** |
| Reading a 4K / 16K / 32K prompt, tok/s | 236 / 375 / 471 | **678 / 896 / 891** | 381 / 613 / 616 | 691 / 733 / 686 |
| Coding, of 63 | 44 (13 / 15 / 16) | 42 (14 / 14 / 14) | 48 (16 / 16 / 16) | 39 (13 / 13 / 13) |
| Arithmetic, of 120 | 120 | 120 | 120 | 117 |
| Sustained: hottest card | 68 °C, never throttled | 80 °C, throttled in 94 of 359 samples | 79 °C, never throttled | 80 °C, throttled in 28 of 361 samples |
| RAM in use once loaded | 31–33 GB | 45–47 GB | 42–45 GB | 2 GB |
| Context | 256K | 256K | 256K | 64K |

- **Qwen3.6-35B-A3B** is on [Junk GPU Lab's P100 llama.cpp](https://github.com/junkgpulab/llama.cpp-p100) at
  `c89a8dc` with `-sm tensor` and the model's MTP head. It is the fastest thing the rig has run. With `-sm layer` it
  is about 10% slower (56.3 tok/s sustained) and does not throttle. The Strata engine in the qr0n fork (0.1.47)
  refuses this model.
- **[Megla123's port](https://github.com/Megla123/qwen3.8-flash-next-2x-p100)** (`a580ef7`) runs the same IQ3_S file
  as serving. It reads prompts 1.9 to 2.9 times as fast and writes stories about 18% faster, but its code replies
  are about 13% slower than serving's, and its load peaks at 55.65 GiB of RAM on a 64 GB machine.
- **The port on three cards** is the only candidate that beat serving on writing without throttling: 53.1 tok/s
  for 12 minutes, 16% above serving, with prompt reading 30–60% faster. Its code replies are about 20% slower, and
  it runs every card at 94–98 W, with GPU 2 peaking at 79 °C. Details are [below](#meglas-port-on-three-cards).
- **All three candidates gave the same answers in all three rounds**, so their three rounds are one sample each.
  13, 14 and 16 of 21 all sit inside the 13–16 that serving's own rounds span. The benchmark cannot rank these four.
- **Both leave GPU 0 idle.** Qwen3.6 also leaves about 58 GB of RAM free, so a second model fits beside it.

### Cooling

- **A card that does all the dense work alone throttles at 140 W.** That was true of the primary card in peer mode
  (122 W, 80 °C) and of any one-card model on GPU 0 (91 W, 80 °C). The three-card layer split works because it
  spreads the work at 50–90 W a card.
- **The printed duct needs help.** On the two front case fans alone it was worse than the old shrouds: GPU 0
  throttled on about 60 W. With a desk fan blowing into it there was no throttling, and with a stronger desk fan the
  serving config peaked at 51 / 54 / 68 °C over 12 minutes, against 61 / 78 / 79 °C under the old shrouds.
- **Speed of the serving config did not change** (45.1 → 45.7 tok/s sustained). It was only throttling in about 9%
  of samples before. What the cooling bought is room for the layouts below.
- GPU 2, the middle card, is the hottest in every layout.

### The same model at other sizes, and on fewer cards

Strata on the qr0n fork, same settings as serving. The cooling differs between rows: the Gyro-S two- and three-card
rows are from 14 Nov under the old shrouds, the rest from the overnight run with the duct and the first desk fan,
and the Gyro-S GPU 1 figure from 16 Nov with the stronger fan.

| | Coding, of 63 | Arithmetic, of 120 | Sustained, tok/s | Verdict |
|---|---|---|---|---|
| IQ3_S, 3 cards (serving) | 44 | 120 | 45.7 | |
| Gyro-M, 3 cards | 43 | 119 | 38.0 | Same quality, about 15% slower |
| Gyro-S, 3 cards | 46 | 114 | not run | No faster; misses the same two sums every round |
| IQ2_XS, 3 cards | **32** | 117 | 49.5 | 8–11% faster and cooler, and clearly worse at coding |
| IQ3_XXS, 2 cards (peer mode) | 45 | 120 | 46.1 | Matches serving from two cards; primary card throttles |
| Coder IQ1_M, 2 cards (peer mode) | 38 | 120 | 41.9 | Not better at this coding set |
| Gyro-S, 2 cards (peer mode) | 48 | 115 | 39.1 | Primary card throttled in half the samples |
| Gyro-S, 1 card | 45 | 115 | 40.0 on GPU 1; 26.9 on GPU 0 | Same answers on one card |

The coding bar set before the runs: 41 or more of 63 counts as equal to serving, 38 or less as a real drop.

### One card

Sustained writing on GPU 1, the best-cooled card, with the stronger desk fan. None throttled.

| | Sustained, tok/s | Reading 4K / 16K / 32K, tok/s | Published one-card figure |
|---|---|---|---|
| Flash-Next Gyro-S, Strata | **40.0** | 263 / 287 / 279 | 58.6–64.9 |
| Ternary Bonsai 2 27B, Kindi 0.4.0 | 27.9 | 89 / 108 / 102 | 31.9–36 |
| Qwen3.8-27B PN3, tensorless | 25.3 | 164 / 154 / 137 | 30.4 |
| Ternary Bonsai 2 27B, [PrismML's llama.cpp](https://github.com/PrismML-Eng/llama.cpp) | 25.0 | 123 / 117 / 107 | 37.3 |

Every card sat at 129–132 W against the 140 W limit, and the published runs used 175–300 W. That is the likely
reason for the gap; it was not tested. On GPU 0 overnight all four throttled and ran at 14–27 tok/s.

### Megla's port on three cards

The port has only run on two cards. [megla/three-card.patch](megla/three-card.patch) makes it build and run on
three: two `static_assert(NCARD == 2)` become run-time checks, and the split works in units of 64 columns, which is
what the P100 expert kernel accepts. Nothing in the kernels changes.

| | Port, 2 cards | 3 cards, 256 / 192 / 192, two-card memory settings | 3 cards, 256 / 192 / 192, more experts in VRAM | 3 cards, 256 / 256 / 128, more experts in VRAM |
|---|---|---|---|---|
| 300-token stories, tok/s | 52.0–54.7 | 36.7–37.6 | 44.3–48.2 | 48.0–54.6 |
| Code replies, easy set, mean tok/s | 56.0 | 27.7 | 39.9 | 50.3 |
| Reading a 4K / 16K / 32K prompt, tok/s | 678 / 896 / 891 | 290 / 536 / 537 | 328 / 561 / 561 | 381 / 613 / 616 |

- An uneven split ([three-card-uneven.patch](megla/three-card-uneven.patch)), with the chipset-slot card given a
  smaller share and placed last, brings writing level with two cards. Prompt reading stays about a third slower.
- **Sustained, the uneven split held 53.1 tok/s for 12 minutes with no throttling**, against 53.8 on two cards
  with GPU 2 throttled in 26% of samples. Peaks were 76 / 62 / 79 °C. The even split ran at 38.6 tok/s.
- **Quality on the uneven split:** 48 of 63 on coding (16 / 16 / 16), 120 of 120 on arithmetic, 7 of 8 on the hard
  set. It passes three tasks the two-card build fails and fails one it passes, on the same model file: the
  different split changes the rounding.

### Stock llama.cpp v1.0.0

llama.cpp 1.0.0 (13 Nov 2026) builds for the P100 without changes on CUDA 12.9
([llama1/Dockerfile](llama1/Dockerfile)).

| Qwen3.6-35B-A3B, 2 cards, same file and flags | Junk GPU Lab's P100 fork (`c89a8dc`) | Stock v1.0.0 |
|---|---|---|
| Sustained writing, tok/s | **62.9** | 38.0 |
| Code replies, easy set, mean tok/s | **115** | 71 |
| Reading a 4K / 16K / 32K prompt, tok/s | 691 / 733 / 686 | **873 / 851 / 742** |
| Sustained: peaks GPU 1 / GPU 2, °C | 64 / 80 | 54 / 67 |
| Mean power GPU 1 / GPU 2, W | 106 / 109 | 77 / 82 |

- Stock reads prompts 8–26% faster than the fork and writes about 40% slower. The fork's P100 decode kernels are
  where its writing speed comes from, and they are not in stock llama.cpp.
- Stock 1.0 also loads the serving model (Flash-Next IQ3_S) across three cards and answers correctly, which only
  Strata and its ports did before. Untuned and without drafting it is far too slow to use: 20.5 tok/s sustained and
  24–26 tok/s reading, against 45.7 and 375 for serving.

### Settings and power limit on the serving config

- **Power limit:** prompt reading rises with it (+7–8% at 180 W, +11–13% at 220 W). Writing does not change at any
  limit. At 220 W GPU 2 is 6–7 °C hotter, at 75 °C.
- **`prefill-pipe=768`:** prompt reading +10% at 4K and +7% at 16K, nothing at 32K. It changes answers and has not
  had a quality run.
- **`pipeline-windows=2`, six sm_60 switches, `layer-split=12,36`:** no change.
- **`spec-min-p=0.65 suffix-draft=0`:** perhaps +4% on stories, from three stories.

### What these runs can't say

- **Quality.** 21 tasks at temperature 0 cannot rank engines that give the same answers every round. Serving's
  rounds vary (13 / 15 / 16); the other three engines' do not. The port scored 42 on two cards and 48 on three
  with the same model file, which shows how much one sample moves.
- **The two-card speeds are throttled figures.** GPU 2 hit 80 °C in both. Neither has been run with GPU 2 kept
  under the limit, other than Qwen3.6 with `-sm layer`.
- **The three-card port has little thermal margin.** GPU 2 peaked at 79 °C after 12 minutes with the stronger desk
  fan on; longer runs have not been done.
- **Most speed figures are one run.** The two unchanged-config runs in the settings session agreed within 1%.
- Bonsai on Kindi scored 11 of 58 on coding in a throttled overnight run and 8 of 8 on the easy set the next day.
  Its coding score is not known.

Open tests are in [TODO.md](TODO.md).

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
- [Megla123](https://github.com/Megla123/qwen3.8-flash-next-2x-p100) for the two-card port.
- [Junk GPU Lab](https://www.youtube.com/@junkgpulab), whose
  [video](https://www.youtube.com/watch?v=zT09gR54e9w) on Strata and these patches is where I found them.

MIT licence.
