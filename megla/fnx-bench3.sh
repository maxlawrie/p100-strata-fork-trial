#!/bin/bash
# fnx-bench3.sh <label> : speed set, one arithmetic round (correctness), hard set, sustained run
cd ~/p100-strata-fork-trial; L=$1; URL=http://127.0.0.1:8080; RES=results/speed
{ free -g; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader; } > $RES/ram-$L.txt
./bench/bench.sh $L $URL none; cp out/$L.txt $RES/speed-$L.txt
RUNS=1 ONLY=arith COOL=0 OUT_DIR=out python3 -I bench/quality.py $URL none $L > $RES/arith-$L.txt 2>&1
CODING_SET=hard ONLY_CODE=1 ./bench/bench.sh $L $URL none; cp out/$L-hard.txt $RES/speed-$L-hard.txt
t0=$SECONDS; until [ "$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | sort -n | tail -1)" -le 58 ] || [ $((SECONDS-t0)) -ge 480 ]; do sleep 15; done
./bench/sustain.sh $L $URL none; cp ~/bench/sustain-$L.txt $RES/sustain-$L.txt
free -g | sed -n 2p >> $RES/ram-$L.txt; cp /srv/fnx2/logs/mem-watch-${L#fnx}.log $RES/memwatch-$L.txt 2>/dev/null
docker logs fnx > $RES/server-$L.txt 2>&1; echo "BENCH3-DONE $L" >> $RES/run.log
