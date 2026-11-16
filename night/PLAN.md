# Overnight test run, 15–16 Nov 2026

The open tests from [TODO.md](../TODO.md) that can run unattended, chained on the 3× P100 rig with the new duct and
the desk fan on. Started 15 Nov 20:59. Serving (`strata`) is down for the whole run and is started again at the end;
the batch worker that uses the rig stays stopped.

## Arms, in order

Each arm is one model in one layout, set in [`arms/<arm>.env`](arms/). Every arm uses the serving image
(`local/strata-pascal:0.2.2-qr0n`) and the fork's kernel flags unless noted.

| # | Arm | Model | Cards | Context | Question |
|---|---|---|---|---|---|
| 1 | `gyro-m-3card` | Flash-Next Gyro-M | 0,1,2, split 12,34 | 256K | Does a model that fits entirely in VRAM at about IQ3_XXS quality beat serving on speed without losing coding? |
| 2 | `iq2xs-3card` | Flash-Next IQ2_XS | 0,1,2, split 12,34 | 256K | Same question one size down from IQ3_XXS, with exactly the serving settings. |
| 3 | `iq3xxs-2card-peer` | Flash-Next IQ3_XXS | 1,2, peer mode | 64K | Can two cards carry a Flash-Next close to serving quality, and does the primary card stay under 80 °C now? |
| 4 | `coder-2card-peer` | Flash-Next Coder IQ1_M | 1,2, peer mode | 64K | Coding-only model whose experts all fit on two cards: speed and coding score. |
| 5 | `qwen36-1card` | Qwen3.6-35B-A3B UD-Q4_K_XL | 0 | 32K | A second-agent candidate on the card a second agent would get. |
| 6 | `gyro-s-1card` | Flash-Next Gyro-S | 0 | 32K | The parts the 14 Nov arm lost to heat: speed runs, hard set, sustained run. Quality is not repeated. |

## What each arm runs

[`run-arm.sh`](run-arm.sh) starts the model, waits for it (the first start of arms 1–4 prepares the pack, about
100 GB in total; 368 GB was free), then:

1. `bench/bench.sh`: 4K / 16K / 32K prompt, three 300-token stories, a tool call, the 8 easy coding tasks.
2. `bench/bench.sh` with the 8 hard coding tasks.
3. `bench/sustain.sh`: 12 minutes of back-to-back stories, the heat test.
4. `bench/quality.py`: 21 coding tasks and 40 arithmetic problems, three rounds.

Before each step it waits up to 8 minutes for every card to be at or below 58 °C. The benchmarks keep their own
guards: `bench.sh` and `sustain.sh` stop at 80 °C, `quality.py` waits for every card to be under 76 °C between
requests.

[`run-all.sh`](run-all.sh) runs the arms in order, lets the cards cool to 50 °C with nothing loaded between arms,
gives each arm at most 170 minutes, logs a failed arm and moves on, and starts `strata` again at the end.

Expected: about 70 minutes an arm plus pack preparation, so roughly 7 hours, finishing around 04:00–05:00.

## Where the output goes

On the rig, `~/p100-strata-fork-trial/results/night/`: `run-all.log` (progress), `arm-<arm>.log`, and per arm
`speed-`, `speed-…-hard`, `sustain-`, `quality-`, `load-`, `ram-` and `launch-<arm>.txt`.

```
ssh -t rig tail -f p100-strata-fork-trial/results/night/run-all.log
```

## Comparison points

- Serving (IQ3_S, three cards): stories 41–46 tok/s, code 52–74, coding 13 / 15 / 16 of 21, arithmetic 120/120,
  sustained 45.7 tok/s with no throttling on today's cooling.
- Gyro-S (14 Nov): coding 45–48 of 63, arithmetic 114–115 of 120.
- Quality bar from the Gyro-S plan: a coding total of 41 or more of 63 counts as equal to serving, 38 or less is a
  real drop.

## Left out tonight, and why

- **Ternary Bonsai 2 27B (PrismML llama.cpp fork, Kindi 0.4.0).** Neither engine is built on the rig. Both have to be
  found, checked and compiled first, and an all-core compile has hard-reset this rig before.
- **Layout A (IQ3_S on two cards plus a second model on GPU 0 at the same time).** IQ3_S in peer mode kept 41.7 GiB of
  experts in RAM and Gyro-S on one card used 27 GB, which is more than the rig's 60 GB together. It also needs a
  second server on another port, which has not been tried. Tonight's `ram-<arm>.txt` files give the numbers to plan
  it with.
- **Batch worker pilot against Gyro-S** and **a small model on the workstation's RTX 5050.** Both run
  real jobs against real data, which should not happen unattended.
- **Gyro-S 1card quality** was completed on 14 Nov.

## If something goes wrong

- The chain stops by itself only at the end. To stop it early: `pkill -f night/run-all.sh` on the rig, then
  `docker rm -f strata-night; docker start strata`.
- The desk fan has to stay on. Without it GPU 0 and GPU 2 throttle within 8 minutes of sustained load; the cards
  protect themselves, but the speed numbers would be worthless.
