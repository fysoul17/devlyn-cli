"""0265 owner: 0237's v1 lifecycle (0233's with explicit Docker init), plus four things.

A B cell's plan names the frozen package folder (plan['install']), mounted read-only at /install so `devlyn run` can
start the engine; A has no such mount. run/result.json records how the owner container ended (Docker's OOMKilled
flag and exit code), so run_cell.py can tell a memory kill from an owner outcome. identity() holds a Codex session
that started before the owner to no model (DESIGN Q7). And the credential copy, volume and container are acquired
inside the lifecycle that removes them (run). mounts() and create_argv() are the container a cell runs in;
instructions.py's launch probe (DESIGN Q2) runs its probes in the same container, without credentials.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import time
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('cell0233_0265', HERE.parent / '0233/cell.py')
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)
base = legacy.base
evidence = legacy.evidence
lines, docker = legacy.lines, legacy.docker
preserve_tmp = legacy.preserve_tmp


def identity(out, plan):
    """0233's identity plus one 0265 rule (DESIGN Q7). `devlyn run codex` reads its config through `codex app-server`
    before it starts the owner, so in a Codex cell a traced session whose trace did not start at or after the owner's
    first trace was not launched by the owner: holding a model seat or running an inference there is a violation. A
    session the owner launches stays listed only, as 0233 lists it."""
    result = legacy.identity(out, plan)
    if plan['engine'] != 'codex':
        return result
    started = {}
    for manifest in (out / 'cell/trace').glob('trace-*/manifest.json'):
        try:
            record = json.loads(manifest.read_text())
        except ValueError:
            continue  # 0232's trace reader already records an unreadable manifest as a gap
        if isinstance(record, dict) and isinstance(record.get('started_at_unix_ms'), int):
            started[record.get('rollout_id')] = record['started_at_unix_ms']
    owner = min((started[thread] for thread, (seat, _, _) in result['codex_seats'].items()
                 if seat == 'owner' and thread in started), default=None)
    early = [s for s in result['owner_launched_sessions'] if s['engine'] == 'codex' and s['model']
             and not (owner is not None and started.get(s['session'], owner - 1) >= owner)]
    result['violations'] += [f'codex session {s["session"]} did not start after the owner and ran {s["model"]}'
                             for s in early]
    if early:
        result['status'] = 'MISMATCH'
    return result


def mounts(plan, credentials=()):
    """The owner container's bind mounts: the cell's folders, the given credential files and, for B, the package."""
    found = [(Path(plan['cell']), '/cell', False), (Path(plan['home']), '/home/participant', False),
             (Path(plan['control']), '/control', True), (Path(plan['harness']), '/harness', True), *credentials]
    if plan.get('install'):
        found.append((Path(plan['install']), '/install', True))
    return found


def create_argv(plan, name, volume, binds, env, command):
    """`docker create` arguments for a cell's container: its limits, its /tmp volume, mounts, environment and command."""
    argv = ['create', '--init', '--name', name, '--label', 'devlyn.task=0233', '--network', 'bridge', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--security-opt', 'seccomp=unconfined', '--read-only',
            '--restart=no', '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            # Codex keeps per-process helper links under CODEX_HOME/tmp/arg0; on the host bind mount a second codex
            # process's janitor cannot see the live lock and deletes them (0224 Amendment 1).
            '--tmpfs', '/home/participant/.codex/tmp:rw,nosuid,exec,uid=501,gid=501', '-w', '/cell/work',
            '--mount', f'type=volume,src={volume},dst=/tmp']
    for src, dst, readonly in binds:
        argv += ['--mount', f'type=bind,src={src},dst={dst}' + (',readonly' if readonly else '')]
    for key, value in env.items():
        argv += ['--env', f'{key}={value}']
    return argv + [plan['image'], *command]


def run(out, runtime):
    """The owner's container from the cell's first credential copy to its teardown. Everything acquired (the per-cell
    credential copy, the /tmp volume, the container) is acquired inside the lifecycle whose finally ends it, so an
    exception anywhere after the copy is made leaves no copy in scratch and no volume or container behind."""
    plan = json.loads((out / 'plan.json').read_text())
    record_dir = out / 'run'
    record_dir.mkdir(exist_ok=False)
    auth = Path(runtime['auth'])
    secret = Path(runtime['scratch']) / 'credentials' / plan['name']
    name = 'devlyn-0231-' + uuid.uuid4().hex
    # /tmp is a per-cell Docker volume, copied to plan['tmp'] after teardown: Codex's Linux sandbox refuses to run any
    # command when /tmp is a host bind mount (0232 SMOKE), which would disable sandboxed Codex children.
    volume = 'devlyn-0233-tmp-' + uuid.uuid4().hex
    record = dict(source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    cid, start, status = None, time.monotonic(), None
    secret.mkdir(parents=True, exist_ok=False)
    try:
        shutil.copyfile(auth / 'claude.json', secret / 'claude.json')
        (secret / 'claude.json').chmod(0o600)
        home = Path(plan['home'])
        (home / '.claude/.credentials.json').touch()
        (home / '.codex/auth.json').touch()
        credentials = [(auth / 'codex.json', '/home/participant/.codex/auth.json', True),
                       (secret / 'claude.json', '/home/participant/.claude/.credentials.json', False)]
        record['tmp_volume'] = volume  # from here on the volume may exist
        docker('volume', 'create', '--label', 'devlyn.task=0233', volume)
        argv = create_argv(plan, name, volume, mounts(plan, credentials), plan['env'], plan['argv'])
        record.update(create_argv=argv, started_at=time.time())
        (record_dir / 'started.json').write_text(json.dumps(record, indent=2))
        cid = docker(*argv)
        start = time.monotonic()
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
            if cid is None and (record_dir / 'started.json').is_file():  # `docker create` gave no answer, yet may
                cid = docker('ps', '-aq', '--no-trunc', '--filter', f'name=^/{name}$') or None  # have made it
            if cid is not None:
                if json.loads(docker('inspect', cid))[0]['State']['Running']:
                    docker('kill', cid)
                state = json.loads(docker('inspect', cid))[0]['State']
                record['container'] = dict(oom_killed=state.get('OOMKilled'), exit_code=state.get('ExitCode'))
                if state['Running'] or state['Pid'] != 0:
                    raise RuntimeError('container survived kill')
                docker('rm', cid)
            if 'tmp_volume' in record:
                preserve_tmp(volume, Path(plan['tmp']), plan['image'])
            record['teardown'] = 'CLEAN'
        except (OSError, RuntimeError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
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

