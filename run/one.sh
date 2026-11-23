#!/usr/bin/env bash
# One la run on the PC (PREREG.md): bash run/one.sh RUN solidcraft|freecad S|T MODEL [NET la-net|la-int]
# Env passed through: LOCAL CTX EXTRA_ENV FC_FLAGS PROMPT WALL_S MAX_TURNS.
# Stop rules (PLAN 3.5): refuses to start under 2 GB Windows free RAM, under 15 GB free on C:, or if another container
# holds the GPU; a sampler logs free RAM + GPU every 5 s and kills the app container under 1 GB (kept as "guard stop").
# Afterwards: Ollama's log for the run window -> ollama.log (request lines, truncation, prompt sizes), truncation count,
# then lab/la_score.py again with that count.
set -uo pipefail
cd "$(dirname "$0")/.."
LA="$(pwd -W 2>/dev/null || pwd)"; ED="$(cd .. && (pwd -W 2>/dev/null || pwd))"
RUN=${1:?RUN}; APP=${2:?app}; TASK=${3:?S|T}; MODEL=${4:?model}; NET=${5:-la-net}
O=out/runs/$RUN
[ -e "$O/stream.jsonl" ] && { echo "refusing: $O has a run"; exit 3; }
mkdir -p "$O"
free_gb() { awk '/MemFree/ {printf "%.2f", $2/1048576}' /proc/meminfo; }
# the WSL VM's page cache (model blobs read at load) is dropped so Windows gets it back (gemma4-12b-8gb-lab pattern)
MSYS_NO_PATHCONV=1 docker run --rm --privileged --entrypoint sh ollama/ollama:0.40.17 -c 'sync; echo 1 > /proc/sys/vm/drop_caches'
for i in $(seq 1 18); do awk -v f="$(free_gb)" 'BEGIN {exit !(f >= 3)}' && break; sleep 5; done
f=$(free_gb); c=$(df -BG /c | awk 'NR==2 {gsub("G","",$4); print $4}')
echo "pre: free RAM $f GB, C: $c GB" | tee "$O/host-pre.txt"
awk -v f="$f" 'BEGIN {exit !(f < 2)}' && { echo "STOP: free RAM $f GB < 2"; exit 5; }
[ "$c" -lt 15 ] && { echo "STOP: C: $c GB < 15"; exit 5; }
for id in $(docker ps -q); do
  n=$(docker inspect -f '{{.Name}} {{json .HostConfig.DeviceRequests}}' "$id")
  case "$n" in "/la-ollama "*|*" null") ;; *) echo "STOP: GPU held: $n"; exit 5 ;; esac
done
if [ "$APP" = solidcraft ]; then
  IMG=sc5-l5:0.28.0; MNT=(-v "$ED/solidcraft-course-lab:/work:ro" -v "$LA:/la"); CMD=(bash /la/lab/la_sc.sh); MEMC=4g; USR=()
else
  IMG=fcc-app:1.1.4-0.1.28; MNT=(-v "$ED/freecad-course-lab:/lab:ro" -v "$LA:/la"); CMD=(bash /la/lab/la_fc.sh); MEMC=6g; USR=(--user maker --hostname pc)
fi
# G0 finding (g4-fc-S guard stop at 0.91 GB): starting the FreeCAD container fills the WSL VM's page cache faster than
# WSL's gradual reclaim gives it back, so a helper drops the VM page cache every 15 s for the run (cache only, no process).
docker rm -f la-dropper > /dev/null 2>&1
MSYS_NO_PATHCONV=1 docker run -d --rm --name la-dropper --privileged --memory 32m --entrypoint sh ollama/ollama:0.40.17 \
  -c 'while true; do sync; echo 1 > /proc/sys/vm/drop_caches; sleep 5; done' > /dev/null
T0=$(date -u +%FT%TZ); S0=$(date +%s)
name=la-run-$RUN
( while docker inspect "$name" > /dev/null 2>&1 || [ $(( $(date +%s) - S0 )) -lt 60 ]; do
    f=$(free_gb); g=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | tr -d '\r ')
    echo "$(date +%s) $f $g" >> "$O/host-samples.txt"
    awk -v f="$f" 'BEGIN {exit !(f < 1)}' && { echo "guard stop: free $f GB" >> "$O/host-guard.txt"; docker kill "$name" > /dev/null 2>&1; }
    sleep 5
  done ) &
SAMP=$!
MSYS_NO_PATHCONV=1 docker run --rm --name "$name" "${USR[@]}" --network "$NET" --memory "$MEMC" --shm-size 1g "${MNT[@]}" \
  -e RUN="$RUN" -e TASK="$TASK" -e MODEL="$MODEL" -e LOCAL="${LOCAL:-1}" -e CTX="${CTX:-}" -e EXTRA_ENV="${EXTRA_ENV:-}" \
  -e FC_FLAGS="${FC_FLAGS:-}" -e PROMPT="${PROMPT:-}" -e WALL_S="${WALL_S:-1500}" -e MAX_TURNS="${MAX_TURNS:-30}" \
  "$IMG" "${CMD[@]}" > "$O/container.log" 2>&1
echo "container exit $?" >> "$O/container.log"
kill $SAMP 2>/dev/null; wait $SAMP 2>/dev/null; docker rm -f la-dropper > /dev/null 2>&1
if docker inspect la-ollama > /dev/null 2>&1; then
  docker logs --since "$T0" la-ollama 2>&1 | grep -a -i -E 'truncat|POST|prompt|offload|level=(WARN|ERROR)|n_ctx|eval|tokens' > "$O/ollama.log"
  grep -a -i -c -E 'truncating input|truncated = [1-9]' "$O/ollama.log" > "$O/ollama-truncations.txt"
fi
awk 'NR==1 {m=$2; g=$3} {if ($2 < m) m=$2; if ($3 > g) g=$3} END {printf "{\"free_gb_min\": %s, \"gpu_mib_peak\": %s, \"samples\": %d}\n", m, g, NR}' \
  "$O/host-samples.txt" > "$O/host.json" 2>/dev/null
echo "{\"run\": \"$RUN\", \"app\": \"$APP\", \"task\": \"$TASK\", \"model\": \"$MODEL\", \"net\": \"$NET\", \"start\": \"$T0\", \"host_wall_s\": $(( $(date +%s) - S0 ))}" > "$O/run.json"
MSYS_NO_PATHCONV=1 docker run --rm -v "$LA:/la" -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3 gemma4-lab-runner:1 \
  /la/lab/la_score.py "/la/$O" "$APP" "$TASK"
cat "$O/host.json"
