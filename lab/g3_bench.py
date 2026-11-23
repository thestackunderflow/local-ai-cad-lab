"""G3 speed probe (no Claude Code): one /api/generate on la-ollama with a synthetic prompt of about N tokens (the G2
"both plugs" page size), 200 tokens written; prints prompt tokens, prefill tok/s, write tok/s.
    python lab/g3_bench.py N OUT.json   (host python, stdlib only; Ollama on 127.0.0.1:11434)"""
import json
import sys
import time
import urllib.request

n, out = int(sys.argv[1]), sys.argv[2]
words = ('The cup has a peg on the front wall and the shell makes the walls two millimetres thick. ' * (n // 18 + 1))
body = {'model': 'gemma4:12b-it-qat', 'prompt': words + '\nSummarise the text above in three sentences.',
        'stream': False, 'options': {'num_predict': 200}, 'keep_alive': '30m'}
t = time.time()
r = json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434/api/generate',
                                                            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}), timeout=1800))
res = {'prompt_tokens': r.get('prompt_eval_count'), 'prefill_tok_s': round(r['prompt_eval_count'] / (r['prompt_eval_duration'] / 1e9), 1),
       'written': r.get('eval_count'), 'write_tok_s': round(r['eval_count'] / (r['eval_duration'] / 1e9), 1),
       'load_s': round(r.get('load_duration', 0) / 1e9, 1), 'wall_s': round(time.time() - t, 1)}
json.dump(res, open(out, 'w'))
print(json.dumps(res))
