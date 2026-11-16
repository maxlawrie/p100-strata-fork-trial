#!/bin/bash
# Run one Gyro-S arm on the rig: stop the serving container, start Gyro-S with gyro/arms/<arm>.env, run the speed
# benchmark and the repeated quality benchmark, save the output under results/gyro/, then put serving back.
#   gyro/run-arm.sh 1card | 2card-peer | 3card
#   SUSTAIN=1 gyro/run-arm.sh 2card-peer     also the 12-minute sustained-load run (bench/sustain.sh)
#   KEEP=1 gyro/run-arm.sh 3card             leave Gyro-S running at the end instead of restoring serving
# Needs STRATA_API_KEY in .env at the repo root, like compose.yaml. The first run downloads 58.5 GB and prepares
# the pack; later arms reuse both. The serving container (name "strata") is down for the whole run.
set -u
ARM=${1:?usage: gyro/run-arm.sh 1card|2card-peer|3card}
cd "$(dirname "$(readlink -f "$0")")/.."
[ -f "gyro/arms/$ARM.env" ] || { echo "no gyro/arms/$ARM.env" >&2; exit 2; }
[ -f .env ] || { echo ".env with STRATA_API_KEY=... is missing" >&2; exit 2; }
KEY=$(sed -n 's/^STRATA_API_KEY=//p' .env | tr -d '"'); URL=http://127.0.0.1:8080; L=gyro-s-$ARM
DC="docker compose -p strata-gyro --project-directory . -f gyro/compose.gyro.yaml --env-file .env --env-file gyro/arms/$ARM.env"
RES=results/gyro; mkdir -p "$RES" out ~/bench

FREE=$(df --output=avail -BG /srv/strata | tail -1 | tr -dc 0-9)
if ! ls /srv/strata/models 2>/dev/null | grep -qi gyro && [ "$FREE" -lt 65 ]; then
  echo "/srv/strata has ${FREE} GB free; Gyro-S needs about 60 GB (58.5 GB file + 1.5 GB pack)." >&2; exit 2; fi

restore() {
  [ -n "${KEEP:-}" ] && { echo "KEEP=1: Gyro-S left running; serving is still stopped."; return; }
  $DC down; docker start strata >/dev/null && echo "serving container started again"; }
trap restore EXIT

docker stop -t 120 strata >/dev/null 2>&1
$DC down >/dev/null 2>&1                      # an arm left over from an earlier run
$DC up -d || exit 1                           # Docker creates /srv/strata-state-gyro/<arm> itself

echo "waiting for the model (the first start downloads 58.5 GB; watch: docker logs -f strata-gyro)"
until curl -sf -m 5 -H "Authorization: Bearer $KEY" $URL/v1/models >/dev/null; do
  [ "$(docker inspect -f '{{.State.Running}}' strata-gyro 2>/dev/null)" = true ] || {
    echo "the container stopped:" >&2; docker logs --tail 40 strata-gyro >&2; exit 1; }
  sleep 15
done

# What the engine says it holds: experts per card, cache slots, RAM arena.
docker logs strata-gyro 2>&1 | grep -iE 'expert|slot|arena|resident|peer|layer' > "$RES/load-$ARM.txt"
free -g > "$RES/ram-$ARM.txt"; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader >> "$RES/ram-$ARM.txt"

./bench/bench.sh "$L" $URL "$KEY";                     cp "out/$L.txt" "$RES/speed-$ARM.txt"
CODING_SET=hard ONLY_CODE=1 ./bench/bench.sh "$L" $URL "$KEY"; cp "out/$L-hard.txt" "$RES/speed-$ARM-hard.txt"
if [ -n "${SUSTAIN:-}" ]; then
  ./bench/sustain.sh "$L" $URL "$KEY"; cp ~/bench/sustain-$L.txt "$RES/sustain-$ARM.txt"; fi
# 21 coding tasks and 40 arithmetic problems, three rounds; waits for every card to be under 76 C between requests.
OUT_DIR=out python3 -I bench/quality.py $URL "$KEY" "$L" 2>&1 | tee "$RES/quality-$ARM.txt"
docker logs strata-gyro 2>&1 | grep -iE 'hit rate|cache hit' | tail -5 >> "$RES/load-$ARM.txt"
echo "done: $RES/*-$ARM*.txt"
