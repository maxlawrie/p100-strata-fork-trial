#!/bin/bash
# Run one overnight arm on the rig: start the model from night/arms/<arm>.env, wait for it, then run the steps in
# STEPS (default: easy hard sustain quality) and save the output under results/night/. Stops its container at exit.
# The serving container must already be stopped (night/run-all.sh does that and restores it at the end).
#   night/run-arm.sh <arm>          LOAD_MIN=150  minutes to wait for the model (the first start prepares its pack)
set -u
ARM=${1:?usage: night/run-arm.sh <arm>}
cd "$(dirname "$(readlink -f "$0")")/.."
[ -f "night/arms/$ARM.env" ] || { echo "no night/arms/$ARM.env" >&2; exit 2; }
[ -f .env ] || { echo ".env with STRATA_API_KEY=... is missing" >&2; exit 2; }
STEPS=$(sed -n 's/^STEPS="\(.*\)"$/\1/p' "night/arms/$ARM.env"); STEPS=${STEPS:-easy hard sustain quality}
KEY=$(sed -n 's/^STRATA_API_KEY=//p' .env | tr -d '"'); URL=http://127.0.0.1:8080; L=night-$ARM
DC="docker compose -p strata-night --project-directory . -f night/compose.arm.yaml --env-file .env --env-file night/arms/$ARM.env"
RES=${RES:-results/night}; mkdir -p "$RES" out ~/bench
ELOG=/srv/strata-state-night/$ARM/state/strata/launch/docker.engine.log
say() { echo "$(date +%T) [$ARM] $*"; }
temps() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '; }
cool() { # max-temp seconds : wait until every card is at or below max-temp, at most seconds
  local t0=$SECONDS
  until [ "$(temps | tr ' ' '\n' | sort -n | tail -1)" -le "$1" ] || [ $((SECONDS - t0)) -ge "$2" ]; do sleep 15; done
  say "cards at $(temps)after waiting $((SECONDS - t0)) s for <= $1 C"; }
trap 'exit 143' TERM INT
trap '$DC down >/dev/null 2>&1; say "container stopped"' EXIT

$DC down >/dev/null 2>&1
say "starting ($STEPS); cards at $(temps)"
$DC up -d || exit 1
T0=$SECONDS
until curl -sf -m 5 -H "Authorization: Bearer $KEY" $URL/v1/models >/dev/null; do
  [ "$(docker inspect -f '{{.State.Running}}' strata-night 2>/dev/null)" = true ] || {
    say "the container stopped before the model was ready:"; docker logs --tail 60 strata-night 2>&1
    sudo -n tail -n 40 "$ELOG" 2>/dev/null; exit 1; }
  [ $((SECONDS - T0)) -ge $(( ${LOAD_MIN:-150} * 60 )) ] && { say "model not ready after ${LOAD_MIN:-150} min"; docker logs --tail 60 strata-night 2>&1; exit 1; }
  sleep 15
done
say "model ready after $((SECONDS - T0)) s"
docker logs strata-night > "$RES/launch-$ARM.txt" 2>&1
sudo -n grep -iE 'expert|slot|arena|resident|peer|layer|split|refus|error' "$ELOG" 2>/dev/null | head -150 > "$RES/load-$ARM.txt"
{ free -g; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader; } > "$RES/ram-$ARM.txt"

for s in $STEPS; do
  cool 58 480
  say "step $s"
  case $s in
    easy)    ./bench/bench.sh "$L" $URL "$KEY"; cp "out/$L.txt" "$RES/speed-$ARM.txt" ;;
    hard)    CODING_SET=hard ONLY_CODE=1 ./bench/bench.sh "$L" $URL "$KEY"; cp "out/$L-hard.txt" "$RES/speed-$ARM-hard.txt" ;;
    sustain) ./bench/sustain.sh "$L" $URL "$KEY"; cp ~/bench/sustain-$L.txt "$RES/sustain-$ARM.txt" ;;
    # 21 coding tasks and 40 arithmetic problems, three rounds; waits for every card to be under 76 C between requests.
    quality) OUT_DIR=out python3 -I bench/quality.py $URL "$KEY" "$L" > "$RES/quality-$ARM.txt" 2>&1 ;;
  esac
done
sudo -n grep -iE 'hit rate|cache hit' "$ELOG" 2>/dev/null | tail -5 >> "$RES/load-$ARM.txt"
free -g | sed -n 2p >> "$RES/ram-$ARM.txt"
say "done"
