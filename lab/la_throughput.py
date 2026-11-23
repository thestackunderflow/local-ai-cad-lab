"""Per-request Ollama throughput for one la run, and the host-fault void rule (PLAN la section 0, 23 Nov 2026).

Why: in the 12B T runs the same model on the same GPU wrote 10-12 tok/s, then dropped to 0.2-0.5 tok/s (prefill too)
whenever llama-server's host-RAM prompt cache (--cache-ram default 8192 MiB) grew past ~5.4 GB inside the 6 GB
la-ollama container, which also holds the mmapped CPU-layer weights. A run is VOID (host fault, re-run once) if any
request before the cap writes < 3 tok/s. Usage: python lab/la_throughput.py out/runs/RUN [...]  -> JSON on stdout.
"""
import json
import re
import sys
from datetime import datetime, timezone

DEGRADED_TOK_S = 3.0   # the 12B's normal write speed here is 10-12 tok/s (G3: 8.2 at a 31.5K prompt)

_REQ = re.compile(r'time=(\S+) .*completion request.*prompt_len=(\d+)')
_CACHE = re.compile(r'cache state: (\d+) prompts, ([\d.]+) MiB')
_NEW = re.compile(r'new prompt.*task\.n_tokens = (\d+)')
_PE = re.compile(r'prompt eval time =\s+([\d.]+) ms /\s+(\d+) tokens')
_EV = re.compile(r'\s eval time =\s+([\d.]+) ms /\s+(\d+) tokens')
_GIN = re.compile(r'\[GIN\] \S+ - \S+ \| \d+ \|\s+(\S+)')
_END = re.compile(r'stop processing: n_tokens = (\d+)')


def _dur_s(s):
    """Gin durations: 12s, 4.26s, 1m0s, 23m0s, 850ms."""
    if s.endswith('ms') and 'm' not in s[:-2]:
        return float(s[:-2]) / 1000
    m = re.fullmatch(r'(?:(\d+)h)?(?:(\d+)m)?(?:([\d.]+)s)?', s)
    if not m:
        return None
    h, mi, se = m.groups()
    return int(h or 0) * 3600 + int(mi or 0) * 60 + float(se or 0)


def parse(lines):
    out, cur = [], None
    for ln in lines:
        m = _REQ.search(ln)
        if m:
            cur = {'start': m.group(1), 'prompt_tokens': None, 'decoded': None, 'write_tok_s': None, 'wall_s': None,
                   'prefill_s': None, 'cache_mib': None}
            continue
        if cur is None:
            continue
        if (m := _CACHE.search(ln)):
            cur['cache_mib'] = float(m.group(2))
        elif (m := _NEW.search(ln)):
            cur['prompt_tokens'] = int(m.group(1))
        elif (m := _PE.search(ln)):
            cur['prefill_s'] = round(float(m.group(1)) / 1000, 1)
        elif (m := _EV.search(ln)):
            cur['decoded'] = int(m.group(2))
            cur['write_tok_s'] = round(int(m.group(2)) / (float(m.group(1)) / 1000), 2)
        elif (m := _GIN.search(ln)):
            cur['wall_s'] = _dur_s(m.group(1))
        elif (m := _END.search(ln)):
            if cur['decoded'] is None and cur['prompt_tokens'] is not None and cur['wall_s']:
                # request cut by the cap: no timing line; rate = tokens written / time open
                cur['decoded'] = int(m.group(1)) - cur['prompt_tokens']
                cur['cut_by_cap'] = True
                if cur['decoded'] < 0:
                    # cut while still reading the prompt (n_tokens = prompt read so far): no write rate to judge
                    cur['decoded'], cur['cut_in_prefill'] = 0, True
                else:
                    cur['write_tok_s'] = round(cur['decoded'] / cur['wall_s'], 2)
            cur['degraded'] = cur['write_tok_s'] is not None and cur['write_tok_s'] < DEGRADED_TOK_S
            out.append(cur)
            cur = None
    return out


def _t(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)


def verdict(reqs, claude_start):
    t0 = _t(claude_start)
    bad = [r for r in reqs if r.get('degraded')]
    first = round((_t(bad[0]['start']) - t0).total_seconds() / 60, 1) if bad else None
    ok = [r['write_tok_s'] for r in reqs if r['write_tok_s'] is not None and not r.get('degraded')]
    return {'void': bool(bad), 'first_degraded_min': first, 'degraded_requests': len(bad), 'requests': len(reqs),
            'normal_write_tok_s': [min(ok), max(ok)] if ok else None,
            'max_cache_mib': max([r['cache_mib'] for r in reqs if r['cache_mib']] or [0])}


_LIMIT = re.compile(r'limits: ([\d.]+) MiB')
_CKPT = re.compile(r'checkpoint \d+ of (\d+)')
_CLI_CACHE = re.compile(r'--cache-ram[ =](-?\d+)')


def fix_check(lines):
    """Did llama-server take LLAMA_ARG_CACHE_RAM=0 / LLAMA_ARG_CTX_CHECKPOINTS=4 (HANDOVER-la-lab2 1a)?
    forwarded = cache limit 0 (or no cache lines) with 4 checkpoints, or limit 0; not_forwarded = the 8192 MiB / 32
    defaults or an explicit --cache-ram on the runner command (an explicit flag beats the env var)."""
    lim, ck, cli = None, None, None
    for ln in lines:
        if (m := _LIMIT.search(ln)):
            lim = float(m.group(1))
        if (m := _CKPT.search(ln)):
            ck = int(m.group(1))
        if (m := _CLI_CACHE.search(ln)):
            cli = int(m.group(1))
    if (cli is not None and cli != 0) or (lim is not None and lim > 0) or (ck is not None and ck != 4):
        st = 'not_forwarded'
    elif lim == 0 or ck == 4 or cli == 0:
        st = 'forwarded'
    else:
        st = 'unknown'
    return {'cache_limit_mib': lim, 'checkpoints_max': ck, 'status': st}


def void_line(res):
    """Suffix for the LA line when a run is void by the host-fault rule; '' otherwise."""
    for v in res.values():
        if v.get('void'):
            return (f"VOID host fault (first < {DEGRADED_TOK_S:g} tok/s at {v['first_degraded_min']} min, "
                    f"{v['degraded_requests']} of {v['requests']} requests)")
    return ''


def main(runs):
    res = {}
    for o in runs:
        ev = [json.loads(x) for x in open(o + '/events.jsonl', encoding='utf-8')]
        start = next(e['t'] for e in ev if e['ev'] == 'claude start')
        reqs = parse(open(o + '/ollama.log', encoding='utf-8', errors='replace'))
        res[o.rstrip('/').split('/')[-1]] = dict(verdict(reqs, start), per_request=reqs)
    json.dump(res, sys.stdout, indent=1)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--fix-check']:      # la_restart.sh: live la-ollama log after the warm-up
        print(json.dumps(fix_check(open(sys.argv[2], encoding='utf-8', errors='replace'))))
    elif sys.argv[1:2] == ['--void-line']:    # run/one.sh: throughput.json -> LA line suffix
        print(void_line(json.load(open(sys.argv[2], encoding='utf-8'))))
    else:
        main(sys.argv[1:])
