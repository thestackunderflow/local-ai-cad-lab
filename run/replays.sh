#!/bin/sh
# Replay strips for F14 F16 F20-F22 (light: PIL frames in cad3way-draw:1, encode in video-qa:2). Seconds = the rows' lengths.
set -e
EV="$(cd "$(dirname "$0")/../.." && pwd -W)"
d() { MSYS_NO_PATHCONV=1 docker run --rm -v "$EV:/ev" -w /ev/local-ai-cad-lab "$@"; }
mkdir -p "$(dirname "$0")/../out/replays"
while read run secs title; do
  d cad3way-draw:1 python3 lab/la_replay.py "$run" "$secs" "$title" "out/replays/$run.mp4"
  d video-qa:2 python3 lab/la_replay.py encode "out/replays/$run.mp4" "$secs"
done <<LIST
12-sc-T-1r 28.6 Gemma 4 12B · SolidCraft
12-fc-T-2r 17.4 Gemma 4 12B · FreeCAD
cl-sc-T-1 9.1 Claude · SolidCraft
cl-fc-T-1 9.1 Claude · FreeCAD
f12-sc-S 12.0 Gemma 4 12B · SolidCraft
f12-fc-S 8.0 Gemma 4 12B · FreeCAD
LIST
