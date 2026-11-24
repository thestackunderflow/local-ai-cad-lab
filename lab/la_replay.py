"""Terminal replay of a logged run (no AI): stream.jsonl (order + text) + transcript.jsonl (MCP wire times) -> timed
rows -> a sped-up strip video. Every row is text the run logged; nothing is typed or generated. The strip carries the
label "replay of the logged run, sped up" and a run clock (real minutes) on every frame.

Rows: think (a thinking block: "✻ thinking"), tool ("● app · tool(args)"), result ("  └ first line"), error (a
tool_result with is_error), compact (auto compaction, "✻ compacting the page (auto) · N.N min"), say (assistant text).
Times: tool / result rows = the transcript's tools/call request / response times (seconds from its first line);
compact = next known time - duration_ms; the rest are spread evenly between their known neighbours.
Status-row words (the take E masks) never appear: BANNED is checked by the tests and by build().

Run in the draw image (PIL + ffmpeg):
  MSYS_NO_PATHCONV=1 docker run --rm -v "<edu-visualization>:/ev" -w /ev/local-ai-cad-lab cad3way-draw:1 \
    python3 lab/la_replay.py RUN SECONDS TITLE OUT.mp4   (e.g. 12-fc-T-2r 17 "Gemma 4 12B · FreeCAD")
Test: tests/test_replay.py."""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

BANNED = ("tokens", "api usage billing", "auto mode", "shift+tab", "esc to interrupt", "sk-ant", "allowed by",
          "resume this session", "@")
LABEL = "replay of the logged run, sped up"


def _t(s):
    return datetime.fromisoformat(s).timestamp()


def _clean(s):
    s = s.replace("\t", " ")
    for b in BANNED:          # never expected in a logged row; cut to "…" so the strip can't carry a status word
        i = s.lower().find(b)
        while i >= 0:
            s = s[:i] + "…" + s[i + len(b):]
            i = s.lower().find(b)
    return s


def _first(text):
    s = str(text).strip()
    if s.startswith("<tool_use_error>"):
        s = s.replace("<tool_use_error>", "").replace("</tool_use_error>", "").strip()
    if s.startswith("{"):
        try:
            d = json.loads(s)
            f = d.get("failed") if isinstance(d, dict) else None
            if isinstance(f, dict) and f.get("error"):
                return "%s: %s" % (f.get("command", ""), f["error"])
        except ValueError:
            pass
    text = s
    for line in str(text).splitlines():
        if line.strip() and line.strip() not in "[]{}":
            return line.strip()
    return str(text).strip()[:80]


def _args(inp):
    parts = []
    for k, v in (inp or {}).items():
        v = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else '"%s"' % v.replace("\n", " ⏎ ")
        parts.append("%s: %s" % (k, v))
    return ", ".join(parts)


def rows(stream_path, transcript_path):
    """The run's rows in order, each {kind, text, t} (t = seconds from the transcript's first line)."""
    tr = [json.loads(l) for l in open(transcript_path, encoding="utf-8") if l.strip()]
    t0 = _t(tr[0]["t"])
    req, resp = [], {}
    for d in tr:
        m = d.get("msg")
        if not isinstance(m, dict):
            continue
        if d.get("dir") == "client->server" and m.get("method") == "tools/call":
            req.append((m.get("id"), _t(d["t"]) - t0))
        elif d.get("dir") == "server->client" and "id" in m and ("result" in m or "error" in m):
            resp.setdefault(m["id"], _t(d["t"]) - t0)
    calls = iter(req)
    out, call_at = [], {}
    for d in (json.loads(l) for l in open(stream_path, encoding="utf-8") if l.strip()):
        typ = d.get("type")
        if typ == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") == "thinking":
                    out.append({"kind": "think", "text": "✻ thinking", "t": None})
                elif c.get("type") == "text" and c.get("text", "").strip():
                    out.append({"kind": "say", "text": "● " + _first(c["text"]), "t": None})
                elif c.get("type") == "tool_use":
                    _, app, tool = (c["name"].split("__") + ["", ""])[:3] if c["name"].startswith("mcp__") \
                        else ("", "", c["name"])
                    rid, at = next(calls, (None, None))
                    call_at[c["id"]] = resp.get(rid)
                    head = "● %s · %s(" % (app, tool) if app else "● %s(" % tool
                    out.append({"kind": "tool", "text": head + _args(c.get("input")) + ")", "t": at})
        elif typ == "user":
            content = d["message"].get("content", [])
            for c in content if isinstance(content, list) else []:
                if c.get("type") != "tool_result":
                    continue
                body = c.get("content")
                if isinstance(body, list):
                    kinds = [b.get("type") for b in body]
                    body = next((b.get("text", "") for b in body if b.get("type") == "text"), "")
                    if not body and "image" in kinds:
                        body = "[a picture of the window]"
                err = bool(c.get("is_error"))
                out.append({"kind": "error" if err else "result", "text": "  └ " + ("Error: " if err else "") +
                            _first(body).removeprefix("Error: "), "t": call_at.get(c.get("tool_use_id"))})
        elif typ == "system" and d.get("subtype") == "compact_boundary":
            ms = (d.get("compact_metadata") or {}).get("duration_ms", 0)
            out.append({"kind": "compact", "text": "✻ compacting the page (auto) · %.1f min" % (ms / 60000.0),
                        "t": None, "dur": ms / 1000.0})
    _fill(out)
    for r in out:
        r["text"] = _clean(r["text"])
    return out


def _fill(out):
    """Compact rows end at the next known time; other unknown times spread evenly between known neighbours."""
    for i, r in enumerate(out):
        if r["kind"] == "compact":
            nxt = next((x["t"] for x in out[i + 1:] if x["t"] is not None), None)
            if nxt is not None:
                r["t"] = round(nxt - r.pop("dur"), 3)
    i = 0
    while i < len(out):
        if out[i]["t"] is not None:
            i += 1
            continue
        j = i
        while j < len(out) and out[j]["t"] is None:
            j += 1
        lo = out[i - 1]["t"] if i else 0.0
        hi = out[j]["t"] if j < len(out) else lo + 2.0 * (j - i)
        for k in range(i, j):
            out[k]["t"] = round(lo + (hi - lo) * (k - i + 1) / (j - i + 1), 3)
        i = j
    for r in out:
        r.pop("dur", None)


def schedule(rs, seconds, lead=1.0, gmin=0.15):
    """Display times inside [lead, seconds - lead]: gaps follow the square root of the real gaps (long waits stay
    visibly long, short bursts readable), at least gmin apart."""
    if not rs:
        return []
    gaps = [0.0] + [max(0.0, b["t"] - a["t"]) ** 0.5 for a, b in zip(rs, rs[1:])]
    span = seconds - 2 * lead - gmin * (len(rs) - 1)
    tot = sum(gaps) or 1.0
    at, res = lead, []
    for g, r in zip(gaps, rs):
        at += (g / tot) * max(span, 0.0) + (gmin if res else 0.0)
        res.append(dict(r, at=round(at, 4)))
    return res


def wrap(s, cols, maxl=2):
    lines = [s[i:i + cols] for i in range(0, len(s), cols)] or [""]
    if len(lines) > maxl:
        lines = lines[:maxl]
        lines[-1] = lines[-1][:cols - 1] + "…"
    return lines


COLORS = {"tool": (230, 230, 230), "result": (150, 150, 150), "error": (255, 120, 110), "compact": (255, 214, 102),
          "think": (140, 140, 160), "say": (130, 200, 255)}
BG = {"error": (70, 25, 25), "compact": (70, 58, 20)}


def render(sch, title, total_s, out_mp4, w=1200, h=1620, font_px=30, run_len_s=None):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", font_px)
    bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", font_px)
    cw = font.getbbox("M")[2]
    cols = (w - 40) // cw
    pitch = int(font_px * 1.45)
    top = 40 + 3 * pitch
    vis = (h - top - 20) // pitch
    tmp = out_mp4 + ".frames"
    os.makedirs(tmp, exist_ok=True)
    run_len = run_len_s or (sch[-1]["t"] if sch else 0)
    lines, frames = [], []

    def frame(k, clock):
        im = Image.new("RGB", (w, h), (18, 18, 22))
        dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, w, top - 12], fill=(40, 40, 48))
        dr.text((20, 20), title, font=bold, fill=(255, 255, 255))
        dr.text((20, 20 + pitch), LABEL, font=font, fill=(255, 214, 102))
        dr.text((20, 20 + 2 * pitch), "run clock %d:%02d of %d:%02d" % (clock // 60, clock % 60, run_len // 60,
                                                                          run_len % 60), font=font, fill=(200, 200, 200))
        y = top
        for kind, txt in lines[-vis:]:
            if kind in BG:
                dr.rectangle([10, y - 4, w - 10, y + pitch - 6], fill=BG[kind])
            dr.text((20, y), txt, font=font, fill=COLORS[kind])
            y += pitch
        p = os.path.join(tmp, "f%04d.png" % k)
        im.save(p)
        return p

    frames.append((frame(0, 0), sch[0]["at"] if sch else total_s))
    for i, r in enumerate(sch):
        for l in wrap(r["text"], cols):
            lines.append((r["kind"], l))
        end = sch[i + 1]["at"] if i + 1 < len(sch) else total_s
        frames.append((frame(i + 1, int(r["t"])), max(end - r["at"], 0.04)))
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for p, d in frames:
            f.write("file '%s'\nduration %.4f\n" % (os.path.abspath(p), d))
        f.write("file '%s'\n" % os.path.abspath(frames[-1][0]))
    if not shutil.which("ffmpeg"):    # the draw image has PIL but no ffmpeg: encode() in video-qa:2 (same mounts)
        return lst
    encode(lst, out_mp4, total_s)


def encode(lst, out_mp4, total_s):
    tmp = os.path.dirname(lst)
    frames = [l.split("'")[1] for l in open(lst) if l.startswith("file")]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf", "fps=30,format=yuv420p",
                    "-c:v", "libx264", "-crf", "18", "-t", "%.3f" % total_s, out_mp4], check=True)
    for p in set(frames):
        os.remove(p)
    os.remove(lst)
    os.rmdir(tmp)


def build(run, seconds, title, out_mp4, base="out/runs"):
    d = os.path.join(base, run)
    rs = rows(os.path.join(d, "stream.jsonl"), os.path.join(d, "transcript.jsonl"))
    for r in rs:
        assert not any(b in r["text"].lower() for b in BANNED), r
    ev = [json.loads(l) for l in open(os.path.join(d, "events.jsonl")) if l.strip()]
    st = {e["ev"]: _t(e["t"].replace("Z", "+00:00")) for e in ev}
    run_len = int(st.get("claude end", 0) - st.get("claude start", 0)) or None
    sch = schedule(rs, seconds)
    with open(out_mp4[:-4] + ".rows.json", "w", encoding="utf-8") as f:
        json.dump({"run": run, "seconds": seconds, "run_len_s": run_len, "rows": sch}, f, ensure_ascii=False, indent=0)
    render(sch, title, seconds, out_mp4, run_len_s=run_len)
    return sch


if __name__ == "__main__":
    if sys.argv[1] == "encode":       # python3 lab/la_replay.py encode OUT.mp4 SECONDS (in video-qa:2)
        encode(sys.argv[2] + ".frames/list.txt", sys.argv[2], float(sys.argv[3]))
        sys.exit(0)
    run, secs, title, out = sys.argv[1], float(sys.argv[2]), sys.argv[3], sys.argv[4]
    sch = build(run, secs, title, out)
    print("%s: %d rows, %d errors, %d compactions -> %s" % (run, len(sch), sum(r["kind"] == "error" for r in sch),
                                                          sum(r["kind"] == "compact" for r in sch), out))
