#!/usr/bin/env bash
# G0 light run on the PC: TAG=.. PLUGS=.. PROMPT=.. [NET=la-net|la-int] bash run/g0.sh ; Ollama log for the window -> ollama.log
set -uo pipefail
cd "$(dirname "$0")/.."
LA="$(pwd -W 2>/dev/null || pwd)"; O=out/g0/${TAG:?}; mkdir -p "$O"
T0=$(date -u +%FT%TZ)
MSYS_NO_PATHCONV=1 docker run --rm --name "la-g0-$TAG" --network "${NET:-la-net}" --memory 3g -v "$LA:/la" \
  -e TAG -e PLUGS -e PROMPT -e MODEL="${MODEL:-gemma4:12b-it-qat}" -e LOCAL="${LOCAL:-1}" -e CTX="${CTX:-}" \
  -e EXTRA_ENV="${EXTRA_ENV:-}" -e FC_FLAGS="${FC_FLAGS:-}" -e ENABLE_TOOL_SEARCH="${ENABLE_TOOL_SEARCH:-false}" \
  -e TRAFFIC_OFF="${TRAFFIC_OFF:-1}" -e OUTPUT="${OUTPUT:-stream-json}" -e MAX_TURNS="${MAX_TURNS:-3}" -e WALL_S="${WALL_S:-600}" \
  --entrypoint bash sc5-l5:0.28.0 /la/lab/g0_cc.sh
docker logs --since "$T0" la-ollama > "$O/ollama-full.log" 2>&1
grep -a -i -E 'truncat|\| *POST|GET|prompt|offload|level=(WARN|ERROR)|n_ctx|model=' "$O/ollama-full.log" | cut -c1-400 > "$O/ollama.log"
echo "free RAM $(awk '/MemFree/ {printf "%.2f", $2/1048576}' /proc/meminfo) GB" > "$O/host-after.txt"
