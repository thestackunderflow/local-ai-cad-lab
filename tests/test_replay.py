import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lab"))
import la_replay

T0 = "2026-11-23T06:00:00.000+00:00"


def _ts(s):
    m, sec = divmod(s, 60)
    return "2026-11-23T06:%02d:%06.3f+00:00" % (m, sec)


def _write(tmp_path):
    stream = [
        {"type": "system", "subtype": "init", "session_id": "x"},
        {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "hmm"}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "c1", "name": "mcp__freecad__list_documents", "input": {}}]}},
        {"type": "user", "message": {"content": [{"tool_use_id": "c1", "type": "tool_result", "content": [{"type": "text", "text": "[\n  \"peg\"\n]"}]}]}},
        {"type": "system", "subtype": "status", "status": "compacting"},
        {"type": "system", "subtype": "compact_boundary", "compact_metadata": {"trigger": "auto", "pre_tokens": 33808, "duration_ms": 120000}},
        {"type": "user", "message": {"content": [{"type": "text", "text": "This session is being continued ..."}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "c2", "name": "mcp__freecad__execute_code", "input": {"code": "import FreeCAD\nApp.activeDocument.Objects"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "Failed to execute code: AttributeError: 'builtin_function_or_method' object has no attribute 'Objects'", "is_error": True, "tool_use_id": "c2"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "I moved the shell before the peg.\nDone."}]}},
        {"type": "result", "subtype": "success"},
    ]
    tr = [
        {"t": _ts(0), "seq": 1, "dir": "proxy", "msg": "started"},
        {"t": _ts(30), "seq": 2, "dir": "client->server", "msg": {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "list_documents"}}},
        {"t": _ts(31), "seq": 3, "dir": "server->client", "msg": {"jsonrpc": "2.0", "id": 5, "result": {}}},
        {"t": _ts(400), "seq": 4, "dir": "client->server", "msg": {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "execute_code"}}},
        {"t": _ts(402), "seq": 5, "dir": "server->client", "msg": {"jsonrpc": "2.0", "id": 6, "result": {}}},
    ]
    s = tmp_path / "stream.jsonl"
    s.write_text("\n".join(json.dumps(d) for d in stream), encoding="utf-8")
    t = tmp_path / "transcript.jsonl"
    t.write_text("\n".join(json.dumps(d) for d in tr), encoding="utf-8")
    return s, t


def test_rows_kinds_and_times(tmp_path):
    s, t = _write(tmp_path)
    rows = la_replay.rows(s, t)
    kinds = [r["kind"] for r in rows]
    assert kinds == ["think", "tool", "result", "compact", "tool", "error", "say"]
    tool = rows[1]
    assert tool["text"].startswith("● freecad · list_documents(")
    assert tool["t"] == 30.0
    assert rows[2]["text"].strip().startswith("└") and "peg" in rows[2]["text"]
    assert rows[5]["t"] == 402.0 and "no attribute 'Objects'" in rows[5]["text"]
    # compaction ends at the next known event and lasts duration_ms
    assert rows[3]["t"] == 400.0 - 120.0 and "2.0 min" in rows[3]["text"]
    # thinking before the first call sits between start and the call
    assert 0.0 <= rows[0]["t"] <= 30.0
    assert rows[-1]["t"] >= 402.0 and rows[-1]["text"].startswith("● I moved the shell")


def test_no_status_words(tmp_path):
    s, t = _write(tmp_path)
    for r in la_replay.rows(s, t):
        low = r["text"].lower()
        for bad in la_replay.BANNED:
            assert bad not in low


def test_schedule_fits_and_is_monotone(tmp_path):
    s, t = _write(tmp_path)
    rows = la_replay.rows(s, t)
    sch = la_replay.schedule(rows, 10.0, lead=1.0)
    ts = [r["at"] for r in sch]
    assert ts == sorted(ts) and ts[0] >= 1.0 and ts[-1] <= 10.0 - 1.0 + 1e-6
    assert all(b - a >= 0.15 - 1e-9 for a, b in zip(ts, ts[1:]))


def test_error_first_line_reads_the_refusal():
    j = '{\n  "applied": [],\n  "failed": {\n    "command": "shell",\n    "error": "unknown command `shell`"\n  }\n}'
    assert la_replay._first(j) == "shell: unknown command `shell`"
    assert la_replay._first("<tool_use_error>Error: No such tool</tool_use_error>") == "Error: No such tool"


def test_wrap_cols():
    out = la_replay.wrap("● freecad · execute_code(code: \"x\" )" + "y" * 100, 40)
    assert all(len(l) <= 40 for l in out) and len(out) <= 2
