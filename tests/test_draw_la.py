"""la cards / chips / insets / Short words (video/draw_la.py, SCRIPT-la.md rev 2 sections 1 + 3, SCRIPT-la-short.md):
every file drawn at its size, card lines 44 columns max, chips and Short words 32, no percent sign or angle brackets,
never a run name or a do-not-say word, every number on screen is NUMBERS-la.json's. Run in the draw image:
  MSYS_NO_PATHCONV=1 docker run --rm -v "<edu-visualization>:/ev" -w /ev/local-ai-cad-lab cad3way-draw:1 \
    python3 -m pytest -q tests/test_draw_la.py"""
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'video'))
import draw_la as d  # noqa: E402

CARDS = ['card-F3-1.png', 'card-F3-2.png', 'card-F3-3.png', 'card-F3-4.png', 'card-F4-1.png', 'card-F4-2.png',
         'card-F4-3.png', 'card-F5.png', 'card-F7-1.png', 'card-F7-2.png', 'card-F7-3.png', 'card-F13.png',
         'card-F18-1.png', 'card-F18-2.png', 'card-F18-3.png', 'card-F19.png', 'card-F23-1.png', 'card-F23-2.png',
         'card-F23-3.png', 'card-F24.png']
OVERLAYS = ['ov-F0-words.png', 'ov-course.png', 'ov-F1-1.png', 'ov-F1-2.png', 'ov-F1-3.png', 'ov-F1-4.png',
            'ov-sped.png', 'ov-P-disk.png', 'ov-F6-26b.png', 'ov-strict.png', 'ov-typed-ahead.png',
            'ov-F8-app.png', 'ov-F8-layers.png', 'ov-F5-private.png', 'ov-F10-conn.png', 'ov-F11-port.png',
            'ov-F11-win.png', 'ov-F12-version.png', 'ov-F14-said.png', 'ov-F15-course.png', 'ov-F16-said.png',
            'ov-F16-row.png', 'ov-F20-proof.png', 'ov-F21-same.png', 'ov-F21-speed.png', 'ov-F22-proof.png',
            'ov-F22-table.png', 'ov-F23-copy.png']
SHORT = ['s-head.png', 's-S1.png', 's-S2.png', 's-S3.png', 's-S4.png', 's-voice.png']


@pytest.fixture(scope='module')
def drawn():
    d.main()
    return d


def test_files_and_sizes(drawn):
    for f in CARDS:
        assert Image.open(os.path.join(d.OUT, f)).size == (2560, 1440), f
    for f in OVERLAYS:
        im = Image.open(os.path.join(d.OUT, f))
        assert im.mode == 'RGBA' and im.size[0] <= 2560 and im.size[1] <= 1440, f
    for f in SHORT:
        im = Image.open(os.path.join(d.OUT, f))
        assert im.mode == 'RGBA' and im.size[0] <= 1080, f


def test_no_problems(drawn):
    assert d.PROBLEMS == []


def test_columns(drawn):
    for name, lines in d.LOG.items():
        cap = 44 if name.startswith('card-') else 32
        for s in lines:      # no waivers: every row fits its cap (the PowerShell card wraps)
            assert len(s) <= cap, (name, s)


def test_forbidden(drawn):
    bad = ('%', '<', '>', 'f12-', '-T-', 'cl-sc', 'cl-fc', 'sonnet', 'failed', 'offline', 'free claude', 'a bug',
           'anthropic supports', 'api usage billing', 'sk-ant', 'auto mode', 'shift+tab', '@')
    for name, lines in d.LOG.items():
        for s in lines:
            for w in bad:
                assert w not in s.lower(), (name, s, w)


def test_numbers_from_numbers_json(drawn):
    n = d.NUM
    words = ' '.join(s for v in d.LOG.values() for s in v)
    assert f"{n['g2_first_request_tokens']['both']:,}" in words                 # 27,116
    assert f"{n['g2_first_request_tokens']['no_plug']:,}" in words              # 16,160
    assert f"{n['g2_first_request_tokens']['solidcraft']:,}" in words           # 21,550
    assert f"{n['page']['default_page']:,}" in words                            # 4,096
    assert f"{n['page']['ollama_context_length']}" in words                     # 65536 (as typed)
    assert n['g3_12b']['65536_q8_0']['gpu_layers'].replace('/', ' of ') in words     # 35 of 49
    assert f"peg {n['runs_12b']['solidcraft_T']['sc_T_3_after']['peg_w_wall2']:g} wide" in words
    assert '6,000' in words and all(v == 6000 for k in ('solidcraft_S', 'freecad_S')
                                    for v in n['runs_12b'][k]['measured_volume'])
    assert 'not tested in our lab' in words and '26B' in words


def test_builds_grow(drawn):
    """each build step adds lines to the one before (cards build, never jump)."""
    for stem, k in (('card-F3', 4), ('card-F4', 3), ('card-F7', 3), ('card-F18', 3), ('card-F23', 3), ('ov-F1', 4)):
        prev = []
        for i in range(1, k + 1):
            cur = d.LOG[f'{stem}-{i}.png']
            assert cur[:len(prev)] == prev and len(cur) > len(prev), (stem, i)
            prev = cur
