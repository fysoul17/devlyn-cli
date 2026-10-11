"""Prospective 0237 owner v1: frozen 0233 lifecycle with explicit Docker init.

Only the owner-container create argv changes. Historical inputs remain immutable.
The copied run body is regression-checked against 0233 except for --init.
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
_spec = importlib.util.spec_from_file_location('cell0233_init_v1', HERE.parent / '0233/cell.py')
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)
base = legacy.base
evidence = legacy.evidence
lines, docker = legacy.lines, legacy.docker
identity, preserve_tmp = legacy.identity, legacy.preserve_tmp


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
    # command when /tmp is a host bind mount (0232 SMOKE), which would disable sandboxed Codex children.
    volume = 'devlyn-0233-tmp-' + uuid.uuid4().hex
    docker('volume', 'create', '--label', 'devlyn.task=0233', volume)
    argv = ['create', '--init', '--name', name, '--label', 'devlyn.task=0233', '--network', 'bridge', '--cap-drop', 'ALL',
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

