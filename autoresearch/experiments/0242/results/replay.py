"""Read-only prospective policy component on retained 0241; not a regrade."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runner0242_replay', HERE / 'runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


if __name__ == '__main__':
    staged = Path('/Users/aipalm/.local/share/nx01/0241-live/staged-v3')
    out = staged / 'out-smoke/s01-h-codex'
    app = r.Runner(staged / 'runtime-smoke.json')
    protected = [out / name for name in ('run/stdout', 'run/stderr', 'plan.json', 'usage.json',
                                        'peer-policy.json', 'claude-accounting.json', 'evidence-manifest.json')]
    protected.append(out.parent / ('verdict-' + out.name + '.json'))
    before = {str(path): r.digest(path) for path in protected if path.is_file()}
    evidence = app.frame.cell_run.evidence
    actual = r.policy.check(out, r.read(out / 'plan.json'), app.tasks, evidence)
    actual = {key: value for key, value in actual.items() if key != 'turns'}
    calls = []
    for line, row in enumerate(evidence.lines(out / 'run/stdout'), 1):
        item = row.get('item') or {}
        if row.get('type') == 'item.completed' and item.get('type') == 'command_execution':
            count = r.base_policy.helper_invocations(item.get('command', ''))
            if count or item.get('id') == 'item_36':
                calls.append(dict(line=line, item_id=item.get('id'), invocations=count))
    after = {name: r.digest(Path(name)) for name in before}
    if before != after:
        raise ValueError('retained input changed')
    print(json.dumps(dict(scope='Policy component only. Original STOP, PARTIAL and native capability failure unchanged.',
        protected_sha256=before, protected_unchanged=True, calls=calls, prospective_policy=actual,
        original_policy_status=r.read(out / 'peer-policy.json')['status'],
        original_usage={key: r.read(out / 'usage.json').get(key) for key in
                        ('completeness', 'input_tokens', 'output_tokens', 'gaps')}), indent=2, sort_keys=True))
