#!/bin/bash
# fnx-quick.sh <label> <profile.json> : load the three-card engine with a config and run the speed set only
cd ~/p100-strata-fork-trial; L=$1; RES=results/speed
/srv/fnx2/fnx-load.sh megla3 $2 ${L#fnx} > $RES/load-$L.txt 2>&1
grep -q '"loaded": tru' $RES/load-$L.txt || { docker logs fnx > $RES/server-$L.txt 2>&1; echo "QUICK-DONE $L FAILED" >> $RES/run.log; exit 1; }
{ free -g; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader; } > $RES/ram-$L.txt
./bench/bench.sh $L http://127.0.0.1:8080 none; cp out/$L.txt $RES/speed-$L.txt
docker logs fnx > $RES/server-$L.txt 2>&1; echo "QUICK-DONE $L" >> $RES/run.log
