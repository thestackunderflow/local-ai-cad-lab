"""Harness fix tests (HANDOVER-la-lab2 section 1): python -m pytest tests  from the repo root (gemma4-lab-runner:1).

1a ollama_up.sh passes LLAMA_ARG_CACHE_RAM=0 + LLAMA_ARG_CTX_CHECKPOINTS=4 to la-ollama (prompt cache off, 4 SWA
   checkpoints) so the 6 GB container does not thrash; fix_check() reads the live log to prove llama-server took them.
1b la_restart.sh (called by run/one.sh) re-creates la-ollama + a 1-token warm-up only when OLLAMA_RESTART=1;
   void_line() turns throughput.json into the "VOID host fault" suffix of the LA line.
Shell scripts run against stub docker/curl on PATH that record their arguments.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'lab'))
import la_throughput as T  # noqa: E402

STUB = """#!/usr/bin/env bash
echo "$(basename "$0") $*" >> "$STUB_LOG"
case "$(basename "$0") $1" in
  "curl "*) echo "Ollama is running"; echo '{"version":"0.40.17"}' ;;
  "docker logs") cat "$STUB_OLLAMA_LOG" 2>/dev/null ;;
esac
exit 0
"""


@pytest.fixture
def stubs(tmp_path):
    b = tmp_path / 'bin'
    b.mkdir()
    for n in ('docker', 'curl', 'sleep'):
        p = b / n
        p.write_text(STUB)
        p.chmod(0o755)
    log = tmp_path / 'calls.log'
    env = dict(os.environ, PATH=f"{b}:{os.environ['PATH']}", STUB_LOG=str(log),
               STUB_OLLAMA_LOG=str(tmp_path / 'ollama.txt'), LA_PY='python3')
    return env, log, tmp_path


def _calls(log):
    return log.read_text().splitlines() if log.exists() else []


def test_ollama_up_passes_cache_off_and_4_checkpoints(stubs):
    env, log, _ = stubs
    r = subprocess.run(['bash', 'lab/ollama_up.sh', '65536', 'q8_0', '6g'], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    run = [c for c in _calls(log) if c.startswith('docker run') and 'la-ollama' in c]
    assert len(run) == 1
    assert '-e LLAMA_ARG_CACHE_RAM=0' in run[0] and '-e LLAMA_ARG_CTX_CHECKPOINTS=4' in run[0]
    assert '--memory 6g' in run[0] and '-e OLLAMA_CONTEXT_LENGTH=65536' in run[0]


def test_restart_is_a_noop_without_the_flag(stubs, tmp_path):
    env, log, _ = stubs
    env.pop('OLLAMA_RESTART', None)
    r = subprocess.run(['bash', 'lab/la_restart.sh', 'gemma4:12b-it-qat', str(tmp_path / 'o')], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert _calls(log) == []


def test_restart_recreates_ollama_then_warms_the_model(stubs, tmp_path):
    env, log, _ = stubs
    env.update(OLLAMA_RESTART='1', CTX='65536')
    (tmp_path / 'ollama.txt').write_text('srv  update:  - cache state: 0 prompts, 0.000 MiB (limits: 0.000 MiB, '
                                         '65536 tokens, 1 est)\n')
    o = tmp_path / 'o'
    o.mkdir()
    r = subprocess.run(['bash', 'lab/la_restart.sh', 'gemma4:12b-it-qat', str(o)], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    c = _calls(log)
    rm = next(i for i, x in enumerate(c) if x.startswith('docker rm -f la-ollama'))
    run = next(i for i, x in enumerate(c) if x.startswith('docker run') and 'la-ollama' in x)
    warm = next(i for i, x in enumerate(c) if x.startswith('curl') and '/api/generate' in x)
    assert rm < run < warm
    assert '--memory 6g' in c[run] and 'OLLAMA_KV_CACHE_TYPE=q8_0' in c[run]
    assert '"model":"gemma4:12b-it-qat"' in c[warm] and '"num_predict":1' in c[warm]
    fix = json.loads((o / 'ollama-fix.json').read_text())
    assert fix['status'] == 'forwarded'


def test_restart_memory_for_the_26b(stubs, tmp_path):
    env, log, _ = stubs
    env.update(OLLAMA_RESTART='1', OLLAMA_MEM='16g')
    o = tmp_path / 'o'
    o.mkdir()
    subprocess.run(['bash', 'lab/la_restart.sh', 'gemma4:26b', str(o)], cwd=ROOT, env=env, capture_output=True)
    run = [x for x in _calls(log) if x.startswith('docker run') and 'la-ollama' in x]
    assert '--memory 16g' in run[0]


# --- fix_check: did llama-server take the env? (live log of la-ollama after the warm-up) ---
OLD = """srv        update:  - cache state: 2 prompts, 3995.653 MiB (limits: 8192.000 MiB, 65536 tokens, 1 est)
slot update_slots: id  0 | task 9 | created context checkpoint 3 of 32 (pos_min = 1, pos_max = 2, size = 170.0 MiB)
"""
NEW = """srv        update:  - cache state: 1 prompts, 12.000 MiB (limits: 0.000 MiB, 65536 tokens, 1 est)
slot update_slots: id  0 | task 9 | created context checkpoint 2 of 4 (pos_min = 1, pos_max = 2, size = 170.0 MiB)
"""


def test_fix_check_old_defaults_not_forwarded():
    f = T.fix_check(OLD.splitlines())
    assert f == {'cache_limit_mib': 8192.0, 'checkpoints_max': 32, 'status': 'not_forwarded'}


def test_fix_check_new_values_forwarded():
    f = T.fix_check(NEW.splitlines())
    assert f['cache_limit_mib'] == 0.0 and f['checkpoints_max'] == 4 and f['status'] == 'forwarded'


def test_fix_check_cache_disabled_means_no_cache_lines():
    f = T.fix_check(['created context checkpoint 1 of 4 (x)'])
    assert f['cache_limit_mib'] is None and f['status'] == 'forwarded'


def test_fix_check_nothing_seen_is_unknown():
    assert T.fix_check(['nothing here'])['status'] == 'unknown'


def test_fix_check_explicit_cli_flag_from_runner_command():
    # if Ollama passes --cache-ram itself, the env var is ignored by llama-server
    f = T.fix_check(['msg="starting runner" cmd="/usr/lib/ollama/llama-server --model x --cache-ram 8192 --port 1"'])
    assert f['status'] == 'not_forwarded'


# --- void_line: LA line suffix from throughput.json ---
def test_void_line_only_when_void():
    ok = {'12-sc-T-1r': {'void': False, 'first_degraded_min': None, 'degraded_requests': 0, 'requests': 9}}
    bad = {'12-sc-T-1r': {'void': True, 'first_degraded_min': 7.5, 'degraded_requests': 3, 'requests': 9}}
    assert T.void_line(ok) == ''
    assert T.void_line(bad) == 'VOID host fault (first < 3 tok/s at 7.5 min, 3 of 9 requests)'
