#!/bin/bash
# The Bonsai arms, after the overnight chain (night/run-all.sh) has finished: wait for its ALL-DONE, load the two
# engine images staged in /srv/kindi/images if they are not loaded yet, run the arms, put serving back.
#   nohup bonsai/run-all.sh > /dev/null 2>&1 &        progress: results/night/run-bonsai.log
set -u
cd "$(dirname "$(readlink -f "$0")")/.."
ARMS=${ARMS:-kindi-1card llama-1card kindi-2card}
RES=results/night; mkdir -p "$RES"; LOG=$RES/run-bonsai.log
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
temps() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '; }
say "waiting for the overnight chain"
until grep -q ALL-DONE $RES/run-all.log 2>/dev/null; do sleep 60; done
finish() { docker rm -f bonsai-night >/dev/null 2>&1; docker start strata >/dev/null 2>&1 && say "serving container started again"; say "BONSAI-DONE"; }
trap 'exit 143' TERM INT
trap finish EXIT
docker stop -t 120 strata >/dev/null 2>&1; say "serving stopped"
for img in kindi:0.4.0 local/llama-prism:c96baf4; do
  docker image inspect $img >/dev/null 2>&1 && continue
  f=/srv/kindi/images/$(echo $img | tr '/:' '__').tar.zst
  [ -f "$f" ] && { say "loading $img"; zstd -dc "$f" | docker load >> "$LOG" 2>&1; } || say "image $img is missing and $f is not staged"
done
for a in $ARMS; do
  t0=$SECONDS
  until [ "$(temps | tr ' ' '\n' | sort -n | tail -1)" -le 50 ] || [ $((SECONDS - t0)) -ge 600 ]; do sleep 15; done
  say "arm bonsai-$a start; cards at $(temps); RAM used $(free -g | awk 'NR==2{print $3}') GB"
  timeout --signal=TERM --kill-after=180 "${ARM_MAX:-170}m" bonsai/run-arm.sh "$a" > "$RES/arm-bonsai-$a.log" 2>&1
  say "arm bonsai-$a end, exit $?; cards at $(temps)"
  pkill -f 'bench/(quality\.py|bench\.sh|sustain\.sh)' 2>/dev/null
  docker rm -f bonsai-night >/dev/null 2>&1
done
