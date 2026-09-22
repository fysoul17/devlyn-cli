"""Apply the prospectively fixed three-session preflight predicate to retained evidence."""
import json
from pathlib import Path
import sys


def verify(directory):
    result = json.loads((directory / 'run/result.json').read_text())
    if result['failure'] or result['classes'] or not result['container_removed']:
        raise ValueError('transport/accounting/teardown did not finish cleanly')
    terminal = result['terminal']
    if (terminal['native']['sessions'] != 2 or terminal['native']['dispatches'] != 2 or
            terminal['reviews']['calls'] != 1 or terminal['combined']['calls'] != 3):
        raise ValueError('missing or extra required native child/reviewer')
    metadata = []
    for path in (directory / 'home/.codex/sessions').rglob('*.jsonl'):
        first = json.loads(path.read_text().split('\n')[0])
        if first['type'] != 'session_meta': raise ValueError('missing initial metadata')
        metadata.append(first['payload'])
    owners = [m for m in metadata if m['source'] == 'exec']
    children = [m for m in metadata if isinstance(m['source'], dict)]
    if (len(owners) != 1 or len(children) != 1 or
            children[0]['source']['subagent']['thread_spawn']['parent_thread_id'] != owners[0]['id']):
        raise ValueError('not one fresh owner plus one direct native child')
    answer = directory / 'work/.devlyn/reviews/call-1/answer.txt'
    if not answer.is_file() or not answer.read_text().strip():
        raise ValueError('missing completed static review')
    checks = json.loads((directory / 'external-checks.json').read_text())
    if checks['exit_code'] != 0 or not checks['argv'] or 'stdout' not in checks or 'stderr' not in checks:
        raise ValueError('missing successful external unit/function checks')
    import hashlib
    for name, digest in checks['source_sha256'].items():
        if hashlib.sha256((directory / 'work' / name).read_bytes()).hexdigest() != digest:
            raise ValueError('source changed after external checks')
    if not list((directory / 'work/.devlyn/checks-final').rglob('*')):
        raise ValueError('owner supplied no check evidence')
    return {'native_sessions': 2, 'reviews': 1, 'calls': 3,
            'native_model_effort': 'gpt-6-astra/high validated by native_cell turn_context',
            'review_requested': 'claude-fable-5-1/medium; provider-internal effort not attested',
            'reported_usage': terminal['combined'],
            'remaining': 'Root must inspect source/scope and independent test/review evidence.'}


if __name__ == '__main__':
    print(json.dumps(verify(Path(sys.argv[1])), indent=2))
