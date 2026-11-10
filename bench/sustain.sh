#!/bin/bash
# Sustained-load test of a running server: 300-token stories back to back for MINUTES (default 12) or until a GPU
# reaches STOP_C (default 80). One line per request: seconds since start, decode tok/s, GPU temperatures, and how many
# of the GPU samples since the last line had the thermal-slowdown flag (0x20) set. Run on the rig.
#   sustain.sh <label> <url> <api-key>      -> ~/bench/sustain-<label>.txt and -gpu.log
set -u
L=$1; URL=$2; K=$3; MIN=${MINUTES:-12}; STOP=${STOP_C:-80}
cd ~/bench; OUT=sustain-$L.txt; : > $OUT
nvidia-smi --query-gpu=timestamp,index,temperature.gpu,power.draw,clocks.sm,clocks_throttle_reasons.active --format=csv,noheader -l 2 > sustain-$L-gpu.log & LOG=$!
trap 'kill $LOG 2>/dev/null' EXIT
echo '{"model":"x","max_tokens":300,"chat_template_kwargs":{"enable_thinking":false},"cache_prompt":false,"messages":[{"role":"user","content":"Write a 400-word story about a lighthouse keeper."}]}' > sustain-gen.json
temps() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '; }
echo "start $(date +%T), GPU C: $(temps)" >> $OUT
T0=$SECONDS; last=0
while [ $((SECONDS - T0)) -lt $((MIN * 60)) ]; do
  tps=$(curl -s $URL/v1/chat/completions -H "Authorization: Bearer $K" -H "Content-Type: application/json" -d @sustain-gen.json \
        | python3 -c "import json,sys; print('%.1f' % json.load(sys.stdin).get('timings',{}).get('predicted_per_second',0))" 2>/dev/null)
  n=$(wc -l < sustain-$L-gpu.log); slow=$(tail -n +$((last + 1)) sustain-$L-gpu.log | awk -F', ' '$6 ~ /20$/' | wc -l); last=$n
  t=$(temps); echo "$((SECONDS - T0)) s  ${tps:-ERR} tok/s  GPU C: $t slowdown samples: $slow" >> $OUT
  if echo "$t" | awk -v m=$STOP '{for(i=1;i<=NF;i++) if($i>=m) f=1} END{exit !f}'; then echo "STOP: a GPU reached $STOP C at $((SECONDS - T0)) s" >> $OUT; break; fi
done
echo "end $(date +%T) after $((SECONDS - T0)) s" >> $OUT
awk -F", " '{g=$2; t=$3+0; if(t>mt[g])mt[g]=t; if($6 ~ /20$/)h[g]++; n[g]++; p[g]+=$4+0} END{for(g in mt) printf "GPU%s max %dC, mean %.0f W, thermal slowdown %d/%d samples\n", g, mt[g], p[g]/n[g], h[g], n[g]}' sustain-$L-gpu.log >> $OUT
echo DONE >> $OUT
