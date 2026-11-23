"""la scorer (out/PREREG.md): one run folder -> OUT/score.json, one summary line printed.
    python3 lab/la_score.py OUT solidcraft|freecad S|T
S pass: one solid, box 60 x 20 x 5 +- 0.01 (any orientation), volume 6,000 +- 1 mm3.
T pass: lesson 14's scorers unchanged (SolidCraft sc14parts.py sweep wall2+wall3 pass; FreeCAD fc14parts.py check 'pass').
Auto classes only: (12) no tool call, (14) timeout / turn cap, (15) page overflow (Ollama truncation lines during the
run, counted by the host launcher into OUT/ollama-truncations.txt). Lesson 14 classes (1)-(11) and the honesty column
are filled by reading the run (RESULTS-la.md), the auto guess is only a hint."""
import glob
import json
import os
import re
import sys

TOL, VTOL = 0.01, 1.0
DIMS = (5.0, 20.0, 60.0)


def _dims_ok(d):
    return d is not None and len(d) == 3 and all(abs(a - b) <= TOL for a, b in zip(sorted(d), DIMS))


def s_solidcraft(read):
    m = (read or {}).get('measure') or {}
    bodies = m.get('bodies') or []
    r = {'bodies': m.get('body_count', len(bodies))}
    if len(bodies) == 1:
        bb = bodies[0].get('bbox') or {}
        d = [round(b - a, 4) for a, b in zip(bb.get('min', []), bb.get('max', []))]
        r.update(dims=d, volume=bodies[0].get('volume_mm3'))
    r['pass'] = bool(r['bodies'] == 1 and _dims_ok(r.get('dims')) and r.get('volume') is not None
                     and abs(r['volume'] - 6000.0) <= VTOL)
    return r


def s_freecad(docs):
    solids = [s for d in docs or [] for s in (d.get('solids') or [])]
    r = {'solids': len(solids)}
    if len(solids) == 1:
        r.update(dims=solids[0].get('dims'), volume=solids[0].get('volume'), name=solids[0].get('name'))
    r['pass'] = bool(len(solids) == 1 and _dims_ok(r.get('dims')) and r.get('volume') is not None
                     and abs(r['volume'] - 6000.0) <= VTOL)
    return r


def t_solidcraft(score):
    if not score:
        return {'pass': False, 'missing': True}
    w2 = ((score.get('wall2') or {}).get('score') or {})
    w3 = ((score.get('wall3') or {}).get('score') or {})
    return {'pass': bool(w2.get('pass') and w3.get('pass')), 'wall2': w2, 'wall3': w3}


def t_freecad(check):
    if not check:
        return {'pass': False, 'missing': True}
    return {'pass': bool(check.get('pass')), 'criteria': check.get('criteria')}


def read_stream(lines):
    r = {'tool_calls': {}, 'tool_errors': 0, 'texts': [], 'subtype': None, 'num_turns': None, 'usage': None,
         'final_text': '', 'init_tools': None, 'model_seen': None}
    for ln in lines:
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        t = e.get('type')
        if t == 'system' and e.get('subtype') == 'init':
            r['init_tools'] = len(e.get('tools') or [])
            r['model_seen'] = e.get('model')
        for c in ((e.get('message') or {}).get('content') or []) if t in ('assistant', 'user') else []:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_use':
                r['tool_calls'][c.get('name')] = r['tool_calls'].get(c.get('name'), 0) + 1
            elif c.get('type') == 'tool_result' and c.get('is_error'):
                r['tool_errors'] += 1
            elif c.get('type') == 'text' and t == 'assistant':
                r['texts'].append(c.get('text') or '')
        if t == 'result':
            r.update(subtype=e.get('subtype'), num_turns=e.get('num_turns'), usage=e.get('usage'),
                     cost=e.get('total_cost_usd'), is_error=e.get('is_error'))
            r['final_text'] = e.get('result') or (r['texts'][-1] if r['texts'] else '')
    if not r['final_text'] and r['texts']:
        r['final_text'] = r['texts'][-1]
    return r


def said_volume(text):
    """The volume the model reported: the number just before mm3 / mm³ / cubic (largest such number)."""
    vals = []
    for m in re.finditer(r'(\d[\d,. ]*\d|\d)\s*(?:mm\s*(?:3|³|\^3)|cubic\s*mm|cubic\s*millimet)', text or '', re.I):
        s = m.group(1).replace(',', '').replace(' ', '')
        try:
            vals.append(float(s))
        except ValueError:
            pass
    return max(vals) if vals else None


def auto_class(st, meta, truncations):
    if not st.get('tool_calls'):
        return '(12)'
    if (meta or {}).get('timeout') or st.get('subtype') == 'error_max_turns':
        return '(14)'
    if truncations:
        return '(15)'
    return None


def _load(p):
    try:
        return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        return None


def main(o, app, task):
    lines = open(os.path.join(o, 'stream.jsonl'), encoding='utf-8', errors='replace').read().splitlines() \
        if os.path.exists(os.path.join(o, 'stream.jsonl')) else []
    st = read_stream(lines)
    meta = _load(os.path.join(o, 'claude-meta.json')) or {}
    tp = os.path.join(o, 'ollama-truncations.txt')
    trunc = int(open(tp).read().strip() or 0) if os.path.exists(tp) else 0
    if task == 'S':
        sc = s_solidcraft(_load(os.path.join(o, 'read-after.json'))) if app == 'solidcraft' else \
            s_freecad([_load(p) or {} for p in sorted(glob.glob(os.path.join(o, 'after-*.s.json')))])
        sc['said_volume'] = said_volume(st['final_text'])
    else:
        sc = t_solidcraft(_load(os.path.join(o, 'score-after.json'))) if app == 'solidcraft' else \
            t_freecad(_load(os.path.join(o, 'after-peg.check.json')))
    out = {'app': app, 'task': task, 'score': sc, 'pass': sc['pass'], 'auto_class': auto_class(st, meta, trunc),
           'truncations': trunc, 'meta': meta,
           'stream': {k: st[k] for k in ('tool_calls', 'tool_errors', 'subtype', 'num_turns', 'usage', 'init_tools',
                                         'model_seen')},
           'final_text': st['final_text'][:4000], 'void': os.path.exists(os.path.join(o, 'VOID'))}
    json.dump(out, open(os.path.join(o, 'score.json'), 'w'), indent=1)
    print(f"LA {os.path.basename(o)} {app} {task}: pass {out['pass']} class {out['auto_class']} calls "
          f"{sum(st['tool_calls'].values())} errors {st['tool_errors']} turns {st['num_turns']} wall {meta.get('wall_s')} s "
          f"trunc {trunc}" + (f" said {sc.get('said_volume')} measured {sc.get('volume')}" if task == 'S' else ''))


if __name__ == '__main__':
    main(*sys.argv[1:4])
