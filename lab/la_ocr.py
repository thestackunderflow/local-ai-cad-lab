"""2 fps OCR leak / mask scan with line boxes (tesseract tsv): for each frame, every OCR line matching PAT is printed
with its box in SOURCE pixels, so the footage script's masks come from measurement, not guesses.
  MSYS_NO_PATHCONV=1 docker run --rm --network none -v "<edu-visualization>:/ev" -w /ev/local-ai-cad-lab fc8-ocr:1 \
    python3 lab/la_ocr.py VIDEO OUT.tsv [FROM TO] [FPS]
OUT.tsv columns: t, x, y, w, h, text (one row per matching line). Last line: "# frames N hits H".
Test: tests/test_ocr.py (the line grouping and the pattern)."""
import os
import re
import subprocess
import sys
import tempfile

PAT = re.compile(r"api usage billing|auto mode|shift\+tab|tokens|resume this session|claude --resume|esc to interrupt|"
                 r"allowed by|sk-ant|claude_ai_|google drive|claude docs|max plan|pro plan|ultra|"
                 r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)


def lines_from_tsv(tsv, scale=1.0):
    """tesseract tsv -> [(x, y, w, h, text)] per line, boxes divided by scale (back to source px)."""
    groups = {}
    for row in tsv.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12 or c[0] != "5" or not c[11].strip():
            continue
        key = (c[2], c[3], c[4])
        x, y, w, h = (int(v) for v in c[6:10])
        g = groups.setdefault(key, [x, y, x + w, y + h, []])
        g[0], g[1], g[2], g[3] = min(g[0], x), min(g[1], y), max(g[2], x + w), max(g[3], y + h)
        g[4].append(c[11])
    out = []
    for x0, y0, x1, y1, words in groups.values():
        out.append((round(x0 / scale), round(y0 / scale), round((x1 - x0) / scale), round((y1 - y0) / scale),
                    " ".join(words)))
    return sorted(out, key=lambda r: (r[1], r[0]))


def hits(lines):
    return [l for l in lines if PAT.search(l[4])]


def main(video, out, t0=None, t1=None, fps=2.0, scale=0.5):
    d = tempfile.mkdtemp()
    cmd = ["ffmpeg", "-v", "error"]
    if t0 is not None:
        cmd += ["-ss", str(t0), "-to", str(t1)]
    cmd += ["-i", video, "-vf", "fps=%s,scale=iw*%s:-1" % (fps, scale), os.path.join(d, "f%05d.png")]
    subprocess.run(cmd, check=True)
    n = h = 0
    with open(out, "w", encoding="utf-8") as f:
        for i, name in enumerate(sorted(os.listdir(d))):
            n += 1
            t = (t0 or 0) + i / fps
            tsv = subprocess.run(["tesseract", os.path.join(d, name), "-", "tsv"], capture_output=True,
                                 text=True).stdout
            for x, y, w, hh, txt in hits(lines_from_tsv(tsv, scale)):
                h += 1
                f.write("%.1f\t%d\t%d\t%d\t%d\t%s\n" % (t, x, y, w, hh, txt))
            os.remove(os.path.join(d, name))
        f.write("# frames %d hits %d\n" % (n, h))
    os.rmdir(d)
    print("%s: frames %d hits %d -> %s" % (video, n, h, out))


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], float(a[2]) if len(a) > 2 else None, float(a[3]) if len(a) > 3 else None,
         float(a[4]) if len(a) > 4 else 2.0)
