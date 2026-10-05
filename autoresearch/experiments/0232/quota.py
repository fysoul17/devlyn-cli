"""Classify shared account faults from native error fields only: quota.py <cell-out>.

Account limit: a Claude result with is_error, api_error_status 429 and the CLI's own limit message (0224's weekly
limit had exactly this shape), or a Codex error naming its usage limit. Authentication: a Claude result with
api_error_status 401/403, or a Codex error naming an expired or missing login. Plain-mode Codex stderr lines that
start with "ERROR:" are read too, as are the raw stdout and stderr of review launcher calls. Model prose is never
read, and a bare status code never counts.
"""
import json
from pathlib import Path
import re
import sys

CLAUDE_LIMIT = re.compile(r"hit your (weekly|session|usage|5-hour|opus) limit|usage limit reached", re.I)
CODEX_LIMIT = re.compile(r"hit your usage limit|usage_limit_reached|usage limit has been reached", re.I)
CODEX_AUTH = re.compile(r"401 Unauthorized|token_expired|refresh_token_reused|not logged in|please log in again", re.I)


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
    if event.get('type') == 'result' and event.get('is_error') is True:
        if event.get('api_error_status') == 429 and CLAUDE_LIMIT.search(str(event.get('result', ''))):
            return 'limit', 'claude limit result'
        if event.get('api_error_status') in (401, 403):
            return 'auth', 'claude authentication result'
    item = event.get('item') if isinstance(event.get('item'), dict) else {}
    payload = event.get('payload') if isinstance(event.get('payload'), dict) else {}
    for message in (str(event.get('message', '')) if event.get('type') == 'error' else '',
                    str(item.get('message', '')) if item.get('type') == 'error' else '',
                    json.dumps(payload) if event.get('type') == 'event_msg' and payload.get('type') == 'error' else ''):
        if CODEX_LIMIT.search(message):
            return 'limit', 'codex usage limit'
        if CODEX_AUTH.search(message):
            return 'auth', 'codex authentication'
    return None


def stderr_hits(path):
    hits = []
    for line in path.read_text(errors='replace').splitlines():
        if line.startswith('ERROR:'):
            if CODEX_LIMIT.search(line):
                hits.append(('limit', 'codex usage limit (stderr)'))
            elif CODEX_AUTH.search(line):
                hits.append(('auth', 'codex authentication (stderr)'))
    return hits


def scan(paths, root):
    hits = []
    for path in paths:
        found = (stderr_hits(path) if path.suffix == '.stderr' or path.name == 'stderr'
                 else [h for h in map(hit, objects(path)) if h])
        hits += [dict(fault=fault, kind=kind, path=str(path.relative_to(root))) for fault, kind in found]
    return hits


def classify(out):
    execution = [out / 'run/stdout', *(out / 'home/.codex/sessions').rglob('*.jsonl'),
                 *(out / 'home/.claude/projects').rglob('*.jsonl'), *(out / 'home/.devlyn/reviews').glob('*/stdout'),
                 *(out / 'home/.devlyn/reviews').glob('*/stderr')]
    for name in ('cell', 'tmp', 'home'):
        for devlyn in (out / name).rglob('.devlyn'):
            execution += [p for p in devlyn.rglob('*') if p.is_file() and p.suffix in ('.json', '.jsonl', '.stdout', '.stderr')]
    assessment = sorted((out / 'assessment').glob('*/stdout'))
    return dict(execution=scan(sorted(set(p for p in execution if p.is_file())), out), assessment=scan(assessment, out))


if __name__ == '__main__':
    print(json.dumps(classify(Path(sys.argv[1]).resolve()), indent=2))
