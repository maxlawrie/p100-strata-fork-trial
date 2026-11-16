# Gyro-S trial plan

Whether agentionai's Gyro-S is worth running on the 3× P100 rig, after
[Junk GPU Lab's video](https://www.youtube.com/watch?v=do25PM72as8) (97/100 GSM8K and 75/80 HumanEval+ on one P100
at 58.6 / 64.9 tok/s). All three arms were run on 14 Nov 2026; see [RESULTS.md](RESULTS.md).

## What is already known

- **Strata's own docs rate Gyro-S below IQ2_XS.** `docs/GYRO.md` in the fork's source: KL 0.268 against IQ2_XS's
  0.236 (13% worse) with 24% fewer bytes, "pick Gyro-S where nothing bigger fits". The rig serves IQ3_S, two steps
  above that. The video's equal scores are on GSM8K and HumanEval+, and my arithmetic set already showed that easy
  sets saturate (120/120 for every arm).
- **It should fit entirely in VRAM.** The weights are 29.7 GB (the other 28.8 GB of the 58.5 GB file is the n-gram
  table). Two cards hold 32 GB, three hold 48 GB, so the expert-cache hit rate should be at or near 100% without
  low-RAM mode. Serving is already at 96–99%, so this is worth little on three cards.
- **No rebuild.** The video used the same fork commit as `build.sh` (`8b1b0f5`). The P100 trellis path
  (`STRATA_TQ_STAGE`) is on by default in v0.2.2; the release notes put Gyro-S at 0.90–0.96 of Q2_0's decode speed
  on a P100.
- **Left out:** `STRATA_Q8_SM60=1`, which the video had on. It needs a requantized second copy of the model and a
  launcher bypass (README, "What each step does"), and the dense matrices in a Gyro file are Q5_K/Q6_K, not what
  `q8_dense_gguf.py` was run on here.

## Questions, one arm each

| Arm | Layout | Question | It is worth adopting if |
|---|---|---|---|
| `1card` | GPU 1, 32K | Can one card serve Flash-Next well enough to free the other two for a second model? | stories ≥ 40 tok/s and coding within reach of serving (below) |
| `2card-peer` | GPUs 1,2 peer mode, 64K | Does a file that fits in VRAM fix peer mode? IQ3_S got 35–48 / 37–55 tok/s at an 83–86% hit rate and stopped at 80 °C. | faster than three-card serving **and** the sustained run finishes under 80 °C |
| `3card` | serving layout, 256K | Like for like against serving: only the model changes. | faster than serving by more than the spread between runs, with no loss in coding |

Serving baseline (10 Nov, `results/` and `results/followup/`): stories 41–46 tok/s, code 52–74, coding
13 / 15 / 16 of 21 over three rounds, arithmetic 120/120.

**Quality bar:** the three coding rounds sum to 44 of 63 for serving, with rounds between 13 and 16. Treat Gyro-S
as equal only if its total is 41 or more; 38 or less is a real drop. In between is not settled by three rounds.

## Before starting

1. On the rig, `df -h /srv/strata`: the first start needs about 60 GB (58.5 GB file, 1.5 GB pack). The 58.6 GB
   Q8 copy from the Q8 trial can go if it is still there.
2. Pull this branch on the rig. `STRATA_API_KEY` in `.env` as for `compose.yaml`.
3. Serving is down for the whole run. Each arm takes about 35 minutes after the model has loaded (speed runs about
   8 minutes, three quality rounds about 25), longer when cards have to cool. Add 12 minutes with `SUSTAIN=1`.

## Run

```
gyro/run-arm.sh 3card                    # first: also does the download and the pack
SUSTAIN=1 gyro/run-arm.sh 2card-peer
gyro/run-arm.sh 1card
```

`run-arm.sh` stops the serving container, starts Gyro-S from `gyro/compose.gyro.yaml` with the arm's settings
(`gyro/arms/*.env`), waits for the model, runs `bench/bench.sh` (easy and hard), optionally `bench/sustain.sh`, then
`bench/quality.py` (three rounds), and starts serving again when it exits. Output goes to `results/gyro/`:
`speed-<arm>.txt`, `speed-<arm>-hard.txt`, `quality-<arm>.txt`, `sustain-<arm>.txt`, `load-<arm>.txt` (the engine's
lines about experts and cache) and `ram-<arm>.txt`.

Start with `3card`: if Gyro-S loses clearly on coding there, the other two arms only matter for the one-card
question, and `2card-peer` can be skipped.

## Things that may need a fix on first contact

- **Key names in `STRATA_SET`.** `vram-reserve-later-mib` is the video's engine flag; I have only used the other
  keys through the launcher. If it is refused, drop it from `gyro/arms/2card-peer.env`.
- **`trim-stage-weights` with a Gyro pack** is untested. If the engine refuses it, remove it from
  `gyro/arms/3card.env` and note that the arm then differs from serving in one more way.
- **`load-<arm>.txt` is a grep** of the container log for expert, slot, arena, peer and hit-rate lines. If the
  lines of interest are worded differently, read `docker logs strata-gyro` before the script exits (`KEEP=1`).
- **Model folder is mounted read-write** for the trial container, because the first start downloads into it. It
  adds files beside the IQ3_S ones and should not touch them.

## Not covered

Gyro-M (92 GB download). Correction, 14 Nov: I wrote here that it has 63 GB of weights and cannot fit the three
cards. Strata's catalog gives 35 GB (the file carries a larger n-gram table), so it does fit in 48 GB of VRAM and is
worth a three-card run; see [TODO.md](../TODO.md). Thinking on. Vision.
