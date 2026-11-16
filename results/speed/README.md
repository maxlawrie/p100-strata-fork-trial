# Speed attempts with the stronger desk fan, 16 Nov 2026

With the duct and the stronger desk fan the serving config peaks at 51 / 54 / 68 °C
([`../cooling/`](../cooling/README.md)), so heat no longer decides every result. These runs use that headroom.
Chain: [`speed/run-all.sh`](../../speed/run-all.sh), 09:57–13:04. Each arm ran `bench/bench.sh` (easy set, and the
hard set where noted) and the 12-minute `bench/sustain.sh`. 140 W limit unless stated. None of these arms has had
the three-round quality benchmark.

## Qwen3.6-35B-A3B on two cards: the fastest run on this rig

Unsloth's UD-Q4_K_XL file with its MTP head, on Junk GPU Lab's P100 llama.cpp (`c89a8dc`), GPUs 1 and 2, 65,536
context, q8_0 K/V, `--spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0.75`.

| | Serving: IQ3_S on Strata, 3 cards | Tensor split (`-sm tensor`) | Layer split (`-sm layer`) |
|---|---|---|---|
| Sustained 12 min, mean tok/s | 45.7 | **62.9** | 56.3 |
| 300-token stories, tok/s | 41–46 | 57.3–62.2 | 55.3–60.0 |
| Code replies, easy set, mean tok/s | 63.5–64.4 | **115** | 103 |
| Reading a 4K / 16K / 32K prompt, tok/s | 236 / 375 / 471 | **691 / 733 / 686** | 501 / 506 / 463 |
| Easy / hard coding set, of 8 (one run each) | 8 / 4–7 | 7 / 5 | 8 / not run |
| Sustained: peaks GPU 1 / GPU 2, °C | 54 / 68 | 64 / 80 | 55 / 77 |
| Sustained: throttled samples, GPU 2 | 0 | 28 of 361 | 0 |
| Mean power GPU 1 / GPU 2, W | 78 / 88 | 106 / 109 | 79 / 102 |
| RAM in use | 31–33 GB | 2 GB | 2 GB |

- Tensor split writes 38% faster than serving and reads prompts 1.5 to 3 times as fast, and held it for 12 minutes
  (62.4 tok/s over the last four). GPU 2 reached 80 °C and throttled in 8% of samples.
- Layer split is about 10% slower and did not throttle.
- MTP drafts were accepted at about 84% in the stories (110 of 131), against 15–32% for Ornith on the same engine.
- GPU 0 is idle and only 2 GB of RAM is used, so a second model fits beside it.
- Strata's qr0n engine (0.1.47) cannot run this model; that is why it is on llama.cpp.

## Quality rounds on the two fast two-card options (14:16–15:35)

`bench/quality.py`, three rounds of 21 coding tasks and 40 arithmetic problems, thinking off, temperature 0.

| | Serving: IQ3_S, qr0n Strata, 3 cards | IQ3_S on Megla's port, 2 cards | Qwen3.6-35B-A3B, llama.cpp, 2 cards |
|---|---|---|---|
| Coding, of 63 | 44 (13 / 15 / 16) | 42 (14 / 14 / 14) | 39 (13 / 13 / 13) |
| Arithmetic, of 120 | 120 | 120 | 117 (39 / 39 / 39) |
| Code replies in the run, mean tok/s | 64.7 | 58.0 | 107.8 |
| Time for the three rounds | about 25 min | 49 min (waits for GPU 2 to cool) | 27 min |

- **Megla's port scores like serving:** 42 of 63 against 44, above the 41 bar, and 120 of 120 on arithmetic. It is
  the same model, so this mostly confirms the port computes it correctly.
- **Qwen3.6-35B is slightly lower:** 39 of 63, between the "equal" bar (41) and the "real drop" line (38), and it
  misses the same arithmetic problem every round.
- **Both are fully deterministic here:** every round passed and failed exactly the same tasks ("mixed 0 of 21").
  So their three rounds are one sample repeated, not three, and 13 or 14 of 21 both sit inside the 13–16 that
  serving's rounds span. This benchmark cannot separate either of them from serving with confidence.
- They fail different tasks: Qwen3.6 fails `regex_match`, `b64`, `crc32` and `normpath`, which IQ3_S passes on
  Megla's port; IQ3_S there fails `parse_csv`, `weighted_intervals` and `big_mul`, which Qwen3.6 passes.

## Stock llama.cpp v1.0.0 (19:01–20:20)

llama.cpp 1.0.0 (13 Nov 2026, `b1b770d`) built for sm_60 on CUDA 12.9 ([llama1/Dockerfile](../../llama1/Dockerfile)); it
builds without changes. Arms `q36v1-tensor` and `fn1-3card` in [`bonsai/run-arm.sh`](../../bonsai/run-arm.sh).

**Qwen3.6-35B-A3B on two cards, the same file, cards and flags as the fork's run:**

| | Junk GPU Lab's P100 fork (`c89a8dc`) | Stock v1.0.0 |
|---|---|---|
| Sustained 12 min, mean tok/s | 62.9 | 38.0 |
| 300-token stories, tok/s | 57.3–62.2 | 36.1–39.4 |
| Code replies, easy set, mean tok/s | 115 | 71.1 |
| Reading a 4K / 16K / 32K prompt, tok/s | 691 / 733 / 686 | **873 / 851 / 742** |
| Easy / hard coding set, of 8 | 7 / 5 | 7 / 5 |
| Sustained: peaks GPU 1 / GPU 2, °C | 64 / 80 (throttled 8%) | 54 / 67 |
| Mean power GPU 1 / GPU 2, W | 106 / 109 | 77 / 82 |

- Stock 1.0 reads prompts 8–26% faster than the fork and writes about 40% slower. The fork's P100 decode kernels are
  what its writing speed comes from; they are not in stock llama.cpp.
- The cards draw about 80 W when writing on stock against 107 W on the fork: they are waiting, not working.

**The serving model (Flash-Next GSQ-RCO IQ3_S) on three cards:** stock 1.0 loads both shards and answers correctly
(180 / 720 / 1440, 7 of 8 on the easy set), which only Strata and its ports could do before. With the experts in
host memory (`-cmoe`), a 30,000 MiB MoE cache on the cards and no CPU share it is far too slow to use: 24–26 tok/s
reading, 15–20 tok/s stories, 20.5 tok/s sustained, against 375 and 45.7 for serving. Nothing was tuned
(`scripts/moe-cache-tune.py` exists for that) and it has no MTP drafting, since the IQ3_S file has no draft head.

## The port on three cards (16:15–17:53)

Megla's port has only ever run on two cards. Built here for three with a small patch
([megla/three-card.patch](../../megla/three-card.patch), [three-card-uneven.patch](../../megla/three-card-uneven.patch);
how in [megla/README.md](../../megla/README.md)). Same IQ3_S file, 64 GB profile, card order GPU 1, GPU 2, GPU 0.

| | Serving: qr0n, 3 cards | Port, 2 cards | Port, 3 cards: 256/192/192, two-card memory settings | 256/192/192, more experts in VRAM | **256/256/128**, more experts in VRAM |
|---|---|---|---|---|---|
| Label | | `fnx2-2card` | `fnx3a` | `fnx3b` | `fnx3u` |
| 300-token stories, tok/s | 41–46 | 52.0–54.7 | 36.7–37.6 | 44.3–48.2 | **48.0–54.6** |
| Code replies, easy set, mean tok/s | 64 | 56.0 | 27.7 | 39.9 | **50.3** |
| Reading a 4K / 16K / 32K prompt, tok/s | 236 / 375 / 471 | 678 / 896 / 891 | 290 / 536 / 537 | 328 / 561 / 561 | 381 / 613 / 616 |
| Easy coding set, of 8 | 8 | 7 | 8 | 8 | 8 |
| Sustained 12 min, mean tok/s | 45.7 | 53.8 (GPU 2 throttled 26%) | 38.6, no throttling | not run | **53.1, no throttling** |
| Sustained: peaks GPU 0 / 1 / 2, °C | 51 / 54 / 68 | idle / 69 / 80 | 70 / 56 / 68 | | 76 / 62 / 79 |
| Sustained: mean power GPU 0 / 1 / 2, W | 51 / 78 / 88 | – / 112 / 107 | 87 / 80 / 80 | | 95 / 94 / 98 |
| Coding, of 63 (three rounds) | 44 (13 / 15 / 16) | 42 (14 / 14 / 14) | | | 48 (16 / 16 / 16) |
| Arithmetic, of 120 | 120 | 120 | 40 of 40 (one round) | | 120 |
| Hard coding set, of 8 | 4–7 | 5 | 6 | | 7 |
| RAM once loaded | 31–33 GB | 45–47 GiB | 47 GiB | | 42–45 GiB |
| Peak RAM during the load | | 55.65 GiB | 52.4 GiB | 48.8 GiB | 48.1 GiB |
| VRAM used, GPU 0 / 1 / 2, GB | | – / 16.0 / 16.0 | 13.0 / 15.4 / 13.0 | 13.4 / 16.1 / 13.4 | 11.0 / 16.1 / 16.1 |

- **It runs and it is correct.** `fnx3a` scored 40 of 40 on an arithmetic round, 8 of 8 and 6 of 8 on the coding
  sets, and every run answered the three long-prompt checks correctly.
- **What had to change.** Two `static_assert(NCARD == 2)` in add-on functions the engine already skips on three
  cards, and the split rule: upstream gives three cards FF slices of 224 / 224 / 192, and the P100 expert kernel
  takes a card's columns only in units of 64 ("p100 moe: columns not in units of 64"). The patch makes the unit 64.
- **Memory settings matter a lot.** With the two-card values the three cards hold no more experts than two did and
  each has 2–3 GB of VRAM empty. Lowering `FNX_EXPERT_RAM_GIB` from 29 to 22.5 (21 is refused: "VRAM short by
  104 MiB on a card") gave +20–40% on writing.
- **The uneven split is the bigger gain:** 256 / 256 / 128 with GPU 0 (chipset slot) last gave another +10–25% on
  everything, which brings writing level with the two-card port. It needed `FNX_EXPERT_DYN_GIB` 14.5 instead of
  13 to fit the full context. GPU 0 then has 5 GB of VRAM unused.
- **Prompt reading is still about a third slower than on two cards** (613 against 896 tok/s at 16K). The two-card
  reading shortcut (`FNX_PF_SP`) is off on three cards, and its author measured it at only about 4%, so most of the
  gap is something else: the slow slot or the three-way exchange.
- **Card order:** GPU 1 first and GPU 2 first gave the same numbers (`fnx3b`, `fnx3d`). GPU 0 first was not
  tested: that run failed on a container-name clash in my script, not in the engine.
- **Sustained, the uneven split holds 53.1 tok/s with no throttling**, level with the two-card port's 53.8, which
  throttled in 26% of samples. It runs hot all the same: GPU 2 peaked at 79 °C and GPU 0 at 76 °C, with every card
  at 94–98 W.
- **Quality:** 48 of 63 on coding and 120 of 120 on arithmetic, deterministic like the two-card build (one sample
  repeated). It passes `parse_csv`, `run_limited` and `weighted_intervals`, which the two-card build fails, and fails
  `text_justify`, which that one passes: the different split changes the rounding, not the model.
- One run per variant.

## Megla123's two-card Strata port: the serving model on two cards (13:39–14:04)

The same IQ3_S file as serving, on [Megla123/qwen3.8-flash-next-2x-p100](https://github.com/Megla123/qwen3.8-flash-next-2x-p100)
(a P100 port of Strata's all-cards split engine, `a580ef7`), GPUs 1 and 2, its 64 GB profile: 262,144 context,
`--spec 4 --lookup 15`, draft min-p 0.7, exact routing. How it was built and run: [megla/README.md](../../megla/README.md).

| | Serving: qr0n Strata, 3 cards | Megla port, 2 cards | Its README, 64 GB mode |
|---|---|---|---|
| Sustained 12 min, mean tok/s | 45.7 | **53.8** | 63.3 (fresh writing) |
| 300-token stories, tok/s | 41–46 | 52.0–54.7 | |
| Code replies, easy / hard set, mean tok/s | 64 / 65 | 56.0 / 56.3 | |
| Reading a 4K / 16K / 32K prompt, tok/s | 236 / 375 / 471 | **678 / 896 / 891** | 768 (cold 38K read) |
| Easy / hard coding set, of 8 (one run each) | 8 / 4–7 | 7 / 5 | |
| Sustained: peaks GPU 1 / GPU 2, °C | 54 / 68 | 69 / 80 | |
| Sustained: throttled samples, GPU 2 | 0 | 94 of 359 | |
| Mean power GPU 1 / GPU 2, W | 78 / 88 | 112 / 107 | |
| RAM once loaded | 31–33 GB | 45–47 GB | 45–46.5 GiB |
| Peak RAM during the load | | 55.65 GiB | 55.6 GiB |
| Load time | about 80 s | about 2 min | about 5 min |

- **Prompt reading is 1.9 to 2.9 times serving's**, on the same model file and one card fewer, and faster than the
  author's own 64 GB figure despite this rig's x8 slots.
- **Stories are about 18% faster; code replies are about 13% slower.** Serving's drafts land better on code
  (64 tok/s) than on prose (45); this engine writes both at 52–56.
- **GPU 2 throttled in 26% of the sustained run** (80 °C at 107 W) while GPU 1 held 112 W at 69 °C, so the 53.8 tok/s
  is a throttled figure.
- **Memory behaved as its README says:** the load peaked at 55.65 GiB inside a 58 GiB cap with 4.2 GB spare on the
  rig, then held 45–47 GiB. That leaves about 12 GB for anything else, where serving leaves about 27 GB.
- **GPU 0 is free**, but there is little RAM left to run a second model beside it.
- One run each; quality has only the two eight-task sets. Its answers are not bit-identical to the qr0n build's.

## Power limit on the serving config

| | 140 W | 180 W | 220 W | 220 W + `prefill-pipe=768` |
|---|---|---|---|---|
| Reading a 4K / 16K / 32K prompt, tok/s | 236 / 375 / 471 | 252 / 403 / 510 | 261 / 420 / 532 | **273 / 439 / 533** |
| Sustained writing, mean tok/s | 45.7 | 45.6 | 45.9 | not run |
| Code replies, easy set, mean tok/s | 63.5–64.4 | 64.1 | 64.5 | 64.6 |
| Sustained: peaks GPU 0 / 1 / 2, °C | 51 / 54 / 68 | 54 / 56 / 74 | 54 / 56 / 75 | |
| Throttled samples | 0 | 0 | 0 | |

- Prompt reading rises with the limit: +7–8% at 180 W, +11–13% at 220 W, +13–17% with `prefill-pipe=768` as well.
- Writing does not change: the cards already run at their full 1328 MHz when writing.
- Only GPU 2 gets hotter, by 6–7 °C, which leaves 5 °C under the throttle point. This needs the stronger desk fan.
- `prefill-pipe=768` changes answers and has not had a quality run.

## One-card engines on GPU 1

The arms that throttled on GPU 0 overnight ([`../night/`](../night/README.md)), repeated on the best-cooled card.

| | Gyro-S, Strata | Bonsai 2 27B, Kindi 0.4.0 | Bonsai 2 27B, PrismML llama.cpp | Qwen3.8-27B PN3, tensorless |
|---|---|---|---|---|
| Sustained 12 min, mean tok/s | **40.0** | 27.9 | 25.0 | 25.3 |
| Overnight on GPU 0 (throttled) | 26.9 | 19.8 | 15.7 | 14.1 |
| Published one-card figure | 58.6–64.9 | 31.9–36 | 37.3 | 30.4 |
| 300-token stories, tok/s | 30.9–41.8 | 23.2–27.7 | 24.9–25.0 | 25.2–25.3 |
| Code replies, easy set, mean tok/s | 51.2 | not reported | 25.0 | 25.2 |
| Reading a 4K / 16K / 32K prompt, tok/s | 263 / 287 / 279 | 89 / 108 / 102 | 123 / 117 / 107 | **164 / 154 / 137** |
| Easy coding set, of 8 | 7 | 8 | 8 | 8 |
| Sustained: GPU 1 peak and mean power | 74 °C, 129 W | 73 °C, 130 W | 74 °C, 132 W | 74 °C, 131 W |
| Throttled samples | 0 | 0 | 0 | 0 |

- No arm throttled: GPU 1 holds 130 W at 73–74 °C.
- **Gyro-S on Strata is the fastest one-card option** at 40 tok/s, 60% faster than the 27B engines.
- **The three 27B engines are close:** Kindi 27.9, tensorless 25.3, llama.cpp 25.0 tok/s. Kindi writes fastest and
  reads slowest; tensorless reads fastest.
- All of them fall short of their published figures. Every card sat at 129–132 W against the 140 W limit, and the
  published runs used 175–300 W, so the limit is the likely cause; that was not tested here.
- Kindi passed 8 of 8 on the easy set, so its 11 of 58 overnight was probably an artefact of that throttled run.
- Bonsai still answers 1439 for 1440 on the long-prompt check on Kindi, and gave no number at 32K on llama.cpp.

## Layer split 12,36 (in `../night/`, arm `split-12-36`)

Two layers moved from GPU 2 to GPU 1: peaks 52 / 56 / 68 °C against 51 / 54 / 68 °C, and prompt reading
234 / 361 / 444 against 236 / 375 / 471 tok/s. No thermal gain and slower reading; serving stays at 12,34.
