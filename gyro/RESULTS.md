# Gyro-S trial: results

Run on 14 Nov 2026 on the 3× P100 rig, following [PLAN.md](PLAN.md). Raw output is in
[`results/gyro/`](../results/gyro/).

**Verdict: do not swap Gyro-S into serving.** It matches the serving model (Qwen3.8 Flash-Next IQ3_S) on coding,
loses a little on arithmetic, and is no faster on three cards. Its one real advantage is that it runs on a single
card with the same answers, which matters only for a two-agent layout, and that layout is blocked by cooling.

## Numbers

| | Gyro-S, 1 card (GPU 0, 32K) | Gyro-S, 2 cards (peer, 64K) | Gyro-S, 3 cards (256K) | Serving (IQ3_S, 10 Nov) |
|---|---|---|---|---|
| Coding, of 63 over three rounds | 45 (15 / 17 / 13) | 48 (16 / 16 / 16) | 46 (15 / 15 / 16) | 44 (13 / 15 / 16) |
| Arithmetic, of 120 | 115 (38 / 39 / 38) | 115 (38 / 39 / 38) | 114 (38 / 38 / 38) | 120 |
| Code speed in the quality run, tok/s | about 37–51 | 65.0 mean | 66.5 mean | 64.7 mean |
| Stories, tok/s | not measured (run aborted) | not measured (run aborted) | 41.7–44.6 | 41–46 |
| Sustained 12 min, mean tok/s | not run | 39.1 | not run | 45.1 |
| Prompt reading 4K / 16K / 32K, tok/s | 258 / 308 / 184 | 300 / 332 / 226 | 285 / 442 / 546 | 234 / 366 / 456 |
| Hard coding speed set, of 8 | aborted after 1 task | aborted | 5 | — |
| Hottest card in the speed runs | GPU 0, 80 °C | GPU 1, 80 °C | GPU 1, 80 °C (hard run) | — |
| RAM in use with the model loaded | 27 GB | see `ram-2card-peer.txt` | see `ram-3card.txt` | — |

## Findings

1. **Coding quality is equal to serving.** All three arms clear the bar set in the plan (41 of 63). The layout
   does not change the answers: the same tasks fail on one, two and three cards (`parse_csv` and `knapsack_pick`
   never pass).
2. **Arithmetic is slightly worse, and consistently so.** Gyro-S misses the same problems every round (`arith01`
   and `arith31`; `arith31` answers 1573.25 for 1873.25). Serving gets 40 of 40 every round. On the 4K prompt test
   it answered 179 where the answer is 180, in every arm.
3. **Three cards: no gain.** All 24,576 experts sit in VRAM, but serving was already at a 96–99% hit rate, so speed
   is the same within the spread between runs. Prompt reading is somewhat faster (546 against 456 tok/s at 32K).
4. **Two cards in peer mode: fine in bursts, not sustained.** With cooling pauses between requests it matches
   three cards (65.0 tok/s). Under sustained load it drops to 39.1 tok/s with GPU 1 throttled in 173 of 358
   samples, while the peer card sits at 45–55 °C. All the dense work lands on one card.
5. **One card: same answers, about a quarter slower, thermally limited.** GPU 0 went from 46 °C to 79 °C in two
   minutes and throttled in 51 of 119 samples; it then idles at 75–76 °C with the model loaded. GPU 0 is on the
   chipset's PCIe 2.0 x4 slot, and this run cannot separate the slot's cost from the throttling. The video's
   58.6 / 64.9 tok/s on one card was not reproduced here.
6. **Heat is the limit in every reduced layout.** Whichever card carries the dense layers reaches 80 °C at the
   140 W cap. A two-agent layout (Flash-Next-class model on one or two cards, a second model on the rest) needs
   better cooling before it is worth testing further.

## Notes on the run

- The 1card arm was moved from GPU 1 to GPU 0 before it started: GPU 1 was heat-soaked from the two-card arm, and
  GPU 0 is the card a second agent would get.
- `bench/bench.sh` aborts at 80 °C, so the 1card and 2card-peer speed files are incomplete; the per-request speeds
  in `quality-<arm>.txt` are the usable speed figures for those arms.
- `quality.py` waits for every card to be under 76 °C between requests, so a card that idles at 75 °C makes an arm
  take 90 minutes instead of 35.
- `run-arm.sh` greps `docker logs` for the load lines and gets nothing useful. The engine log is
  `/srv/strata-state-gyro/<arm>/state/strata/launch/docker.engine.log`; `load-<arm>.txt` here was taken from that.
- Nothing in `STRATA_SET` was refused (`vram-reserve-later-mib`, `trim-stage-weights` with a Gyro pack).

## State of the rig after the run (14 Nov, 12:10)

- Gyro-S is still loaded on GPU 0 (container `strata-gyro`, 1card arm). The serving container `strata` is stopped.
- The batch worker that uses the rig (on another machine) is stopped.
- The IQ3_S pack (49 GB) was moved off the rig to make room and now exists only on another machine
  (sha256-verified when parked). It belongs at `/srv/strata/packs/iq3_s`,
  root-owned.
- The rig has 43 GB free, less than the pack, so serving cannot come back until either the 55 GB Gyro-S model
  (`/srv/strata/models/gyro-Gyro-S`) is deleted or the disk is larger. The plan is to swap in the 1 TB SSD first.

To restore serving after the SSD swap:

```
docker compose -p strata-gyro --project-directory . -f gyro/compose.gyro.yaml --env-file .env --env-file gyro/arms/1card.env down
# from the other machine: rsync the parked pack back into /srv/strata/packs/iq3_s (root-owned), then verify
docker start strata
# on the other machine: start the batch worker again
```

## Not done

The open tests from this trial are listed in [TODO.md](../TODO.md).
