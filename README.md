# local-ai-cad-lab (video la: Claude Code on a local Ollama driving SolidCraft + FreeCAD MCP)

Lab for The Stack Underflow video "Claude Code + Local AI for CAD: Gemma 4 12B Local Setup, Step by Step". Every number in
the video comes from the runs in `out/`. Tests: `python -m pytest tests` (`test_draw_la.py` needs the video plan's NUMBERS file, not
included). Paths like `Refream-Canvas/...` below point at the channel's private video workspace.

## Intent
Keep Claude Code as the host and swap only the model: Claude Code talks to Ollama's Anthropic-compatible endpoint
(`ANTHROPIC_BASE_URL`), the model is Gemma 4 12B (QAT) or 26B, and the same two plugs as the courses drive SolidCraft
0.28.0 and FreeCAD 1.1.4 (freecad-mcp 0.1.28). Then score, by code and with lesson 14's scorers unchanged:
- **S**: a 60 x 20 x 5 mm block from an empty design (pass: one solid, box 60 x 20 x 5 +- 0.01, volume 6,000 +- 1 mm3);
- **T**: lesson 14's shell-order trap, the B1 prompt word for word (pass: lesson 14 (a)-(e) at wall 2 and wall 3).

## Pins (G0, `out/g0/pins.json`)
- Ollama `ollama/ollama:0.40.17@sha256:ccc42bcd3d5fcf7ab0d532b300382154e1a4da56fc666bdb313b78ebdd912754` (latest stable on
  22 Nov 2026), container `la-ollama`, Docker network `la-net`, model volume `gemma-lab-models` (the gemma labs' volume;
  manifests match the registry on 22 Nov: 12b-it-qat 38044be4..., 26b 001e5daf...), `OLLAMA_NOPRUNE=1`.
- Apps: `sc5-l5:0.28.0` (Claude Code 2.1.311) and `fcc-app:1.1.4-0.1.28` (Claude Code 2.1.308), as lesson 14.
- Lesson 14 code is mounted read-only from `solidcraft-course-lab` (/work) and `freecad-course-lab` (/lab); this repo is /la.

## Layout
- `lab/` in-container scripts (`la_sc.sh`, `la_fc.sh`), scorers (`la_score.py`, `la_fcS.py`), Ollama start (`ollama_up.sh`).
- `run/` host launchers (`one.sh` = one pre-registered run, `queue.sh` = a list of runs, one at a time, with the RAM guard).
- `out/PREREG.md` pre-registration (committed before the first scored run); `out/g0/` G0 checks; `out/runs/<id>/` runs.
- `tests/` the scorer and prompt tests (`python -m pytest tests`).

## Rules
Docker only; `--strict-mcp-config` on every Claude Code start; no claude.ai connector names in any log; one model loaded at
a time; Windows free RAM >= 2 GB before a load, runs stop under 1 GB; the GPU lock `Refream-Canvas/.render-lock` is taken
for model loads and runs.
