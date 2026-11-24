#!/bin/bash
# la FreeCAD run (PLAN la 3.3): in fcc-app:1.1.4-0.1.28 as maker, freecad-course-lab mounted read-only at /lab, this repo
# at /la. FreeCAD 1.1.4 on Xvfb with the add-on's socket on (auto-start), no document (S) or lesson 14's peg-trap.FCStd
# open (T). G6: a no-AI MCP client asks the plug list_documents before the run (no answer = void, re-run once).
# Claude Code headless (-p), --strict-mcp-config (freecad plug only, logging proxy, uvx freecad-mcp@0.1.28 + FC_FLAGS),
# --max-turns 30, 25 min wall clock. After: every open document saved and scored by code (S: lab/la_fcS.py; T: lesson
# 14's lab/fc14parts.py check, unchanged). Env as lab/la_sc.sh, plus FC_FLAGS (G5: "--only-text-feedback" or "").
set -u
O=/la/out/runs/${RUN:?}; : "${TASK:?}" "${MODEL:?}"
[ -e "$O/stream.jsonl" ] && { echo "refusing: $O has a run"; exit 1; }
mkdir -p "$O"
. /la/lab/la_common.sh
mkdir -p "$HOME/.claude"; printf '{"claudeMdExcludes": ["/lab/**", "/la/**"]}\n' > "$HOME/.claude/settings.json"
. /lab/lab/common.sh; . /lab/lab/fx19_lib.sh; . /lab/lab/fx20_lib.sh; . /lab/lab/fc9_lib.sh; . /lab/lab/fc10_lib.sh; . /lab/lab/fc11_lib.sh; . /lab/lab/fc12_lib.sh; . /lab/lab/fc13_lib.sh; . /lab/lab/fc14_lib.sh
cd ~ && tar xzf /lab/out/scratch/seed/fc-profile.tgz
tools_install; addon_install; autostart_on true
mkdir -p ~/la ~/run-la; claude_home /home/maker/run-la
uvx freecad-mcp@0.1.28 --help > /dev/null 2>&1
python3 - "$O" "${FC_FLAGS:-}" <<'PY'
import json, os, sys
o, flags = sys.argv[1], sys.argv[2].split()
e = {'command': 'python3', 'args': ['/lab/proxy/mcp_log_proxy.py', '--log', o + '/transcript.jsonl', '--png-dir', o,
                                   '--', 'uvx', 'freecad-mcp@0.1.28'] + flags}
json.dump({'mcpServers': {'freecad': e}}, open(os.path.join(o, 'entry.json'), 'w'), indent=1)
PY
sl_display $W $H
fc_start "$O/app.log" 1.5; sleep 8
place "FreeCAD 1.1.4" 0 0 $W $H; sleep 1
if [ "$TASK" = T ]; then
  cp $X/P/peg-trap.FCStd ~/la/peg.FCStd; sha256sum ~/la/peg.FCStd > "$O/start-sha256.txt"
  Q "import FreeCAD, FreeCADGui
d = FreeCAD.openDocument('/home/maker/la/peg.FCStd')
print(d.Name)" > "$O/setup-rpc.txt" 2>&1
  FQ "prep('peg')" >> "$O/setup-rpc.txt" 2>&1
fi
report_hide; sleep 2
SL_SHOT_WAKE=0 sl_shot "$O/before.png"
# G6: the socket answers a no-AI MCP client through the same plug
python3 - "$O" <<'PY' > "$O/g6.txt" 2>&1
import json, sys
sys.path.insert(0, '/lab')
from client.mcp import McpClient
c = McpClient(['uvx', 'freecad-mcp@0.1.28', '--only-text-feedback'], timeout_s=60)
c.start()
r = c.call_tool('list_documents', {})
print(json.dumps(r)[:600])
c.close()
PY
grep -q -E '"isError": true|Failed|refused|Errno|Traceback' "$O/g6.txt" && { echo "G6: socket off before the run"; echo void > "$O/VOID"; exit 4; }
# REC=1 (filmed take S12-fc, render stage 3): the whole display recorded (screen-lab kit) into $O/take/ from 3 s before
# the Claude Code start to 8 s after its end.
if [ "${REC:-0}" = 1 ]; then mkdir -p "$O/take"; sl_record "$O/take" nomouse; sl_mark "take S12 start"; sleep 3; fi
la_claude freecad /home/maker/run-la
if [ "${REC:-0}" = 1 ]; then sl_mark "claude end"; Q "import FreeCADGui; FreeCADGui.SendMsgToActiveView('ViewFit'); print(1)" > /dev/null 2>&1; sleep 8; sl_stop; fi
SL_SHOT_WAKE=0 sl_shot "$O/after.png"
Q "import FreeCAD; print('\n'.join(d.Name for d in FreeCAD.listDocuments().values()))" > "$O/docs.txt" 2>&1
for d in $(cat "$O/docs.txt"); do lab_save "$d" "$O/after-$d.FCStd" >> "$O/save.log" 2>&1; done
fc_quit; pkill Xvfb 2>/dev/null
if [ "$TASK" = T ]; then
  for f in "$O"/after-*.FCStd; do [ -e "$f" ] && check14 "$f" "${f%.FCStd}.check.json" >> "$O/check.log"; done
else
  for f in "$O"/after-*.FCStd; do [ -e "$f" ] && \
    LA_DOC=$f LA_OUT=${f%.FCStd}.s.json timeout 300 /opt/freecad/AppRun freecadcmd /la/lab/la_fcS.py 2>&1 | tr '\r' '\n' | grep '^LAS' | tail -1 >> "$O/check.log"; done
fi
python3 /la/lab/la_score.py "$O" freecad "$TASK" > "$O/score.txt" 2>&1
cat "$O/score.txt"
echo "run $RUN done"
