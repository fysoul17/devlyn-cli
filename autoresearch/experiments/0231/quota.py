"""Classify shared account-limit faults from native error fields only: quota.py <cell-out>.

Claude: a result with is_error and api_error_status 429, or an assistant event whose error is rate_limit (0224's
weekly limit had exactly this shape). Codex: an error event, error item or rollout error message whose own error text
names a usage or rate limit. Model prose is never read: only these structured fields count.
"""
import json
from pathlib import Path
import re
import sys

LIMIT = re.compile(r'usage limit|rate limit|usage_limit|rate_limit|\b429\b', re.I)


def objects(path):
    """JSON objects in a file: one per line, or the whole file as one object."""
    text = path.read_text(errors='replace')
    try:
        whole = json.loads(text)
        return [whole] if isinstance(whole, dict) else []
    except ValueError:
        pass
    found = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            found.append(value)
    return found


def hit(event):
    if event.get('type') == 'result' and event.get('is_error') is True and event.get('api_error_status') == 429:
        return 'claude 429 result'
    if event.get('type') == 'assistant' and event.get('error') == 'rate_limit':
        return 'claude rate_limit'
    if event.get('type') == 'error' and LIMIT.search(str(event.get('message', ''))):
        return 'codex error event'
    item = event.get('item') if isinstance(event.get('item'), dict) else {}
    if item.get('type') == 'error' and LIMIT.search(str(item.get('message', ''))):
        return 'codex error item'
    payload = event.get('payload') if isinstance(event.get('payload'), dict) else {}
    if event.get('type') == 'event_msg' and payload.get('type') == 'error' and LIMIT.search(json.dumps(payload)):
        return 'codex rollout error'
    return None


def scan(paths, root):
    hits = []
    for path in paths:
        for event in objects(path):
            kind = hit(event)
            if kind:
                hits.append(dict(kind=kind, path=str(path.relative_to(root))))
    return hits


def classify(out):
    execution = [out / 'run/stdout', *(out / 'home/.codex/sessions').rglob('*.jsonl'),
                 *(out / 'home/.claude/projects').rglob('*.jsonl')]
    for name in ('cell', 'tmp', 'home'):
        for devlyn in (out / name).rglob('.devlyn'):
            execution += [p for p in devlyn.rglob('*') if p.is_file() and p.suffix in ('.json', '.jsonl', '.stdout', '.stderr')]
    assessment = sorted((out / 'assessment').glob('*/stdout'))
    return dict(execution=scan(sorted(set(p for p in execution if p.is_file())), out), assessment=scan(assessment, out))


if __name__ == '__main__':
    print(json.dumps(classify(Path(sys.argv[1]).resolve()), indent=2))
