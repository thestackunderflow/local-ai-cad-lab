#!/usr/bin/env bash
# la Ollama (PLAN la 3.1): bash lab/ollama_up.sh CTX [KV f16|q8_0] [MEM 6g|16g]
# One container la-ollama on la-net (+ la-int, internal, for G1c), port 11434, the gemma labs' model volume (blobs match
# the registry on 22 Nov), pinned by digest. Re-created to change the page (as step 3 of the video: rm, run again).
set -euo pipefail
CTX=${1:?CTX}; KV=${2:-f16}; MEM=${3:-6g}
IMG=ollama/ollama:0.40.17@sha256:ccc42bcd3d5fcf7ab0d532b300382154e1a4da56fc666bdb313b78ebdd912754
docker network inspect la-net > /dev/null 2>&1 || docker network create --subnet 10.231.77.0/24 la-net > /dev/null
docker network inspect la-int > /dev/null 2>&1 || docker network create --internal --subnet 10.231.78.0/24 la-int > /dev/null
docker rm -f la-ollama > /dev/null 2>&1 || true
CTXE=(); [ "$CTX" = default ] || CTXE=(-e "OLLAMA_CONTEXT_LENGTH=$CTX")   # "default" = Ollama's own page (G2b)
MSYS_NO_PATHCONV=1 docker run -d --name la-ollama --gpus=all --memory "$MEM" --network la-net -p 127.0.0.1:11434:11434 \
  -v gemma-lab-models:/root/.ollama \
  "${CTXE[@]}" -e OLLAMA_KV_CACHE_TYPE="$KV" -e OLLAMA_FLASH_ATTENTION=1 -e OLLAMA_NUM_PARALLEL=1 \
  -e OLLAMA_MAX_LOADED_MODELS=1 -e OLLAMA_KEEP_ALIVE=30m -e OLLAMA_DEBUG=1 -e OLLAMA_NOPRUNE=1 "$IMG" > /dev/null
docker network connect la-int la-ollama
for i in $(seq 1 30); do curl -s http://127.0.0.1:11434/ | grep -q "Ollama is running" && break; sleep 1; done
curl -s http://127.0.0.1:11434/api/version; echo " ctx=$CTX kv=$KV mem=$MEM"
