"""Run one prepared owner in a private container: cell.py <cell> <runtime.json>. Never schedules cells.

The only kill is the hang wall. Exit 0 records any owner outcome; exit 2 means the container survived teardown.
"""
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / 'tasks.json').read_text())
_spec = importlib.util.spec_from_file_location('usage0222', HERE / 'record_usage.py')
usage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(usage)


def lines(path):
    """JSON events of a stream; non-JSON lines (warnings, progress) are ignored."""
    out = []
    for line in path.read_text(errors='replace').splitlines() if path.exists() else ():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return [event for event in out if isinstance(event, dict)]


def docker(*args, timeout=60):
    return subprocess.run(['docker', *args], capture_output=True, text=True, check=True, timeout=timeout).stdout.strip()


INTERNAL = re.compile(r'^claude-haiku-')  # Claude Code's own helper calls, never a routed role


def routed(plan):
    """Models each engine may run in this cell, from its route roles."""
    route = TASKS['routes'][plan['config']]
    roles = [route['owner'], *(route['F_roles'].values() if plan['arm'] == 'F' else ())]
    allowed = {'claude': set(), 'codex': set()}
    for role in roles:
        allowed[role['engine']] |= {role.get('model'), role.get('child_model')} - {None}
    return allowed


def walk(value, key):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from ([v] if k == key and isinstance(v, str) else walk(v, key))
    elif isinstance(value, list):
        for item in value:
            yield from walk(item, key)


def dicts(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from dicts(item)


def identity(cell, plan):
    """Bind observed models to roles; any unrouted model, reroute or reviewer mismatch is a violation."""
    allowed, violations = routed(plan), []
    sessions = {}
    for path in (cell / 'home/.codex/sessions').rglob('*.jsonl'):
        events = lines(path)
        meta = next((e['payload'] for e in events if e.get('type') == 'session_meta'), {})
        source = meta.get('source')
        parent = source['subagent']['thread_spawn']['parent_thread_id'] if isinstance(source, dict) else None
        own = usage.own_events(events)
        models = {e['payload'].get('model') for e in own if e.get('type') == 'turn_context'}
        if any(e.get('type') == 'event_msg' and (e.get('payload') or {}).get('type') == 'model_reroute' for e in own):
            violations.append(f'model_reroute in {path.name}')
        sessions[meta.get('id', path.name)] = dict(parent=parent, models=models)
        violations += [f'codex {m} unrouted ({path.name})' for m in models - allowed['codex']]
    stdout = lines(cell / 'run/stdout')
    if plan['engine'] == 'codex':
        owner_id = next((e['thread_id'] for e in stdout if e.get('type') == 'thread.started'), None)
        owner = ('UNKNOWN' if owner_id not in sessions else
                 'MATCH' if sessions[owner_id]['models'] == {plan['model']} else 'MISMATCH')
        child = TASKS['routes'][plan['config']]['owner'].get('child_model')
        for sid, session in sessions.items():
            ancestor = session['parent']
            while ancestor and ancestor != owner_id:
                ancestor = sessions.get(ancestor, {}).get('parent')
            if ancestor == owner_id and session['models'] - {child}:
                violations.append(f'native child {sid} not on {child}')
    else:
        init = next((e for e in stdout if e.get('type') == 'system' and e.get('subtype') == 'init'), None)
        owner = ('UNKNOWN' if not init else
                 'MATCH' if str(init.get('model', '')).split('[')[0] == plan['model'] else 'MISMATCH')
    final = [e for e in stdout if e.get('type') == 'result']
    claude = set(final[-1].get('modelUsage') or {}) if final else set()
    for path in (cell / 'home/.claude/projects').rglob('*.jsonl'):
        claude |= {(e.get('message') or {}).get('model') for e in lines(path)
                   if e.get('type') == 'assistant' and not e.get('isApiErrorMessage')}
    claude = {str(m).split('[')[0] for m in claude - {None, '<synthetic>'}}
    violations += [f'claude {m} unrouted' for m in claude - allowed['claude'] if not INTERNAL.match(m)]
    gaps = []
    roles = TASKS['routes'][plan['config']]['F_roles'] if plan['arm'] == 'F' else {}
    for path in (cell / 'work/.devlyn').rglob('pipeline.state.json'):
        try:
            state = json.loads(path.read_text())
        except ValueError:  # an in-place writer can be cut by the hang wall
            gaps.append(f'unreadable {path.relative_to(cell)}')
            continue
        requested = {m.split('[')[0] for m in set(walk(state, 'model_requested')) | set(walk(state, 'model_effective'))}
        violations += [f'pipeline {m} unrouted' for m in requested - allowed['claude'] - allowed['codex']]
        violations += [f'pipeline requested {d["model_requested"]} but ran {d["model_effective"]}'
                       for d in dicts(state) if d.get('model_requested') and d.get('model_effective')
                       and d['model_requested'].split('[')[0] != d['model_effective'].split('[')[0]]
        frozen = ((state.get('role_resolution') or {}).get('roles') or {})
        violations += [f'role {role} frozen as {frozen[role].get("engine")}/{frozen[role].get("model_requested")}'
                       for role, want in roles.items() if role in frozen
                       and (frozen[role].get('engine'), frozen[role].get('model_requested')) != (want['engine'], want.get('model'))]
    # 3.2.1 leaves a Codex worker's model_effective null; bind each wrapper-captured Codex worker session to its
    # rollout. Claude transcripts share the file pattern (surface-close) and are covered by the checks above.
    worker = roles.get('worker', {})
    for log in (cell / 'work/.devlyn').rglob('*.worker-session.*.jsonl'):
        thread = next((e.get('thread_id') for e in lines(log) if e.get('type') == 'thread.started'), None)
        if thread is None:
            continue
        ran = sessions.get(thread, {}).get('models')
        if worker.get('engine') != 'codex':
            violations.append(f'unexpected Codex worker session {log.name}')
        elif ran is None:
            violations.append(f'no rollout for worker session {log.name}')
        elif ran != {worker['model']}:
            violations.append(f'worker session {log.name} ran {sorted(ran)}, not {worker["model"]}')
    for result in (cell / 'work/.devlyn/reviews').glob('call-*/result.json'):
        if json.loads(result.read_text()).get('identity') == 'MISMATCH':
            violations.append('reviewer mismatch in ' + result.parent.name)
    evidence = bool(sessions or claude)
    status = ('MISMATCH' if owner == 'MISMATCH' or violations else
              'UNVERIFIED' if owner == 'UNKNOWN' and evidence else owner)
    return dict(owner=owner, status=status, violations=violations, gaps=gaps, claude_models=sorted(claude),
                codex_sessions={sid: sorted(s['models']) for sid, s in sessions.items()})


def run(cell, runtime):
    plan = json.loads((cell / 'plan.json').read_text())
    out = cell / 'run'
    out.mkdir(exist_ok=False)
    auth = Path(runtime['auth'])
    secret = Path(runtime['scratch']) / 'credentials' / plan['name']
    secret.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(auth / 'claude.json', secret / 'claude.json')
    (secret / 'claude.json').chmod(0o600)
    work, home = Path(plan['work']), Path(plan['home'])
    (home / '.claude/.credentials.json').touch()
    (home / '.codex/auth.json').touch()
    mounts = [(work, '/work', False), (home, '/home/participant', False), (Path(plan['control']), '/control', True),
              (auth / 'claude.json', '/credentials/claude.json', True), (auth / 'codex.json', '/credentials/codex.json', True),
              (auth / 'codex.json', '/home/participant/.codex/auth.json', True),
              (secret / 'claude.json', '/home/participant/.claude/.credentials.json', False),
              (work / '.devlyn/caller.json', '/work/.devlyn/caller.json', True)]
    if (work / '.devlyn/engines.json').exists():  # arm F role binding is harness setup, not owner-editable
        mounts.append((work / '.devlyn/engines.json', '/work/.devlyn/engines.json', True))
    name = 'devlyn-0222-' + uuid.uuid4().hex
    argv = ['create', '--name', name, '--label', 'devlyn.task=0222', '--network', 'bridge', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--security-opt', 'seccomp=unconfined', '--read-only',
            '--restart=no', '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            '--tmpfs', '/tmp:rw,nosuid,exec,size=536870912', '-w', '/work']
    for src, dst, readonly in mounts:
        argv += ['--mount', f'type=bind,src={src},dst={dst}' + (',readonly' if readonly else '')]
    for key, value in plan['env'].items():
        argv += ['--env', f'{key}={value}']
    argv += [plan['image'], *plan['argv']]
    record = dict(create_argv=argv, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  started_at=time.time())
    (out / 'started.json').write_text(json.dumps(record, indent=2))
    cid = docker(*argv)
    start, status = time.monotonic(), None
    try:
        with (out / 'stdout').open('xb') as stdout, (out / 'stderr').open('xb') as stderr:
            process = subprocess.Popen(['docker', 'start', '-a', cid], stdout=stdout, stderr=stderr)
            try:
                code = process.wait(timeout=plan['wall_seconds'])
                status = 'EXITED_0' if code == 0 else 'EXITED_NONZERO'
            except subprocess.TimeoutExpired:
                status = 'HANG_TIMEOUT'
    finally:
        record.update(owner_status=status, seconds=time.monotonic() - start)
        try:
            if json.loads(docker('inspect', cid))[0]['State']['Running']:
                docker('kill', cid)
            state = json.loads(docker('inspect', cid))[0]['State']
            if state['Running'] or state['Pid'] != 0:
                raise RuntimeError('container survived kill')
            docker('rm', cid)
            record['teardown'] = 'CLEAN'
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            record.update(teardown='FAILED', teardown_error=str(exc))
        shutil.rmtree(secret)
        (out / 'result.json').write_text(json.dumps(record, indent=2))
    try:
        record['identity'] = identity(cell, plan)
    except (OSError, ValueError, KeyError, TypeError) as exc:  # an apparatus defect: stop, but with a record
        record['identity'] = dict(status='UNVERIFIED', violations=[f'identity check failed: {exc}'])
    (out / 'result.json').write_text(json.dumps(record, indent=2))
    (cell / 'final.txt').write_text(final_message(lines(out / 'stdout'), plan['engine']))
    return record


def final_message(events, engine):
    for event in reversed(events):
        if engine == 'claude' and event.get('type') == 'result':
            return str(event.get('result') or '')
        if engine == 'codex' and event.get('type') == 'item.completed' and event['item'].get('type') == 'agent_message':
            return event['item'].get('text') or ''
    return ''


if __name__ == '__main__':
    result = run(Path(sys.argv[1]).resolve(), json.loads(Path(sys.argv[2]).read_text()))
    print(json.dumps({k: result[k] for k in ('owner_status', 'teardown', 'seconds')}))
    sys.exit(2 if result['teardown'] != 'CLEAN' else 0)
