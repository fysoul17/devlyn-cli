"""One inventory of what ran in a finished 0231 cell, shared by identity and usage: evidence.py <cell-out>.

Codex: every traced process (deduplicated globally by rollout and inference id), seated by independent launch
evidence: the Codex owner's JSON thread, a worker's captured JSON session, or a plain judge's native header.
Threads below a root are native children. Claude: the owner's stream, every separate `claude -p` result envelope
(deduplicated by session) and every transcript session. Attempted calls come from dispatch records and worker
receipts, so a call whose result vanished is still inventoried.
"""
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('trace0231e', HERE / 'trace_usage.py')
traces = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(traces)
TASKS = json.loads((HERE.parent / '0222/tasks.json').read_text())
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


def claude_envelopes(out):
    """Separate `claude -p` result envelopes anywhere under .devlyn, deduplicated by session id."""
    found, unreadable, conflicts = {}, [], []
    for devlyn in devlyn_dirs(out):
        for path in sorted(p for p in devlyn.rglob('*') if p.is_file() and 'judge' in p.name
                           and (p.name.endswith('.output.json') or p.name.endswith('.stdout'))):
            text = path.read_text(errors='replace').strip()
            if not text.startswith('{'):
                continue  # a Codex judge's plain stdout, not a Claude envelope
            try:
                value = json.loads(text)
            except ValueError:
                unreadable.append(str(path.relative_to(out)))
                continue
            if not isinstance(value, dict) or value.get('type') != 'result' or not value.get('session_id'):
                unreadable.append(str(path.relative_to(out)))
                continue
            entry = dict(models=sorted(value.get('modelUsage') or {}), usage=value.get('modelUsage') or {},
                         is_error=value.get('is_error'), path=str(path.relative_to(out)))
            previous = found.setdefault(value['session_id'], entry)
            if previous['usage'] != entry['usage']:
                conflicts.append(f'conflicting copies of Claude result {value["session_id"]}')
    return found, unreadable, conflicts


def transcripts(out):
    """Claude transcript sessions: models and per-message usage, deduplicated by message id."""
    sessions = {}
    for path in sorted((out / 'home/.claude/projects').rglob('*.jsonl')):
        for event in lines(path):
            message = event.get('message') or {}
            if event.get('type') != 'assistant' or event.get('isApiErrorMessage') or message.get('model') == '<synthetic>':
                continue
            session = sessions.setdefault(event.get('sessionId'), dict(models=set(), messages={}))
            session['models'].add(str(message.get('model')).split('[')[0])
            if message.get('usage') and message.get('id'):
                session['messages'][message['id']] = message['usage']
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
        contexts = [e['payload'] for e in rows if e.get('type') == 'turn_context']
        found[meta['id']] = dict(models={c.get('model') for c in contexts} - {None},
                                 efforts={c.get('effort') for c in contexts} - {None},
                                 parent=source['subagent']['thread_spawn']['parent_thread_id'] if isinstance(source, dict) else None)
    return found


def inventory(out, plan):
    rollouts = traces.load(out / 'cell/trace')
    headers, header_conflicts = judge_headers(out)
    owner_threads = ({e['thread_id'] for e in lines(out / 'run/stdout') if e.get('type') == 'thread.started'}
                     if plan['engine'] == 'codex' else set())
    worker_threads = set()
    for devlyn in devlyn_dirs(out):
        for log in devlyn.rglob('*.worker-session.*.jsonl'):
            worker_threads |= {e['thread_id'] for e in lines(log) if e.get('type') == 'thread.started'}
    seated, unbound, inferences, gaps = {}, [], {}, list(header_conflicts)
    for rollout in rollouts:
        gaps += [f'{rollout["trace"]}: {gap}' for gap in rollout['gaps']]
        root = rollout.get('rollout_id')
        seat = ('owner' if root in owner_threads else 'worker' if root in worker_threads else
                'codex_judge' if root in headers else None)
        if seat is None:
            unbound.append(root)
        for thread, item in rollout['threads'].items():
            seated[thread] = dict(seat=seat if thread == root else 'child', root=root, model=item.get('model'),
                                  effort=item.get('effort'), agent_path=item.get('agent_path'))
        for call, item in rollout['inferences'].items():
            key = (root, call)
            if item['thread'] not in rollout['threads']:
                gaps.append(f'inference {call} on undeclared thread {item["thread"]}')
            if key in inferences and inferences[key]['usage'] != item['usage']:
                gaps.append(f'conflicting copies of inference {call}')
            inferences.setdefault(key, item)
    envelopes, unreadable, envelope_conflicts = claude_envelopes(out)
    stream = lines(out / 'run/stdout')
    init = next((e for e in stream if e.get('type') == 'system' and e.get('subtype') == 'init'), None)
    final = [e for e in stream if e.get('type') == 'result']
    return dict(rollouts=rollouts, seated=seated, unbound=unbound, inferences=inferences, headers=headers,
                native=native_rollouts(out),
                owner_threads=owner_threads, worker_threads=worker_threads, envelopes=envelopes, unreadable=unreadable,
                transcripts=transcripts(out), attempted=attempted(out), gaps=gaps + envelope_conflicts,
                claude_owner=dict(init_model=(init or {}).get('model'), session=(init or {}).get('session_id'),
                                  usage=final[-1].get('modelUsage') if final else None))


if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    data = inventory(out, json.loads((out / 'plan.json').read_text()))
    print(json.dumps({k: v for k, v in data.items() if k in ('unbound', 'gaps', 'attempted')}, indent=2, default=sorted))
