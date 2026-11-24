import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lab"))
import la_ocr

HEAD = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def _w(b, p, l, x, y, w, h, t):
    return "5\t1\t%d\t%d\t%d\t1\t%d\t%d\t%d\t%d\t90\t%s\n" % (b, p, l, x, y, w, h, t)


def test_lines_grouped_and_scaled_back():
    tsv = HEAD + _w(1, 1, 1, 10, 20, 50, 10, "gemma4") + _w(1, 1, 1, 70, 21, 40, 10, "API") + \
        _w(1, 1, 1, 115, 20, 60, 11, "Billing") + _w(2, 1, 1, 5, 200, 30, 10, "hello")
    ls = la_ocr.lines_from_tsv(tsv, scale=0.5)
    assert ls[0] == (20, 40, 330, 22, "gemma4 API Billing")
    assert ls[1][4] == "hello"


def test_patterns():
    hit = lambda s: bool(la_ocr.hits([(0, 0, 1, 1, s)]))
    for s in ["gemma4 · API Usage Billing", "auto mode on (shift+tab to cycle)", "↓ 120 tokens",
              "Resume this session with: claude --resume 1234", "esc to interrupt", "a.b@example.com", "sk-ant-x"]:
        assert hit(s), s
    for s in ["Hi there! How can I help you today?", "41% until auto-compact", "Ollama is running"]:
        assert not hit(s), s
