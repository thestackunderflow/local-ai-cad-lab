"""Masks for the la terminal takes (source px, 2880 x 1620, take seconds = screen.mp4 seconds), measured by
lab/la_ocr.py at 2 fps (out/scratch/la-e/ocr-E1.tsv 19-146 s, ocr-E2.tsv 620-649 s; 24 Nov):
  "gemma4:12b-it-qat · API Usage Billing" x 224-960 y 106-140, 23.5-632.0 (only the "· API Usage Billing" part masked)
  "Auto mode is now Claude Code's default..." notice rows y 300-470, 23.5-34.0
  status row ">> auto mode on (shift+tab to cycle) · esc to interrupt" x 48-1140 y 1588-1620, 23.5-632.0
  spinner "Drizzling.. (25s · 1.2k tokens · thinking)" x 4-856 y 1394-1426, 141.0-141.5 (masked 116-142.5: the whole
    thinking wait; the reply's "Thought for 24s" stays)
  "Resume this session with: / claude --resume <id>" x 4-1040 y 380-466, 632.5-648.0
WANTED (never masked): the G9 line "Model ... isn't recognized · context assumed to be 200k tokens", the typed
"export CLAUDE_CODE_MAX_CONTEXT_TOKENS=65536", "41% until auto-compact".
mask_filter(take, t_off) -> ffmpeg drawbox chain for a segment cut from take seconds t_off on (enable times shifted).
Test: tests/test_masks.py (every OCR hit not WANTED lies inside a live mask)."""
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from la_ocr import PAT

BG = "0xfdfdfd"
# (x, y, w, h, t_from, t_to, why[, fill colour]: BG when absent)
MASKS = {
    'E': [
        (560, 100, 440, 48, 23.0, 636.0, 'banner: API Usage Billing'),
        (0, 290, 2850, 186, 23.0, 34.6, 'auto mode notice'),
        (0, 1582, 1300, 38, 23.0, 633.0, 'status row: auto mode / shift+tab / esc to interrupt'),
        (0, 1386, 1300, 48, 116.0, 142.5, 'spinner row: tokens counter'),
        (0, 376, 1100, 91, 632.4, 649.0, 'resume line + session id'),
    ],
    # 24 Nov (out/scratch/la-m/*.tsv at 1 fps + gridded crops sc-upd.png / fc-start.png / fc110c.png / fc127c.png):
    # S12-sc (2880 x 1620): SolidCraft's "Update to 0.48.0" button x 1878-2118 y 12-50, the whole take; filled with
    # the title bar's colour (50, 55, 63) sampled at x 1860 / 2125
    'S12sc': [
        (1872, 8, 254, 48, 0.0, 118.0, 'SolidCraft Update to 0.48.0 button', '0x32373f'),
    ],
    # S12-fc (2880 x 1800): FreeCAD's "Tasks" title + "Start Part / New Body" panel x 2304-2874 y 465-596 from the new
    # document (93.7) to the end; under it: the empty view f7f7f7 (10 fps pixel scan: 247) (93.6-104.2), the block's face 92979d seen close
    # (104.2-120.4, Claude's Block fills the view), the empty view again after ViewFit (120.4 on)
    'S12fc': [
        (2296, 450, 584, 152, 93.6, 104.2, 'FreeCAD Start Part panel', '0xf7f7f7'),
        (2296, 450, 584, 152, 104.2, 120.4, 'FreeCAD Start Part panel', '0x92979d'),
        (2296, 450, 584, 152, 120.4, 130.0, 'FreeCAD Start Part panel', '0xf7f7f7'),
    ],
}
WANTED = re.compile(r"isn.t recognized|context assumed|context window of|context[ _]*tokens|until auto-compact", re.I)


def covered(take, t, x, y, w, h, pad=4):
    for mx, my, mw, mh, a, b, *_ in MASKS.get(take, []):
        if a - 0.01 <= t <= b + 0.01 and mx - pad <= x and my - pad <= y and x + w <= mx + mw + pad \
                and y + h <= my + mh + pad:
            return True
    return False


def uncovered(take, tsv_lines):
    """OCR hits (t, x, y, w, h, text) that are neither WANTED nor inside a live mask."""
    out = []
    for t, x, y, w, h, txt in tsv_lines:
        if WANTED.search(txt):
            continue
        m = [mm.span() for mm in PAT.finditer(txt)] or [(0, len(txt))]
        n = max(len(txt), 1)          # monospace: the match's x range in proportion to its characters
        x0 = x + w * min(a for a, _ in m) // n
        x1 = x + w * max(b for _, b in m) // n
        if not covered(take, t, x0, y, x1 - x0, h):
            out.append((t, x, y, w, h, txt))
    return out


def mask_filter(take, t_off=0.0, color=BG):
    parts = []
    for x, y, w, h, a, b, _, *c in MASKS.get(take, []):
        parts.append("drawbox=x=%d:y=%d:w=%d:h=%d:color=%s:t=fill:enable='between(t,%.2f,%.2f)'"
                     % (x, y, w, h, c[0] if c else color, a - t_off, b - t_off))
    return ",".join(parts)


def read_tsv(path):
    rows = []
    for l in open(path, encoding="utf-8"):
        if l.startswith("#") or not l.strip():
            continue
        t, x, y, w, h, txt = l.rstrip("\n").split("\t", 5)
        rows.append((float(t), int(x), int(y), int(w), int(h), txt))
    return rows
