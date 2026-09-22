"""Bounded deterministic checks and scope seal for one finished owner cell."""
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import uuid

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(cell, runtime_path):
    runtime = json.loads(runtime_path.read_text())
    terminal = json.loads((cell / 'run/result.json').read_text())
    if terminal['failure'] or terminal['classes'] or not terminal['container_removed']:
        raise ValueError('owner transport/accounting/teardown failure; stop screen')
    baseline = json.loads((cell / 'baseline.json').read_text())
    task, work = baseline['task'], cell / 'work'
    if digest(cell / 'home/.codex/config.toml') != baseline['config_sha256']:
        raise ValueError('sealed configuration changed; stop screen')
    current = {str(p.relative_to(work)): digest(p) for p in work.rglob('*')
               if p.is_file() and '.git' not in p.relative_to(work).parts}
    changed = sorted(n for n in baseline['files'].keys() | current.keys()
                     if baseline['files'].get(n) != current.get(n))
    allowed = {str(p.relative_to(work)) for pattern in task['allowed'] for p in work.glob(pattern)}
    allowed.update(n for n in baseline['files'] if any(Path(n).match(p) for p in task['allowed']))
    violations = [n for n in changed if n not in allowed and not n.startswith('.devlyn/')]
    if current.get('.devlyn/caller.json') != baseline['files']['.devlyn/caller.json']:
        raise ValueError('caller changed; stop screen')
    start = time.monotonic()
    container = 'devlyn-0211-check-' + uuid.uuid4().hex

    def expired(_signum, _frame):
        raise TimeoutError('deterministic check deadline; stop screen')

    signal.signal(signal.SIGALRM, expired)
    signal.alarm(110)
    try:
        command = ['node', '--test'] if task['id'] in ('D1', 'D3') else ['python', '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider']
        argv = ['docker', 'run', '--name', container, '--rm', '--network', 'none', '--read-only',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '256',
                '--memory', '4g', '--cpus', '2', '--tmpfs', '/tmp:rw,nosuid,exec,size=536870912',
                '--env', 'HOME=/tmp', '--env', 'PYTHONPATH=/work/src:/control/python',
                '--env', 'PATH=/control/less/usr/bin:/opt/codex/bin:/opt/codex/codex-path:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin',
                '--mount', f'type=bind,src={work},dst=/work,readonly',
                '--mount', f'type=bind,src={runtime["control"]},dst=/control,readonly',
                runtime['image'], 'timeout', '--kill-after=2s', '90s', *command]
        public = subprocess.run(argv, capture_output=True, text=True, timeout=100)
        spec = importlib.util.spec_from_file_location('calibrate', HERE.parent / '0207/calibrate.py')
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        with tempfile.TemporaryDirectory(prefix='oracle-', dir=runtime['scratch']) as temp:
            scratch = Path(temp) / 'fixtures'
            scratch.mkdir()
            requirements = oracle.evaluate(work, task['id'], SimpleNamespace(
                node=runtime['node'], python310=runtime['python310']), scratch)
        record = dict(public=dict(argv=argv, exit_code=public.returncode, stdout=public.stdout,
                                  stderr=public.stderr), requirements=requirements)
        (cell / 'checks-raw.json').write_text(json.dumps(record, indent=2))
        if public.returncode == 124:
            raise TimeoutError('public suite timeout; stop screen')
        checks = dict(public=dict(argv=command, exit_code=public.returncode,
                                  stdout_tail=public.stdout[-2000:], stderr=public.stderr),
                      requirements=requirements['checks'], scope_violations=violations,
                      evidence_limit='Full command output is retained separately; this assessment packet includes the public-suite tail and every requirement result.')
        (cell / 'checks.json').write_text(json.dumps(checks, indent=2))
        seal = dict(eligible_for_assessment=True,
            product_check_pass=public.returncode == 0 and all(c['pass'] for c in requirements['checks']) and not violations,
            changed=changed, source_sha256=current)
    finally:
        signal.alarm(0)
        probe = subprocess.run(['docker', 'inspect', container], capture_output=True, text=True, timeout=5)
        if probe.returncode == 0:
            state = json.loads(probe.stdout)[0]['State']
            if state['Running']:
                subprocess.run(['docker', 'kill', container], capture_output=True, check=True, timeout=5)
            subprocess.run(['docker', 'rm', container], capture_output=True, check=True, timeout=5)
        elif 'No such object' not in probe.stderr:
            raise RuntimeError('cannot verify deterministic container teardown')
    seal['seconds'] = time.monotonic()-start
    if seal['seconds'] > 120:
        raise TimeoutError('deterministic checks including teardown exceeded120s')
    (cell / 'local-seal.json').write_text(json.dumps(seal, indent=2))
    print(json.dumps(checks))


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
