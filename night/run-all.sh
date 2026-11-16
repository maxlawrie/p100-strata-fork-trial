#!/bin/bash
# Run the overnight arms one after another on the rig, then put serving back. Each arm gets at most ARM_MAX minutes
# (default 170); a failed or timed-out arm is logged and the chain moves on.
#   nohup night/run-all.sh > /dev/null 2>&1 &        progress: results/night/run-all.log
#   ARMS="gyro-m-3card iq2xs-3card" night/run-all.sh
set -u
cd "$(dirname "$(readlink -f "$0")")/.."
ARMS=${ARMS:-gyro-m-3card iq2xs-3card iq3xxs-2card-peer coder-2card-peer qwen36-1card gyro-s-1card}
RES=results/night; mkdir -p "$RES"; LOG=$RES/run-all.log
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
temps() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '; }
finish() { docker rm -f strata-night >/dev/null 2>&1; docker start strata >/dev/null 2>&1 && say "serving container started again"; say "ALL-DONE"; }
trap 'exit 143' TERM INT
trap finish EXIT

say "chain start: $ARMS"
docker stop -t 120 strata >/dev/null 2>&1; say "serving stopped"
for a in $ARMS; do
  t0=$SECONDS       # with nothing loaded the cards cool quickly: wait for <= 50 C, at most 10 minutes
  until [ "$(temps | tr ' ' '\n' | sort -n | tail -1)" -le 50 ] || [ $((SECONDS - t0)) -ge 600 ]; do sleep 15; done
  say "arm $a start; cards at $(temps); $(df -h --output=avail /srv | tail -1 | tr -d ' ') free; RAM used $(free -g | awk 'NR==2{print $3}') GB"
  timeout --signal=TERM --kill-after=180 "${ARM_MAX:-170}m" night/run-arm.sh "$a" > "$RES/arm-$a.log" 2>&1
  say "arm $a end, exit $?; cards at $(temps)"
  pkill -f 'bench/(quality\.py|bench\.sh|sustain\.sh)' 2>/dev/null   # anything a timed-out arm left behind
  docker rm -f strata-night >/dev/null 2>&1
done
