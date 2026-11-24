#!/bin/bash
# la FreeCAD takes (SCRIPT-la F9 + F10), no AI, in fcc-app:1.1.4-0.1.28 as maker; freecad-course-lab at /lab (ro), this
# repo at /la, the screen-lab kit through /lab's common.sh. Started by run/film_fc.sh (docker run -d, lock held there).
#   F    FreeCAD 1.1.4 full window (socket OFF: the add-on's auto-start off): hold, workbench list -> type "MCP" ->
#        "MCP Addon", the toolbar's "Start RPC Server", the status bar held 6 s
#   Mfc  the terminal take for the FreeCAD plug (as take M): claude mcp add freecad -- uvx freecad-mcp@0.1.28
#        --only-text-feedback, then claude mcp list (FreeCAD stays open with the socket on, off screen behind the terminal)
# Positions are measured OFF CAMERA first (a pre-pass with the socket on, Qt widget centres in display px), then FreeCAD
# is restarted with the socket off for the filmed pass: the clicks hit the measured spots. Out: /la/out/takes/{F,Mfc}/.
set -u
export W=2880 H=1620
. /lab/lab/common.sh; . /lab/lab/fx19_lib.sh; . /lab/lab/fc8_lib.sh
OUT=/la/out/takes; mkdir -p "$OUT/F" "$OUT/Mfc"; L=$OUT/F/take.log; : > "$L"
cd ~ && tar xzf /lab/out/scratch/seed/fc-profile.tgz
tools_install; addon_install
uvx freecad-mcp@0.1.28 --help > /dev/null 2>&1      # the package in uv's cache before the filmed list (not filmed)
sl_display $W $H; xdotool mousemove $((W - 60)) $((H - 60))

# ---- pre-pass (not filmed): socket on, measure the workbench list and the Start RPC Server button, hide the docks ----
autostart_on true
fc_start "$OUT/F/app-pre.log" 1.5; sleep 8; place "FreeCAD 1.1.4" 0 0 $W $H; sleep 3
Q "exec(open('/lab/lab/fc8q.py').read())
import time
cur = FreeCADGui.activeWorkbench().MenuText
names = {v.MenuText: k for k, v in FreeCADGui.listWorkbenches().items()}
wb = [c for c in _mw.findChildren(QtWidgets.QComboBox) if c.isVisible() and c.currentText() == cur]
out = ['CUR ' + cur, 'WB ' + (' '.join(map(str, _px(wb[0]))) if wb else 'none')]
FreeCADGui.activateWorkbench(names['MCP Addon'])
for i in range(10):
    QtWidgets.QApplication.processEvents(); time.sleep(0.2)
bt = [b for b in _mw.findChildren(QtWidgets.QToolButton) if b.isVisible() and b.defaultAction() and b.defaultAction().text() == 'Start RPC Server']
out.append('BT ' + (' '.join(map(str, _px(bt[0]))) if bt else 'none'))
FreeCADGui.activateWorkbench(names[cur])
for i in range(5):
    QtWidgets.QApplication.processEvents(); time.sleep(0.2)
n = 0
for w in _mw.findChildren(QtWidgets.QDockWidget):
    if w.windowTitle() in ('Tasks', 'Combo View', 'Report view', 'Python console') or w.objectName() in ('Tasks', 'TaskView', 'Combo View', 'Report view', 'Python console'):
        w.hide(); n += 1
out.append('DOCKS %d' % n)
print(chr(10).join(out))" > "$OUT/F/positions.txt" 2>&1
cat "$OUT/F/positions.txt" >> "$L"
fc_quit; sleep 3
WBP=$(awk '$1 == "WB" {print $2, $3}' "$OUT/F/positions.txt"); BTP=$(awk '$1 == "BT" {print $2, $3}' "$OUT/F/positions.txt")
case "$WBP $BTP" in *none*|" "|"") echo "STOP: positions not measured" | tee -a "$L"; sl_display_stop; exit 4;; esac

# ---- take F (filmed): socket off ----
autostart_on false
fc_start "$OUT/F/app.log" 1.5; sleep 8; place "FreeCAD 1.1.4" 0 0 $W $H; sleep 3
xdotool mousemove $((W - 60)) $((H - 60))
sl_record "$OUT/F" nomouse; sl_mark "take F start: full window, socket off"; sl_nap 3
SL_SHOT_WAKE=0 sl_shot "$OUT/F/01-window.png"
sl_glide ${WBP% *} ${WBP#* } 20; sl_nap 0.6
sl_click ${WBP% *} ${WBP#* } "workbench list: opened"; sl_nap 2.5
SL_SHOT_WAKE=0 sl_shot "$OUT/F/02-list.png"
xdotool type --delay 150 "MCP"; sl_nap 1.2; sl_key Return "workbench list: MCP Addon chosen"; sl_nap 2.5
SL_SHOT_WAKE=0 sl_shot "$OUT/F/03-mcp-addon.png"
sl_glide ${BTP% *} ${BTP#* } 20; sl_nap 1.0
sl_click ${BTP% *} ${BTP#* } "FreeCAD: Start RPC Server"; sl_nap 1.5
sl_mark "status bar: started (hold 6 s)"; xdotool mousemove $((W - 60)) $((H - 60))
SL_SHOT_WAKE=0 sl_shot "$OUT/F/04-status.png"; sl_nap 6
sl_mark "take F end"; sl_stop
Q "import FreeCADGui; print('workbench:', FreeCADGui.activeWorkbench().MenuText)" >> "$L" 2>&1
ss -ltn 2>/dev/null | grep -q ':9875' && echo "socket 9875: listening" >> "$L" || echo "socket 9875: NOT listening" >> "$L"

# ---- take Mfc (filmed): the terminal on top, as take M ----
printf 'PS1='"'"'\\[\\e[1;32m\\]$\\[\\e[0m\\] '"'"'\nexport PATH="$HOME/.local/bin:$PATH"\ncd ~\n' > ~/.bashrc
claude_home /home/maker
mkdir -p ~/.claude; printf '{"claudeMdExcludes": ["/lab/**", "/la/**"]}\n' > ~/.claude/settings.json
term_open Terminal 0 0 110 30 24 bash; w=$(sl_wait_window '^Terminal$' 30)
xdotool windowsize --sync "$w" $W $H; xdotool windowmove "$w" 0 0; xdotool windowactivate --sync "$w"
xdotool mousemove $((W - 40)) $((H - 40)); sleep 1.5; tmux send-keys -t Terminal 'clear' Enter; sleep 1; tmux clear-history -t Terminal
pc() { tmux capture-pane -p -J -S -2000 -t Terminal | grep -cE '^\$( |$)'; }
tt() {   # tt "command" REGEX TIMEOUT HOLD: typed at 45 ms/char (as la_term.sh), Enter, wait for the next prompt
  local c=$1 re=$2 to=${3:-60} hold=${4:-3} i n
  n=$(pc); sl_mark "type: $c"
  for ((i = 0; i < ${#c}; i++)); do tmux send-keys -t Terminal -l -- "${c:i:1}"; sleep 0.045; done
  sleep 0.6; tmux send-keys -t Terminal Enter; sl_mark "enter: $c"
  for ((i = 0; i < to * 4; i++)); do [ "$(pc)" -gt "$n" ] && break; sleep 0.25; done
  tmux capture-pane -p -J -S -2000 -t Terminal | grep -Eq -- "$re" && sl_mark "seen: $re" || sl_mark "NOT SEEN: $re"
  sleep "$hold"
}
sl_record "$OUT/Mfc" nomouse; sl_nap 1.5; sl_mark "take Mfc start"
tt "claude mcp add freecad -- uvx freecad-mcp@0.1.28 --only-text-feedback" '[Aa]dded|rror' 60 3
tt "claude mcp list" 'freecad.*([Cc]onnected|[Ff]ailed)' 120 6
sl_mark "take Mfc end"; sleep 1
tmux capture-pane -p -J -S -2000 -t Terminal > "$OUT/Mfc/pane.txt"; SL_SHOT_WAKE=0 sl_shot "$OUT/Mfc/end.png"; sl_stop
fc_quit; sl_display_stop
echo "la_fcfilm done" >> "$L"
