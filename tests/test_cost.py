"""la Claude runs: cost from stream.jsonl + the stage ledger (PREREG: --max-budget-usd 0.15 S / 0.20 T, stage cap $0.50).
python -m pytest tests  from the repo root (gemma4-lab-runner:1)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lab'))
import la_cost as C  # noqa: E402

MARK = '# --- GO 23 Nov 2026 la'


def _stream(tmp_path, events):
    p = tmp_path / 'stream.jsonl'
    p.write_text('\n'.join(json.dumps(e) for e in events) + '\n')
    return str(p)


def test_cost_from_the_result_event(tmp_path):
    s = _stream(tmp_path, [{'type': 'system', 'subtype': 'init'},
                           {'type': 'result', 'subtype': 'success', 'total_cost_usd': 0.0731}])
    assert C.cost(s) == 0.0731


def test_cost_missing_when_killed(tmp_path):
    s = _stream(tmp_path, [{'type': 'system', 'subtype': 'init'}, {'type': 'assistant', 'message': {}}])
    assert C.cost(s) is None
    assert C.cost(str(tmp_path / 'none.jsonl')) is None


def test_ledger_counts_only_rows_below_the_la_mark(tmp_path):
    led = tmp_path / 'BUDGET.tsv'
    led.write_text('sc14-A1\t0.2100\tlogged\tsc14\n' + MARK + ' (la)\n' + 'cl-sc-S-1\t0.0500\tlogged\tla\n')
    assert C.total(str(led), MARK) == 0.05


def test_check_allows_only_while_spent_plus_run_cap_fits(tmp_path):
    led = tmp_path / 'BUDGET.tsv'
    led.write_text(MARK + '\n')
    assert C.allowed(str(led), MARK, 0.15, 0.50)
    led.write_text(MARK + '\ncl-sc-S-1\t0.1500\tlogged\tla\ncl-fc-S-1\t0.1500\tlogged\tla\n')
    assert C.allowed(str(led), MARK, 0.20, 0.50)          # 0.30 + 0.20 = 0.50: fits
    led.write_text(MARK + '\ncl-sc-S-1\t0.1600\tlogged\tla\ncl-fc-S-1\t0.1500\tlogged\tla\n')
    assert not C.allowed(str(led), MARK, 0.20, 0.50)      # 0.31 + 0.20 > 0.50


def test_record_writes_a_row_and_a_killed_run_counts_at_its_cap(tmp_path):
    led = tmp_path / 'BUDGET.tsv'
    led.write_text(MARK + '\n')
    C.record(str(led), 'cl-sc-S-1', 0.0412, 0.15)
    C.record(str(led), 'cl-sc-T-1', None, 0.20)
    rows = led.read_text().splitlines()[1:]
    assert rows == ['cl-sc-S-1\t0.0412\tlogged\tla', 'cl-sc-T-1\t0.2000\tkilled-floor\tla']
    assert C.total(str(led), MARK) == 0.2412


def test_mark_line_added_once(tmp_path):
    led = tmp_path / 'BUDGET.tsv'
    led.write_text('old\t0.1\tlogged\tx\n')
    C.ensure_mark(str(led), MARK, 'la lab Claude runs')
    C.ensure_mark(str(led), MARK, 'la lab Claude runs')
    assert led.read_text().count(MARK) == 1
