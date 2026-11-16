# Overnight run, 15–16 Nov 2026: results

Plan and configs: [night/PLAN.md](../../night/PLAN.md), [night/arms/](../../night/arms/). New duct, desk fan on, 140 W
cap. Each arm ran the speed benchmark (easy and hard sets), a 12-minute sustained run and three rounds of
`bench/quality.py`. The six Strata arms ran 20:59–02:00. The Bonsai, tensorless and settings arms are added below as
they finish.

## Strata arms

| | Serving: IQ3_S, 3 cards | Gyro-M, 3 cards | IQ2_XS, 3 cards | IQ3_XXS, 2 cards (peer) | Coder IQ1_M, 2 cards (peer) | Gyro-S, 1 card (GPU 0) |
|---|---|---|---|---|---|---|
| Coding, of 63 over three rounds | 44 (13 / 15 / 16) | 43 (16 / 14 / 13) | **32** (11 / 11 / 10) | 45 (17 / 15 / 13) | 38 (14 / 13 / 11) | 45 (14 Nov) |
| Arithmetic, of 120 | 120 | 119 | 117 | 120 | 120 | 115 (14 Nov) |
| Hard coding set, of 8 (one run) | 4–7 | 2 | 3 | 5 | 6 | aborted at 80 °C after 3 tasks |
| 300-token stories, tok/s | 41–46 | 35.3–38.7 | 45.6–47.5 | 37.8–48.3 | 43.4–43.9 | not reached (abort) |
| Code replies in the quality run, mean tok/s | 64.7 | 54.5 | 71.8 | 61.8 | 64.7 | about 40–47 |
| Sustained 12 min, mean tok/s | 45.7 | 38.0 | 49.5 | 46.1 | 41.9 | 26.9 |
| Sustained: peaks GPU 0 / 1 / 2, °C | 70 / 65 / 79 | 70 / 66 / 73 | 63 / 61 / 67 | 44 / **80** / 48 | 43 / 79 / 50 | **80** / 38 / 39 |
| Sustained: throttled samples on the hottest card | 0 of 360 | 0 | 0 | 77 of 361 | 3 of 360 | 153 of 360 |
| Reading a 4K / 16K / 32K prompt, tok/s | 234 / 366 / 456 | 252 / 385 / 474 | 256 / 396 / 489 | 332 / 360 / 350 | 324 / 339 / 333 | 233 / 266 / 203 |
| Decode expert-cache hit rate | 96–99% | 99.8–100% | 99.5–99.9% | 91–93% | 99.8–99.9% | 98% |
| RAM in use with the model loaded | 31–33 GB | 39–40 GB | 20–21 GB | 38–39 GB | 28–29 GB | 27 GB |

The serving column is from 10 Nov (quality, speeds) and 15 Nov (sustained run on the same cooling,
[`../cooling/`](../cooling/README.md)). The coding bar from the Gyro-S plan: 41 or more of 63 counts as equal to
serving, 38 or less is a real drop.

### What each arm says

- **Gyro-M on three cards: no.** Coding and arithmetic match serving, but it writes about 15% slower (38.0 against
  45.7 tok/s sustained, 54.5 against 64.7 on code) even with every expert in VRAM. It also uses more RAM.
- **IQ2_XS on three cards: faster and cooler, but clearly worse at coding.** About 8–11% faster and the coolest run of
  the night (67 °C peak). It scored 32 of 63 on coding with 11 / 11 / 10 per round, well below the bar, and failed
  the same nine tasks every round.
- **IQ3_XXS on two cards: serving-level quality and speed from two cards, limited by heat on the primary.** Coding
  45 of 63, arithmetic 120, sustained 46.1 tok/s. The primary card (GPU 1) drew 122 W on average, reached 80 °C and
  throttled in 77 of 361 samples, while the peer card stayed under 50 °C. Prompt reading is flat at about 350 tok/s
  where three cards reach 456 at 32K. It leaves GPU 0 and about 20 GB of RAM free for a second model.
- **Coder IQ1_M on two cards: not better at this coding set.** 38 of 63, at the "real drop" line, though it had the
  best single hard-set run (6 of 8). Its primary card ran at 79 °C with almost no throttling.
- **Qwen3.6-35B-A3B: did not run.** The launcher stopped with "this engine (0.1.47) does not run Qwen3.6-35B-A3B
  yet". It needs a newer Strata engine than the qr0n fork carries.
- **Gyro-S on GPU 0: still thermally limited.** With the new duct and the desk fan, GPU 0 carrying a whole model
  alone reached 80 °C in the first speed run, aborted both speed sets, and throttled in 153 of 360 samples of the
  sustained run (26.9 tok/s at 91 W). In the three-card layout the same card peaks at 70 °C on about 60 W.

### Across the arms

- **Nothing beats the serving config.** The only faster arm (IQ2_XS) loses a quarter of the coding score.
- **A single card carrying all the dense work throttles on this rig**, whichever card it is: GPU 1 (the best-cooled
  card) at 122 W in the two-card arms, GPU 0 at 91 W alone. The three-card split works because it spreads the dense
  work at 60–90 W a card.
- **A two-plus-one layout is now plausible on RAM:** IQ3_XXS on GPUs 1 and 2 uses 38–39 GB, which leaves room for a
  small model on GPU 0. Both halves would be heat-limited under sustained load.

## Bonsai and tensorless arms (02:07–07:19)

One 27B-class model on one card, as second-agent candidates, plus Kindi across two cards. Runners:
[`bonsai/run-arm.sh`](../../bonsai/run-arm.sh). Kindi reports no timings, so its speeds are tokens over wall-clock
time. The quality rounds were cut short on the one-card arms: with GPU 0 idling near 76 °C between answers they are
mostly waiting.

| | Bonsai 2 27B, Kindi 0.4.0, GPU 0 | Bonsai 2 27B, PrismML llama.cpp, GPU 0 | Qwen3.8-27B PN3, tensorless, GPU 0 | Bonsai 2 27B, Kindi, GPUs 1+2 |
|---|---|---|---|---|
| File | PTQ1_0 | PQ2_0 | PN3-P0k19 | PTQ1_0 |
| Sustained 12 min, mean tok/s | 19.8 | 15.7 | 14.1 | 34.5 |
| Sustained: hottest card | GPU 0, 80 °C, 91 W | GPU 0, 80 °C, 90 W | GPU 0, 80 °C, 91 W | GPU 2, 80 °C, 109 W |
| Sustained: throttled samples | 194 of 356 | 257 of 362 | 257 of 366 | 67 of 362 (GPU 2), 2 (GPU 1) |
| Reading a 4K / 16K / 32K prompt, tok/s | 86 / 88 / 49 | 122 / 100 / 57 | 163 / 149 / 65 | 133 / 165 / 156 |
| Speed runs | aborted at 80 °C | aborted at 80 °C | aborted at 80 °C | stories 26.7–34.8; easy set 6/8, then abort |
| Coding in `quality.py` | 11 of 58 answers (4/21, 4/21, 3/16) | stopped after 4 answers | not run | not run |
| Published figure for one P100 | 31.9 tok/s writing (video, 175 W) | 37.3 tok/s (video, 175 W) | 30.4 tok/s (its recipe) | 39.7 (Kindi docs, 300 W SXM2) |

- **All three one-card engines run, and all three are heat-limited on GPU 0.** The card reaches 80 °C within about
  four minutes and then averages 90 W with more than half the samples throttled. None gets within reach of its
  published speed, so these runs do not rank the engines; they show that GPU 0 cannot carry a dense 27B model at
  this cooling. The 32K prompt, read after the card is hot, is the slowest figure in every column.
- **Kindi on two cards is the best Bonsai result:** 34.5 tok/s sustained with the load spread over GPUs 1 and 2,
  though GPU 2 still throttled in 67 of 362 samples.
- **Kindi's coding score is very low and not yet trusted.** 11 of 58 where the Flash-Next models pass about 70%.
  It may be the model, or a setting of the run (`KINDI_REPEAT_STOP=1`, the exact head, the chat template); the
  failing answers have not been read. Kindi passed 6 of 8 on the easy set on two cards.
- **Long-prompt arithmetic:** Bonsai answered 1438 or 1439 where the answer is 1440, and 719 for 720, on both
  engines. tensorless's PN3 answered all three correctly.
- **RAM:** all of these use 1–2 GB of host RAM once loaded, so any of them fits beside a two-card Flash-Next.

## Settings on the serving config (07:19–08:54)

Settings other people's P100 repos report gains from, each as the serving config plus one change
([`night/arms/tune-*.env`](../../night/arms/)), speed runs only, with the unchanged config first and last.

| | Baseline, first | `pipeline-windows=2` | `spec-min-p=0.65 suffix-draft=0` | six sm_60 switches | `prefill-pipe=768` | Baseline, last |
|---|---|---|---|---|---|---|
| Reading 4K / 16K / 32K, tok/s | 236 / 375 / 471 | 236 / 375 / 470 | 234 / 374 / 469 | 235 / 374 / 469 | **260 / 400** / 470 | 236 / 374 / 469 |
| 300-token stories, tok/s | 42.0 / 44.3 / 46.0 | 40.3 / 45.5 / 46.2 | 42.9 / 48.1 / 48.5 | 41.8 / 44.2 / 46.1 | 38.8 / 45.9 / 46.5 | 41.7 / 44.3 / 47.3 |
| Easy code set, mean tok/s | 63.5 | 63.7 | 64.9 | 64.4 | 64.2 | 64.4 |
| Hard code set, mean tok/s | 65.5 | 64.0 | 65.1 | 65.1 | 65.1 | 65.4 |
| Easy / hard set passed, of 8 | 8 / 4 | 7 / 6 | 8 / 5 | 8 / 6 | 7 / 5 | 8 / 6 |

- **`prefill-pipe=768` is the one measurable gain:** prompt reading +10% at 4K and +7% at 16K, nothing at 32K, as
  its source reported. It changes answers, so it needs a quality run before adoption.
- **`pipeline-windows=2` did nothing on three cards.** The engine accepted it (it reserved 216 MiB on GPU 0 for the
  second verifier), but code speed is unchanged. The +23–26% it gave elsewhere was on two cards with a newer engine.
- **`spec-min-p=0.65` with `suffix-draft=0`: perhaps +4% on stories** (two of three were 48 tok/s against 44–47),
  nothing on code. Three stories are too few to call it.
- **The six sm_60 switches changed nothing**, so this engine version probably has them on already or ignores them.
- The two baselines agree within 1%, so the session was stable.
