#!/usr/bin/env bash
# Host launcher, DETACHED: bash run/film_fc.sh -> takes Refream-Canvas/.render-lock (mkdir + owner.txt "la lab film fc ..."),
# refuses under 3 GB Windows free RAM, drops the Docker VM page cache, starts lab/la_fcfilm.sh in fcc-app:1.1.4-0.1.28
# with `docker run -d --name la-filmfc` and returns. The poller waits for the container to exit, then releases the lock
# with `bash run/film_fc.sh release` (only if owner.txt is ours). Footage: out/takes/{F,Mfc}/ (git-ignored).
set -uo pipefail
cd "$(dirname "$0")/.."
LA="$(pwd -W 2>/dev/null || pwd)"; ED="$(cd .. && (pwd -W 2>/dev/null || pwd))"
LOCK=../Refream-Canvas/.render-lock
if [ "${1:-}" = release ]; then
  grep -q '^la lab film fc' "$LOCK/owner.txt" 2>/dev/null && rm -rf "$LOCK" && echo released; exit 0
fi
mkdir "$LOCK" 2> /dev/null || { echo "STOP: lock held: $(cat "$LOCK/owner.txt" 2>/dev/null)"; exit 6; }
echo "la lab film fc F Mfc $(date -u +%FT%TZ)" > "$LOCK/owner.txt"
wsl -d docker-desktop sh -c "sync; echo 3 > /proc/sys/vm/drop_caches" 2> /dev/null
free_kb=$(powershell -NoProfile -c "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory" | tr -d '\r ')
[ "${free_kb:-0}" -ge 3145728 ] || { echo "STOP: free RAM ${free_kb} kB < 3 GB"; rm -rf "$LOCK"; exit 5; }
docker rm -f la-filmfc > /dev/null 2>&1
MSYS_NO_PATHCONV=1 docker run -d --name la-filmfc --hostname pc --user maker --network la-net --memory 6g --shm-size 1g \
  -v "$ED/freecad-course-lab:/lab:ro" -v "$LA:/la" fcc-app:1.1.4-0.1.28 bash /la/lab/la_fcfilm.sh
