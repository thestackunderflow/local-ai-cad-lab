#!/bin/bash
# G0 light run (no CAD app window): Claude Code headless in sc5-l5:0.28.0 with a fresh HOME (no Anthropic login), the
# plug set PLUGS (none | sc | fc | both; fc = uvx freecad-mcp@0.1.28 with uv copied from fcc-app into /la/out/scratch/uv),
# one prompt. Env: TAG PLUGS PROMPT MODEL; LOCAL/CTX/EXTRA_ENV as lab/la_common.sh; OUTPUT text|stream-json.
set -u
O=/la/out/g0/${TAG:?}; mkdir -p "$O"; : "${MODEL:?}"
export HOME=/tmp/h-$TAG; mkdir -p "$HOME/.claude" "$HOME/w"
printf '{"claudeMdExcludes": ["/la/**", "/work/**"]}\n' > "$HOME/.claude/settings.json"
python3 - <<'PY'
import json, os
json.dump({'hasCompletedOnboarding': True, 'theme': 'light',
           'projects': {os.path.expanduser('~/w'): {'hasTrustDialogAccepted': True}}}, open(os.path.expanduser('~/.claude.json'), 'w'))
PY
export PATH=/la/out/scratch/uv:$PATH
python3 - "$O" "${PLUGS:-none}" "${FC_FLAGS:-}" <<'PY'
import json, os, sys
o, plugs, flags = sys.argv[1], sys.argv[2], sys.argv[3].split()
s = {}
if plugs in ('sc', 'both'):
    s['solidcraft'] = {'command': '/opt/solidcraft/bin/solidcraft-cli', 'args': ['mcp']}
if plugs in ('fc', 'both'):
    s['freecad'] = {'command': 'uvx', 'args': ['freecad-mcp@0.1.28'] + flags}
json.dump({'mcpServers': s}, open(os.path.join(o, 'entry.json'), 'w'), indent=1)
PY
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 DISABLE_AUTOUPDATER=1
export ENABLE_TOOL_SEARCH=${ENABLE_TOOL_SEARCH:-false} CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=${TRAFFIC_OFF:-1}
[ "${TRAFFIC_OFF:-1}" = 0 ] && unset CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC
if [ "${LOCAL:-1}" = 1 ]; then
  export ANTHROPIC_BASE_URL=${BASE_URL:-http://la-ollama:11434} ANTHROPIC_AUTH_TOKEN=ollama ANTHROPIC_API_KEY=""
  [ -n "${CTX:-}" ] && export CLAUDE_CODE_MAX_CONTEXT_TOKENS=$CTX
fi
for kv in ${EXTRA_ENV:-}; do export "$kv"; done
env | grep -E '^(ANTHROPIC_BASE_URL|ANTHROPIC_AUTH_TOKEN|CLAUDE_CODE_|ENABLE_TOOL_SEARCH|ANTHROPIC_DEFAULT_)' | sort > "$O/env-lines.txt"
claude --version > "$O/claude-version.txt" 2>&1
(cd ~/w && timeout 90 claude mcp list --strict-mcp-config --mcp-config "$O/entry.json") 2>&1 | grep -v -i '^claude\.ai' > "$O/mcp-list.txt"
t0=$(date +%s)
(cd ~/w && timeout -k 5 "${WALL_S:-600}" claude -p "${PROMPT:?}" --model "$MODEL" --strict-mcp-config --mcp-config "$O/entry.json" \
   --max-turns "${MAX_TURNS:-3}" --output-format "${OUTPUT:-stream-json}" --verbose < /dev/null > "$O/out.txt" 2> "$O/err.txt")
echo "rc $? wall $(( $(date +%s) - t0 ))" > "$O/rc.txt"
# the context line Claude Code prints for an unknown model (G9), from its own /context-style status if printed
grep -a -i -o "context[^\"]\{0,120\}assumed[^\"]\{0,80\}" "$O/out.txt" "$O/err.txt" 2>/dev/null | head -3 > "$O/context-line.txt"
cat "$O/rc.txt"
