"""Post-hoc usage for one finished 0234 cell: record_usage.py <cell-out>. Recording only; never gates or stops.

Built on evidence.inventory: Codex inferences counted once by native ids; Claude from the owner's result, each
separate result envelope (one per session) and, for any transcript session no result
covers, its transcript usage as a known lower bound. Every owner-launched trace without usage, untraced or unresulted launch, footer or
rollout disagreement, undeclared thread, conflicting copy and missing Claude counter is a named gap: never zero, and
never COMPLETE.

Input is processed input, counted once: a Codex inference's input_tokens already include its cached and cache-write
tokens (0208's validated counter semantics), while Claude reports uncached input, cache reads and cache writes apart.
"""
import importlib.util
import json
from pathlib import Path
import re
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
# Claude counters under their native names in a result's modelUsage and in a transcript message's usage.
RESULT = dict(input='inputTokens', cache_read='cacheReadInputTokens', cache_write='cacheCreationInputTokens',
              output='outputTokens')
TRANSCRIPT = dict(input='input_tokens', cache_read='cache_read_input_tokens', cache_write='cache_creation_input_tokens',
                  output='output_tokens')


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


def surviving(copies):
    """A logical launch's carrier from whichever copies survived; differing surviving copies are a conflict."""
    present = [p for p in copies if p.is_file()]
    return (present[0] if present else None), len({p.read_bytes() for p in present}) > 1


def codex(out, inv):
    totals, per_thread, gaps = {}, {}, list(inv['gaps'])
    for (root, call), item in inv['inferences'].items():
        if item['usage'] is None:
            continue
        for bucket in (totals.setdefault(item['model'] or 'UNKNOWN', dict.fromkeys(COUNTERS, 0)),
                       per_thread.setdefault(item['thread'], dict.fromkeys(COUNTERS, 0))):
            for key in COUNTERS:
                bucket[key] += item['usage'][key]
    gaps += [f'owner-launched Codex session {root} has no traced inference usage' for root in inv['owner_launched_codex']
             if not any(rollout.get('rollout_id') == root and rollout['inferences'] for rollout in inv['rollouts'])]
    traced = {r.get('rollout_id') for r in inv['rollouts']}
    launches = inv['owner_threads'] | inv['worker_threads'] | set(inv['headers'])
    gaps += [f'launch {root} has no trace' for root in sorted(launches - traced)]
    for (run, round_, role, engine), copies in inv['attempted']['judges'].items():
        if engine != 'codex':
            continue
        capture, conflict = surviving(copies)
        if conflict:
            gaps.append(f'run {run}: copies of codex {role} r{round_} capture disagree')
        header = evidence.HEADER.search(capture.read_text(errors='replace')) if capture else None
        session = re.search(r'^session id: (\S+)$', header.group(1), re.M) if header else None
        if not session or session.group(1) not in traced:
            gaps.append(f'run {run}: dispatched codex {role} r{round_} has no traced native header beside its dispatch')
    for (run, name), copies in inv['attempted']['workers'].items():
        session_path, conflict = surviving(copies)
        if conflict:
            gaps.append(f'run {run}: copies of worker session {name} disagree')
        threads = {e['thread_id'] for e in evidence.lines(session_path) if e.get('type') == 'thread.started'} if session_path else set()
        if not threads & traced:
            gaps.append(f'run {run}: worker invocation {name} has no traced session beside it')
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
    captures = {}
    for root in (out / 'cell', out / 'tmp'):
        for path in root.rglob('peer*.jsonl'):
            if not path.is_file() or (root.name == 'cell' and '.devlyn' not in path.parts):
                continue
            rows = evidence.lines(path)
            thread = next((e.get('thread_id') for e in rows if e.get('type') == 'thread.started'), None)
            if not thread:
                gaps.append(f'Codex peer capture {path.relative_to(out)} has no thread.started')
                continue
            turn = next((e.get('usage') for e in reversed(rows) if e.get('type') == 'turn.completed'), None)
            if not isinstance(turn, dict) or not all(type(turn.get(k)) is int for k in
                                                     ('input_tokens', 'cached_input_tokens', 'output_tokens')):
                gaps.append(f'Codex peer capture {path.relative_to(out)} has no completed turn usage')
                continue
            key = (thread, path.name)
            previous = captures.setdefault(key, turn)
            if previous != turn:
                gaps.append(f'Codex peer {thread} conflicting copies of {path.name}')
    by_thread = {}
    for (thread, name), turn in captures.items():
        by_thread.setdefault(thread, []).append((int((re.search(r'peer(\d+)', name) or [None, 0])[1]), turn))
    for thread, entries in by_thread.items():
        entries.sort(key=lambda pair: pair[0])
        values = [row for _, row in entries]
        keys = ('input_tokens', 'cached_input_tokens', 'output_tokens')
        cumulative = all(values[i][k] >= values[i-1][k] for i in range(1, len(values)) for k in keys)
        last = {k: values[-1][k] for k in keys}
        summed = {k: sum(v[k] for v in values) for k in keys}
        traced = per_thread.get(thread)
        if not cumulative:
            gaps.append(f'Codex peer {thread} decreasing turn usage snapshot')
        if traced:
            if not (all(last[k] == traced[k] for k in keys) or all(summed[k] == traced[k] for k in keys)):
                gaps.append(f'Codex peer {thread} turn usage disagrees with trace')
            continue
        chosen = last if cumulative else {k: max(v[k] for v in values) for k in keys}
        native = inv['native'].get(thread, {})
        models = native.get('models', set())
        model = next(iter(models)) if len(models) == 1 else 'UNKNOWN'
        if model == 'UNKNOWN':
            gaps.append(f'Codex peer {thread} capture has no model attribution')
        gaps.append(f'Codex peer {thread} has no inference trace; turn usage is a lower bound')
        bucket = totals.setdefault(model, dict.fromkeys(COUNTERS, 0))
        for key in keys:
            bucket[key] += chosen[key]
    return totals, gaps


def claude(inv, plan):
    totals, gaps = {}, []

    def add(model, usage, names, where):
        values = {key: (usage or {}).get(name) for key, name in names.items()}
        if not all(type(v) is int for v in values.values()):
            gaps.append(f'{where}: {model} usage lacks a counter')
            return
        row = totals.setdefault(model.split('[')[0], dict.fromkeys(names, 0))
        for key, value in values.items():
            row[key] += value
    owner = inv['claude_owner']
    envelopes = {session: list(entries) for session, entries in inv['envelopes'].items()}
    if plan['engine'] == 'claude':
        if not owner['usage']:
            gaps.append('owner result without usage')
        else:
            envelopes.setdefault(owner['session'], []).append(dict(usage=owner['usage'], path='owner result'))
    covered = set()
    for session, entries in envelopes.items():
        maxima, previous = {}, {}
        for entry in entries:
            if not entry['usage']:
                gaps.append(f'Claude result {entry["path"]} without usage')
                continue
            for model, usage in entry['usage'].items():
                values = {key: usage.get(name, usage.get(TRANSCRIPT[key])) for key, name in RESULT.items()}
                if not all(type(value) is int and value >= 0 for value in values.values()):
                    gaps.append(f'Claude result {entry["path"]}: {model} usage lacks a counter')
                    continue
                if model in previous and any(values[key] < previous[model][key] for key in RESULT):
                    gaps.append(f'Claude session {session}: decreasing {model} snapshot at {entry["path"]}; transcript is a lower bound')
                previous[model] = values
                maximum = maxima.setdefault(model, dict.fromkeys(RESULT, 0))
                for key, value in values.items():
                    maximum[key] = max(maximum[key], value)
        transcript = inv['transcripts'].get(session)
        lower = {}
        for message in transcript['messages'].values() if transcript else ():
            row = lower.setdefault(message['model'], dict.fromkeys(RESULT, 0))
            for key, name in TRANSCRIPT.items():
                value = message['usage'].get(name)
                if type(value) is int:
                    row[key] += value
                else:
                    gaps.append(f'Claude session {session}: transcript message lacks {name}')
        if 'UNKNOWN' in maxima and 'UNKNOWN' not in lower and (lower or len(maxima) > 1):
            aggregate = maxima.pop('UNKNOWN')
            if len(lower) == 1 and maxima.keys() <= lower.keys():
                model = next(iter(lower))
                target = maxima.setdefault(model, dict.fromkeys(RESULT, 0))
                for key in RESULT:
                    target[key] = max(target[key], aggregate[key])
            else:
                maxima['UNKNOWN'] = {key: max(aggregate[key], sum(row[key] for row in lower.values()),
                                              sum(row[key] for row in maxima.values()))
                                     for key in RESULT}
                maxima = {'UNKNOWN': maxima['UNKNOWN']}
                lower = {}
                gaps.append(f'Claude session {session}: aggregate usage has no model attribution')
        if not maxima:
            gaps.append(f'Claude session {session} has no result; its transcript usage is a lower bound')
        for model in maxima.keys() | lower.keys():
            bound = lower.get(model, {})
            maximum = maxima.get(model, {})
            if any(bound.get(key, 0) > maximum.get(key, 0) for key in RESULT):
                gaps.append(f'Claude session {session}: {model} transcript exceeds result snapshot; transcript is a lower bound')
            add(model, {RESULT[key]: max(bound.get(key, 0), maximum.get(key, 0)) for key in RESULT},
                RESULT, f'Claude session {session}')
        covered.add(session)
    gaps += [f'unreadable Claude result {path}' for path in inv['unreadable']]
    for (run, round_, role, engine), copies in inv['attempted']['judges'].items():
        if engine != 'claude':
            continue
        capture, conflict = surviving(copies)
        if conflict:
            gaps.append(f'run {run}: copies of claude {role} r{round_} result disagree')
        try:
            session = json.loads(capture.read_text()).get('session_id') if capture else None
        except ValueError:
            session = None
        if not session or not any(entry['usage'] for entry in inv['envelopes'].get(session, [])):
            gaps.append(f'run {run}: dispatched claude {role} r{round_} left no result beside its dispatch')
    for session, transcript in inv['transcripts'].items():
        if session not in covered:
            gaps.append(f'Claude session {session} has no result; its transcript usage is a lower bound')
            for message in transcript['messages'].values():
                add(message['model'], message['usage'], TRANSCRIPT, f'Claude session {session}')
    return totals, gaps


def valid_claude_result(path):
    try:
        value = json.loads(path.read_text(errors='replace'))
    except ValueError:
        return False
    return (isinstance(value, dict) and value.get('type') == 'result' and bool(value.get('session_id'))
            and bool(value.get('modelUsage') or value.get('usage')))


def record(out):
    plan = json.loads((out / 'plan.json').read_text())
    inv = evidence.inventory(out, plan)
    codex_totals, codex_gaps = codex(out, inv)
    claude_totals, claude_gaps = claude(inv, plan)
    diagnostics = load('diagnostics0234u', HERE / 'diagnostics.py')
    for call in diagnostics.calls(evidence.lines(out / 'run/stdout'), plan['engine']):
        command = diagnostics.text_of(call)
        if 'codex-monitored.sh' not in command and not re.search(r'\bclaude\s+-p\b', command):
            continue
        capture = diagnostics.redirected_capture(out, command)
        if capture is None:
            (codex_gaps if 'codex-monitored.sh' in command else claude_gaps).append(
                'owner-launched peer turn has no unambiguous saved capture')
        elif 'codex-monitored.sh' not in command:
            # Any observed Claude capture, whatever its name, must hold a result envelope with usage that entered the
            # inventory (freeze a2/a3); otherwise its usage is a named gap.
            relative = str(capture.relative_to(out))
            if not valid_claude_result(capture):
                claude_gaps.append(f'Claude peer capture {relative} holds no valid result envelope with usage')
            else:
                session = json.loads(capture.read_text(errors='replace'))['session_id']
                if not any(Path(entry['path']).name == capture.name for entry in inv['envelopes'].get(session, [])):
                    claude_gaps.append(f'Claude peer capture {relative} was not counted')
    if plan['engine'] == 'codex' and not inv['owner_threads']:
        codex_gaps.append('owner thread missing')
    gaps = codex_gaps + claude_gaps
    input_ = (sum(row['input_tokens'] for row in codex_totals.values())
              + sum(row['input'] + row['cache_read'] + row['cache_write'] for row in claude_totals.values()))
    output = sum(row['output_tokens'] for row in codex_totals.values()) + sum(row['output'] for row in claude_totals.values())
    completeness = 'COMPLETE' if not gaps else 'PARTIAL' if input_ or output else 'UNKNOWN'
    usage = dict(completeness=completeness, input_tokens=input_, output_tokens=output, gaps=gaps, codex=codex_totals,
                 claude=claude_totals)
    (out / 'usage.json').write_text(json.dumps(usage, indent=2))
    return usage


if __name__ == '__main__':
    print(json.dumps({k: v for k, v in record(Path(sys.argv[1]).resolve()).items()
                      if k in ('completeness', 'input_tokens', 'output_tokens', 'gaps')}))
