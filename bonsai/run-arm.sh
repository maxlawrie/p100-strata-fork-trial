#!/bin/bash
# Run one Ternary Bonsai 2 27B arm on the rig and save the output under results/night/, like night/run-arm.sh.
#   bonsai/run-arm.sh llama-1card     PrismML llama.cpp fork, PQ2_0 file, GPU 0
#   bonsai/run-arm.sh kindi-1card     Kindi 0.4.0, PTQ1_0 file, GPU 0 (the first run converts the model, CPU only)
#   bonsai/run-arm.sh kindi-2card     Kindi 0.4.0 on GPUs 1 and 2: speed and sustained run only
#   bonsai/run-arm.sh tensorless-1card   iammrduncan/tensorless engine, Qwen3.8-27B in its PN3 format, GPU 0, with
#                                     the flags and switches of its recipe (recipes/.../Qwen3.8-27B-PN3-GGUF/p100.toml);
#                                     the first run downloads the 13 GB model and checks its sha256
# Settings: 65,536-token context and q8_0 K/V in llama.cpp, as in Kindi's own P100 comparison; Kindi with its
# installer's P100 profile (docs/CARDS.md, install.sh). The serving container must already be stopped.
set -u
A=${1:?usage: bonsai/run-arm.sh llama-1card|kindi-1card|kindi-2card|tensorless-1card}; ARM=bonsai-$A
[ "$A" = tensorless-1card ] && ARM=tensorless-1card
case $A in q36-*|q36v1-*|fn1-*) ARM=$A ;; esac
[ -n "${CARD:-}" ] && ARM=$ARM-gpu$CARD        # CARD=1: run a one-card arm on another card than GPU 0
cd "$(dirname "$(readlink -f "$0")")/.."
KEY=$(sed -n 's/^STRATA_API_KEY=//p' .env | tr -d '"'); L=night-$ARM
M=/srv/models/bonsai-2-27b; KD=/srv/kindi; RES=${RES:-results/night}; mkdir -p "$RES" out ~/bench
DEFSTEPS="easy hard sustain quality"; GPUS=${CARD:-0}; STEPS=$DEFSTEPS
say() { echo "$(date +%T) [$ARM] $*"; }
temps() { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits | tr '\n' ' '; }
cool() { local t0=$SECONDS
  until [ "$(temps | tr ' ' '\n' | sort -n | tail -1)" -le "$1" ] || [ $((SECONDS - t0)) -ge "$2" ]; do sleep 15; done
  say "cards at $(temps)after waiting $((SECONDS - t0)) s for <= $1 C"; }
trap 'exit 143' TERM INT
trap 'docker logs bonsai-night > "$RES/server-$ARM.txt" 2>&1; docker rm -f bonsai-night >/dev/null 2>&1; say "container stopped"' EXIT
docker rm -f bonsai-night >/dev/null 2>&1

case $A in
  llama-1card)
    URL=http://127.0.0.1:8080
    docker run -d --name bonsai-night --gpus all --network host -e CUDA_DEVICE_ORDER=PCI_BUS_ID -e CUDA_VISIBLE_DEVICES=$GPUS \
      -v $M:/models:ro local/llama-prism:c96baf4 -m /models/Ternary-Bonsai-2-27B-PQ2_0.gguf --alias bonsai2-27b \
      --host 127.0.0.1 --port 8080 --api-key "$KEY" -ngl 99 -fa on -c 65536 -ctk q8_0 -ctv q8_0 -np 1 \
      --jinja --reasoning-format deepseek || exit 1 ;;
  kindi-1card|kindi-2card)
    URL=http://127.0.0.1:8093
    [ $A = kindi-2card ] && { GPUS=1,2; STEPS="easy sustain"; }
    SD=state-$A${CARD:+-gpu$CARD}
    sudo -n mkdir -p $KD && sudo -n chown "$(id -u):$(id -g)" $KD
    if [ ! -d $KD/pack-27b ]; then
      say "converting the PTQ1_0 file (CPU only)"
      docker run --rm -u "$(id -u):$(id -g)" -v $KD:/data -v $M:/models:ro kindi:0.4.0 \
        convert /models/Ternary-Bonsai-2-27B-PTQ1_0.gguf --out /data/pack-27b > "$RES/convert-$ARM.txt" 2>&1 \
        || { say "convert failed"; tail -20 "$RES/convert-$ARM.txt"; exit 1; }
      say "converted: $(du -sh $KD/pack-27b | cut -f1)"
    fi
    MEM="--memory 14g"; [ $A = kindi-2card ] && MEM=
    docker run -d --name bonsai-night --gpus all --network host $MEM -u "$(id -u):$(id -g)" -v $KD:/data \
      -e CUDA_DEVICE_ORDER=PCI_BUS_ID -e CUDA_VISIBLE_DEVICES=$GPUS -e KINDI_CARDS=$(echo $GPUS | tr ',' '\n' | wc -l) \
      -e KINDI_REPEAT_STOP=1 -e KINDI_MAX_TOKENS=65536 -e KINDI_PACK=/data/pack-27b -e KINDI_CTX=65536 -e KINDI_HEAD=exact \
      -e KINDI_STATE_DIR=/data/$SD -e KINDI_HOST=127.0.0.1 -e KINDI_API_KEY="$KEY" kindi:0.4.0 || exit 1 ;;
  tensorless-1card)
    STEPS="easy hard sustain"   # no quality rounds: on GPU 0 they are mostly waiting for the card to cool
    URL=http://127.0.0.1:8080; TD=/srv/models/tensorless; F=Qwen3.8-27B-PN3-P0k19.gguf
    SHA=15ce2d4469673f1f1753c55de3780cfe04311dd6f05cb41633d73df128e91476
    sudo -n mkdir -p $TD && sudo -n chown "$(id -u):$(id -g)" $TD
    if [ ! -f $TD/$F.done ]; then
      say "downloading $F (13 GB)"
      for try in 1 2 3 4 5; do
        curl -fL -sS -C - --retry 5 --retry-delay 10 -o $TD/$F \
          https://huggingface.co/iamMrDuncan/Qwen3.8-27B-PN3-GGUF/resolve/c701b6690ec360b16d40f85df1cb76062e30cd38/$F && break
        sleep 20
      done
      echo "$SHA  $TD/$F" | sha256sum -c >/dev/null 2>&1 || { say "model download failed its sha256 check"; exit 1; }
      touch $TD/$F.done; say "model downloaded and checked"
    fi
    docker run -d --name bonsai-night --gpus all --network host -e CUDA_DEVICE_ORDER=PCI_BUS_ID -e CUDA_VISIBLE_DEVICES=$GPUS \
      -v $TD:/models:ro -e OMP_NUM_THREADS=6 \
      -e GGML_CUDA_FATTN_SM60=1 -e GGML_CUDA_FATTN_SM60_CTAS=4 -e GGML_CUDA_FATTN_TILE_OCC1=1 \
      -e GGML_CUDA_FUSE_PRE_ADD=1 -e GGML_CUDA_MMV_SM60=1 \
      -e GGML_CUDA_MMV_SM60_INPLACE_IQ3S=1 -e GGML_CUDA_MMV_SM60_INPLACE_XXS=1 \
      -e GGML_CUDA_MMV_SM60_IQ3S_STOCK=1 -e GGML_CUDA_MMV_SM60_Q3K=1 \
      -e GGML_CUDA_MMV_SM60_Q4K_DHEAD=1 -e GGML_CUDA_MMV_SM60_Q4K_HEAD=1 \
      -e GGML_CUDA_MMV_SM60_Q6K=1 -e GGML_CUDA_MMV_SM60_XXS_KB_WIDE=1 \
      -e GGML_CUDA_MMV_SM60_XXS_STOCK=1 -e GGML_CUDA_NORM_EMIT_Q8=1 \
      -e GGML_CUDA_PREFILL_CHUNK_GEMM=1 -e GGML_CUDA_PREFILL_CHUNK_STREAMS=3 \
      -e GGML_CUDA_PREFILL_DEQ_F4=1 -e GGML_CUDA_PREFILL_REP_DIRECT=1 \
      -e GGML_CUDA_SM86_GDN_COLS=8 -e GGML_CUDA_SM86_IQ3_SMEM_GRID=1 \
      local/tensorless-engine:sm60 -m /models/$F --host 127.0.0.1 --port 8080 --api-key "$KEY" -c 65536 \
      --alias qwen3.8-27b-pn3 -t 6 -tb 6 -np 1 -ngl 99 -ot token_embd.weight=CUDA0 -ctk q4_0 -ctv q4_0 -sm none -lm none \
      -fit off --threads-http 4 -b 512 -ub 512 -fa on --jinja || exit 1 ;;
  q36-tensor|q36-layer)
    # Qwen3.6-35B-A3B UD-Q4_K_XL (the file has the MTP head) on Junk GPU Lab's P100 llama.cpp, GPUs 1 and 2.
    # MTP settings from duncandoestech/houston-p100-lab's MoE runs (n-max 3, p-min 0.75).
    URL=http://127.0.0.1:8080; GPUS=1,2; STEPS="easy hard sustain"
    docker run -d --name bonsai-night --gpus all --network host -e CUDA_DEVICE_ORDER=PCI_BUS_ID -e CUDA_VISIBLE_DEVICES=$GPUS \
      -e GGML_CUDA_P2P=1 -e GGML_CUDA_GRAPHS_PRE_VOLTA=3 -v /srv/strata/models/qwen36-UD-Q4_K_XL:/models:ro \
      local/llama-junkgpulab:c89a8dc -m /models/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf --alias qwen3.6-35b-a3b \
      --host 127.0.0.1 --port 8080 --api-key "$KEY" -ngl 99 -sm ${A#q36-} -fa on -c 65536 -ctk q8_0 -ctv q8_0 -np 1 \
      --jinja --reasoning-format deepseek --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0.75 || exit 1 ;;
  q36v1-tensor|q36v1-layer)
    # The q36-* arms on stock llama.cpp v1.0.0 (llama1/Dockerfile) instead of Junk GPU Lab's P100 fork: same file, cards and flags.
    URL=http://127.0.0.1:8080; GPUS=1,2; STEPS="easy hard sustain"
    docker run -d --name bonsai-night --gpus all --network host -e CUDA_DEVICE_ORDER=PCI_BUS_ID -e CUDA_VISIBLE_DEVICES=$GPUS \
      -v /srv/strata/models/qwen36-UD-Q4_K_XL:/models:ro \
      local/llama-cpp:v1.0.0-sm60 -m /models/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf --alias qwen3.6-35b-a3b \
      --host 127.0.0.1 --port 8080 --api-key "$KEY" -ngl 99 -sm ${A#q36v1-} -fa on -c 65536 -ctk q8_0 -ctv q8_0 -np 1 \
      --jinja --reasoning-format deepseek --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0.75 || exit 1 ;;
  fn1-3card)
    # The serving model (Flash-Next GSQ-RCO IQ3_S, both shards; the second is the per-layer embedding table) on stock
    # llama.cpp v1.0.0, three cards: experts in host memory with the new MoE cache on the cards (docs/moe-cache.md).
    # No MTP: the IQ3_S file has no draft head (Strata keeps it apart).
    URL=http://127.0.0.1:8080; GPUS=0,1,2; STEPS="easy sustain"
    docker run -d --name bonsai-night --gpus all --network host --memory 58g --memory-swap 58g \
      -e CUDA_DEVICE_ORDER=PCI_BUS_ID -e CUDA_VISIBLE_DEVICES=$GPUS -v /srv/strata/models/IQ3_S:/models:ro \
      local/llama-cpp:v1.0.0-sm60 -m /models/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf --alias flash-next-iq3_s \
      --host 127.0.0.1 --port 8080 --api-key "$KEY" -ngl 99 -cmoe --moe-cache-mib ${MOE_CACHE_MIB:-30000} \
      --moe-cache-cpu-share ${MOE_CPU_SHARE:-0} -t 6 -fa on -c 65536 -ctk q8_0 -ctv q8_0 -np 1 \
      --jinja --reasoning-format deepseek || exit 1 ;;
  *) echo "unknown arm $A" >&2; exit 2 ;;
esac

STEPS=${STEPS_OVERRIDE:-$STEPS}
say "starting ($STEPS) on GPU $GPUS; cards at $(temps)"; T0=$SECONDS
until curl -sf -m 5 $URL/health >/dev/null; do
  [ "$(docker inspect -f '{{.State.Running}}' bonsai-night 2>/dev/null)" = true ] || {
    say "the container stopped before the model was ready:"; docker logs --tail 60 bonsai-night 2>&1; exit 1; }
  [ $((SECONDS - T0)) -ge 2700 ] && { say "model not ready after 45 min"; docker logs --tail 60 bonsai-night 2>&1; exit 1; }
  sleep 10
done
say "model ready after $((SECONDS - T0)) s; health: $(curl -s -m 5 $URL/health | head -c 300)"
{ free -g; nvidia-smi --query-gpu=index,memory.used --format=csv,noheader; } > "$RES/ram-$ARM.txt"

for s in $STEPS; do
  cool 58 480
  say "step $s"
  case $s in
    easy)    ./bench/bench.sh "$L" $URL "$KEY"; cp "out/$L.txt" "$RES/speed-$ARM.txt" ;;
    hard)    CODING_SET=hard ONLY_CODE=1 ./bench/bench.sh "$L" $URL "$KEY"; cp "out/$L-hard.txt" "$RES/speed-$ARM-hard.txt" ;;
    sustain) ./bench/sustain.sh "$L" $URL "$KEY"; cp ~/bench/sustain-$L.txt "$RES/sustain-$ARM.txt" ;;
    quality) OUT_DIR=out python3 -I bench/quality.py $URL "$KEY" "$L" > "$RES/quality-$ARM.txt" 2>&1 ;;
  esac
done
say "done"
