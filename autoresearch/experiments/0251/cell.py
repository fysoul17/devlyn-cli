"""0238 owner lifecycle with fixed access-only Claude auth via private env-file.

The configured native module retains identity, evidence, parsing and /tmp custody.
No secret value is placed in a plan or recorded Docker argument.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid


def run(out, runtime, *, native, check_auth):
    plan = json.loads((out / 'plan.json').read_text())
    # Recheck after preparation, immediately before launch: preparation can take time.
    _, blocked = check_auth(runtime)
    if blocked:
        raise ValueError('fixed authentication refused before launch: ' + blocked)
    if any(key.startswith(('ANTHROPIC_', 'CLAUDE_CODE_OAUTH_', 'CLAUDE_CODE_REMOTE_'))
           or key in ('CLAUDE_CODE_SUBSCRIPTION_TYPE', 'CLAUDE_CODE_RATE_LIMIT_TIER')
           for key in plan['env']):
        raise ValueError('plan contains a competing authentication setting')
    record_dir = out / 'run'
    record_dir.mkdir(exist_ok=False)
    auth = Path(runtime['auth'])
    home = Path(plan['home'])
    (home / '.claude/.credentials.json').touch()
    (home / '.codex/auth.json').touch()
    mounts = [(Path(plan['cell']), '/cell', False), (home, '/home/participant', False),
              (Path(plan['control']), '/control', True), (Path(plan['harness']), '/harness', True),
              (auth / 'codex.json', '/home/participant/.codex/auth.json', True)]
    name = 'devlyn-0231-' + uuid.uuid4().hex
    volume = 'devlyn-0234-tmp-' + uuid.uuid4().hex
    native.docker('volume', 'create', '--label', 'devlyn.task=0234', volume)
    argv = ['create', '--init', '--name', name, '--label', 'devlyn.task=0234', '--network', 'bridge', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--security-opt', 'seccomp=unconfined', '--read-only',
            '--restart=no', '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            '--tmpfs', '/home/participant/.codex/tmp:rw,nosuid,exec,uid=501,gid=501', '-w', '/cell/work',
            '--mount', f'type=volume,src={volume},dst=/tmp']
    for src, dst, readonly in mounts:
        argv += ['--mount', f'type=bind,src={src},dst={dst}' + (',readonly' if readonly else '')]
    for key, value in plan['env'].items():
        argv += ['--env', f'{key}={value}']
    argv += ['--env-file', str(auth / 'claude.env'), plan['image'], *plan['argv']]
    record = dict(create_argv=argv, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  tmp_volume=volume, started_at=time.time())
    (record_dir / 'started.json').write_text(json.dumps(record, indent=2))
    cid, start, status = None, None, None
    try:
        cid = native.docker(*argv)
        start = time.monotonic()
        with (record_dir / 'stdout').open('xb') as stdout, (record_dir / 'stderr').open('xb') as stderr:
            process = subprocess.Popen(['docker', 'start', '-a', cid], stdout=stdout, stderr=stderr)
            try:
                code = process.wait(timeout=plan['wall_seconds'])
                status = 'EXITED_0' if code == 0 else 'EXITED_NONZERO'
            except subprocess.TimeoutExpired:
                status = 'HANG_TIMEOUT'
    finally:
        record.update(owner_status=status, seconds=time.monotonic() - start if start is not None else None,
                      ended_at=time.time())
        try:
            if cid is not None:
                # Config.Env now contains a bearer token. Request only State, never the whole inspect document.
                if json.loads(native.docker('inspect', '--format', '{{json .State}}', cid))['Running']:
                    native.docker('kill', cid)
                state = json.loads(native.docker('inspect', '--format', '{{json .State}}', cid))
                if state['Running'] or state['Pid'] != 0:
                    raise RuntimeError('container survived kill')
                native.docker('rm', cid)
                native.preserve_tmp(volume, Path(plan['tmp']), plan['image'])
            else:
                native.docker('volume', 'rm', volume)
            record['teardown'] = 'CLEAN'
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            stderr = getattr(exc, 'stderr', None)
            stderr = stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr
            record.update(teardown='FAILED', teardown_error=' '.join(filter(None, (str(exc), stderr))))
        (record_dir / 'result.json').write_text(json.dumps(record, indent=2))
    try:
        record['identity'] = native.identity(out, plan)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        record['identity'] = dict(status='UNVERIFIED', violations=[f'identity check failed: {exc}'])
    (record_dir / 'result.json').write_text(json.dumps(record, indent=2))
    (out / 'final.txt').write_text(native.base.final_message(native.lines(record_dir / 'stdout'), plan['engine']))
    return record
