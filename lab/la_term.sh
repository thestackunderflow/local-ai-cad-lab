#!/bin/bash
# la terminal takes (PLAN la 3.4: O, P, C, M (SolidCraft plug), E): a real xterm + tmux on a 2880 x 1620 virtual screen,
# typed at a person's pace, recorded with the screen-lab kit (/kit). Runs in sc5-l5:0.28.0 (Claude Code + solidcraft-cli)
# started by run/film.sh with the Docker socket and a docker CLI binary (/la/out/bin/docker): every `docker` line on
# screen is real and drives the PC's Docker. localhost:11434 inside this container is forwarded to the PC's 11434 (as on
# a viewer's PC). No key anywhere: ANTHROPIC_API_KEY is unset; claude.ai connectors are never listed (fresh HOME, no
# login, --strict-mcp-config on every Claude Code start that talks to a model).
# Usage (in the container): bash /la/lab/la_term.sh TAKE...   (TAKE = O | P | C | M | E)
set -uo pipefail
. /kit/lib/screenlab.sh
export PATH=/la/out/bin:/opt/solidcraft/bin:$PATH HOME=/root LANG=C.UTF-8 LC_ALL=C.UTF-8
unset ANTHROPIC_API_KEY
OUT=/la/out/takes
W=2880; H=1620
IMG=ollama/ollama:0.40.17
RUNLINE_DEFAULT="docker run -d --gpus=all -v gemma-models:/root/.ollama -p 127.0.0.1:11434:11434 --name ollama $IMG"
RUNLINE_PAGE="docker run -d --gpus=all -v gemma-models:/root/.ollama -p 127.0.0.1:11434:11434 -e OLLAMA_CONTEXT_LENGTH=65536 -e OLLAMA_KV_CACHE_TYPE=q8_0 -e OLLAMA_FLASH_ATTENTION=1 --name ollama $IMG"
CC="claude --model gemma4:12b-it-qat --strict-mcp-config"
REPLY_MARK=$(printf '●')   # Claude Code 2.1.311's reply bullet (U+25CF)

# localhost:11434 -> the PC's port (the container has no Ollama of its own)
python3 - > /dev/null 2>&1 <<'PY' &
import socket, threading
def pipe(a, b):
    try:
        while (d := a.recv(65536)): b.sendall(d)
    except OSError: pass
    finally:
        for s in (a, b):
            try: s.shutdown(socket.SHUT_RDWR)
            except OSError: pass
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(('127.0.0.1', 11434)); srv.listen(16)
while True:
    c, _ = srv.accept()
    try: u = socket.create_connection(('host.docker.internal', 11434))
    except OSError: c.close(); continue
    threading.Thread(target=pipe, args=(c, u), daemon=True).start(); threading.Thread(target=pipe, args=(u, c), daemon=True).start()
PY

mkdir -p "$HOME/.claude"
python3 - <<'PY'
import json, os
json.dump({'hasCompletedOnboarding': True, 'theme': 'light',
           'projects': {'/root': {'hasTrustDialogAccepted': True, 'hasCompletedProjectOnboarding': True}}},
          open(os.path.expanduser('~/.claude.json'), 'w'), indent=1)
PY
printf '{"claudeMdExcludes": ["/la/**", "/work/**"]}\n' > "$HOME/.claude/settings.json"
printf 'set -g status off\nset -g history-limit 5000\n' > "$HOME/.tmux.conf"
cat > "$HOME/.bashrc" <<'RC'
PS1='\[\e[1;32m\]$\[\e[0m\] '
export PATH=/la/out/bin:/opt/solidcraft/bin:$PATH
cd /root
RC

sl_display $W $H
xterm -u8 -geometry 110x30+0+0 -fa "DejaVu Sans Mono" -fs 24 -bg white -fg black -T Terminal \
  -e tmux -u new-session -s t > /dev/null 2>&1 &
w=$(sl_wait_window '^Terminal$' 30) || { echo "no terminal window"; exit 4; }
xdotool windowsize --sync "$w" $W $H; xdotool windowmove "$w" 0 0; xdotool mousemove $((W-40)) $((H-40))
sleep 2; tmux send-keys -t t 'clear' Enter; sleep 1

typeit() { local c=$1 i; for ((i = 0; i < ${#c}; i++)); do tmux send-keys -t t -l -- "${c:i:1}"; sleep 0.045; done; }
pcount() { tmux capture-pane -p -J -S -2000 -t t | grep -cE '^\$( |$)'; }
lastline() { tmux capture-pane -p -J -t t | grep -v '^[[:space:]]*$' | tail -n 1; }
tt() {   # tt "command" REGEX TIMEOUT [HOLD]: type, Enter, wait for the NEXT shell prompt (the command finished; nothing
         # is typed ahead), then check REGEX on the output after the command line only, hold
  local c=$1 re=$2 to=${3:-30} hold=${4:-2.5} i n out
  n=$(pcount); sl_mark "type: $c"; typeit "$c"
  sleep 0.6; tmux send-keys -t t Enter; sl_mark "enter: $c"
  for ((i = 0; i < to * 4; i++)); do
    [ "$(pcount)" -gt "$n" ] && lastline | grep -qE '^\$ ?$' && break; sleep 0.25
  done
  out=$(tmux capture-pane -p -J -S -2000 -t t | awk -v c="$c" 'index($0, c) {buf = ""; f = 1; next} f {buf = buf $0 "\n"} END {printf "%s", buf}')
  if lastline | grep -qE '^\$ ?$'; then sl_mark "done: $c"; else sl_mark "TIMEOUT (no prompt): $c"; fi
  printf '%s' "$out" | grep -Eq -- "$re" && sl_mark "seen: $re" || sl_mark "NOT SEEN: $re"
  sleep "$hold"
}
say() {  # say "text" REGEX TIMEOUT HOLD: type into the visible screen (Claude Code's box or a shell), Enter, wait until
         # the VISIBLE pane (no scrollback) matches REGEX on a line that is not the typed text
  local c=$1 re=$2 to=${3:-60} hold=${4:-3} i
  sl_mark "type: $c"; typeit "$c"; sleep 0.6; tmux send-keys -t t Enter; sl_mark "enter: $c"; sleep 2
  for ((i = 0; i < to * 4; i++)); do tmux capture-pane -p -J -t t | grep -vF -- "$c" | grep -Eq -- "$re" && break; sleep 0.25; done
  tmux capture-pane -p -J -t t | grep -vF -- "$c" | grep -Eq -- "$re" && sl_mark "seen: $re" || sl_mark "TIMEOUT waiting: $re"
  sleep "$hold"
}
clr() { tmux send-keys -t t 'clear' Enter; sleep 0.5; tmux clear-history -t t; sleep 1; }
begin() { D=$OUT/$1; rm -rf "$D"; mkdir -p "$D"; clr; sl_record "$D" nomouse; sleep 1.5; sl_mark "take $1 start"; }
finish() { sleep 2; tmux capture-pane -p -J -S -2000 -t t > "$D/pane.txt"; sl_shot "$D/end.png"; sl_stop; }

take_O() {   # step 1: Ollama in Docker on the default page; "Ollama is running"; the card's name in the log
  docker rm -f ollama > /dev/null 2>&1
  begin O
  tt "$RUNLINE_DEFAULT" '^[0-9a-f]{64}' 90 3
  tt "curl -w '\n' http://localhost:11434" 'Ollama is running' 30 4
  tt "docker logs ollama 2>&1 | grep -E 'Listening|inference compute'" 'RTX' 30 6
  finish
}
take_P() {   # step 2: the model (already on this PC's disk: the pull checks it; the label says so), list, show
  begin P
  tt "docker exec -it ollama ollama pull gemma4:12b-it-qat" 'success|Error' 900 3
  tt "docker exec -it ollama ollama list" 'GB' 30 4
  tt "docker exec -it ollama ollama show gemma4:12b-it-qat" 'tools' 30 6
  finish
}
take_C() {   # step 3: the default page refuses Claude Code's first request; then the page set, ollama ps CONTEXT
  begin C
  tt "export ANTHROPIC_BASE_URL=http://localhost:11434 ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY=" '.*' 10 1
  tt "claude -p \"say hi\" --model gemma4:12b-it-qat --strict-mcp-config" 'API Error' 400 5
  tt "docker logs ollama 2>&1 | grep 'v1/messages' | tail -n 2" '400' 20 6
  clr
  tt "docker rm -f ollama" 'ollama' 30 1.5
  tt "$RUNLINE_PAGE" '^[0-9a-f]{64}' 90 2
  tt "claude -p \"say hi\" --model gemma4:12b-it-qat --strict-mcp-config" '[A-Za-z]' 500 4
  tt "docker exec -it ollama ollama ps" 'CONTEXT' 30 3
  tt "docker logs ollama 2>&1 | grep -E 'offloaded' | tail -n 1" 'offloaded' 20 6
  finish
}
take_M() {   # step 4 (SolidCraft plug; the FreeCAD line is filmed in the FreeCAD image): add, list
  begin M
  tt "claude mcp add solidcraft -- solidcraft-cli mcp" '[Aa]dded|rror' 60 3
  tt "claude mcp list" '[Cc]onnected|[Ff]ailed' 90 6
  finish
}
take_E() {   # step 6: five lines, Claude Code on the 12B (the G9 "assumes 200k" warning), /exit, the page line, again,
             # say hi, Ollama's log line for the request
  docker inspect ollama > /dev/null 2>&1 || { $RUNLINE_PAGE > /dev/null; sleep 5; }   # off camera: step 1 with the page
  begin E
  tt "export ANTHROPIC_BASE_URL=http://localhost:11434" '.*' 5 1
  tt "export ANTHROPIC_AUTH_TOKEN=ollama" '.*' 5 1
  tt "export ANTHROPIC_API_KEY=\"\"" '.*' 5 1
  tt "export ENABLE_TOOL_SEARCH=false" '.*' 5 1
  tt "export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1" '.*' 5 2
  say "$CC" 'for shortcuts|context window|recognize' 60 8
  tmux capture-pane -p -J -t t > "$D/pane-warning.txt"; sl_shot "$D/warning.png"
  say "/exit" '^\$ ?$' 30 1.5
  tt "export CLAUDE_CODE_MAX_CONTEXT_TOKENS=65536" '.*' 5 2
  say "$CC" 'for shortcuts|context window|recognize' 60 6
  tmux capture-pane -p -J -t t > "$D/pane-fixed.txt"; sl_shot "$D/fixed.png"
  say "say hi" "$REPLY_MARK" 500 6
  tmux capture-pane -p -J -t t > "$D/pane-hi.txt"
  say "/exit" '^\$ ?$' 30 1.5
  tt "docker logs ollama 2>&1 | grep 'v1/messages' | tail -n 2" 'v1/messages' 20 6
  finish
}
for T in "$@"; do "take_$T"; done
sl_display_stop
