#!/bin/bash
# fnx-load.sh <image-tag> <profile.json> <label> : stop serving, start the engine under a 58 GB cap, wait for it
IMG=local/fnx-2xp100:$1; CFG=$2; L=$3
docker stop -t 120 strata >/dev/null 2>&1; docker rm -f fnx >/dev/null 2>&1; sleep 3
docker run -d --name fnx --gpus all --network host --memory 58g --memory-swap 58g --ulimit memlock=-1:-1 --shm-size 2g \
  -u $(id -u):$(id -g) -e HOME=/data -v /srv/fnx2:/data -v /srv/strata/models/IQ3_S:/models-ro:ro $IMG \
  -c "export LD_LIBRARY_PATH=/usr/local/cuda/lib64; exec bash run.sh /data --config /data/$CFG --port 8080 --host 127.0.0.1" >/dev/null
( while docker inspect -f '{{.State.Running}}' fnx 2>/dev/null | grep -q true; do
    echo "$(date +%T) $(free -m | awk 'NR==2{print "used " $3 " avail " $7}') $(docker stats --no-stream --format '{{.MemUsage}}' fnx 2>/dev/null) gpu $(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr '\n' ' ')"
    sleep 10; done > /srv/fnx2/logs/mem-watch-$L.log 2>&1 & )
for i in $(seq 1 50); do h=$(curl -s -m 5 http://127.0.0.1:8080/health); echo "$h" | grep -q '"loaded": *true' && break
  docker inspect -f '{{.State.Running}}' fnx 2>/dev/null | grep -q true || break; sleep 10; done
date +%T; echo "health: $h" | cut -c1-160; docker ps -a --filter name=fnx --format '{{.Names}} {{.Status}}'
sort -t' ' -k3 -n /srv/fnx2/logs/mem-watch-$L.log | tail -1; tail -1 /srv/fnx2/logs/mem-watch-$L.log
docker logs fnx 2>&1 | grep -E 'failed|error|sfnx:|ready:|arena: card|experts|slots' | tail -14 | cut -c1-230
