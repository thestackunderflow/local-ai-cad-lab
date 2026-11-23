"""la_throughput tests (PLAN la 0, host-fault void rule): python -m pytest tests  from the repo root."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lab'))
import la_throughput as T  # noqa: E402

FAST = """time=2026-11-23T01:00:00.000Z level=DEBUG source=llama_server.go:1717 msg="llama-server completion request" media=0 prompt_len=1000
srv        update:  - cache state: 2 prompts, 3995.653 MiB (limits: 8192.000 MiB, 65536 tokens, 1 est)
slot   operator(): id  0 | task 1 | new prompt, n_ctx_slot = 65536, n_keep = 4, task.n_tokens = 20000
slot print_timing: id  0 | task 1 | prompt eval time =    2000.00 ms /   100 tokens (   20.00 ms per token,    50.00 tokens per second)
slot print_timing: id  0 | task 1 |        eval time =   10000.00 ms /   120 tokens (   83.33 ms per token,    12.00 tokens per second)
slot      release: id  0 | task 1 | stop processing: n_tokens = 20119, truncated = 0
[GIN] 2026/11/23 - 01:00:12 | 200 |     12s |     10.231.77.3 | POST     "/v1/messages?beta=true"
"""
SLOW_OPEN = """time=2026-11-23T01:01:00.000Z level=DEBUG source=llama_server.go:1717 msg="llama-server completion request" media=0 prompt_len=1000
srv        update:  - cache state: 5 prompts, 6505.333 MiB (limits: 8192.000 MiB, 65536 tokens, 1 est)
slot   operator(): id  0 | task 2 | new prompt, n_ctx_slot = 65536, n_keep = 4, task.n_tokens = 30000
[GIN] 2026/11/23 - 01:21:00 | 200 |    20m0s |     10.231.77.3 | POST     "/v1/messages?beta=true"
slot      release: id  0 | task 2 | stop processing: n_tokens = 30300, truncated = 0
"""


def test_parse_fast_request():
    r = T.parse(FAST.splitlines())
    assert len(r) == 1
    assert r[0]['prompt_tokens'] == 20000 and r[0]['decoded'] == 120
    assert abs(r[0]['write_tok_s'] - 12.0) < 0.01 and r[0]['degraded'] is False
    assert r[0]['cache_mib'] == 3995.653


def test_open_request_rate_from_wall_and_n_tokens():
    r = T.parse(SLOW_OPEN.splitlines())
    assert r[0]['decoded'] == 300 and r[0]['wall_s'] == 1200
    assert r[0]['write_tok_s'] < 3 and r[0]['degraded'] is True


def test_void_rule_any_degraded_request_before_the_cap():
    reqs = T.parse((FAST + SLOW_OPEN).splitlines())
    v = T.verdict(reqs, '2026-11-23T00:59:00Z')
    assert v['void'] is True and v['first_degraded_min'] == 2.0
    assert T.verdict(T.parse(FAST.splitlines()), '2026-11-23T00:59:00Z')['void'] is False
