"""Post-hoc usage for one finished cell: record_usage.py <cell>. Recording only; never gates or stops.

Missing or unparseable usage is PARTIAL/UNKNOWN, never zero. Codex rollouts are validated per exec root with the
0208/0210 accounting (limits infinite). Claude: the owner's result.modelUsage (includes native subagents) plus each
separate CLI run's archived result (claude_nested); transcripts are a cross-check only.
"""
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('accounting0210', HERE.parent / '0210/native_accounting.py')
accounting = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(accounting)


def events(path):
    """JSON objects of a stream; a torn or non-JSON line (e.g. after a hang kill) is skipped, not fatal."""
    out = []
    for line in path.read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            out.append(event)
    return out


def own_events(events):
    """A forked native child's rollout first copies its parent's context; only events after its
    thread_settings_applied boundary are the child's own (0210 native_accounting fork rule)."""
    meta = next((e['payload'] for e in events if e.get('type') == 'session_meta'), {})
    if not meta.get('forked_from_id'):
        return events
    for index, event in enumerate(events):
        payload = event.get('payload') or {}
        if (event.get('type') == 'event_msg' and payload.get('type') == 'thread_settings_applied'
                and payload.get('thread_id') == meta.get('id')):
            return events[index + 1:]
    return []


def add(totals, model, tokens):
    row = totals.setdefault(model, dict(input=0, cache_read=0, cache_write=0, output=0))
    for key, value in tokens.items():
        row[key] += value


def codex(sessions):
    """Per-model totals from native rollouts, one validated accounting pass per exec root."""
    files, parents, models = {}, {}, {}
    for path in sessions.rglob('*.jsonl'):
        rows = events(path)
        meta = next((e['payload'] for e in rows if e.get('type') == 'session_meta'), None)
        if meta is None:
            continue
        files[meta['id']] = path
        source = meta.get('source')
        parents[meta['id']] = source['subagent']['thread_spawn']['parent_thread_id'] if isinstance(source, dict) else None
        own = [e['payload'].get('model') for e in own_events(rows) if e.get('type') == 'turn_context']
        models[meta['id']] = own[-1] if own else 'UNKNOWN'

    def root(sid):
        while parents.get(sid):
            sid = parents[sid]
        return sid
    totals, failures = {}, []
    for owner in {root(sid) for sid in files}:
        with tempfile.TemporaryDirectory() as temp:
            for sid, path in files.items():
                if root(sid) == owner:
                    (Path(temp) / path.name).symlink_to(path.resolve())
            meter = accounting.Rollouts(temp, owner, input_limit=math.inf, output_limit=math.inf,
                                        dispatch_limit=math.inf, stale_seconds=math.inf, started=0)
            try:
                meter.finish(0)
            except (accounting.AccountingError, KeyError, ValueError) as exc:
                failures.append(f'{owner}: {exc}')
                continue
            for sid, session in meter.sessions.items():
                usage = session['usage']
                add(totals, models.get(sid, 'UNKNOWN'), dict(
                    input=usage['input_tokens'] - usage['cached_input_tokens'] - usage['cache_write_input_tokens'],
                    cache_read=usage['cached_input_tokens'], cache_write=usage['cache_write_input_tokens'],
                    output=usage['output_tokens']))
    return totals, failures


def claude_result(stdout):
    final = [e for e in events(stdout) if e.get('type') == 'result'] if stdout.exists() else []
    totals = {}
    for model, usage in (final[-1].get('modelUsage') or {}).items() if final else ():
        add(totals, model, dict(input=usage.get('inputTokens', 0), cache_read=usage.get('cacheReadInputTokens', 0),
                                cache_write=usage.get('cacheCreationInputTokens', 0), output=usage.get('outputTokens', 0)))
    return totals if final else None


def intent_reviews(devlyn):
    """B': the intent gate's review calls in the current and archived runs, as (engine, stdout path); an
    archived run keeps its recorded `.devlyn/intent/...` paths, so each is re-rooted at its own run.json."""
    calls, unreadable = [], []
    for path in sorted(devlyn.glob('intent/**/run.json')):
        try:
            reviews = json.loads(path.read_text()).get('reviews') or ()
        except ValueError:
            unreadable.append(path.name)
            continue
        calls += [(r['engine'], path.parent / Path(r['stdout']['path']).relative_to('.devlyn/intent')) for r in reviews]
    return calls, unreadable


def claude_nested(devlyn):
    """Separate `claude -p --output-format json` runs (3.2.1 judges, SURFACE_CLOSE, intent-gate Claude reviews)
    keep their own results. They are separate processes, so they are not in the owner's modelUsage; deduplicated
    by session."""
    totals, seen = {}, set()
    calls, unreadable = intent_reviews(devlyn)
    for path in sorted(devlyn.rglob('*.output.json')) + [p for engine, p in calls if engine == 'claude']:
        try:
            result = json.loads(path.read_text(errors='replace'))
        except (OSError, ValueError):  # e.g. a review killed before it wrote its result
            unreadable.append(path.name)
            continue
        if not isinstance(result, dict) or not result.get('modelUsage') or result.get('session_id') in seen:
            continue
        seen.add(result.get('session_id'))
        for model, usage in result['modelUsage'].items():
            add(totals, model.split('[')[0], dict(
                input=usage.get('inputTokens', 0), cache_read=usage.get('cacheReadInputTokens', 0),
                cache_write=usage.get('cacheCreationInputTokens', 0), output=usage.get('outputTokens', 0)))
    return totals, unreadable


def claude_transcripts(projects):
    """Assistant usage in persisted transcripts, deduplicated by message id (owner, subagents, nested judges)."""
    totals, seen = {}, set()
    for path in sorted(projects.rglob('*.jsonl')):
        for event in events(path):
            message = event.get('message') or {}
            if (event.get('type') != 'assistant' or not message.get('usage') or message.get('id') in seen
                    or event.get('isApiErrorMessage') or message.get('model') == '<synthetic>'):
                continue
            seen.add(message.get('id'))
            usage = message['usage']
            add(totals, message.get('model', 'UNKNOWN'), dict(
                input=usage.get('input_tokens', 0), cache_read=usage.get('cache_read_input_tokens', 0),
                cache_write=usage.get('cache_creation_input_tokens', 0), output=usage.get('output_tokens', 0)))
    return totals


def reviews(work):
    calls = []
    for folder in sorted((work / '.devlyn/reviews').glob('call-*')):
        result = folder / 'result.json'
        record = json.loads(result.read_text()) if result.exists() else {}
        calls.append(dict(call=folder.name, route=json.loads((folder / 'started.json').read_text()).get('route')
                          if (folder / 'started.json').exists() else None,
                          usage=record.get('usage', 'UNKNOWN'), identity=record.get('identity', 'UNKNOWN')))
    return calls


def record(cell):
    home, work = cell / 'home', cell / 'work'
    native, failures = codex(home / '.codex/sessions')
    result = claude_result(cell / 'run/stdout')
    transcripts = claude_transcripts(home / '.claude/projects')
    nested, unreadable = claude_nested(work / '.devlyn')
    intent_codex = any(engine == 'codex' for engine, _ in intent_reviews(work / '.devlyn')[0])
    calls = reviews(work)
    plan = json.loads((cell / 'plan.json').read_text())
    owner_known = bool(result) if plan['engine'] == 'claude' else bool(native) and not failures
    # 3.2.1 and the intent gate run isolated Codex judges with --ephemeral: they persist no rollout.
    gaps = [name for name, missing in (('owner', not owner_known), ('codex rollout', bool(failures)),
                                       ('review', any(c['usage'] == 'UNKNOWN' for c in calls)),
                                       ('unreadable nested Claude result ' + ', '.join(unreadable), bool(unreadable)),
                                       ('F isolated codex judges', plan['arm'] == 'F'),
                                       ("B' isolated codex reviews", intent_codex)) if missing]
    completeness = 'COMPLETE' if not gaps else 'PARTIAL' if owner_known or native or transcripts else 'UNKNOWN'
    usage = dict(completeness=completeness, gaps=gaps, codex=native, codex_failures=failures, claude_result=result,
                 claude_nested=nested, claude_transcripts=transcripts, reviews=calls)
    (cell / 'usage.json').write_text(json.dumps(usage, indent=2))
    return usage


if __name__ == '__main__':
    print(json.dumps(record(Path(sys.argv[1]).resolve())['completeness']))
