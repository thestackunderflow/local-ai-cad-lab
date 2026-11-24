import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lab"))
import la_panescan


def test_hits_and_clean(tmp_path):
    (tmp_path / "A").mkdir()
    (tmp_path / "A" / "pane.txt").write_text("$ curl http://localhost:11434\nOllama is running\n")
    assert la_panescan.scan(tmp_path) == []
    (tmp_path / "A" / "pane-hi.txt").write_text("  esc to interrupt\nkey sk-ant-xyz\n")
    assert len(la_panescan.scan(tmp_path)) == 2
