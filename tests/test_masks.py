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


def test_app_masks_measured_24nov():
    # SolidCraft "Update to 0.48.0" button (x 1878-2118, y 12-50) all through S12-sc; FreeCAD's Tasks / Start Part
    # panel (x 2304-2874, y 465-596) from 93.6 s to the end of S12-fc, filled with what lies under it
    assert la_masks.covered("S12sc", 50.0, 1931, 22, 167, 22)
    assert la_masks.covered("S12sc", 117.0, 1931, 22, 167, 22)
    for t in (95.0, 110.0, 125.0):
        assert la_masks.covered("S12fc", t, 2319, 501, 128, 35), t
        assert la_masks.covered("S12fc", t, 2542, 467, 331, 15), t
    assert not la_masks.covered("S12fc", 60.0, 2319, 501, 128, 35)
    f = la_masks.mask_filter("S12fc", t_off=90.0)
    assert "color=0x92979d" in f and "color=0xf7f7f7" in f and "between(t,14.20,30.40)" in f
    assert "color=0x32373f" in la_masks.mask_filter("S12sc")


SCANM = pathlib.Path(__file__).resolve().parents[1] / "out" / "scratch" / "la-m"


@pytest.mark.skipif(not (SCANM / "sc-upd-masked.tsv").exists(), reason="scan files are git-ignored")
def test_masked_takes_scan_clean():
    # the takes re-encoded through mask_filter, then OCR'd at 1 fps (out/scratch/la-m/masked.sh): no hit left
    for f in ("sc-upd-masked.tsv", "fc-start-masked.tsv"):
        assert open(SCANM / f, encoding="utf-8").read().strip().endswith("hits 0"), f


def test_ocr_pattern_catches_squashed_update():
    assert la_masks.PAT.search("Updateto0.48.0) Report a bug")
