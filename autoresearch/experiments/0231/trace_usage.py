"""Codex usage and models from private rollout traces (CODEX_ROLLOUT_TRACE_ROOT, Codex 0.156.1 trace schema 1).

Each process writes trace-<trace_id>-<rollout_id>/ with manifest.json, trace.jsonl and payloads/. An inference
counts once, by its inference_call_id; a started inference without completed usage, a torn line or a missing
payload is a named gap, never zero.
"""
import json
from pathlib import Path

SCHEMA = 1
COUNTERS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'output_tokens', 'reasoning_output_tokens')


def _rows(path, gaps):
    rows = []
    for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
        try:
            row = json.loads(line)
        except ValueError:
            gaps.append(f'torn line {number} in {path.parent.name}')
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _payload(trace, reference, gaps):
    path = trace / str((reference or {}).get('path', ''))
    try:
        return json.loads(path.read_text()) if reference and path.is_file() else None
    except ValueError:
        gaps.append(f'unreadable payload {path.relative_to(trace.parent)}')
        return None


def load(root):
    """One record per traced process: its threads (model, effort, agent path) and inferences (model, usage)."""
    rollouts = []
    for trace in sorted(Path(root).glob('trace-*')):
        gaps = []
        try:
            manifest = json.loads((trace / 'manifest.json').read_text())
        except (OSError, ValueError):
            rollouts.append(dict(trace=trace.name, gaps=['missing or unreadable manifest'], threads={}, inferences={}))
            continue
        if manifest.get('schema_version') != SCHEMA:
            gaps.append(f'trace schema {manifest.get("schema_version")}, expected {SCHEMA}')
        threads, inferences, status = {}, {}, None
        for row in _rows(trace / manifest.get('raw_event_log', 'trace.jsonl'), gaps):
            payload = row.get('payload') or {}
            kind = payload.get('type')
            if kind == 'thread_started':
                meta = _payload(trace, payload.get('metadata_payload'), gaps) or {}
                threads[payload['thread_id']] = dict(agent_path=payload.get('agent_path'), model=meta.get('model'),
                                                     effort=None, status=None)
            elif kind == 'protocol_event_observed' and payload.get('event_type') == 'session_configured':
                configured = _payload(trace, payload.get('event_payload'), gaps) or {}
                if not configured.get('thread_id'):
                    gaps.append('session_configured without its payload')
                    continue
                thread = threads.setdefault(configured['thread_id'], dict(agent_path=None, model=None, status=None))
                thread.update(model=configured.get('model'), effort=configured.get('reasoning_effort'))
            elif kind == 'inference_started':
                inferences[payload['inference_call_id']] = dict(thread=payload.get('thread_id'),
                                                                model=payload.get('model'), usage=None)
            elif kind == 'inference_completed':
                response = _payload(trace, payload.get('response_payload'), gaps) or {}
                usage = response.get('token_usage')
                call = inferences.setdefault(payload['inference_call_id'], dict(thread=None, model=None, usage=None))
                if isinstance(usage, dict) and all(isinstance(usage.get(k), int) for k in COUNTERS):
                    call['usage'] = {k: usage[k] for k in COUNTERS}
                else:
                    gaps.append(f'inference {payload["inference_call_id"]} completed without usage')
            elif kind == 'thread_ended':
                threads.setdefault(payload.get('thread_id'), dict(agent_path=None, model=None))['status'] = payload.get('status')
            elif kind == 'rollout_ended':
                status = payload.get('status')
        gaps += [f'inference {call} started without completed usage' for call, item in inferences.items()
                 if item['usage'] is None and not any(call in gap for gap in gaps)]
        if status is None:
            gaps.append('rollout did not end')
        rollouts.append(dict(trace=trace.name, rollout_id=manifest.get('rollout_id'),
                             root_thread_id=manifest.get('root_thread_id'), status=status,
                             threads=threads, inferences=inferences, gaps=gaps))
    return rollouts


def models(root):
    """Thread id -> models it ran (inference starts and configured sessions)."""
    seen = {}
    for rollout in load(root):
        for thread, item in rollout['threads'].items():
            if item.get('model'):
                seen.setdefault(thread, set()).add(item['model'])
        for item in rollout['inferences'].values():
            if item['model']:
                seen.setdefault(item['thread'], set()).add(item['model'])
    return seen


def footer_tokens(rollout):
    """What a plain `codex exec` prints as `tokens used`: uncached input plus output over the root thread's
    inferences (probe 2026-10-04: one and two inferences, reasoning included in output)."""
    usages = [item['usage'] for item in rollout['inferences'].values() if item['thread'] == rollout.get('rollout_id')]
    if not usages or any(u is None for u in usages):
        return None
    return sum(u['input_tokens'] - u['cached_input_tokens'] + u['output_tokens'] for u in usages)


def usage(root):
    """Per-model totals over every traced inference, with every gap named."""
    totals, gaps, rollouts = {}, [], load(root)
    for rollout in rollouts:
        gaps += [f'{rollout["trace"]}: {gap}' for gap in rollout['gaps']]
        for item in rollout['inferences'].values():
            if item['usage'] is None:
                continue
            row = totals.setdefault(item['model'] or 'UNKNOWN', dict.fromkeys(COUNTERS, 0))
            for key in COUNTERS:
                row[key] += item['usage'][key]
    return dict(totals=totals, gaps=gaps, rollouts=[
        dict(trace=r['trace'], rollout_id=r.get('rollout_id'), status=r.get('status'), inferences=len(r['inferences']),
             footer_tokens=footer_tokens(r)) for r in rollouts])


if __name__ == '__main__':
    import sys
    print(json.dumps(usage(sys.argv[1]), indent=2))
