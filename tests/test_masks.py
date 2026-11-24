import pathlib, sys
import pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "lab"))
import la_masks

SCAN = pathlib.Path(__file__).resolve().parents[1] / "out" / "scratch" / "la-e"


def test_banner_partial_mask_and_wanted():
    rows = [(30.0, 224, 106, 736, 34, "gemma4:12b-it-qat · API Usage Billing"),
            (24.0, 12, 224, 2348, 34, 'Model "gemma4:12b-it-qat" isn\'t recognized · context assumed to be 200k tokens'),
            (700.0, 224, 106, 736, 34, "gemma4:12b-it-qat · API Usage Billing")]
    assert la_masks.uncovered("E", rows) == [rows[2]]


def test_filter_shifts_times():
    f = la_masks.mask_filter("E", t_off=20.0)
    assert "between(t,3.00,616.00)" in f and f.count("drawbox") == len(la_masks.MASKS["E"])


@pytest.mark.skipif(not (SCAN / "ocr-E1.tsv").exists(), reason="scan files are git-ignored")
def test_every_measured_hit_is_masked():
    rows = la_masks.read_tsv(SCAN / "ocr-E1.tsv") + la_masks.read_tsv(SCAN / "ocr-E2.tsv")
    assert la_masks.uncovered("E", rows) == []


@pytest.mark.skipif(not (SCAN / "ocr-C.tsv").exists(), reason="scan files are git-ignored")
def test_other_takes_need_no_mask():
    for k in "OPCMN":
        assert la_masks.uncovered(k, la_masks.read_tsv(SCAN / ("ocr-%s.tsv" % k))) == [], k
