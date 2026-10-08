"""Freeze the 0236 continuation messages (registration §3): messages.py <0235 output dir>. No model runs here.

G is the generic repair request. F is the same text, then "The reviewers' findings:" and each original assessor's
`findings` array, in the 0235 assessor order, cut verbatim from that assessor's raw answer in assessment/<engine>/stdout
(the normalized result.json keeps only severe findings). Writes messages/G.txt and messages/<unit>-F.txt; each file's
bytes are the exact message.
"""
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('assess0236m', HERE.parent / '0235/assess.py')
assess = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assess)
GENERIC = ('At least one independent reviewer judged this work incomplete. Re-verify every requirement, required failure '
           'behavior and compatibility contract in the original request against the code and tests; fix what is real, '
           'verify it, and report.')
FINDINGS = "The reviewers' findings:"
ENGINES = tuple(route['engine'] for route in assess.TASKS['assessors'])
UNITS = ('r01-D3-claude-B-r1', 'r03-D4-claude-R-r1', 'r04-D4-claude-B-r1', 'r08-D4-claude-R-r2')


def answer(stdout, engine):
    """The assessor's final answer text, read exactly as 0235 assess.one reads it."""
    stream = assess.events(stdout)
    if engine == 'claude':
        texts = [e.get('result') for e in stream if e.get('type') == 'result']
    else:
        texts = [e['item'].get('text') for e in stream
                 if e.get('type') == 'item.completed' and e['item'].get('type') == 'agent_message']
    if not texts or not isinstance(texts[-1], str):
        raise ValueError(f'{stdout}: no final answer')
    return texts[-1]


def findings_text(text):
    """The `findings` array of a valid assessor answer, as the exact substring of the answer."""
    parsed = assess.valid(text)
    if parsed is None:
        raise ValueError('not a valid assessor verdict')
    decoder = json.JSONDecoder()
    for match in re.finditer(r'"findings"\s*:\s*', text):
        try:
            value, end = decoder.raw_decode(text, match.end())
        except ValueError:
            continue
        if value == parsed['findings']:
            return text[match.end():end]
    raise ValueError('findings array not found verbatim in the answer')


def message(source_output, unit, arm):
    if arm == 'G':
        return GENERIC
    if arm != 'F':
        raise ValueError(f'unknown arm {arm}')
    blocks = [f'Reviewer {index}:\n' + findings_text(answer(Path(source_output) / unit / 'assessment' / engine / 'stdout', engine))
              for index, engine in enumerate(ENGINES, 1)]
    return GENERIC + '\n\n' + FINDINGS + '\n\n' + '\n\n'.join(blocks)


def frozen(arm, unit):
    return HERE / 'messages' / ('G.txt' if arm == 'G' else f'{unit}-F.txt')


def generate(source_output):
    return {frozen('G', None).name: message(source_output, None, 'G')} | {
        frozen('F', unit).name: message(source_output, unit, 'F') for unit in UNITS}


if __name__ == '__main__':
    for name, text in generate(sys.argv[1]).items():
        (HERE / 'messages' / name).write_text(text)
