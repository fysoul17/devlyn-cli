"""Post-hoc usage for one finished 0231 cell: record_usage.py <cell-out>. Recording only; never gates or stops.

Claude: the owner's result.modelUsage (it includes native subagents) plus each separate `claude -p` result,
deduplicated by session; transcripts are a cross-check only. Codex: every inference in the private traces, both arms.
Each traced process must bind to independent launch evidence (the Codex owner's thread, a worker session, a plain
judge's native header) and each piece of launch evidence to a trace; plain roots must reproduce their `tokens used`
footer and traced threads with a rollout must match its counters. Any miss is a named gap, never zero.
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
traces = load('trace0231', HERE / 'trace_usage.py')
cells = load('cell0231', HERE / 'cell.py')
HEADER = re.compile(r'^OpenAI Codex v[^\n]+\n--------\n(.*?)\n--------\n', re.S | re.M)
FOOTER = re.compile(r'^tokens used\n([\d,]+)\s*$', re.M)


def plain_roots(out):
    """Native plain-mode headers saved by the products: session id -> printed `tokens used` (None if absent)."""
    roots = {}
    for devlyn in cells.devlyn_dirs(out):
        for path in devlyn.rglob('*.stderr'):
            text = path.read_text(errors='replace')
            for header in HEADER.finditer(text):
                session = re.search(r'^session id: (\S+)$', header.group(1), re.M)
                if session:
                    footer = FOOTER.search(text, header.end())
                    roots.setdefault(session.group(1), int(footer.group(1).replace(',', '')) if footer else None)
    return roots


def json_roots(out, plan):
    """Thread ids of JSON-mode Codex processes: the Codex owner and receipt-bound workers' captured sessions."""
    roots = set()
    if plan['engine'] == 'codex':
        roots |= {e['thread_id'] for e in cells.lines(out / 'run/stdout') if e.get('type') == 'thread.started'}
    for devlyn in cells.devlyn_dirs(out):
        for log in devlyn.rglob('*.worker-session.*.jsonl'):
            roots |= {e['thread_id'] for e in cells.lines(log) if e.get('type') == 'thread.started'}
    return roots


def rollout_totals(sessions):
    """Per-thread own counters from native rollouts (fork context excluded), for the trace cross-check."""
    totals = {}
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
        if last:
            totals[meta['id']] = last
    return totals


def codex(out, plan):
    measured = traces.usage(out / 'cell/trace')
    gaps = list(measured['gaps'])
    rollouts = {r['rollout_id']: r for r in measured['rollouts']}
    plain, json_threads = plain_roots(out), json_roots(out, plan)
    for rollout_id in rollouts.keys() - plain.keys() - json_threads:
        gaps.append(f'trace {rollout_id} binds to no launch evidence')
    for root in (plain.keys() | json_threads) - rollouts.keys():
        gaps.append(f'launch {root} has no trace')
    for root, printed in plain.items():
        traced = rollouts.get(root, {}).get('footer_tokens')
        if root in rollouts and (printed is None or traced != printed):
            gaps.append(f'plain root {root}: footer {printed} vs trace {traced}')
    per_thread = {}
    for rollout in traces.load(out / 'cell/trace'):
        for item in rollout['inferences'].values():
            if item['usage']:
                per_thread[item['thread']] = per_thread.get(item['thread'], 0) + item['usage']['output_tokens']
    for thread, counters in rollout_totals(out / 'home/.codex/sessions').items():
        if counters.get('output_tokens') != per_thread.get(thread):
            gaps.append(f'thread {thread}: rollout output {counters.get("output_tokens")} vs trace {per_thread.get(thread)}')
    return measured['totals'], gaps


def record(out):
    plan = json.loads((out / 'plan.json').read_text())
    codex_totals, codex_gaps = codex(out, plan)
    result = base.claude_result(out / 'run/stdout')
    nested, unreadable = {}, []
    for devlyn in cells.devlyn_dirs(out):
        found, missing = base.claude_nested(devlyn)
        for model, row in found.items():
            for key, value in row.items():
                nested.setdefault(model, dict(input=0, cache_read=0, cache_write=0, output=0))[key] += value
        unreadable += missing
    transcripts = base.claude_transcripts(out / 'home/.claude/projects')
    owner_known = bool(result) if plan['engine'] == 'claude' else bool(json_roots(out, plan))
    gaps = ([] if owner_known else ['owner usage']) + codex_gaps + [f'unreadable Claude result {n}' for n in unreadable]
    output = (sum(row['output'] for row in (result or {}).values()) + sum(row['output'] for row in nested.values())
              + sum(row['output_tokens'] for row in codex_totals.values()))
    completeness = 'COMPLETE' if not gaps else 'PARTIAL' if output else 'UNKNOWN'
    usage = dict(completeness=completeness, output_tokens=output, gaps=gaps, codex=codex_totals,
                 claude_result=result, claude_nested=nested, claude_transcripts=transcripts)
    (out / 'usage.json').write_text(json.dumps(usage, indent=2))
    return usage


if __name__ == '__main__':
    print(json.dumps({k: v for k, v in record(Path(sys.argv[1]).resolve()).items() if k in ('completeness', 'output_tokens', 'gaps')}))
