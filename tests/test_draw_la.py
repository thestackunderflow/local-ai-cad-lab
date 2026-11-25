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
         'card-F23-3.png', 'card-F23-4.png', 'card-F24-1.png', 'card-F24-2.png', 'card-F24-3.png',
         'card-F13-page-1.png', 'card-F13-page-2.png', 'card-F13-page-3.png', 'card-F22-pegs.png']
OVERLAYS = ['ov-F0-words.png', 'ov-course.png', 'ov-F1-1.png', 'ov-F1-2.png', 'ov-F1-3.png', 'ov-F1-4.png',
            'ov-sped.png', 'ov-P-disk.png', 'ov-F6-26b.png', 'ov-strict.png', 'ov-typed-ahead.png',
            'ov-F8-app.png', 'ov-F8-layers.png', 'ov-F5-private.png', 'ov-F10-conn.png', 'ov-F11-port.png',
            'ov-F11-win.png', 'ov-F12-version.png', 'ov-F14-said.png', 'ov-F15-course.png', 'ov-F16-said.png',
            'ov-F16-row.png', 'ov-F20-proof.png', 'ov-F21-same.png', 'ov-F21-speed.png', 'ov-F22-proof.png',
            'ov-F22-table.png', 'ov-F23-copy.png']
SHORT = ['s-head.png', 's-S1.png', 's-S2.png', 's-S3.png', 's-S4.png', 's-voice.png', 's-S4a.png']
TRAP = ['s-trap-1.png', 's-trap-2.png', 's-trap-3.png', 's-trap-4.png']


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
    for stem, k in (('card-F3', 4), ('card-F4', 3), ('card-F7', 3), ('card-F18', 3), ('card-F23', 4), ('ov-F1', 4),
                    ('card-F24', 3), ('card-F13-page', 3)):
        prev = []
        for i in range(1, k + 1):
            cur = d.LOG[f'{stem}-{i}.png']
            assert cur[:len(prev)] == prev and len(cur) > len(prev), (stem, i)
            prev = cur


def test_cut2_card_fixes(drawn):
    """la cut 2 (GATES-la-c1 fixes 8, 12, 13 + S3): the opening badge names Claude Code + Gemma (never "+ Claude" while
    Gemma drives); card-F5 agrees with the voice (the Windows / Mac app was not filmed here); card-F18 shows the peg
    widths (10 mm vs 14 mm); the Claude table says ~12 cents a run (cost_usd 0.115 / 0.1171)."""
    course = ' '.join(d.LOG['ov-course.png'])
    assert '+ Claude' not in course and 'Claude Code + Gemma 4 12B' in course
    f5 = d.LOG['card-F5.png']
    assert 'Mac: not tested' not in ' '.join(f5) and any('not filmed' in s for s in f5)
    assert '10 mm' in d.LOG['card-F18-1.png'] and '14 mm' in d.LOG['card-F18-2.png']
    runs = d.NUM['runs_claude']
    cents = {round(100 * r['cost_usd']) for k, r in runs.items() if '-T-' in k}
    assert cents == {12}, cents
    assert any('~12 cents a run' in s for s in d.LOG['ov-F22-table.png'])


def test_short_c2_trap_card_and_card_words(drawn):
    """la Short cut 2 (GATES-la-short-c1 fixes 5 + 10): the trap card builds 10 -> + 2 -> + 2 = 14, then the goal (peg back
    to 10) before "Fix it"; 1080 x 1080 (the Short's square view); the "8 GB card" words chip for the close."""
    for f in TRAP:
        assert Image.open(os.path.join(d.OUT, f)).size == (1080, 1080), f
    prev = []
    for i in range(1, 5):
        cur = d.LOG[f's-trap-{i}.png']
        assert cur[:len(prev)] == prev and len(cur) > len(prev), i
        prev = cur
    peg = d.NUM['runs_12b']['solidcraft_T']['sc_T_3_after']['peg_w_wall2']
    assert '10 mm' in d.LOG['s-trap-1.png']
    assert any('+ 2' in s for s in d.LOG['s-trap-2.png'][len(d.LOG['s-trap-1.png']):])
    assert f'10 + 2 + 2 = {peg:g} mm' in d.LOG['s-trap-3.png']
    goal = d.LOG['s-trap-4.png'][len(d.LOG['s-trap-3.png']):]
    assert any('goal: peg back to 10' in s for s in goal)
    s4a = ' '.join(d.LOG['s-S4a.png'])
    assert '8 GB card' in s4a and 'not yet' in s4a


def test_cut3_card_fixes(drawn):
    """la cut 3 (GATES-la-c2 fixes 1-3, 4a, 6-8): the strict chip names the flag plainly; the compaction page card
    (65,536 page, half mark, the measured compacting range, the assumed 200,000 and its half past the real page); the
    measured-peg card (12B edit 14 / 16 = the trap, Claude 10 / 10) with the table; card-F5's bullet clear of the right
    column; card-F23 in 4 builds with the Python row; card-F24 in 3 builds, AI voice in the last only; F7 running totals;
    the layers chip says what the rest does."""
    n = d.NUM
    strict = ' '.join(d.LOG['ov-strict.png'])
    assert '--strict-mcp-config' in strict and 'you leave that flag off' in strict
    p3 = ' '.join(d.LOG['card-F13-page-3.png'])
    ac = n['auto_compaction']
    lo = min(ac['threshold_pre_tokens'] + [ac['reruns']['pre_tokens_range'][0]])
    hi = max(ac['threshold_pre_tokens'] + [ac['reruns']['pre_tokens_range'][1]])
    assert f'{lo:,}-{hi:,}' in p3, (lo, hi)                                    # 32,293-37,823
    assert f"{n['page']['claude_code_max_context_tokens']:,}" in p3                # 65,536
    assert f"{n['g9_context_window']['without_line']:,}" in p3                     # 200,000
    assert f"{n['page']['claude_code_max_context_tokens'] // 2:,}" in p3           # half: 32,768
    assert f"{n['g9_context_window']['without_line'] // 2:,}" in p3                # half: 100,000
    assert 'error' not in p3.lower() and 'crash' not in p3.lower()                # g9 records no failure: claim none
    assert '200,000' not in ' '.join(d.LOG['card-F13-page-1.png'])
    pegs = ' '.join(d.LOG['card-F22-pegs.png'])
    sc = n['runs_12b']['solidcraft_T']['sc_T_3_after']
    cl = n['runs_claude']['cl-fc-T-1']
    assert f"{sc['peg_w_wall2']:g} at wall 2, {sc['peg_w_wall3']:g} at wall 3" in pegs and 'not fixed' in pegs
    assert f"{cl['measured_wall2']['peg_w']:g} at wall 2, {cl['measured_wall3']['peg_w']:g} at wall 3" in pegs
    assert '~12 cents a run' in pegs and '0 of 6 in 25 min' in pegs
    f = d.font(d.B, 64)
    for s in d.LOG['card-F5.png']:
        if s.startswith('• '):
            assert 180 + f.getlength(s) <= 1360, (s, 180 + f.getlength(s))      # right column starts at 1400
    assert any("FreeCAD's plug runs any Python" in s for s in d.LOG['card-F23-4.png'])
    assert not any("FreeCAD's plug" in s for s in d.LOG['card-F23-2.png'])
    assert any('Mac app' in s for s in d.LOG['card-F23-3.png'])
    for k in (1, 2):
        assert not any('AI voice' in s for s in d.LOG[f'card-F24-{k}.png'])
    assert any('AI voice' in s for s in d.LOG['card-F24-3.png'])
    f7 = ' '.join(d.LOG['card-F7-3.png'])
    assert 'running total 21,550' in f7 and 'running total 27,116' in f7
    assert any('the rest run on the CPU' in s for s in d.LOG['ov-F8-layers.png'])


def test_short_c3_s1_names_both_apps(drawn):
    """la Short cut 3 (GATES-la-short-c2 C5): FreeCAD is spoken in S1, so the words chip names both apps, each count
    from NUMBERS-la.json (runs_12b solidcraft_S / freecad_S pass)."""
    r = d.NUM['runs_12b']
    sc, fc = r['solidcraft_S']['pass'].split(' of '), r['freecad_S']['pass'].split(' of ')
    assert sc[0] == sc[1] and fc[0] == fc[1]                     # every run right, so "3 in SolidCraft" is the claim
    assert int(sc[0]) + int(fc[0]) == 6
    assert d.LOG['s-S1.png'] == ['simple block: 6 of 6 right', f'{sc[0]} in SolidCraft, {fc[0]} in FreeCAD']
    assert all(len(s) <= 32 for s in d.LOG['s-S1.png'])
