"""Run one prepared 0231 owner in a private container: cell.py <cell> <runtime.json>. Never schedules cells.

The only kill is the hang wall. Exit 0 records any owner outcome; exit 2 means the container survived teardown.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('cell0222', HERE.parent / '0222/cell.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
_spec = importlib.util.spec_from_file_location('trace0231', HERE / 'trace_usage.py')
traces = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(traces)
TASKS = base.TASKS
lines, walk, dicts, docker, INTERNAL = base.lines, base.walk, base.dicts, base.docker, base.INTERNAL
# Container paths the owner can write, and where each is preserved on the host.
WRITABLE = {'/cell': 'cell', '/tmp': 'tmp', '/home/participant': 'home'}


def routed(plan):
    """Models each engine may run in this cell: the owner, its native children and every product role."""
    route = TASKS['routes'][plan['config']]
    allowed = {'claude': set(), 'codex': set()}
    for role in [route['owner'], *route['product_roles'].values()]:
        allowed[role['engine']] |= {role.get('model'), role.get('child_model')} - {None}
    return allowed


def devlyn_dirs(out):
    """Every `.devlyn` directory the owner could have used: the anchor, any linked worktree and their run archives."""
    return sorted(p for name in WRITABLE.values() for p in (out / name).rglob('.devlyn') if p.is_dir())


def identity(out, plan):
    """Bind observed models to the registered routes; an unrouted model, a reroute or a frozen-role mismatch is a
    violation. A missing model record for a call that ran is a gap, which leaves the status UNVERIFIED."""
    allowed, violations, gaps = routed(plan), [], []
    sessions = {}
    for path in (out / 'home/.codex/sessions').rglob('*.jsonl'):
        events = lines(path)
        meta = next((e['payload'] for e in events if e.get('type') == 'session_meta'), {})
        source = meta.get('source')
        parent = source['subagent']['thread_spawn']['parent_thread_id'] if isinstance(source, dict) else None
        own = base.usage.own_events(events)
        models = {e['payload'].get('model') for e in own if e.get('type') == 'turn_context'}
        if any(e.get('type') == 'event_msg' and (e.get('payload') or {}).get('type') == 'model_reroute' for e in own):
            violations.append(f'model_reroute in {path.name}')
        sessions[meta.get('id', path.name)] = dict(parent=parent, models=models)
        violations += [f'codex {m} unrouted ({path.name})' for m in models - allowed['codex']]
    traced = traces.models(out / 'cell/trace')  # every Codex inference, ephemeral judges included
    for thread, models in traced.items():
        violations += [f'codex {m} unrouted (trace {thread})' for m in models - allowed['codex']]
    stdout = lines(out / 'run/stdout')
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
    for path in (out / 'home/.claude/projects').rglob('*.jsonl'):
        claude |= {(e.get('message') or {}).get('model') for e in lines(path)
                   if e.get('type') == 'assistant' and not e.get('isApiErrorMessage')}
    roles = TASKS['routes'][plan['config']]['product_roles']
    for devlyn in devlyn_dirs(out):
        for path in devlyn.rglob('*.output.json'):  # separate `claude -p` runs (judges) keep their own results
            try:
                claude |= set((json.loads(path.read_text(errors='replace')) or {}).get('modelUsage') or {})
            except (ValueError, AttributeError):
                gaps.append(f'unreadable Claude result {path.relative_to(out)}')
        for path in devlyn.rglob('pipeline.state.json'):
            try:
                state = json.loads(path.read_text())
            except ValueError:  # an in-place writer can be cut by the hang wall
                gaps.append(f'unreadable {path.relative_to(out)}')
                continue
            requested = {m.split('[')[0] for m in set(walk(state, 'model_requested')) | set(walk(state, 'model_effective'))}
            violations += [f'pipeline {m} unrouted' for m in requested - allowed['claude'] - allowed['codex']]
            violations += [f'pipeline requested {d["model_requested"]} but ran {d["model_effective"]}'
                           for d in dicts(state) if d.get('model_requested') and d.get('model_effective')
                           and d['model_requested'].split('[')[0] != d['model_effective'].split('[')[0]]
            violations += base.frozen_mismatch((state.get('role_resolution') or {}).get('roles') or {}, roles)
    claude = {str(m).split('[')[0] for m in claude - {None, '<synthetic>'}}
    violations += [f'claude {m} unrouted' for m in claude - allowed['claude'] if not INTERNAL.match(m)]
    evidence = bool(sessions or claude or traced)
    status = ('MISMATCH' if owner == 'MISMATCH' or violations else
              'UNVERIFIED' if (owner == 'UNKNOWN' and evidence) or gaps else owner)
    return dict(owner=owner, status=status, violations=violations, gaps=gaps, claude_models=sorted(claude),
                codex_sessions={sid: sorted(s['models']) for sid, s in sessions.items()},
                codex_traces={thread: sorted(models) for thread, models in traced.items()})


def run(out, runtime):
    plan = json.loads((out / 'plan.json').read_text())
    record_dir = out / 'run'
    record_dir.mkdir(exist_ok=False)
    auth = Path(runtime['auth'])
    secret = Path(runtime['scratch']) / 'credentials' / plan['name']
    secret.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(auth / 'claude.json', secret / 'claude.json')
    (secret / 'claude.json').chmod(0o600)
    home = Path(plan['home'])
    (home / '.claude/.credentials.json').touch()
    (home / '.codex/auth.json').touch()
    mounts = [(Path(plan['cell']), '/cell', False), (Path(plan['tmp']), '/tmp', False), (home, '/home/participant', False),
              (Path(plan['control']), '/control', True), (Path(plan['harness']), '/harness', True),
              (auth / 'codex.json', '/home/participant/.codex/auth.json', True),
              (secret / 'claude.json', '/home/participant/.claude/.credentials.json', False)]
    name = 'devlyn-0231-' + uuid.uuid4().hex
    argv = ['create', '--name', name, '--label', 'devlyn.task=0231', '--network', 'bridge', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--security-opt', 'seccomp=unconfined', '--read-only',
            '--restart=no', '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            # Codex keeps per-process helper links under CODEX_HOME/tmp/arg0; on the host bind mount a second codex
            # process's janitor cannot see the live lock and deletes them (0224 Amendment 1).
            '--tmpfs', '/home/participant/.codex/tmp:rw,nosuid,exec,uid=501,gid=501', '-w', '/cell/work']
    for src, dst, readonly in mounts:
        argv += ['--mount', f'type=bind,src={src},dst={dst}' + (',readonly' if readonly else '')]
    for key, value in plan['env'].items():
        argv += ['--env', f'{key}={value}']
    argv += [plan['image'], *plan['argv']]
    record = dict(create_argv=argv, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  started_at=time.time())
    (record_dir / 'started.json').write_text(json.dumps(record, indent=2))
    cid = docker(*argv)
    start, status = time.monotonic(), None
    try:
        with (record_dir / 'stdout').open('xb') as stdout, (record_dir / 'stderr').open('xb') as stderr:
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
        (record_dir / 'result.json').write_text(json.dumps(record, indent=2))
    try:
        record['identity'] = identity(out, plan)
    except (OSError, ValueError, KeyError, TypeError) as exc:  # an apparatus defect: stop, but with a record
        record['identity'] = dict(status='UNVERIFIED', violations=[f'identity check failed: {exc}'])
    (record_dir / 'result.json').write_text(json.dumps(record, indent=2))
    (out / 'final.txt').write_text(base.final_message(lines(record_dir / 'stdout'), plan['engine']))
    return record


if __name__ == '__main__':
    result = run(Path(sys.argv[1]).resolve(), json.loads(Path(sys.argv[2]).read_text()))
    print(json.dumps({k: result[k] for k in ('owner_status', 'teardown', 'seconds')}))
    sys.exit(2 if result['teardown'] != 'CLEAN' else 0)
