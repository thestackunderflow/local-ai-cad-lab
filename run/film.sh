#!/usr/bin/env bash
# Host launcher for the la terminal takes: bash run/film.sh TAKE...   (e.g. O P C)
# Takes Refream-Canvas/.render-lock (atomic mkdir + owner.txt, released on EXIT only if ours), refuses under 5 GB Windows
# free RAM (MIN_KB overrides for takes that load no model, e.g. M), copies a static docker CLI out of docker:27.4.0-cli once, runs lab/la_term.sh in sc5-l5:0.28.0 on la-net with
# the Docker socket. Footage: out/takes/<TAKE>/ (git-ignored).
set -uo pipefail
cd "$(dirname "$0")/.."
LA="$(pwd -W 2>/dev/null || pwd)"; ED="$(cd .. && (pwd -W 2>/dev/null || pwd))"
LOCK=../Refream-Canvas/.render-lock; ME="la film $* pid $$ $(date -u +%FT%TZ)"
mkdir "$LOCK" 2> /dev/null || { echo "STOP: lock held: $(cat "$LOCK/owner.txt" 2>/dev/null)"; exit 6; }
echo "$ME" > "$LOCK/owner.txt"
trap '[ "$(cat "$LOCK/owner.txt" 2>/dev/null)" = "$ME" ] && rm -rf "$LOCK"' EXIT
free_kb=$(powershell -NoProfile -c "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory" | tr -d '\r ')
[ "${free_kb:-0}" -ge ${MIN_KB:-5242880} ] || { echo "STOP: Windows free RAM ${free_kb} kB < 5 GB"; exit 5; }
mkdir -p out/bin out/takes
if [ ! -x out/bin/docker ]; then
  id=$(docker create docker:27.4.0-cli); docker cp "$id:/usr/local/bin/docker" out/bin/docker; docker rm "$id" > /dev/null
fi
MSYS_NO_PATHCONV=1 docker run --rm --name la-film --network la-net --memory 4g --shm-size 512m \
  -v //var/run/docker.sock:/var/run/docker.sock -v "$LA:/la" -v "$ED/screen-lab-kit:/kit:ro" \
  --entrypoint bash sc5-l5:0.28.0 /la/lab/la_term.sh "$@"
