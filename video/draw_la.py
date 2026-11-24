"""Local AI CAD setup (la): cards, chips, insets and Short words, SCRIPT-la.md rev 2 sections 1 + 3 and
SCRIPT-la-short.md. Self-contained (PIL + DejaVu in cad3way-draw:1).
Out: video/frames-la/ (git-ignored, re-drawn by this script):
  card-*.png  2560 x 1440 RGB, light paper, 44 columns a line, no exceptions;
  ov-*.png    tight RGBA chips / insets / panels for the footage script to place (32 columns a line);
  s-*.png     tight RGBA Short words, 1080 wide max (32 columns a line).
Every number is NUMBERS-la.json's (or the script's arithmetic: 10 + 2 + 2 = 14); no percent sign, no angle brackets,
never a run name. Build cards ("-1", "-2", ...) only add lines (tests/test_draw_la.py checks it).
Run:  MSYS_NO_PATHCONV=1 docker run --rm -v "<edu-visualization>:/ev" -w /ev/local-ai-cad-lab cad3way-draw:1 \
        python3 video/draw_la.py
Test: tests/test_draw_la.py"""
import json
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

LAB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
OUT = os.path.join(LAB, 'video', 'frames-la')
NUM = json.load(open(os.path.join(LAB, '..', 'Refream-Canvas', 'inputs', 'video-plans', '2026-11-21-local-ai-cad-setup',
                                  'NUMBERS-la.json'), encoding='utf-8'))
FD = '/usr/share/fonts/truetype/dejavu/'
R, B, M, MB = 'DejaVuSans.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSansMono.ttf', 'DejaVuSansMono-Bold.ttf'
W, H = 2560, 1440
PAPER, INK, GREY, WHITE = (246, 247, 250), (24, 28, 38), (108, 116, 130), (255, 255, 255)
BLUE, ORANGE, RED, GREEN, AMBER = (37, 99, 235), (234, 108, 0), (200, 30, 30), (22, 140, 70), (180, 120, 0)
LIGHT = (226, 231, 240)
LOG, PROBLEMS, CUR = {}, [], []

T = NUM['g2_first_request_tokens']
PAGE = NUM['page']
LAYERS = NUM['g3_12b']['65536_q8_0']['gpu_layers'].replace('/', ' of ')          # "35 of 49"
PEG = NUM['runs_12b']['solidcraft_T']['sc_T_3_after']['peg_w_wall2']              # 14.0
VOL = NUM['runs_12b']['solidcraft_S']['measured_volume'][0]                       # 6000
assert VOL == 6000 and NUM['runs_12b']['freecad_S']['measured_volume'][0] == 6000
PROMPT = ("My wall cup's key peg should be a solid 10 by 10 peg, but after the shell it came out hollow and bigger, "
          "open into the cup. Fix it so the peg stays solid and 10 wide when I change the wall thickness. Then check "
          "the peg and the front wall and tell me what you find.")


def c(v):
    return f'{v:,}'


def font(p, px):
    return ImageFont.truetype(FD + p, px)


def text(d, xy, s, px=56, fill=INK, path=B, anchor='la'):
    CUR.append(s)
    d.text(xy, s, font=font(path, px), fill=fill, anchor=anchor)


def canvas():
    CUR.clear()
    im = Image.new('RGB', (W, H), PAPER)
    return im, ImageDraw.Draw(im)


def header(d, s, sub=None):
    text(d, (140, 90), s, 80, INK)
    if sub:
        text(d, (140, 200), sub, 52, GREY, R)


def save(im, name):
    LOG[name] = list(CUR)
    for s in CUR:
        if '%' in s or '<' in s or '>' in s:
            PROBLEMS.append(f'{name}: {s!r} has a forbidden sign')
    im.save(os.path.join(OUT, name))


def arrow(d, a, z, col, w=10, size=34):
    d.line((a, z), fill=col, width=w)
    dx, dy = z[0] - a[0], z[1] - a[1]
    n = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / n, dy / n
    d.polygon([z, (z[0] - size * ux + size * 0.6 * uy, z[1] - size * uy - size * 0.6 * ux),
               (z[0] - size * ux - size * 0.6 * uy, z[1] - size * uy + size * 0.6 * ux)], fill=col)


def box(d, xy, lines, edge=INK, fill=WHITE, px=56, col=INK):
    d.rounded_rectangle(xy, radius=24, fill=fill, outline=edge, width=6)
    cx, cy = (xy[0] + xy[2]) // 2, (xy[1] + xy[3]) // 2
    top = cy - (len(lines) - 1) * (px + 12) // 2
    for i, s in enumerate(lines):
        text(d, (cx, top + i * (px + 12)), s, px if i == 0 else px - 8, col if i == 0 else GREY, B if i == 0 else R,
             anchor='mm')


def chip(name, lines, px=52, fg=INK, edge=ORANGE, bg=WHITE, alpha=245):
    """A tight RGBA chip: rounded box, one or more lines (logged under its own name)."""
    CUR.clear()
    f = font(B, px)
    w = int(max(f.getlength(s) for s in lines)) + 56
    h = (px + 16) * len(lines) + 28
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((2, 2, w - 3, h - 3), radius=18, fill=bg + (alpha,), outline=edge + (255,), width=5)
    for i, s in enumerate(lines):
        text(d, (28, 16 + i * (px + 16)), s, px, fg)
    save(im, name)


# ---------- cards ----------
def figure(d, x, y, col, faded=False):
    """A teacher: head + body (x = centre, y = feet)."""
    k = (200, 205, 214) if faded else col
    d.ellipse((x - 45, y - 330, x + 45, y - 240), fill=k)
    d.rounded_rectangle((x - 70, y - 230, x + 70, y), radius=30, fill=k)


def card_F3(step):
    im, d = canvas()
    header(d, 'A substitute teacher')
    d.rectangle((300, 300, 1500, 760), fill=(36, 84, 60), outline=(120, 90, 50), width=14)     # board
    text(d, (900, 530), 'the classroom', 64, WHITE, anchor='mm')
    d.rectangle((1650, 900, 2300, 960), fill=(150, 110, 70))                                  # desk
    d.rectangle((1700, 960, 1730, 1200), fill=(150, 110, 70))
    d.rectangle((2220, 960, 2250, 1200), fill=(150, 110, 70))
    d.polygon([(1820, 900), (2080, 900), (2060, 860), (1840, 860)], fill=WHITE, outline=INK)  # the plan
    text(d, (1950, 820), 'lesson plan', 52, INK, anchor='mb')
    if step == 1:
        figure(d, 1500, 1200, BLUE)
    text(d, (140, 1280), '1. the usual teacher, the plan on the desk', 48, BLUE, R)
    if step >= 2:
        figure(d, 420, 1200, BLUE, faded=step > 2)
        d.rectangle((300, 820, 560, 1210), outline=GREY, width=8)                             # door
        text(d, (140, 1340), '2. the usual teacher leaves', 48, GREY, R)
    if step >= 3:
        figure(d, 1500, 1200, ORANGE)
        text(d, (1300, 1340), '3. a substitute reads the same plan', 48, ORANGE, R)
    if step >= 4:
        d.rounded_rectangle((900, 800, 1310, 920), radius=30, fill=WHITE, outline=GREEN, width=6)
        text(d, (1105, 860), 'easy: ✓', 56, GREEN, anchor='mm')
        d.rounded_rectangle((900, 950, 1310, 1070), radius=30, fill=WHITE, outline=RED, width=6)
        text(d, (1105, 1010), 'tricky: ...?', 56, RED, anchor='mm')
        text(d, (1650, 300), 'same plan, different teacher', 52, INK)
        text(d, (1650, 380), 'the plan = the plug', 48, GREY, R)
        text(d, (1650, 450), 'the substitute = the local model', 48, ORANGE, R)
    save(im, f'card-F3-{step}.png')


def card_F4(step):
    im, d = canvas()
    header(d, 'Claude Code is the host')
    box(d, (260, 760, 1060, 1000), ['Claude Code', 'the host'], BLUE)
    box(d, (1700, 640, 2400, 820), ['SolidCraft plug'], INK, px=52)
    box(d, (1700, 960, 2400, 1140), ['FreeCAD plug'], INK, px=52)
    arrow(d, (1060, 860), (1690, 740), INK)
    arrow(d, (1060, 900), (1690, 1040), INK)
    text(d, (1380, 1180), 'reads each plug\'s tools', 44, GREY, R, anchor='mm')
    if step >= 2:
        box(d, (260, 300, 1060, 500), ['Claude', 'on the internet'], GREY if step > 2 else BLUE)
        arrow(d, (660, 760), (660, 510), GREY if step > 2 else BLUE)
        text(d, (800, 600), 'asks a model what to do', 44, GREY, R)
    if step >= 3:
        d.line((560, 560, 760, 700), fill=RED, width=10)
        d.line((760, 560, 560, 700), fill=RED, width=10)
        box(d, (260, 1150, 1060, 1360), ['Ollama on your PC', 'Gemma 4 12B'], GREEN)
        arrow(d, (660, 1000), (660, 1140), GREEN)
        d.rounded_rectangle((1240, 250, 2460, 470), radius=20, fill=WHITE, outline=ORANGE, width=6)
        text(d, (1280, 280), 'Ollama documents this. Anthropic does', 48, INK)
        text(d, (1280, 360), 'not support Claude Code on other models.', 48, INK)
    save(im, f'card-F4-{step}.png')


def card_F5():
    im, d = canvas()
    header(d, 'What we used')
    for i, s in enumerate(['NVIDIA RTX 4060, 8 GB', '32 GB RAM', 'Linux in Docker', 'Mac: not tested']):
        text(d, (180, 330 + i * 110), '• ' + s, 64, GREY if 'not' in s else INK)
    text(d, (1400, 330), 'Step 1: run Ollama', 64, BLUE)
    box(d, (1400, 460, 2420, 700), ['Windows or Mac', 'the Ollama app (easiest)'], GREEN, px=56)
    box(d, (1400, 760, 2420, 1000), ['Linux, or Docker users', 'Docker (what we filmed)'], BLUE, px=56)
    save(im, 'card-F5.png')


def card_F7(step):
    im, d = canvas()
    header(d, 'The page: everything the model reads at once', 'counted in tokens, small pieces of words')
    k, x0, x1, base = 0.032, 300, 1100, 1330
    segs = [(T['no_plug'], "Claude Code's instructions", BLUE), (T['solidcraft'], '+ SolidCraft tools', ORANGE),
            (T['both'], '+ FreeCAD tools', GREEN)]
    prev = 0
    for i, (tot, label, col) in enumerate(segs[:step]):
        d.rectangle((x0, base - tot * k, x1, base - prev * k), fill=col, outline=WHITE, width=4)
        text(d, (x1 + 40, base - (tot + prev) / 2 * k), f'{label}: {c(tot)}', 52, col, anchor='lm')
        prev = tot
    if step >= 3:
        text(d, (x0, base - T['both'] * k - 20), f'total {c(T["both"])} tokens', 60, INK, anchor='lb')
        dp = PAGE['default_page']
        d.rectangle((1700, base - dp * k, 2200, base), outline=RED, width=10)
        text(d, (1950, base - dp * k - 20), f"Ollama's default page: {c(dp)}", 48, RED, anchor='mb')
        text(d, (1950, base - dp * k / 2), 'refused', 64, RED, anchor='mm')
    save(im, f'card-F7-{step}.png')


def card_F13():
    im, d = canvas()
    header(d, 'Windows (PowerShell): the same lines', 'in PowerShell form, not run in our lab')
    # every row 44 columns max: the longest name (40) cannot carry "$env:" and "=", so the card shows the
    # PowerShell form once and lists name / value rows (full lines in the description)
    rows = ['type each one as  $env:NAME="value"', 'ANTHROPIC_BASE_URL', '    "http://localhost:11434"',
            'ANTHROPIC_AUTH_TOKEN  "ollama"', 'leave ANTHROPIC_API_KEY unset', '    (our PowerShell 5.1 check)',
            'CLAUDE_CODE_MAX_CONTEXT_TOKENS', f'    "{PAGE["claude_code_max_context_tokens"]}"',
            'ENABLE_TOOL_SEARCH  "false"', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC', '    "1"']
    for i, s in enumerate(rows):
        code = s[:1].isupper() or s.startswith('    "')
        text(d, (180, 300 + i * 96), s, 56, INK if code else AMBER, MB if code else B)
    save(im, 'card-F13.png')


def section(d, cx, cy, s, peg_w, hollow_peg, col):
    """Top section of the wall cup: 2 mm walls, the peg on the front (down on the page); s = px per mm."""
    ow, oh, wall = 50, 30, 2
    x0, y0, x1, y1 = cx - ow * s / 2, cy - oh * s / 2, cx + ow * s / 2, cy + oh * s / 2
    d.rectangle((x0, y0, x1, y1), fill=col)
    d.rectangle((x0 + wall * s, y0 + wall * s, x1 - wall * s, y1 - wall * s), fill=PAPER)
    pw = peg_w * s
    d.rectangle((cx - pw / 2, y1 - 1, cx + pw / 2, y1 + 10 * s), fill=col)
    if hollow_peg:
        d.rectangle((cx - 5 * s, y1 - wall * s - 2, cx + 5 * s, y1 + (10 - wall) * s), fill=PAPER)
    return y1 + 10 * s


def card_F18(step):
    im, d = canvas()
    header(d, 'Lesson 14: the shell order trap')
    s = 13
    bot = section(d, 520, 640, s, 10, False, (120, 130, 150))
    text(d, (520, bot + 50), 'wall cup, 2 mm walls,', 48, INK, anchor='mt')
    text(d, (520, bot + 115), 'a 10 mm square peg', 48, INK, anchor='mt')
    if step >= 2:
        bot = section(d, 1280, 640, s, 14, True, RED)
        text(d, (1280, bot + 50), 'hollowed AFTER the peg:', 48, RED, anchor='mt')
        text(d, (1280, bot + 115), '10 + 2 + 2 = 14, open into the cup', 44, RED, R, anchor='mt')
    if step >= 3:
        bot = section(d, 2040, 640, s, 10, False, GREEN)
        text(d, (2040, bot + 50), 'the fix:', 48, GREEN, anchor='mt')
        text(d, (2040, bot + 115), 'hollow first, then the peg', 48, GREEN, anchor='mt')
    save(im, f'card-F18-{step}.png')


def card_F19():
    im, d = canvas()
    header(d, 'The words (same as lesson 14)')
    f = font(M, 60)
    lines, lit = textwrap.wrap(PROMPT, 44), []
    flat = ' '.join(lines)
    j = flat.find('check the peg')          # light "check the peg", across a line break if the wrap splits it
    for i, ln in enumerate(lines):
        y, start = 300 + i * 120, len(' '.join(lines[:i])) + (1 if i else 0)
        lo, hi = max(j, start), min(j + len('check the peg'), start + len(ln))
        if lo < hi:
            x0, x1 = 180 + f.getlength(ln[:lo - start]), 180 + f.getlength(ln[:hi - start])
            d.rectangle((x0 - 8, y - 6, x1 + 8, y + 74), fill=(255, 226, 150))
            lit.append(ln[lo - start:hi - start])
        text(d, (180, y), ln, 60, INK, M)
    if ' '.join(lit) != 'check the peg':
        PROBLEMS.append(f'card-F19: lit {lit!r}')
    save(im, 'card-F19.png')


def card_F23(step):
    im, d = canvas()
    header(d, 'What it means (8 GB card)')
    rows = [('local did: the setup + simple blocks, 6 of 6', GREEN),
            ('local did not: the multi-step fix,', RED), ('0 of 6 in 25 min', RED),
            ('not tested: 26B, bigger cards, Mac', GREY)]
    upto = {1: 1, 2: 3, 3: 4}[step]
    for i, (s, col) in enumerate(rows[:upto]):
        text(d, (180 + (60 if i == 2 else 0), 330 + i * 130), s, 64, col)
    if step >= 3:
        d.rounded_rectangle((180, 1000, 1500, 1200), radius=20, fill=WHITE, outline=ORANGE, width=6)
        text(d, (220, 1030), 'work on a saved copy;', 56, INK)
        text(d, (220, 1110), 'check it with Measure yourself', 52, GREY, R)
    save(im, f'card-F23-{step}.png')


def card_F24():
    im, d = canvas()
    text(d, (180, 150), 'Next: SolidCraft + Claude course', 72, INK)
    box(d, (180, 320, 1500, 640), ['Lesson 1', 'add the plug from zero'], BLUE, px=72)
    box(d, (180, 700, 1500, 1020), ['FreeCAD + Claude course', 'lesson 1: the same, in FreeCAD'], INK, px=56)
    d.rounded_rectangle((1700, 420, 2300, 560), radius=20, fill=(204, 0, 0))
    text(d, (2000, 490), 'Subscribe', 64, WHITE, anchor='mm')
    text(d, (180, 1300), 'The voice in this video is an AI voice.', 48, GREY, R)
    save(im, 'card-F24.png')


def chips():
    chip('ov-F0-words.png', ['Local Gemma 4 vs Claude:', 'same setup, same CAD job'], px=72, edge=BLUE)
    chip('ov-course.png', ['SolidCraft + Claude', 'FreeCAD + Claude · bonus lesson'], px=44, edge=BLUE)
    f1 = ['simple block: 6 of 6 right', 'checked by code:', 'our script reads the saved file',
          'lesson 14 trap: 0 of 6', 'done in 25 min', 'Claude: block + fix, 4 of 4', 'usable for simple parts;',
          'multi-step fix: not done here']
    for i, n in enumerate((3, 5, 6, 8), 1):
        chip(f'ov-F1-{i}.png', f1[:n], px=48, edge=INK)
    chip('ov-sped.png', ['sped up'], px=44, edge=AMBER)
    chip('ov-P-disk.png', ['already on this disk:', 'the real download is 7.2 GB'])
    chip('ov-F6-26b.png', ['26B (17 GB download):', 'not tested in our lab'], edge=GREY)
    chip('ov-strict.png', ['our lab adds --strict-mcp-config', "to keep this PC's other tools",
                           'out: leave it off, or your', 'plugs will not load'], px=44, edge=RED)
    chip('ov-typed-ahead.png', ['step 6 lines, typed ahead', '(see step 6)'], px=48)
    chip('ov-F8-app.png', ['Ollama app: set Context length', 'in Settings (not run in our lab)'], px=48)
    chip('ov-F8-layers.png', [f'{LAYERS} layers on the card'])
    chip('ov-F5-private.png', ['127.0.0.1: private to this PC'])
    chip('ov-F10-conn.png', ['Connected ≠ socket on'], edge=RED)
    chip('ov-F11-port.png', ["11434 = Ollama's door number"])
    chip('ov-F11-win.png', ['Windows lines: end of step 6', '+ description'], px=44, edge=GREY)
    chip('ov-F12-version.png', ['Claude Code 2.1.311', '(newer versions: 1m)'], px=48, edge=GREY)
    chip('ov-F14-said.png', [f'it said: {c(VOL)} mm³', f'by code: {c(VOL)} mm³'], px=60, edge=GREEN)
    chip('ov-F15-course.png', ['SolidCraft + Claude course:', 'lesson 1'], edge=BLUE)
    chip('ov-F16-said.png', [f'it said {c(VOL)} · by code {c(VOL)}'], px=56, edge=GREEN)
    chip('ov-F16-row.png', ['12B, simple block:', 'SolidCraft 3 of 3', 'FreeCAD 3 of 3'], px=48, edge=INK)
    chip('ov-F20-proof.png', [f'by code: peg {PEG:g} wide at wall 2'], edge=RED)
    chip('ov-F21-same.png', ['same line 4 times:', 'doc = App.activeDocument', '(no brackets)'], px=48, edge=RED)
    chip('ov-F21-speed.png', ['writing ~11 tokens a second'], px=48, edge=GREY)
    chip('ov-F22-proof.png', ['by code: peg 10 x 10', 'at wall 2 and 3'], edge=GREEN)
    chip('ov-F22-table.png', ['Claude: 2 of 2, 30 and 37 s', '12B: 0 of 6 in 25 min'], px=56, edge=INK)
    chip('ov-F23-copy.png', ['work on a saved copy'], edge=ORANGE)


def short_words():
    chip('s-head.png', ['FREE LOCAL AI vs CLAUDE:', 'SAME CAD TRAP'], px=58, edge=RED)
    chip('s-S1.png', ['simple block: 6 of 6 right'], px=56, edge=GREEN)
    chip('s-S2.png', ['walls grew round the peg:', '10 + 2 + 2 = 14'], px=56, edge=RED)
    chip('s-S3.png', ['local: 0 of 6 in 25 min', 'Claude: 2 of 2, under 40 s each'], px=52, edge=INK)
    chip('s-S4.png', ['full setup: Local AI CAD Setup', '(long video)'], px=52, edge=BLUE)
    chip('s-voice.png', ['AI voice'], px=44, edge=GREY)


def main():
    os.makedirs(OUT, exist_ok=True)
    LOG.clear()
    PROBLEMS.clear()
    for s in (1, 2, 3, 4):
        card_F3(s)
    for s in (1, 2, 3):
        card_F4(s)
        card_F7(s)
        card_F18(s)
        card_F23(s)
    card_F5()
    card_F13()
    card_F19()
    card_F24()
    chips()
    short_words()
    for name, im in ((n, Image.open(os.path.join(OUT, n))) for n in LOG if n.startswith('s-')):
        if im.size[0] > 1080:
            PROBLEMS.append(f'{name}: {im.size[0]} wide, over the Short frame')
    print('drawn', len(LOG), 'PROBLEMS:', PROBLEMS or 'none')


if __name__ == '__main__':
    main()
