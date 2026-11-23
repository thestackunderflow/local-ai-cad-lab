"""Cost of one la Claude run + the stage ledger (PREREG: --max-budget-usd 0.15 S / 0.20 T, stage cap $0.50).

The ledger is the TSV lesson 14 used (edu-visualization/sc13-BUDGET.tsv: run, cost_usd, kind, lab); only rows below
the la GO line count. A run without a result event (killed) counts at its cap (budget.py's killed-floor rule).
    python la_cost.py check  LEDGER MARK RUN_CAP TOTAL_CAP          exit 0 = may start, 2 = stop
    python la_cost.py record LEDGER MARK RUN STREAM_JSONL RUN_CAP   prints the run cost and the stage total
"""
import json
import os
import sys


def cost(stream):
    if not os.path.exists(stream):
        return None
    c = None
    for ln in open(stream, encoding='utf-8', errors='replace'):
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if e.get('type') == 'result' and e.get('total_cost_usd') is not None:
            c = float(e['total_cost_usd'])
    return c


def total(path, mark):
    if not os.path.exists(path):
        return 0.0
    s, on = 0.0, False
    for line in open(path, encoding='utf-8'):
        if line.startswith(mark):
            on = True
            continue
        if on and line.strip() and not line.startswith('#'):
            s += float(line.split('\t')[1])
    return round(s, 4)


def allowed(path, mark, run_cap, total_cap):
    return total(path, mark) + run_cap <= total_cap + 1e-9


def ensure_mark(path, mark, note):
    if os.path.exists(path) and any(ln.startswith(mark) for ln in open(path, encoding='utf-8')):
        return
    with open(path, 'a', encoding='utf-8', newline='\n') as f:
        f.write(f'{mark} ({note})\n')


def record(path, run, c, run_cap):
    kind = 'logged' if c is not None else 'killed-floor'
    with open(path, 'a', encoding='utf-8', newline='\n') as f:
        f.write(f'{run}\t{(c if c is not None else run_cap):.4f}\t{kind}\tla\n')


if __name__ == '__main__':
    cmd, led, mark = sys.argv[1], sys.argv[2], sys.argv[3]
    if cmd == 'check':
        cap, tot = float(sys.argv[4]), float(sys.argv[5])
        ensure_mark(led, mark, f'la lab Claude runs cl-*: USD 0.15 S / 0.20 T per run, USD {tot:.2f} total')
        ok = allowed(led, mark, cap, tot)
        print(f'la spend ${total(led, mark):.4f}; this run up to ${cap:.2f}; cap ${tot:.2f}: {"GO" if ok else "STOP"}')
        sys.exit(0 if ok else 2)
    if cmd == 'record':
        c = cost(sys.argv[5])
        record(led, sys.argv[4], c, float(sys.argv[6]))
        print(f'cost {c if c is not None else "none (killed: counted at cap)"}; la total ${total(led, mark):.4f}')
