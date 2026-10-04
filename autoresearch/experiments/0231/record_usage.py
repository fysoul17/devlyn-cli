"""Post-hoc usage for one finished 0231 cell: record_usage.py <cell-out>. Recording only; never gates or stops.

Built on evidence.inventory: Codex inferences counted once by native ids; Claude from the owner's result, each
separate result envelope (one per session) and, for any transcript session no result covers, its transcript usage as
a known lower bound. Every unbound trace, untraced or unresulted launch, footer or rollout disagreement, undeclared
thread and conflicting copy is a named gap: never zero, and never COMPLETE.
"""
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load('usage0222', HERE.parent / '0222/record_usage.py')
evidence = load('evidence0231', HERE / 'evidence.py')
COUNTERS = evidence.traces.COUNTERS


def rollout_counters(sessions):
    """Per-thread own counters from native rollouts (fork context excluded); None when a rollout has none."""
    found = {}
    for path in sessions.rglob('*.jsonl'):
        rows = base.events(path)
        meta = next((e['payload'] for e in rows if e.get('type') == 'session_meta'), None)
        if meta is None:
            continue
        last = None
        for event in base.own_events(rows):
            info = (event.get('payload') or {}).get('info') if event.get('type') == 'event_msg' else None
            if isinstance(info, dict) and isinstance(info.get('total_token_usage'), dict):
                last = info['total_token_usage']
        found[meta['id']] = last
    return found


def codex(out, inv):
    totals, per_thread, gaps = {}, {}, list(inv['gaps'])
    for (root, call), item in inv['inferences'].items():
        if item['usage'] is None:
            continue
        for bucket in (totals.setdefault(item['model'] or 'UNKNOWN', dict.fromkeys(COUNTERS, 0)),
                       per_thread.setdefault(item['thread'], dict.fromkeys(COUNTERS, 0))):
            for key in COUNTERS:
                bucket[key] += item['usage'][key]
    gaps += [f'trace {root} binds to no launch evidence' for root in inv['unbound']]
    traced = {r.get('rollout_id') for r in inv['rollouts']}
    launches = inv['owner_threads'] | inv['worker_threads'] | set(inv['headers'])
    gaps += [f'launch {root} has no trace' for root in sorted(launches - traced)]
    for round_, role, engine in inv['attempted']['judges']:
        if engine == 'codex' and not any(f'.r{round_}.' in h['path'] for h in inv['headers'].values()):
            gaps.append(f'dispatched codex {role} r{round_} left no native header')
    for name in inv['attempted']['workers']:
        stem, round_ = name.split('.invocation.')[0], name.rsplit('.', 2)[1]
        sessions = [p for d in evidence.devlyn_dirs(out) for p in d.rglob(f'{stem}.worker-session.{round_}.jsonl')]
        threads = {e['thread_id'] for p in sessions for e in evidence.lines(p) if e.get('type') == 'thread.started'}
        if not threads & traced:
            gaps.append(f'worker invocation {name} has no traced session')
    for session, header in inv['headers'].items():
        if any(s['root'] == session and s['seat'] == 'child' for s in inv['seated'].values()):
            gaps.append(f'plain root {session} has children: its footer scope is not established')
            continue
        own = [i['usage'] for (root, _), i in inv['inferences'].items() if root == session and i['thread'] == session]
        printed = header['footer']
        computed = (sum(u['input_tokens'] - u['cached_input_tokens'] + u['output_tokens'] for u in own)
                    if own and all(own) else None)
        if session in traced and (printed is None or computed != printed):
            gaps.append(f'plain root {session}: footer {printed} vs trace {computed}')
    for thread, counters in rollout_counters(out / 'home/.codex/sessions').items():
        if counters is None:
            gaps.append(f'rollout {thread} has no usable counters')
        elif any(counters.get(key) != per_thread.get(thread, {}).get(key) for key in COUNTERS):
            gaps.append(f'thread {thread}: rollout counters {[counters.get(k) for k in COUNTERS]} vs trace '
                        f'{[per_thread.get(thread, {}).get(k) for k in COUNTERS]}')
    return totals, gaps


def claude(inv, plan):
    totals, gaps = {}, []

    def add(model, output):
        totals[model] = totals.get(model, 0) + output
    owner = inv['claude_owner']
    covered = set(inv['envelopes'])
    if plan['engine'] == 'claude':
        if owner['usage'] is None:
            gaps.append('owner result without usage')
        else:
            covered.add(owner['session'])
            for model, usage in owner['usage'].items():
                add(model.split('[')[0], usage.get('outputTokens', 0))
    for session, envelope in inv['envelopes'].items():
        for model, usage in envelope['usage'].items():
            add(model.split('[')[0], usage.get('outputTokens', 0))
        if not envelope['usage']:
            gaps.append(f'Claude result {session} without usage')
    gaps += [f'unreadable Claude result {path}' for path in inv['unreadable']]
    for round_, role, engine in inv['attempted']['judges']:
        if engine == 'claude' and not any(f'.r{round_}.' in e['path'] for e in inv['envelopes'].values()):
            gaps.append(f'dispatched claude {role} r{round_} left no result')
    for session, transcript in inv['transcripts'].items():
        if session not in covered:
            gaps.append(f'Claude session {session} has no result; its transcript usage is a lower bound')
            for usage in transcript['messages'].values():
                add(next(iter(transcript['models'])), usage.get('output_tokens', 0))
    return totals, gaps


def record(out):
    plan = json.loads((out / 'plan.json').read_text())
    inv = evidence.inventory(out, plan)
    codex_totals, codex_gaps = codex(out, inv)
    claude_totals, claude_gaps = claude(inv, plan)
    if plan['engine'] == 'codex' and not inv['owner_threads']:
        codex_gaps.append('owner thread missing')
    gaps = codex_gaps + claude_gaps
    output = sum(row['output_tokens'] for row in codex_totals.values()) + sum(claude_totals.values())
    completeness = 'COMPLETE' if not gaps else 'PARTIAL' if output else 'UNKNOWN'
    usage = dict(completeness=completeness, output_tokens=output, gaps=gaps, codex=codex_totals, claude_output=claude_totals)
    (out / 'usage.json').write_text(json.dumps(usage, indent=2))
    return usage


if __name__ == '__main__':
    print(json.dumps({k: v for k, v in record(Path(sys.argv[1]).resolve()).items() if k in ('completeness', 'output_tokens', 'gaps')}))
