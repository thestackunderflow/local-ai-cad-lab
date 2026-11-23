#!/bin/bash
# la SolidCraft run (PLAN la 3.3): in sc5-l5:0.28.0, solidcraft-course-lab mounted read-only at /work, this repo at /la.
# SolidCraft 0.28.0 on Xvfb, an empty design (S) or lesson 14's ~/peg-trap.sc (T); Claude Code headless (-p) with
# --strict-mcp-config (SolidCraft plug only, behind the logging proxy), --max-turns 30, a 25 min wall clock; then the
# design read and scored by code (S: lab/la_score.py from read-after.json; T: lesson 14's lab/sc14parts.py sweep, unchanged).
# Env: RUN TASK(S|T) MODEL; LOCAL=1 adds the base URL lines (BASE_URL, CTX); EXTRA_ENV="K=V ..." for G0 variations.
set -u
O=/la/out/runs/${RUN:?}; : "${TASK:?}" "${MODEL:?}"
[ -e "$O/stream.jsonl" ] && { echo "refusing: $O has a run"; exit 1; }
mkdir -p "$O"
. /la/lab/la_common.sh
mkdir -p "$HOME/.claude"; printf '{"claudeMdExcludes": ["/work/**", "/la/**"]}\n' > "$HOME/.claude/settings.json"
. /work/lab/fx13lib.sh
E=$O/events.jsonl; : > "$E"
python3 - <<'PY'
import json, os
json.dump({'hasCompletedOnboarding': True, 'theme': 'light',
           'projects': {'/root': {'hasTrustDialogAccepted': True, 'hasCompletedProjectOnboarding': True}}},
          open(os.path.expanduser('~/.claude.json'), 'w'), indent=1)
PY
solidcraft-cli mcp setup > "$O/setup.txt" 2>&1
start_display
openbox > /dev/null 2>&1 &
sleep 1
start_app "$O/app.log" /opt/solidcraft/bin/solidcraft
sleep 10
python3 /work/client/ctl.py ui.prefs "{\"theme\":\"light\",\"ui_scale\":$SCALE}" 27878 > /dev/null 2>&1
fill_window 0 0 $W $H; sleep 2
g 398 206 6; xdotool click 1; sleep 3                          # start page: New design
if [ "$TASK" = T ]; then
  cp /work/out/sc14/P/peg-trap.sc /root/peg-trap.sc; sha256sum /root/peg-trap.sc > "$O/start-sha256.txt"
  FX9_ALLOW=1 python3 /work/lab/fx9.py open /root/peg-trap.sc > "$O/open.txt" 2>&1; sleep 3
  grep -q '"isError": true' "$O/open.txt" && { echo "setup: the start file did not open"; echo void > "$O/VOID"; exit 4; }
fi
FX9_ALLOW=1 python3 /work/lab/fx9.py read "$O" before > "$O/read-before.txt" 2>&1
shot "$O/before.png"
python3 - "$O" <<'PY'
import json, os, sys
o = sys.argv[1]
d = json.load(open(os.path.expanduser('~/.claude.json')))
e = d['mcpServers']['solidcraft']
args = list(e.get('args') or []) + ['--allow-path', '/root']      # lesson 7's fix, as lesson 14
run = {'command': 'python3', 'args': ['/work/proxy/mcp_log_proxy.py', '--log', o + '/transcript.jsonl', '--png-dir', o,
                                     '--watchdog', '330', '--', e['command']] + args}
json.dump({'mcpServers': {'solidcraft': run}}, open(os.path.join(o, 'entry.json'), 'w'), indent=1)
PY
la_claude solidcraft /root
FX9_ALLOW=1 python3 /work/lab/fx9.py read "$O" after > "$O/read-after.txt" 2>&1
shot "$O/after.png"
python3 /work/lab/sc14api.py "$O" save 300 "[[\"save\", {\"path\": \"/root/run-$RUN.sc\"}]]" > "$O/save.txt" 2>&1
cp "/root/run-$RUN.sc" "$O/run-$RUN.sc" 2>/dev/null
[ "$TASK" = T ] && (cd /work && python3 -I /work/lab/sc14parts.py "$O" sweep after > "$O/score-after.txt" 2>&1)
pkill -x solidcraft
python3 /la/lab/la_score.py "$O" solidcraft "$TASK" > "$O/score.txt" 2>&1
cat "$O/score.txt"
echo "run $RUN done"
