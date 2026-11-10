#!/bin/bash
# Guarded speed + coding benchmark of an OpenAI-compatible server that is already running (as used for README.md).
#   bench.sh <label> <url> [api-key]             4K/16K/32K prompt, 3x 300-token replies, a tool call, the 8 easy coding tasks
#   CODING_SET=hard ONLY_CODE=1 bench.sh ...     the 8 harder coding tasks only
# Writes out/<label>[-hard].txt and a GPU log beside it. Stops sending requests once any GPU reaches 80 C.
# Speeds are the server's own timings when it reports them (llama.cpp, Strata), otherwise wall-clock.
# The coding tasks run the model's code in a throwaway Docker container with no network (python:3.12-slim).
set -u
HERE=$(dirname "$(readlink -f "$0")")
L=$1; URL=$2; K=${3:-none}
mkdir -p out; cd out; OUT=$L${CODING_SET:+-$CODING_SET}.txt; : > $OUT; rm -f ABORT; export ABORT_FILE=$PWD/ABORT

nvidia-smi --query-gpu=timestamp,index,temperature.gpu,power.draw,clocks.sm,clocks_throttle_reasons.active --format=csv,noheader -l 2 > ${OUT%.txt}-gpu.log & LOG=$!
( while sleep 2; do
    if nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | awk '$1>=80{f=1} END{exit !f}'; then
      echo "ABORT: a GPU reached 80C at $(date +%T)" >> $OUT; touch ABORT; break; fi; done ) & GUARD=$!
trap 'kill $LOG $GUARD 2>/dev/null' EXIT

req() { # label json-file
  local T0=$(date +%s.%N)
  curl -s $URL/v1/chat/completions -H "Authorization: Bearer $K" -H "Content-Type: application/json" -d @"$2" \
  | python3 -c "
import json,sys
d=json.load(sys.stdin); t=d.get('timings',{}); m=d['choices'][0]['message']
if not t:
    import time; u=d.get('usage',{}); w=time.time()-float('$T0'); pn=u.get('prompt_tokens',0); gn=u.get('completion_tokens',0)
    t={'prompt_n':pn,'predicted_n':gn,'prompt_per_second':pn/w if gn<=10 else 0,'predicted_per_second':gn/w if pn<1000 else 0,'draft_n':'wall %.1fs' % w}
calls=[(c['function']['name'],c['function']['arguments']) for c in (m.get('tool_calls') or [])]
print('%-10s prompt %5d tok @ %6.1f tok/s | gen %4d tok @ %5.1f tok/s | drafts %s/%s | %s' % ('$1', t.get('prompt_n',0), t.get('prompt_per_second',0), t.get('predicted_n',0), t.get('predicted_per_second',0), t.get('draft_n_accepted','-'), t.get('draft_n','-'), (repr((m.get('content') or '').strip()[:40]) if not calls else calls)))" >> $OUT 2>&1; }
mk() { # file n_records seed
  python3 -c "
import json,random; random.seed($3)
f=' '.join(f'Record {i}: rack {random.randint(0,6)} temp {random.randint(30,90)}C fan {random.randint(900,1900)} rpm.' for i in range($2))
print(json.dumps({'model':'x','max_tokens':10,'chat_template_kwargs':{'enable_thinking':False},'cache_prompt':False,'messages':[{'role':'user','content':f+' How many records are there? Just the number.'}]}))" > "$1"; }
mk p4k.json 180 1; mk p16k.json 720 2; mk p32k.json 1440 3
echo '{"model":"x","max_tokens":300,"chat_template_kwargs":{"enable_thinking":false},"cache_prompt":false,"messages":[{"role":"user","content":"Write a 400-word story about a lighthouse keeper."}]}' > gen.json
echo '{"model":"x","max_tokens":800,"tools":[{"type":"function","function":{"name":"get_weather","description":"Current weather for a city","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}}],"messages":[{"role":"user","content":"What is the weather in Brisbane right now?"}]}' > tool.json

echo "start $(date +%T), GPU C: $(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' ')" >> $OUT
if [ -z "${ONLY_CODE:-}" ]; then
  for p in p4k p16k p32k; do [ -f ABORT ] || req $p $p.json; done
  for r in 1 2 3; do [ -f ABORT ] || req gen gen.json; done
  [ -f ABORT ] || req tool tool.json
fi
[ -f ABORT ] || python3 -I "$HERE/coding.py" $URL $K $L >> $OUT 2>&1
echo "end $(date +%T)" >> $OUT
awk -F", " '{g=$2; t=$3+0; p=$4+0; if(t>mt[g])mt[g]=t; if(p>mp[g])mp[g]=p; if($6 ~ /20$/)h[g]++; n[g]++} END{for(g in mt) printf "GPU%s max %dC, max %.0fW, thermal slowdown %d/%d\n", g, mt[g], mp[g], h[g], n[g]}' ${OUT%.txt}-gpu.log >> $OUT
echo DONE >> $OUT
