#!/bin/bash
# Speed attempts with the duct and the stronger desk fan (16 Nov): the fastest model on two cards, a higher power
# limit on the serving config, and the one-card engines on the best-cooled card. Serving is down for the run and
# comes back at the end with the 140 W limit restored.   nohup speed/run-all.sh > /dev/null 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/.."
export RES=results/speed; mkdir -p $RES; LOG=$RES/run.log
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
temps() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '; }
finish() { sudo -n nvidia-smi -pl 140 >/dev/null 2>&1; docker rm -f bonsai-night strata-night >/dev/null 2>&1
  docker start strata >/dev/null 2>&1 && say "power limit back to 140 W; serving container started again"; say "SPEED-DONE"; }
trap 'exit 143' TERM INT
trap finish EXIT
arm() { # runner name [power-limit]
  local t0=$SECONDS
  until [ "$(temps | tr ' ' '\n' | sort -n | tail -1)" -le 50 ] || [ $((SECONDS - t0)) -ge 600 ]; do sleep 15; done
  sudo -n nvidia-smi -pl "${3:-140}" >/dev/null 2>&1
  say "arm $2 start at ${3:-140} W; cards at $(temps)"
  timeout --signal=TERM --kill-after=180 60m "$1" "$2" > "$RES/arm-$2${CARD:+-gpu$CARD}.log" 2>&1
  say "arm $2 end, exit $?; cards at $(temps)"
  pkill -f 'bench/(quality\.py|bench\.sh|sustain\.sh)' 2>/dev/null; docker rm -f bonsai-night strata-night >/dev/null 2>&1
  sudo -n nvidia-smi -pl 140 >/dev/null 2>&1
}
say "chain start"; docker stop -t 120 strata >/dev/null 2>&1; say "serving stopped"
arm bonsai/run-arm.sh q36-tensor
STEPS_OVERRIDE="easy sustain" arm bonsai/run-arm.sh q36-layer
arm night/run-arm.sh pl180 180
arm night/run-arm.sh pl220 220
arm night/run-arm.sh pl220-prefillpipe 220
arm night/run-arm.sh gyro-s-1card-gpu1
export CARD=1 STEPS_OVERRIDE="easy sustain"
arm bonsai/run-arm.sh kindi-1card
arm bonsai/run-arm.sh llama-1card
arm bonsai/run-arm.sh tensorless-1card
