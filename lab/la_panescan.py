"""First-pass leak scan of the la takes' terminal text (pane*.txt), before the 2 fps OCR gate on the render.
python lab/la_panescan.py out/takes  -> one line per hit, exit 1 if any.
Patterns = the HANDOVER/brief list: plan names, connectors, emails, billing line, keys, Claude Code status-row words."""
import os, pathlib, re, sys

PATTERNS = [r"\bPro\b plan", r"\bMax\b", r"Team plan", r"Enterprise", r"claude\.ai", r"[\w.+-]+@[\w-]+\.[\w.]+",
            r"API Usage Billing", r"sk-ant", r"auto mode", r"shift\+tab", r"esc to interrupt", r"\btokens\b",
            r"Allowed by", os.environ.get("SCAN_USER", "USERNAME"), r"/c/Users", r"C:\\Users"]


def scan(root):
    hits = []
    for p in sorted(pathlib.Path(root).rglob("pane*.txt")):
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for pat in PATTERNS:
                if re.search(pat, line):
                    hits.append(f"{p}:{n}: [{pat}] {line.strip()[:160]}")
    return hits


if __name__ == "__main__":
    h = scan(sys.argv[1] if len(sys.argv) > 1 else "out/takes")
    print("\n".join(h) if h else "0 hits")
    sys.exit(1 if h else 0)
