#!/bin/bash
# Download Strata model files straight from Hugging Face at the revisions and hashes pinned in Strata 0.2.2's setup.py,
# into /srv/strata/models/<dir>, without starting an engine (no GPU load). Packs are prepared later, at first start.
# Usage: fetch-models.sh NAME...   (IQ3_XXS, Gyro-M, coder-IQ1_M, IQ2_XS, qwen36, bonsai)
# bonsai: PrismML's Ternary Bonsai 2 27B (PQ2_0 and PTQ1_0, for llama.cpp / Kindi), into /srv/models/bonsai-2-27b.
set -u
M=/srv/strata/models; HF=https://huggingface.co
ISTA=ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/resolve/ed59f92082b1e93c0e96d60a8b11aab089b52f09
CODER=ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF/resolve/5348543e0147355ac9cbcb031184a3546350988e
GYRO=agentionai/Qwen3.8-Flash-Next-Gyro-GGUF/resolve/1ada08422e404aca51ab9df665f089f34c419c6b
NGRAM_SHA=316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113
NGRAM_SRC=$M/IQ3_S/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00002-of-00002.gguf

get() { # dir file url bytes sha
  local d=$M/$1 f=$2 url=$3 bytes=$4 sha=$5
  sudo mkdir -p "$d"
  if sudo test -f "$d/$f.done"; then echo "$(date +%T) have $1/$f"; return 0; fi
  echo "$(date +%T) fetching $1/$f"
  for try in 1 2 3 4 5 6 7 8; do
    sudo curl -fL -sS -C - --retry 5 --retry-delay 10 -o "$d/$f" "$url" && break
    echo "$(date +%T) curl stopped (try $try), resuming"; sleep 20
  done
  check "$d" "$f" "$bytes" "$sha"
}
check() { # dir file bytes sha
  local got; got=$(sudo stat -c %s "$1/$2" 2>/dev/null)
  [ -z "$3" ] || [ "$got" = "$3" ] || { echo "$(date +%T) FAILED size $1/$2: $got, want $3"; return 1; }
  got=$(sudo sha256sum "$1/$2" | cut -d' ' -f1)
  [ "$got" = "$4" ] || { echo "$(date +%T) FAILED sha256 $1/$2"; return 1; }
  echo "sha256 $4" | sudo tee "$1/$2.done" >/dev/null; echo "$(date +%T) OK $1/$2"
}
ngram() { # dir file : the n-gram table (shard 2) is the same bytes for every ISTA size and the Coder; copy it locally
  local d=$M/$1 f=$2
  sudo mkdir -p "$d"
  sudo test -f "$d/$f.done" && { echo "$(date +%T) have $1/$f"; return 0; }
  echo "$(date +%T) copying the n-gram table to $1/$f"
  sudo cp "$NGRAM_SRC" "$d/$f" && check "$d" "$f" 28800138432 $NGRAM_SHA
}
for name in "$@"; do case $name in
  IQ3_XXS) p=Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS
    get IQ3_XXS $p-00001-of-00002.gguf $HF/$ISTA/IQ3_XXS/$p-00001-of-00002.gguf 47039860096 219ea929900dfa9ef091f3aa473fdba6874b65fcb36526d7d851ac9e95856d15
    ngram IQ3_XXS $p-00002-of-00002.gguf ;;
  IQ2_XS) p=Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS
    get IQ2_XS $p-00001-of-00002.gguf $HF/$ISTA/IQ2_XS/$p-00001-of-00002.gguf 39225954592 92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7
    ngram IQ2_XS $p-00002-of-00002.gguf ;;
  coder-IQ1_M) p=Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M
    get coder-IQ1_M $p-00001-of-00002.gguf $HF/$CODER/IQ1_M/$p-00001-of-00002.gguf 29608446496 e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad
    ngram coder-IQ1_M $p-00002-of-00002.gguf ;;
  Gyro-M) f=Qwen3.8-Flash-Next-Gyro-M-TQ2_0.gguf
    get gyro-Gyro-M $f $HF/$GYRO/$f 91965774272 7aa36d15131d255179ab6c87fa9c9f81a0b541fc9e81e959d4c3e29eb20feb5f ;;
  qwen36) f=Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf   # Strata runs it on one card, with no pack
    get qwen36-UD-Q4_K_XL $f $HF/unsloth/Qwen3.6-35B-A3B-MTP-GGUF/resolve/5bc3e238d916f48a861bac2f8a1990a0e9b7e98d/$f 22853663008 55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1 ;;
  bonsai) B=$HF/prism-ml/Ternary-Bonsai-2-27B-gguf/resolve/839bd57023c1558945afea70a74fa83c054f35f9
    M=/srv/models
    get bonsai-2-27b Ternary-Bonsai-2-27B-PQ2_0.gguf $B/Ternary-Bonsai-2-27B-PQ2_0.gguf "" 3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1
    get bonsai-2-27b Ternary-Bonsai-2-27B-PTQ1_0.gguf $B/Ternary-Bonsai-2-27B-PTQ1_0.gguf "" 53107f530aa52eb00912263ab1ee29bd199261c87cd7b4ad4ca1318c1fe33ee3
    M=/srv/strata/models ;;
  *) echo "unknown model $name" ;;
esac; done
echo "$(date +%T) ALL-DOWNLOADS-DONE"; df -h /srv/strata | tail -1
