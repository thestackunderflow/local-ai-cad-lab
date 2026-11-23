# la common part (sourced by lab/la_sc.sh and lab/la_fc.sh): the pre-registered Claude Code start (PREREG.md).
# la_claude SERVER CWD: one headless Claude Code run of the task prompt, logs into $O.
WALL_S=${WALL_S:-1500}      # 25 min wall clock, then killed and kept as class (14)
MAX_TURNS=${MAX_TURNS:-30}

prompt_for() {   # prompt_for SERVER TASK
  local B1="My wall cup's key peg should be a solid 10 by 10 peg, but after the shell it came out hollow and bigger, open into the cup. Fix it so the peg stays solid and 10 wide when I change the wall thickness. Then check the peg and the front wall and tell me what you find."
  case $2 in
    S) echo "Use the $1 tools. Make a block 60 mm long, 20 mm wide and 5 mm thick, then tell me its volume." ;;
    T) echo "$B1" ;;
    *) echo "${PROMPT:?TASK $2 needs PROMPT}" ;;
  esac
}

la_claude() {
  local server=$1 cwd=$2 t0 rc
  local msg; msg=$(prompt_for "$server" "$TASK"); echo "$msg" > "$O/prompt.txt"
  export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 DISABLE_AUTOUPDATER=1
  # pre-registered for all runs (local and Claude): full tool list, no non-essential traffic
  export ENABLE_TOOL_SEARCH=${ENABLE_TOOL_SEARCH:-false} CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
  if [ "${LOCAL:-1}" = 1 ]; then
    export ANTHROPIC_BASE_URL=${BASE_URL:-http://la-ollama:11434} ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY=""
    [ -n "${CTX:-}" ] && export CLAUDE_CODE_MAX_CONTEXT_TOKENS=$CTX
  fi
  for kv in ${EXTRA_ENV:-}; do export "$kv"; done
  claude --version > "$O/claude-version.txt" 2>&1
  (cd "$cwd" && timeout 60 claude mcp list --strict-mcp-config --mcp-config "$O/entry.json") 2>&1 | grep -v -i '^claude\.ai' > "$O/mcp-list.txt"
  env | grep -E '^(ANTHROPIC_BASE_URL|ANTHROPIC_AUTH_TOKEN|CLAUDE_CODE_|ENABLE_TOOL_SEARCH|ANTHROPIC_DEFAULT_)' | sort > "$O/env-lines.txt"
  [ -n "${ANTHROPIC_API_KEY+x}" ] && echo "ANTHROPIC_API_KEY set, length ${#ANTHROPIC_API_KEY}" >> "$O/env-lines.txt"
  t0=$(date +%s.%N)
  echo "{\"t\": \"$(date -u +%FT%TZ)\", \"ev\": \"claude start\"}" >> "$O/events.jsonl"
  (cd "$cwd" && timeout -k 10 "$WALL_S" claude -p "$msg" --model "$MODEL" --strict-mcp-config --mcp-config "$O/entry.json" \
      --max-turns "$MAX_TURNS" --allowedTools "mcp__$server" --output-format stream-json --verbose \
      ${MAX_BUDGET:+--max-budget-usd $MAX_BUDGET} < /dev/null > "$O/stream.jsonl" 2> "$O/claude.err")
  rc=$?
  echo "{\"t\": \"$(date -u +%FT%TZ)\", \"ev\": \"claude end\", \"rc\": $rc}" >> "$O/events.jsonl"
  python3 - "$O" "$rc" "$t0" "$MODEL" "$server" <<'PY'
import json, sys, time
o, rc, t0, model, server = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5]
json.dump({'rc': rc, 'timeout': rc in (124, 137), 'wall_s': round(time.time() - t0, 1), 'model': model, 'server': server,
           'claude_version': open(o + '/claude-version.txt').read().strip()}, open(o + '/claude-meta.json', 'w'), indent=1)
PY
  cp "$HOME"/.claude/projects/*/*.jsonl /tmp/session.jsonl 2>/dev/null   # account details may be inside: never in out/
  grep -o '"model":"[^"]*"' /tmp/session.jsonl 2>/dev/null | sort | uniq -c > "$O/session-models.txt"
}
