"""Deterministic grading of the 0235 selected snapshot: check.py <cell-out> <runtime.json>. Never dispatches models.

0222's evaluator, rows and verdict rules, unchanged, except where it runs: check containers mount the public tools at
/control and the oracle tree over /control/autoresearch, so participants (public tools only) never see the oracle.
Exit 0 with a verdict, 2 only when no verdict can be produced or a check container survives.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('check0222', HERE.parent / '0222/check.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
NoVerdict, packet, SECONDS = base.NoVerdict, base.packet, base.SECONDS


def in_image(runtime, work, command):
    name = 'devlyn-0231-check-' + uuid.uuid4().hex
    control = Path(runtime['control'])
    argv = ['docker', 'run', '--name', name, '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            '--tmpfs', '/tmp:rw,nosuid,exec,size=536870912', '--tmpfs', '/cell:rw,exec,mode=1777',
            '--mount', f'type=bind,src={work},dst=/cell/work,readonly',
            '--mount', f'type=bind,src={control / "public"},dst=/control,readonly',
            '--mount', f'type=bind,src={control / "oracle"},dst=/control/autoresearch,readonly',
            '--env', 'HOME=/tmp', '--env', 'TMPDIR=/tmp', '--env', 'PYTHONPATH=/cell/work/src:/control/python',
            '-w', '/cell/work', runtime['image'], 'timeout', '--kill-after=5s', f'{SECONDS}s', *command]
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=SECONDS + 30)
        return dict(argv=command, exit_code=done.returncode, timeout=done.returncode == 124,
                    stdout=done.stdout, stderr=done.stderr)
    except subprocess.TimeoutExpired as exc:
        return dict(argv=command, exit_code=None, timeout=True, stdout=str(exc.stdout or ''), stderr='host timeout')
    finally:
        probe = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=30)
        if probe.returncode == 0:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=30)
            if subprocess.run(['docker', 'inspect', name], capture_output=True, timeout=30).returncode == 0:
                raise NoVerdict('check container survived teardown')
        elif 'No such object' not in probe.stderr:
            raise NoVerdict('cannot verify check container teardown')


base.in_image = in_image  # 0222's evaluate() resolves in_image at call time
TASKS = json.loads((HERE / 'tasks.json').read_text())
base.TASKS = TASKS
task = base.task
ROWS = {t['id']: t['oracle'] for t in TASKS['tasks'] if t['id'] == 'E1'}


def evaluate(work, task_id, runtime):
    if task_id not in ROWS:
        return base.evaluate(work, task_id, runtime)
    spec = task(task_id)
    public = [in_image(runtime, work, ['sh', '-c',
               'mkdir /tmp/public-work && cp -a /cell/work/. /tmp/public-work/ && cd /tmp/public-work && ' + command])
              for command in spec['public_checks']]
    for result in public:
        base.last_json(result)
    rows, raw = [], []
    for row in ROWS[task_id]:
        result = in_image(runtime, work, ['node', '/control/autoresearch/experiments/0233/oracle.js',
                                          task_id, row, '/cell/work'])
        raw.append(result)
        base.last_json(result)
        rows.append(dict(id=row, status='PASS' if result['exit_code'] == 0 else 'FAIL'))
    return dict(public=public, rows=rows, raw=raw)


def check(out, runtime):
    baseline = json.loads((out / 'baseline.json').read_text())
    spec, snapshot = task(baseline['task']), out / 'snapshot'
    current = packet.tree(snapshot)
    changed = sorted(n for n in baseline['files'].keys() | current.keys() if baseline['files'].get(n) != current.get(n))
    violations = [n for n in changed if not packet.allowed(n, spec['allowed'])]
    result = evaluate(snapshot, spec['id'], runtime)
    (out / 'checks-raw.json').write_text(json.dumps(result, indent=2))
    public_pass = all(r['exit_code'] == 0 for r in result['public'])
    statuses = {r['status'] for r in result['rows']}
    seal = dict(public_pass=public_pass, oracle=result['rows'], scope_violations=violations, changed=changed,
                adjudication_needed='NOT_TRIGGERED' in statuses,
                product_check_pass=public_pass and statuses <= {'PASS'} and not violations,
                public=[dict(argv=r['argv'], exit_code=r['exit_code'], timeout=r['timeout'],
                             stdout_tail=r['stdout'][-2000:], stderr_tail=r['stderr'][-2000:]) for r in result['public']])
    (out / 'checks.json').write_text(json.dumps(seal, indent=2))
    return seal


if __name__ == '__main__':
    try:
        print(json.dumps(check(Path(sys.argv[1]).resolve(), json.loads(Path(sys.argv[2]).read_text()))['oracle']))
    except NoVerdict as exc:
        print('NO_VERDICT: ' + str(exc), file=sys.stderr)
        sys.exit(2)
