#!/usr/bin/env bash
# Fresh la-ollama before a run (HANDOVER-la-lab2 1b): bash lab/la_restart.sh MODEL OUTDIR   (no-op unless OLLAMA_RESTART=1)
# Why: a run's speed depended on the prompt cache left by the runs before it (fc-T-3 inherited fc-T-2's). Re-create the
# container (cache off, lab/ollama_up.sh), load the model with a 1-token request so the load is not inside the 25 min,
# then record whether llama-server took the cache env (OUTDIR/ollama-fix.json; restart alone still counts if not).
# Env: CTX (65536) OLLAMA_KV (q8_0) OLLAMA_MEM (6g; 26B: 16g) LA_PY (python command; default = gemma4-lab-runner:1).
set -uo pipefail
[ "${OLLAMA_RESTART:-0}" = 1 ] || exit 0
cd "$(dirname "$0")/.."
MODEL=${1:?MODEL}; O=${2:?OUTDIR}
LA="$(pwd -W 2>/dev/null || pwd)"
bash lab/ollama_up.sh "${CTX:-65536}" "${OLLAMA_KV:-q8_0}" "${OLLAMA_MEM:-6g}" || exit 5
S=$(date +%s)
curl -s --max-time 900 http://127.0.0.1:11434/api/generate \
  -d "{\"model\":\"$MODEL\",\"prompt\":\"hi\",\"stream\":false,\"options\":{\"num_predict\":1}}" > "$O/warmup.json"
echo "warm-up $MODEL $(( $(date +%s) - S )) s"
docker logs la-ollama > "$O/ollama-start.log" 2>&1
if [ -n "${LA_PY:-}" ]; then PY=($LA_PY); else
  PY=(docker run --rm -v "$LA:/la" -w /la -e PYTHONDONTWRITEBYTECODE=1 --entrypoint python3 gemma4-lab-runner:1); fi
MSYS_NO_PATHCONV=1 "${PY[@]}" lab/la_throughput.py --fix-check "$O/ollama-start.log" > "$O/ollama-fix.json"
echo "cache fix: $(cat "$O/ollama-fix.json")"
