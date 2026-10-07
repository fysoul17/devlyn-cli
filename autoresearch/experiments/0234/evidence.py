"""One inventory of what ran in a finished 0234 cell, shared by identity and usage: evidence.py <cell-out>.

Codex: every traced process (deduplicated globally by rollout and inference id), seated by independent launch
evidence: the Codex owner's JSON thread or a native child below it. Every other traced session is owner-launched:
counted for usage, reported, never held to a registered model. Claude: the owner's stream, every saved `claude -p`
result envelope (usage only, deduplicated by session) and every transcript session; transcripts other than the
owner's and its native children are owner-launched. Saved legacy captures (judge headers, dispatch records) feed
usage accounting only.
"""
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('trace0232e', HERE.parent / '0232/trace_usage.py')
traces = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(traces)
_spec = importlib.util.spec_from_file_location('usage0222e', HERE.parent / '0222/record_usage.py')
usage0222 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(usage0222)
TASKS = json.loads((HERE / 'tasks.json').read_text())
WRITABLE = ('cell', 'tmp', 'home')
HEADER = re.compile(r'^OpenAI Codex v[^\n]+\n--------\n(.*?)\n--------\n', re.S | re.M)
FOOTER = re.compile(r'^tokens used\n([\d,]+)\s*$', re.M)
INTERNAL = re.compile(r'^claude-haiku-')


def lines(path):
    out = []
    for line in path.read_text(errors='replace').splitlines() if path.is_file() else ():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            out.append(value)
    return out


def devlyn_dirs(out):
    return sorted(p for name in WRITABLE for p in (out / name).rglob('.devlyn') if p.is_dir())


def seats(plan):
    """Expected model and effort per seat for this cell's config (efforts only where the route sets one)."""
    route = TASKS['routes'][plan['config']]
    owner, roles = route['owner'], route['product_roles']
    judge = {engine: next(dict(role=r, **v) for r, v in roles.items() if r != 'worker' and v['engine'] == engine)
             for engine in ('claude', 'codex')}
    return dict(owner=dict(engine=owner['engine'], model=owner['model'], effort=owner['effort']),
                child=dict(engine='codex', model=owner.get('child_model', owner['model']),
                           effort=owner.get('child_effort', owner['effort'])),
                worker=dict(roles['worker']), codex_judge=judge['codex'], claude_judge=judge['claude'])


def judge_headers(out):
    """Native plain-mode headers saved under any .devlyn: session id -> fields, footer and the file."""
    found, conflicts = {}, []
    for devlyn in devlyn_dirs(out):
        for path in sorted(devlyn.rglob('*.stderr')):
            text = path.read_text(errors='replace')
            for header in HEADER.finditer(text):
                fields = dict(re.findall(r'^([a-z ]+): (.+)$', header.group(1), re.M))
                session = fields.get('session id')
                if not session:
                    continue
                footer = FOOTER.search(text, header.end())
                entry = dict(model=fields.get('model'), effort=fields.get('reasoning effort'), path=str(path.relative_to(out)),
                             footer=int(footer.group(1).replace(',', '')) if footer else None)
                previous = found.setdefault(session, entry)
                if (previous['model'], previous['effort'], previous['footer']) != (entry['model'], entry['effort'], entry['footer']):
                    conflicts.append(f'conflicting copies of judge header {session}')
    return found, conflicts


def add_envelope(found, value, where, any_source=False, order=None):
    """Record one Claude result envelope under its session, once per (usage, error flag, source name); with
    any_source, once per (usage, error flag) — a printed copy of a saved capture is the same envelope."""
    model_usage = value.get('modelUsage') or {}
    if not model_usage and isinstance(value.get('usage'), dict):
        raw = value['usage']
        if any(key in raw for key in ('inputTokens', 'input_tokens')):
            model_usage = {value.get('model') or 'UNKNOWN': raw}
        else:
            model_usage = raw
    entry = dict(models=sorted(model_usage), usage=model_usage, is_error=value.get('is_error'), path=where, order=order)
    entries = found.setdefault(value['session_id'], [])
    if not any(previous['usage'] == entry['usage'] and previous['is_error'] == entry['is_error']
               and (any_source or Path(previous['path']).name == Path(where).name) for previous in entries):
        entries.append(entry)


def claude_envelopes(out):
    """Preserve every turn's result envelope, including peer captures in linked worktrees and tmp."""
    found, unreadable = {}, []
    commands, outputs, command_order = [], [], []
    for order, event in enumerate(lines(out / 'run/stdout')):
        message = event.get('message') or {}
        for block in message.get('content', ()) if isinstance(message.get('content'), list) else ():
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'tool_use':
                commands.append(str((block.get('input') or {}).get('command', '')))
                command_order.append(order)
            elif block.get('type') == 'tool_result':
                content = block.get('content')
                text = content if isinstance(content, str) else '\n'.join(
                    str(part.get('text', '')) for part in content or () if isinstance(part, dict))
                outputs.append((f'run/stdout#{order:06d}-{block.get("tool_use_id")}', text))
        item = event.get('item') or {}
        if isinstance(item, dict):
            detail = item.get('input') or {}
            commands.append(str(item.get('command') or (detail.get('command', '') if isinstance(detail, dict) else detail)))
            command_order.append(order)
            if event.get('type') == 'item.completed' and item.get('aggregated_output'):
                outputs.append((f'run/stdout#{order:06d}-{item.get("id")}', str(item['aggregated_output'])))
    capture_order = {}  # capture file name -> event order of the last command that wrote it (turn chronology)
    for command, when in zip(commands, command_order):
        match = re.search(r'>\s*([\w./-]+\.jsonl?)\b', command) if '--output-format json' in command else None
        if match:
            capture_order[Path(match.group(1)).name] = when
    capture_names = set(capture_order)
    roots = [*devlyn_dirs(out), out / 'tmp', out / 'cell']
    for root in roots:
        for path in sorted(p for p in root.rglob('*.json*') if p.is_file() and p.suffix in ('.json', '.jsonl') and
                           (p.suffix == '.json' or p.name in capture_names) and
                           (root.name != 'cell' or p.name in capture_names or re.fullmatch(r'peer[\w-]*\.json', p.name))):
            text = path.read_text(errors='replace').strip()
            try:
                value = json.loads(text)
            except ValueError:
                if path.name.endswith('.output.json') or re.fullmatch(r'peer[\w-]*\.json', path.name):
                    unreadable.append(str(path.relative_to(out)))
                continue
            if not isinstance(value, dict) or value.get('type') != 'result' or not value.get('session_id'):
                if path.name.endswith('.output.json') or re.fullmatch(r'peer[\w-]*\.json', path.name):
                    unreadable.append(str(path.relative_to(out)))
                continue
            add_envelope(found, value, str(path.relative_to(out)), order=capture_order.get(path.name))
    # A peer's result envelope printed to the owner's tool output (owners that keep no capture file; 0234 SMOKE r2).
    for where, text in outputs:
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith('{'):
                continue
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and value.get('type') == 'result' and value.get('session_id'):
                add_envelope(found, value, where, any_source=True, order=int(where.split('#')[1].split('-')[0]))
    def turn(entry):
        # Chronology first (the owner's call order for saved and printed results alike), then the turn number.
        match = re.search(r'(?:peer|turn)[-_]?(\d+)', Path(entry['path']).name)
        return (entry['order'] is None, entry['order'] or 0, int(match.group(1)) if match else -1, entry['path'])
    return {session: sorted(entries, key=turn) for session, entries in found.items()}, unreadable




def transcripts(out):
    """Claude transcript sessions: models and per-message usage, deduplicated by message id."""
    sessions = {}
    for path in sorted((out / 'home/.claude/projects').rglob('*.jsonl')):
        for event in lines(path):
            message = event.get('message') or {}
            if event.get('type') != 'assistant' or event.get('isApiErrorMessage') or message.get('model') == '<synthetic>':
                continue
            session = sessions.setdefault(event.get('sessionId'), dict(models=set(), efforts=set(), messages={}, parents=set()))
            if event.get('parentSessionId'):
                session['parents'].add(event['parentSessionId'])
            model = str(message.get('model')).split('[')[0]
            session['models'].add(model)
            if event.get('effort'):
                session['efforts'].add(event['effort'])
            if message.get('usage') and message.get('id'):
                session['messages'][message['id']] = dict(model=model, usage=message['usage'])
    return sessions


def run_of(folder):
    """The run a .devlyn directory (live or archived, in a worktree or in custody) belongs to."""
    state = folder / 'pipeline.state.json'
    try:
        return json.loads(state.read_text()).get('run_id') or str(folder) if state.is_file() else str(folder)
    except ValueError:
        return str(folder)


def attempted(out):
    """Calls each run recorded launching, matched only to that run's own carriers: judge roles per dispatch record
    (expected capture beside it) and worker invocation receipts (expected session beside it). Copies of one run
    (a worktree archive and its custody copy) are one logical launch with every copy's carrier path kept."""
    judges, workers = {}, {}
    for devlyn in devlyn_dirs(out):
        for path in devlyn.rglob('verify-judge.r*.dispatch.json'):
            record = json.loads(path.read_text())
            round_ = re.search(r'\.r(\d+)\.', path.name).group(1)
            for role, entry in (record.get('roles') or {}).items():
                if entry.get('decision') == 'dispatch':
                    engine = entry.get('engine')
                    capture = path.parent / (f'{engine}-judge.r{round_}' + ('.output.json' if engine == 'claude' else '.stderr'))
                    judges.setdefault((run_of(path.parent), round_, role, engine), []).append(capture)
        for path in devlyn.rglob('*.invocation.*.json'):
            stem, round_ = path.name.split('.invocation.')[0], path.name.rsplit('.', 2)[1]
            workers.setdefault((run_of(path.parent), path.name), []).append(path.parent / f'{stem}.worker-session.{round_}.jsonl')
    return dict(judges=judges, workers=workers)


def native_rollouts(out):
    """Codex rollouts in the cell home: thread id -> own models and efforts (turn_context), and its parent."""
    found = {}
    for path in (out / 'home/.codex/sessions').rglob('*.jsonl'):
        rows = lines(path)
        meta = next((e['payload'] for e in rows if e.get('type') == 'session_meta'), None)
        if meta is None:
            continue
        source = meta.get('source')
        contexts = [e['payload'] for e in usage0222.own_events(rows) if e.get('type') == 'turn_context']
        found[meta['id']] = dict(models={c.get('model') for c in contexts} - {None},
                                 efforts={c.get('effort') for c in contexts} - {None},
                                 parent=source['subagent']['thread_spawn']['parent_thread_id'] if isinstance(source, dict) else None)
    return found


def inventory(out, plan):
    rollouts = traces.load(out / 'cell/trace')
    headers, header_conflicts = judge_headers(out)
    owner_threads = ({e['thread_id'] for e in lines(out / 'run/stdout') if e.get('type') == 'thread.started'}
                     if plan['engine'] == 'codex' else set())
    worker_threads = set()  # 0234 arms register no worker or judge seats; saved captures only feed usage
    native = native_rollouts(out)
    def native_child(thread):
        parent, seen = (native.get(thread) or {}).get('parent'), set()
        while parent and parent not in seen:
            if parent in owner_threads:
                return True
            seen.add(parent)
            parent = (native.get(parent) or {}).get('parent')
        return False

    seated, owner_launched, inferences, gaps = {}, [], {}, list(header_conflicts)
    for rollout in rollouts:
        gaps += [f'{rollout["trace"]}: {gap}' for gap in rollout['gaps']]
        root = rollout.get('rollout_id')
        seat = 'owner' if root in owner_threads else 'child' if native_child(root) else 'owner_launched'
        if seat == 'owner_launched':
            owner_launched.append(root)
        for thread, item in rollout['threads'].items():
            seated[thread] = dict(seat=seat if thread == root or seat == 'owner_launched' else 'child', root=root, model=item.get('model'),
                                  effort=item.get('effort'), agent_path=item.get('agent_path'))
        for call, item in rollout['inferences'].items():
            key = (root, call)
            if item['thread'] not in rollout['threads']:
                gaps.append(f'inference {call} on undeclared thread {item["thread"]}')
            if key in inferences and inferences[key]['usage'] != item['usage']:
                gaps.append(f'conflicting copies of inference {call}')
            inferences.setdefault(key, item)
    envelopes, unreadable = claude_envelopes(out)
    stream = lines(out / 'run/stdout')
    init = next((e for e in stream if e.get('type') == 'system' and e.get('subtype') == 'init'), None)
    final = [e for e in stream if e.get('type') == 'result']
    transcript_sessions = transcripts(out)
    owner_session = (init or {}).get('session_id')
    def owner_child(session, seen=None):
        seen = set() if seen is None else seen
        if session in seen:
            return False
        seen.add(session)
        parents = transcript_sessions.get(session, {}).get('parents', set())
        return owner_session in parents or any(owner_child(parent, seen) for parent in parents)
    launched_claude = sorted(session for session in transcript_sessions
                            if session != owner_session and not owner_child(session))
    return dict(rollouts=rollouts, seated=seated, owner_launched_codex=sorted(set(owner_launched)),
                owner_launched_claude=launched_claude, inferences=inferences, headers=headers,
                native=native,
                owner_threads=owner_threads, worker_threads=worker_threads, envelopes=envelopes, unreadable=unreadable,
                transcripts=transcript_sessions, attempted=attempted(out), gaps=gaps,
                claude_owner=dict(init_model=(init or {}).get('model'), session=(init or {}).get('session_id'),
                                  usage=final[-1].get('modelUsage') if final else None))


if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    data = inventory(out, json.loads((out / 'plan.json').read_text()))
    print(json.dumps({k: v for k, v in data.items() if k in ('owner_launched_codex', 'owner_launched_claude', 'gaps', 'attempted')},
                     indent=2, default=sorted))
