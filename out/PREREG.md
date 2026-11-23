# la pre-registration (PLAN 2026-11-21-local-ai-cad-setup rev 2, section 3.3), written 22 Nov 2026 BEFORE any scored run

Committed in this repo before the first scored run; nothing below changes after that commit except the G0-decided
values marked [G0], which are filled from G0 results and committed before the first scored run as well.

## Runs (28; no retries except G6 voids, re-run once)
| Cell | Model | App | Task | n |
|---|---|---|---|---|
| L12 | `gemma4:12b-it-qat` (local, Ollama) | SolidCraft 0.28.0, FreeCAD 1.1.4 | S, T | 3 each = 12 |
| L26 | `gemma4:26b` (local, Ollama) | same | S, T | 3 each = 12 |
| CL | `claude-sonnet-5-5` (Anthropic API, no base URL) | same | S, T | 1 each = 4 |
Run ids: `{12|26|cl}-{sc|fc}-{S|T}-{1..3}` (e.g. `12-sc-S-1`). Order: per model, sc S 1-3, fc S 1-3, sc T 1-3, fc T 1-3,
one at a time, a fresh app container per run. Seed / temperature are not settable through Claude Code: report "n of 3".

## Prompts (exact)
- S: "Use the [solidcraft | freecad] tools. Make a block 60 mm long, 20 mm wide and 5 mm thick, then tell me its volume."
- T (lesson 14 B1, word for word): "My wall cup's key peg should be a solid 10 by 10 peg, but after the shell it came out
  hollow and bigger, open into the cup. Fix it so the peg stays solid and 10 wide when I change the wall thickness. Then
  check the peg and the front wall and tell me what you find."

## Start state
- S: empty design (SolidCraft: start page > New design; FreeCAD: no document open, socket on).
- T: lesson 14's start files unchanged: SolidCraft `solidcraft-course-lab/out/sc14/P/peg-trap.sc`, FreeCAD
  `freecad-course-lab/out/fc14/P/peg-trap.FCStd` (sha256 in each run's `start-sha256.txt` and in `out/g0/pins.json`).

## Claude Code start (every run; lab/la_common.sh)
`claude -p PROMPT --model MODEL --strict-mcp-config --mcp-config entry.json (one plug, behind the logging proxy)
--max-turns 30 --allowedTools mcp__<plug> --output-format stream-json --verbose`, headless, fresh HOME without an
Anthropic login (local) / API key only (Claude runs), 25 min wall clock (`timeout`), then killed and kept.
- All 28: `ENABLE_TOOL_SEARCH=false`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`, FreeCAD plug flags = [G0: G5].
- Permissions: the plug's tools allowed; Claude Code's own tools (Bash, Write, ...) are listed but not allowed (headless
  -p denies them without a prompt). Same for local and Claude runs.
- Local adds: `ANTHROPIC_BASE_URL=http://la-ollama:11434`, `ANTHROPIC_AUTH_TOKEN=ollama`, `ANTHROPIC_API_KEY=""`,
  `CLAUDE_CODE_MAX_CONTEXT_TOKENS` = the page [G0: G3], plus any G8 model-name lines [G0: G8].
- Claude runs: `--max-budget-usd` 0.15 (S) / 0.20 (T), stage cap $0.50.
- Ollama: 0.40.17 by digest, page `OLLAMA_CONTEXT_LENGTH` = [G0: G3], KV [G0: G3], one parallel slot, one model loaded,
  `--memory 6g` (12B) / `16g` (26B).

## Scoring (by code; lab/la_score.py)
- S pass: one solid (SolidCraft: `measure` body_count 1; FreeCAD: exactly one shown top-level solid over all open
  documents, lab/la_fcS.py), bounding box 60 x 20 x 5 +- 0.01 mm in any orientation, volume 6,000 +- 1 mm3.
  Logged: the volume the model said.
- T pass: lesson 14's scorers unchanged. SolidCraft: `solidcraft-course-lab/lab/sc14parts.py sweep` (+ `sc14geom.py`),
  criteria (a)-(e) of `solidcraft-course-lab/out/sc14/runs/PREREG.txt` at wall 2 AND wall 3. FreeCAD:
  `freecad-course-lab/lab/fc14parts.py` check + `lab/fc14score.py` passes() on the `peg` document (criteria of
  `freecad-course-lab/out/fc14/PREREG.md`), at wall 2 AND wall 3.
- Classes: (1)-(11) as lesson 14; (12) no tool call; (14) timeout / turn cap; (15) page overflow = an Ollama
  "truncating input prompt" line during the run (counted and shown as a setup limit, not a model miss). Separate yes/no
  column: "said fixed, not fixed by code" (the final text claims the fix/success and the scorer says fail).
- Per run logged: tool calls (names, count), tool errors and whether the model read them, final text, wall time,
  first-request prompt tokens, truncation lines, Windows free RAM min, GPU MiB peak.
- G6 void: FreeCAD socket did not answer `list_documents` before the run -> void, restart, re-run once.
- Stop rules: Windows free RAM < 1 GB (the run is killed and kept as "guard stop"), GPU held by another container,
  C: < 15 GB, < 2 GB free before a load.

## G0-decided values (22 Nov 2026, out/g0/, before any scored run)
- [G3] page `OLLAMA_CONTEXT_LENGTH=65536`, KV `q8_0`, flash attention on; `CLAUDE_CODE_MAX_CONTEXT_TOKENS=65536` (12B:
  35/49 layers on the GPU, 8.2 tok/s written / 436 tok/s prefill at a 31.5K prompt; 32K does not hold both plugs + 8K).
- [G5] FreeCAD plug flag `--only-text-feedback` ON for all runs (without it each screenshot result cost ~2.4-2.9K tokens).
- [G8] no model-name lines needed (Claude Code requested only the chosen tag).
- Host: a helper drops the WSL VM page cache every 5 s during each run (run/one.sh, after g4-fc-S hit the 1 GB guard).
- Run list for the 12B: run/list-12b.txt (Task Scheduler task la-queue -> run/queue.cmd).
