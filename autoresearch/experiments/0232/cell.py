"""Run one prepared 0232 owner in a private container: cell.py <cell> <runtime.json>. Never schedules cells.

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
_spec = importlib.util.spec_from_file_location('evidence0231c', HERE / 'evidence.py')
evidence = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(evidence)
lines, docker, INTERNAL = base.lines, base.docker, base.INTERNAL
devlyn_dirs = evidence.devlyn_dirs


def identity(out, plan):
    """Every seat's native model (and Codex effort) against the registered route. An unrouted model, a wrong effort,
    an unbound Codex process or a reroute is a violation; a seat that ran without any native model record is a gap
    (UNVERIFIED); an owner with no evidence at all never ran (UNKNOWN). Lost usage records are not identity gaps.
    A review launcher call runs its engine's registered reviewer pin; which engine it used is methodology, read by
    compliance.py, not identity."""
    inv, expect = evidence.inventory(out, plan), evidence.seats(plan)
    violations, gaps = [], []
    for thread, seat in sorted(inv['seated'].items()):
        if seat['seat'] is None:
            violations.append(f'unbound Codex process {seat["root"]}')
            continue
        want = expect[seat['seat']]
        native = inv['native'].get(thread) or {}
        for field, values in (('model', native.get('models')), ('effort', native.get('efforts'))):
            if values and seat[field] is None:  # an incomplete trace: that field from the rollout bound by the same id
                seat = dict(seat, **{field: next(iter(values)) if len(values) == 1 else str(sorted(values))})
            elif values and values != {seat[field]}:
                violations.append(f'{seat["seat"]} {thread}: trace {field} {seat[field]} contradicts its rollout {sorted(values)}')
        if want.get('engine') != 'codex':
            violations.append(f'{seat["seat"]} ran on codex but is registered on {want.get("engine")}')
        elif seat['model'] is None:
            gaps.append(f'{seat["seat"]} {thread} without a native model record')
        elif seat['model'] != want.get('model') or (want.get('effort') and seat['effort'] != want['effort']):
            violations.append(f'{seat["seat"]} {thread} ran {seat["model"]}/{seat["effort"]}, '
                              f'registered {want.get("model")}/{want.get("effort")}')
    for (root, call), item in inv['inferences'].items():  # the model each inference actually ran
        seat = inv['seated'].get(item['thread'], {}).get('seat')
        if seat and item['model'] and item['model'] != expect[seat].get('model'):
            violations.append(f'{seat} inference {call} ran {item["model"]}, registered {expect[seat].get("model")}')
    traced = {t for t, s in inv['seated'].items() if t == s['root']}  # roots with their own trace records
    for seat, threads in (('owner', inv['owner_threads']), ('worker', inv['worker_threads']),
                          ('reviewer', inv['review_threads'])):
        for thread in sorted(threads - traced):  # no own trace: the rollout, bound by the same thread id, still names it
            native = inv['native'].get(thread)
            want = expect[seat]
            if not native or not native['models']:
                gaps.append(f'{seat} {thread} has neither a trace nor a rollout model record')
            elif native['models'] != {want.get('model')} or (want.get('effort') and native['efforts'] != {want['effort']}):
                violations.append(f'{seat} {thread} rollout ran {sorted(native["models"])}/{sorted(native["efforts"])}')
    bound_roots = inv['owner_threads'] | inv['worker_threads']
    for thread, native in inv['native'].items():  # untraced native children, found by ancestry to a bound launch
        ancestor, seen = native['parent'], set()
        while ancestor and ancestor not in bound_roots and ancestor not in seen:
            seen.add(ancestor)
            ancestor = (inv['native'].get(ancestor) or {}).get('parent')
        if not native['parent'] or ancestor not in bound_roots or thread in inv['seated']:
            continue
        want = expect['child']
        if native['models'] != {want['model']} or (want.get('effort') and native['efforts'] != {want['effort']}):
            violations.append(f'native child {thread} ran {sorted(native["models"])}/{sorted(native["efforts"])}')
    for session, header in inv['headers'].items():
        want = expect['codex_judge']
        if header['model'] != want['model'] or header['effort'] != want.get('effort'):
            violations.append(f'codex judge header {session} names {header["model"]}/{header["effort"]}')
    for path in (out / 'home/.codex/sessions').rglob('*.jsonl'):
        if any(e.get('type') == 'event_msg' and (e.get('payload') or {}).get('type') == 'model_reroute' for e in lines(path)):
            violations.append(f'model_reroute in {path.name}')
    claude_models = {expect['owner']['model']} if plan['engine'] == 'claude' else set()
    claude_models |= {expect['claude_judge']['model'], evidence.REVIEWERS['claude']['model']}
    owner = 'UNKNOWN'
    if plan['engine'] == 'claude':
        init = inv['claude_owner']['init_model']
        owner = 'UNKNOWN' if not init else 'MATCH' if init.split('[')[0] == plan['model'] else 'MISMATCH'
        owner_models = {m.split('[')[0] for m in (inv['claude_owner']['usage'] or {})}
        violations += [f'claude owner ran {m}' for m in owner_models - {plan['model']} if not INTERNAL.match(m)]
    else:
        roots = [s for t, s in inv['seated'].items() if s['seat'] == 'owner' and t == s['root']]
        models = {s['model'] for s in roots} | {m for thread in inv['owner_threads'] for m in (inv['native'].get(thread) or {}).get('models', ())}
        owner = ('UNKNOWN' if not inv['owner_threads'] else 'UNVERIFIED' if not models - {None} else
                 'MATCH' if models - {None} == {plan['model']} else 'MISMATCH')
    for session, envelope in inv['envelopes'].items():  # a judge's or a Claude review's registered model
        violations += [f'claude result {session} ran {m}' for m in envelope['models']
                       if m.split('[')[0] not in {expect['claude_judge']['model'], evidence.REVIEWERS['claude']['model']}
                       and not INTERNAL.match(m)]
    for session, transcript in inv['transcripts'].items():
        violations += [f'claude session {session} ran {m}' for m in transcript['models'] - claude_models if not INTERNAL.match(m)]
    status = ('MISMATCH' if owner == 'MISMATCH' or violations else 'UNKNOWN' if owner == 'UNKNOWN' else
              'UNVERIFIED' if gaps or owner == 'UNVERIFIED' else 'MATCH')
    return dict(owner=owner, status=status, violations=violations, gaps=gaps,
                codex_seats={t: [s['seat'], s['model'], s['effort']] for t, s in inv['seated'].items()})


def preserve_tmp(volume, dest, image):
    """Copy the cell's /tmp volume into dest (tar skips sockets), then remove the volume. On failure the volume stays
    for recovery and the caller records a teardown failure."""
    docker('run', '--rm', '--network', 'none', '--user', '0', '--mount', f'type=volume,src={volume},dst=/src,readonly',
           '--mount', f'type=bind,src={dest},dst=/dst', '--entrypoint', 'bash', image, '-c',
           'set -o pipefail; tar -C /src -cf - . | tar -C /dst -xpf -', timeout=600)
    docker('volume', 'rm', volume)


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
    mounts = [(Path(plan['cell']), '/cell', False), (home, '/home/participant', False),
              (Path(plan['control']), '/control', True), (Path(plan['harness']), '/harness', True),
              (auth / 'codex.json', '/home/participant/.codex/auth.json', True),
              (secret / 'claude.json', '/home/participant/.claude/.credentials.json', False)]
    name = 'devlyn-0231-' + uuid.uuid4().hex
    # /tmp is a per-cell Docker volume, copied to plan['tmp'] after teardown: Codex's Linux sandbox refuses to run any
    # command when /tmp is a host bind mount (0232 SMOKE), which would disable every sandboxed Codex reviewer, judge
    # and worker.
    volume = 'devlyn-0232-tmp-' + uuid.uuid4().hex
    docker('volume', 'create', '--label', 'devlyn.task=0232', volume)
    argv = ['create', '--name', name, '--label', 'devlyn.task=0231', '--network', 'bridge', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--security-opt', 'seccomp=unconfined', '--read-only',
            '--restart=no', '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            # Codex keeps per-process helper links under CODEX_HOME/tmp/arg0; on the host bind mount a second codex
            # process's janitor cannot see the live lock and deletes them (0224 Amendment 1).
            '--tmpfs', '/home/participant/.codex/tmp:rw,nosuid,exec,uid=501,gid=501', '-w', '/cell/work',
            '--mount', f'type=volume,src={volume},dst=/tmp']
    for src, dst, readonly in mounts:
        argv += ['--mount', f'type=bind,src={src},dst={dst}' + (',readonly' if readonly else '')]
    for key, value in plan['env'].items():
        argv += ['--env', f'{key}={value}']
    argv += [plan['image'], *plan['argv']]
    record = dict(create_argv=argv, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  tmp_volume=volume, started_at=time.time())
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
            preserve_tmp(volume, Path(plan['tmp']), plan['image'])
            record['teardown'] = 'CLEAN'
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            stderr = getattr(exc, 'stderr', None)  # bytes on a timeout, even when the call asked for text
            stderr = stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr
            record.update(teardown='FAILED', teardown_error=' '.join(filter(None, (str(exc), stderr))))
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
