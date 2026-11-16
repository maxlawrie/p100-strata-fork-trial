#!/bin/bash
# After the Bonsai chain: the tensorless arm on GPU 0 (if its image is staged or loaded), then the settings arms
# (tune-*) through night/run-all.sh, which also puts serving back.   nohup night/run-extra.sh > /dev/null 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/.."
RES=results/night; LOG=$RES/run-extra.log
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
temps() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '; }
say "waiting for the Bonsai chain"
until grep -q BONSAI-DONE $RES/run-bonsai.log 2>/dev/null; do sleep 60; done
docker stop -t 120 strata >/dev/null 2>&1; say "serving stopped"
IMG=local/tensorless-engine:sm60; f=/srv/kindi/images/local_tensorless-engine_sm60.tar.zst
docker image inspect $IMG >/dev/null 2>&1 || { [ -f $f ] && { say "loading $IMG"; zstd -dc $f | docker load >> "$LOG" 2>&1; }; }
if docker image inspect $IMG >/dev/null 2>&1; then
  t0=$SECONDS
  until [ "$(temps | tr ' ' '\n' | sort -n | tail -1)" -le 50 ] || [ $((SECONDS - t0)) -ge 600 ]; do sleep 15; done
  say "arm tensorless-1card start; cards at $(temps)"
  timeout --signal=TERM --kill-after=180 170m bonsai/run-arm.sh tensorless-1card > "$RES/arm-tensorless-1card.log" 2>&1
  say "arm tensorless-1card end, exit $?; cards at $(temps)"
  pkill -f 'bench/(quality\.py|bench\.sh|sustain\.sh)' 2>/dev/null; docker rm -f bonsai-night >/dev/null 2>&1
else
  say "no tensorless image: arm skipped"
fi
say "handing over to the settings arms"
ARMS="tune-base tune-pipeline tune-specp tune-p6 tune-prefillpipe tune-base2" ARM_MAX=45 exec night/run-all.sh
