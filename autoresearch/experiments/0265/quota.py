"""0233 shared account classifier with 0259's retry-only authentication shape."""
import importlib.util
import json
from pathlib import Path
import sys


PRIOR = Path(__file__).resolve().parent.parent / '0233/quota.py'
spec = importlib.util.spec_from_file_location('quota0233', PRIOR)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def scan(paths, root):
    hits = []
    for path in paths:
        if path.suffix == '.stderr' or path.name == 'stderr':
            found = prior.stderr_hits(path)
        else:
            found = []
            last_retry_status = None
            for event in prior.objects(path):
                if event.get('type') == 'system' and event.get('subtype') == 'api_retry':
                    last_retry_status = event.get('error_status')
                original = prior.hit(event)
                if original:
                    found.append(original)
                elif (event.get('type') == 'result' and event.get('is_error') is True
                      and event.get('terminal_reason') == 'api_error'
                      and event.get('api_error_status') is None
                      and last_retry_status in (401, 403)):
                    found.append(('auth', 'claude authentication retry'))
                if event.get('type') == 'result' or (event.get('type') == 'assistant'
                    and (not isinstance(event.get('message'), dict)
                         or event['message'].get('model') != '<synthetic>')):
                    last_retry_status = None
        hits.extend(dict(fault=fault, kind=kind, path=str(path.relative_to(root)))
                    for fault, kind in found)
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
