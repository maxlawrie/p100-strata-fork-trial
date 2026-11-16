#!/bin/bash
# Stock llama.cpp v1.0.0 on the rig: Qwen3.6 on two cards against the fork's run, then the serving model on three cards.
# Waits for the three-card port's run to finish first.   nohup speed/run-llama1.sh > /dev/null 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/.."
export RES=results/speed; LOG=$RES/run.log
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
temps() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '; }
until grep -qs FNX3U-FULL-DONE $LOG; do sleep 30; done
finish() { docker rm -f bonsai-night >/dev/null 2>&1; docker start strata >/dev/null 2>&1 && say "serving container started again"; say "LLAMA1-DONE"; }
trap 'exit 143' TERM INT
trap finish EXIT
IMG=local/llama-cpp:v1.0.0-sm60; f=/srv/kindi/images/local_llama-cpp_v1.0.0-sm60.tar.zst
docker image inspect $IMG >/dev/null 2>&1 || { until [ -f $f ]; do sleep 10; done; zstd -dc $f | docker load >> "$LOG" 2>&1; }
docker stop -t 120 strata >/dev/null 2>&1; say "llama.cpp 1.0 chain: serving stopped"
arm() { local t0=$SECONDS
  until [ "$(temps | tr ' ' '\n' | sort -n | tail -1)" -le 50 ] || [ $((SECONDS - t0)) -ge 600 ]; do sleep 15; done
  say "arm $1 start; cards at $(temps)"
  timeout --signal=TERM --kill-after=180 60m bonsai/run-arm.sh "$1" > "$RES/arm-$1.log" 2>&1
  say "arm $1 end, exit $?; cards at $(temps)"
  pkill -f 'bench/(quality\.py|bench\.sh|sustain\.sh)' 2>/dev/null; docker rm -f bonsai-night >/dev/null 2>&1; }
arm q36v1-tensor
arm fn1-3card
