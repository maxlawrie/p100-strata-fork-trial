# New cooling duct: sustained-load runs, 15 Nov 2026

First tests of the 3D-printed duct on the 3× P100 rig. The duct is designed in a private
repo (branch `cooling-duct`, `cooling/duct.py`): a printed plenum takes the two 120 mm front intake fans to the
card tails, and printed blocks and a side wall cap the fin tips so air can leave only through each card's rear
bracket. It adds no fans.

**Short version:** on the case fans alone the duct is worse than the old shrouds, because GPU 0 (bottom card) loses
most of its airflow. With the desk fan on as well it is the best setup measured so far: no throttling in 12 minutes.
GPU 2 (middle card) is still the limit and was at 79 °C and creeping up when that run ended.

## Runs

Every run is [`bench/sustain.sh`](../../bench/sustain.sh): 12 minutes of back-to-back 300-token stories against the
serving config (IQ3_S, three cards, `layer-split=12,34`, 140 W cap). The baseline is the 10 Nov run in
[`../followup/sustain-sus-12-34.txt`](../followup/sustain-sus-12-34.txt).

| | Old shrouds (10 Nov) | Duct, all parts | Duct, rear blocks out | Duct, rear side panel back | Duct, side panel + desk fan |
|---|---|---|---|---|---|
| File | `followup/sustain-sus-12-34.txt` | `sustain-shroud-12-34.txt` | `sustain-shroud-noblocks-12-34.txt` | `sustain-shroud-sideonly-12-34.txt` | `sustain-shroud-sidepanel-deskfan-12-34.txt` |
| Start, GPU 0 / 1 / 2, °C | 55 / 55 / 55 | 43 / 39 / 40 | 63 / 47 / 53 | 64 / 46 / 55 | 63 / 47 / 54 |
| Peak, GPU 0 / 1 / 2, °C | 61 / 78 / 79 | 75 / 78 / 80 | 80 / 73 / 79 | 79 / 73 / 79 | 70 / 65 / 79 |
| Throttled samples of ~360, GPU 0 | 0 | 0 | 57 | 30 | 0 |
| Throttled samples of ~360, GPU 2 | 33 | 55 | 88 | 87 | 0 |
| Mean power, GPU 0 / 1 / 2, W | 56 / 89 / 90 | 58 / 86 / 84 | 60 / 81 / 76 | 64 / 86 / 83 | 60 / 85 / 92 |
| Mean speed, tok/s | 45.1 | 43.9 | 42.1 | 43.9 | 45.7 |

GPU 0 is the bottom card (chipset slot), GPU 1 the top card, GPU 2 the middle card.

- **Duct, all parts (18:41).** Started a few minutes after a cold boot, so 12–16 °C cooler than the baseline, and
  still ended as hot or hotter. GPU 0 climbed the whole run and had not levelled off at 75 °C.
- **Rear blocks out (19:16).** The rear bottom block, rear mid block and rear side block were removed. GPU 1 improved
  (73 °C), GPU 0 and GPU 2 both throttled, and the last stories fell to 25–29 tok/s.
- **Rear side panel back (19:40).** Same start temperatures as the run before. GPU 0 throttled later (from 10 min
  instead of 7.5 min); GPU 2 unchanged.
- **Side panel + desk fan (19:58).** Same parts as the run before, with the supplementary desk fan on. The cards were
  cooled to the same start temperatures first (`cooldown-…txt`, [`bench/coolrun.sh`](../../bench/coolrun.sh)).
  GPU 0 levelled off at 69–70 °C, GPU 1 at 65 °C, and GPU 2 reached 79 °C only in the last seconds. Speed stayed at
  45–46 tok/s to the end.

## What the runs show

- **GPU 0 gets very little air from the duct alone.** It throttled on about 60 W, less than either other card
  draws, and it cooled slowly after each run (79 → 77 °C in a minute, against 71 → 63 °C for GPU 1). Eleven minutes
  after the first run it still idled at 66 °C on 43 W, with GPU 1 at 50 °C and GPU 2 at 58 °C.
- **The floor block is not the main cause.** Taking out the rear blocks did not bring GPU 0 back towards the 61 °C
  it reached under the old shrouds.
- **The duct works when something supplies the airflow.** The desk fan took 9 °C off GPU 0's peak and 8 °C off
  GPU 1's and removed all throttling. That fits the two case fans not having the pressure to push enough air through
  three sealed fin stacks; the design notes say no pressure-drop calculation was done.
- **GPU 1 is better than under the old shrouds** in every run after the first (65–73 °C against 78 °C).
- **GPU 2 is the limit in every setup.** It runs the last layer stage plus the head, draft and verify.

## Bottom case holes reopened (20:39)

Same setup as the desk-fan run (duct, rear blocks out, rear side panel on, desk fan on), with some of the taped-over
holes at the back of the case floor opened again. File: `sustain-shroud-bottomholes-12-34.txt`.

| | Desk fan, holes taped (19:58) | Desk fan, holes reopened (20:39) |
|---|---|---|
| Start, GPU 0 / 1 / 2, °C | 63 / 47 / 54 | 50 / 41 / 43 |
| Peak, GPU 0 / 1 / 2, °C | 70 / 65 / 79 | 65 / 65 / 75 |
| Throttled samples | 0 | 0 |
| Mean power, GPU 0 / 1 / 2, W | 60 / 85 / 92 | 57 / 83 / 91 |
| Mean speed, tok/s | 45.7 | 45.7 |

Not a clean comparison: this run started 13 / 6 / 11 °C cooler. GPU 1 ended at the same 65 °C in both. GPU 0 and
GPU 2 ended 4–5 °C lower but were both still rising about 0.5 °C a minute at the end, where GPU 0 had levelled off at
69 °C in the earlier run. The holes may help a little or not at all; a longer run, or one from the same start
temperatures, would settle it.

## A stronger desk fan (16 Nov, 09:20)

Same duct and parts as the run above, with the desk fan replaced by a stronger one. File:
`sustain-shroud-newdeskfan-12-34.txt`.

| | Old desk fan (15 Nov 20:39) | New desk fan (16 Nov 09:20) |
|---|---|---|
| Start, GPU 0 / 1 / 2, °C | 50 / 41 / 43 | 41 / 36 / 40 |
| Peak, GPU 0 / 1 / 2, °C | 65 / 65 / 75 | 51 / 54 / 68 |
| Throttled samples | 0 | 0 |
| Mean power, GPU 0 / 1 / 2, W | 57 / 83 / 91 | 51 / 78 / 88 |
| Mean speed, tok/s | 45.7 | 45.7 |

GPU 0 and GPU 1 levelled off at 50–51 and 52–53 °C from about minute 6; GPU 2 was at 67–68 °C for the last three
minutes. That is 14 / 11 / 7 °C below the old desk fan and the first run with real headroom on every card: GPU 2 is
11 °C under the throttle point. Speed is unchanged, as expected when nothing throttles. A minute after the run the
cards were at 48 / 45 / 58 °C.

GPU 2 is now the only warm card. It carries the last layer stage plus the head and the draft work (88 W against 51
and 78 W), in the middle slot. The layer split (12,34) was tuned for the old shrouds and is worth re-tuning for this
cooling.

## Not known

- Whether the 10 Nov baseline was measured with the desk fan on. In the 20 Oct tests on the old shrouds the desk fan
  was worth only 1–2 °C on GPU 0 and nothing on GPU 2.
- Why GPU 0 peaked at 61 °C on 10 Nov when it peaked at 75–76 °C in the October runs.
- The front fans' actual RPM. They are wired straight to 12 V, so they already run at full speed with no
  control; fan control cannot add cooling, only different fans can. There is still no RPM reading.
- Whether GPU 0's rear bracket is partly covered by the plate over the old PSU hole. The design did not model the
  back of the case.
- How the last setup behaves beyond 12 minutes; GPU 2 was still rising.
