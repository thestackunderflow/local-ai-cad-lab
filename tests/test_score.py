"""la scorer tests (PREREG.md pass rules): run with  python -m pytest tests  from the repo root."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lab'))
import la_score as L  # noqa: E402


def body(dx, dy, dz, vol, name='Body1'):
    return {'name': name, 'volume_mm3': vol, 'bbox': {'min': [0, 0, 0], 'max': [dx, dy, dz]}}


def test_s_solidcraft_pass_any_orientation():
    m = {'measure': {'body_count': 1, 'bodies': [body(20, 60, 5, 6000.0)], 'total': {'volume_mm3': 6000.0}}}
    assert L.s_solidcraft(m)['pass'] is True


def test_s_solidcraft_fails_wrong_size_or_two_bodies():
    m = {'measure': {'body_count': 1, 'bodies': [body(60, 20, 6, 7200.0)]}}
    assert L.s_solidcraft(m)['pass'] is False
    m2 = {'measure': {'body_count': 2, 'bodies': [body(60, 20, 5, 6000.0), body(1, 1, 1, 1.0, 'B2')]}}
    assert L.s_solidcraft(m2)['pass'] is False
    assert L.s_solidcraft({'measure': {'body_count': 0, 'bodies': []}})['pass'] is False


def test_s_freecad_one_solid_across_documents():
    docs = [{'solids': [{'name': 'Box', 'dims': [60, 20, 5], 'volume': 6000.0}]}, {'solids': []}]
    assert L.s_freecad(docs)['pass'] is True
    docs.append({'solids': [{'name': 'Pad', 'dims': [5, 20, 60], 'volume': 6000.0}]})
    assert L.s_freecad(docs)['pass'] is False      # two solids shown: not one block
    assert L.s_freecad([{'solids': [{'name': 'Box', 'dims': [60, 20, 5], 'volume': 6001.5}]}])['pass'] is False


def test_t_solidcraft_needs_both_walls():
    s = {'wall2': {'score': {'pass': True}}, 'wall3': {'score': {'pass': False}}}
    assert L.t_solidcraft(s)['pass'] is False
    s['wall3']['score']['pass'] = True
    assert L.t_solidcraft(s)['pass'] is True
    assert L.t_solidcraft(None)['pass'] is False


def test_t_freecad_uses_lesson14_check():
    assert L.t_freecad({'pass': True, 'criteria': {}})['pass'] is True
    assert L.t_freecad(None)['pass'] is False


def stream(*events):
    return [json.dumps(e) for e in events]


def test_stream_tool_calls_and_result():
    lines = stream(
        {'type': 'system', 'subtype': 'init', 'tools': ['Bash', 'mcp__solidcraft__execute']},
        {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'mcp__solidcraft__execute', 'input': {}}]}},
        {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'is_error': True, 'content': 'bad'}]}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'The volume is 6,000 mm³.'}]}},
        {'type': 'result', 'subtype': 'success', 'num_turns': 3, 'result': 'The volume is 6,000 mm³.',
         'usage': {'input_tokens': 9000, 'output_tokens': 50}})
    r = L.read_stream(lines)
    assert r['tool_calls'] == {'mcp__solidcraft__execute': 1}
    assert r['tool_errors'] == 1
    assert r['subtype'] == 'success'
    assert L.said_volume(r['final_text']) == 6000.0


def test_classes_auto():
    assert L.auto_class({'tool_calls': {}}, {'timeout': False}, 0) == '(12)'
    assert L.auto_class({'tool_calls': {'x': 1}, 'subtype': 'error_max_turns'}, {'timeout': False}, 0) == '(14)'
    assert L.auto_class({'tool_calls': {'x': 1}, 'subtype': 'success'}, {'timeout': True}, 0) == '(14)'
    assert L.auto_class({'tool_calls': {'x': 1}, 'subtype': 'success'}, {'timeout': False}, 2) == '(15)'
    assert L.auto_class({'tool_calls': {'x': 1}, 'subtype': 'success'}, {'timeout': False}, 0) is None


def test_prompts_match_lesson14_b1():
    b1 = open(os.path.join(os.path.dirname(__file__), '..', 'lab', 'la_common.sh'), encoding='utf-8').read()
    assert ("My wall cup's key peg should be a solid 10 by 10 peg, but after the shell it came out hollow and bigger, open "
            "into the cup. Fix it so the peg stays solid and 10 wide when I change the wall thickness. Then check the peg "
            "and the front wall and tell me what you find.") in b1
    assert 'Make a block 60 mm long, 20 mm wide and 5 mm thick, then tell me its volume.' in b1
