#!/bin/bash
# Wait until the cards are at or below the given start temperatures (max 20 min), then run sustain.sh.
#   coolrun.sh <label> <gpu0_max> <gpu1_max> <gpu2_max>
cd ~/bench; L=$1; C=cooldown-$L.txt; : > $C; T0=$SECONDS
while :; do
  t=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '); echo "$(date +%T) $t" >> $C
  set -- $t
  read a b c <<< "$t"
  [ $a -le ${G0:-64} ] && [ $b -le ${G1:-47} ] && [ $c -le ${G2:-55} ] && break
  [ $((SECONDS-T0)) -ge 1200 ] && { echo TIMEOUT >> $C; break; }
  sleep 20
done
K=$(docker inspect strata --format '{{range .Config.Env}}{{println .}}{{end}}' | sed -n 's/^API_KEY=//p')
exec ./sustain.sh "$L" http://127.0.0.1:8080 "$K"
