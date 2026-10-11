"""Read-only component replay; never calls record(), run(), evaluates or writes old cells."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runner0241_replay', HERE / 'runner.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def replay(runtime, out):
    protected = [out / name for name in ('plan.json', 'usage.json', 'claude-accounting.json', 'peer-policy.json',
                                        'evidence-manifest.json', 'run/stdout', 'run/stderr')]
    protected += [out.parent / ('verdict-' + out.name + '.json')]
    before = {str(path): r.digest(path) for path in protected if path.is_file()}
    app = r.Runner(runtime)
    evidence = app.frame.cell_run.evidence
    old = r.load('evidence0234_replay', HERE.parent / '0234/evidence.py')
    old_envelopes, old_unreadable = old.claude_envelopes(out)
    envelopes, unreadable = evidence.claude_envelopes(out)
    plan = r.read(out / 'plan.json')
    inventory = evidence.inventory(out, plan)
    codex, codex_gaps = app.frame.usage.codex(out, inventory)
    claude, claude_gaps = app.frame.usage.claude(inventory, plan)
    receipts, receipt_gaps = r.policy.receipts(out, evidence)
    closure = r.legacy.legacy.accounting.audit(out, evidence, receipts)
    tokens = dict(input_tokens=sum(row['input_tokens'] for row in codex.values()) +
                  sum(row['input'] + row['cache_read'] + row['cache_write'] for row in claude.values()),
                  output_tokens=sum(row['output_tokens'] for row in codex.values()) +
                  sum(row['output'] for row in claude.values()))
    after = {name: r.digest(Path(name)) for name in before}
    if before != after:
        raise ValueError('retained evidence changed')
    return dict(cell=str(out), protected_sha256=before, protected_unchanged=True,
                old_envelopes=old_envelopes, old_unreadable=old_unreadable,
                new_envelopes=envelopes, new_unreadable=unreadable, component_tokens=tokens,
                codex_gaps=codex_gaps, claude_gaps=claude_gaps, receipt_gaps=receipt_gaps,
                claude_accounting=closure, original_usage=r.read(out / 'usage.json'))


if __name__ == '__main__':
    live = Path('/Users/aipalm/.local/share/nx01')
    cases = [('0240', 'runtime-smoke.json', 'out-smoke/s01-h-codex'),
             ('0238', 'runtime-smoke-v2.json', 'out-smoke-v2/s01-h-claude-v3'),
             ('0238', 'runtime-smoke-v2.json', 'out-smoke-v2/s02-h-codex-v2')]
    rows = [replay(live / (number + '-live/staged-v1') / runtime,
                   live / (number + '-live/staged-v1') / name) for number, runtime, name in cases]
    print(json.dumps(dict(scope='Component diagnostics only; original verdicts are never regraded.', rows=rows),
                     indent=2, sort_keys=True))
