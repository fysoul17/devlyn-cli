"""Deterministic grading inside the pinned image: check.py <cell> <runtime.json>. Never dispatches models.

Exit 0 with a verdict (pass or fail), 2 only when no verdict can be produced or a check container survives.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import uuid

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / 'tasks.json').read_text())
SECONDS = TASKS['watchdog_seconds']['evaluator']
_spec = importlib.util.spec_from_file_location('packet0222', HERE / 'packet.py')
packet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packet)
ORACLE_D = ("import json,importlib.util,sys;from pathlib import Path;from types import SimpleNamespace as N;"
            "s=importlib.util.spec_from_file_location('c','/control/autoresearch/experiments/0207/calibrate.py');"
            "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);Path('/tmp/fixtures').mkdir();"
            "r=m.evaluate(Path('/cell/work'),sys.argv[1],N(node='/usr/local/bin/node',python310=None),Path('/tmp/fixtures'));"
            "print(json.dumps(dict(checks=r['checks'],cleanup=not any(Path('/tmp/fixtures').iterdir()))))")
REPLAYS = {'release': ('replay.js', 'release'), 'alias': ('replay.js', 'alias'),
           'terminal-alias': ('replay-terminal.js', 'alias'), 'absence-lock': ('replay-absence.js', None)}


class NoVerdict(RuntimeError):
    pass


def task(task_id):
    return next(t for t in TASKS['tasks'] if t['id'] == task_id)


def in_image(runtime, work, command):
    name = 'devlyn-0222-check-' + uuid.uuid4().hex
    argv = ['docker', 'run', '--name', name, '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '256', '--memory', '4g', '--cpus', '2',
            '--tmpfs', '/tmp:rw,nosuid,exec,size=536870912', '--tmpfs', '/cell:rw,exec,mode=1777',
            '--mount', f'type=bind,src={work},dst=/cell/work,readonly',
            '--mount', f'type=bind,src={runtime["control"]},dst=/control,readonly',
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


def last_json(record):
    """The oracle's JSON verdict; None when the product crashed it. Docker/exec startup failure is NoVerdict."""
    if record['exit_code'] in (125, 126, 127) or (record['exit_code'] is None and not record['timeout']):
        raise NoVerdict('evaluator did not run: ' + record['stderr'][-500:])
    if record['exit_code'] != 0:  # printed JSON does not count if the harness then hung or crashed
        return None
    try:
        return json.loads(record['stdout'].strip().splitlines()[-1])
    except (IndexError, ValueError):
        return None


def evaluate(work, task_id, runtime):
    """Public checks plus the task oracle; returns rows with status PASS, FAIL or NOT_TRIGGERED."""
    spec = task(task_id)
    public = [in_image(runtime, work, ['sh', '-c', cmd]) for cmd in spec['public_checks']]
    for record in public:
        last_json(record)
    rows, raw = [], []
    if task_id in ('D3', 'D4'):
        record = in_image(runtime, work, ['python3', '-B', '-c', ORACLE_D, task_id])
        raw.append(record)
        result = last_json(record)
        if result is None:  # the product crashed or hung the oracle
            rows = [dict(id=task_id + '.oracle', status='FAIL')]
        elif not result['cleanup']:
            raise NoVerdict('oracle fixtures were not cleaned')
        else:
            rows = [dict(id=r['id'], status='PASS' if r['pass'] else 'FAIL') for r in result['checks']]
    elif 'oracle_commands' in spec:
        for index, command in enumerate(spec['oracle_commands']):
            record = in_image(runtime, work, ['sh', '-c', command])
            raw.append(record)
            last_json(record)
            rows.append(dict(id=f'{task_id}.{index + 1}', status='PASS' if record['exit_code'] == 0 else 'FAIL'))
    else:
        product = '/cell/work/bin/devlyn.js'
        oracle = '/control/autoresearch/experiments/'
        record = in_image(runtime, work, ['env', 'PRODUCT=' + product, 'node', '--test', oracle + '0185/heldout.js'])
        raw.append(record)
        last_json(record)  # raises only if the evaluator itself did not start
        rows.append(dict(id='heldout', status='PASS' if record['exit_code'] == 0 else 'FAIL'))
        for kind, (script, argument) in REPLAYS.items():
            record = in_image(runtime, work, ['node', oracle + '0222/oracle/' + script, product,
                                              *([argument] if argument else [])])
            raw.append(record)
            result = last_json(record)
            if result is None:  # the product crashed or hung the replay harness
                rows.append(dict(id=kind, status='FAIL'))
                continue
            fired = result.get('failed') and result.get('contender') if kind == 'absence-lock' else result.get('fired')
            rows.append(dict(id=kind, status='PASS' if result['passed'] else 'FAIL' if fired else 'NOT_TRIGGERED'))
    return dict(public=public, rows=rows, raw=raw)


def check(cell, runtime):
    baseline = json.loads((cell / 'baseline.json').read_text())
    spec, work = task(baseline['task']), cell / 'work'
    current = packet.tree(work)
    changed = sorted(n for n in baseline['files'].keys() | current.keys() if baseline['files'].get(n) != current.get(n))
    violations = [n for n in changed if not packet.allowed(n, spec['allowed'])]
    result = evaluate(work, spec['id'], runtime)
    (cell / 'checks-raw.json').write_text(json.dumps(result, indent=2))
    public_pass = all(r['exit_code'] == 0 for r in result['public'])
    statuses = {r['status'] for r in result['rows']}
    seal = dict(public_pass=public_pass, oracle=result['rows'], scope_violations=violations, changed=changed,
                adjudication_needed='NOT_TRIGGERED' in statuses,
                product_check_pass=public_pass and statuses <= {'PASS'} and not violations,
                public=[dict(argv=r['argv'], exit_code=r['exit_code'], timeout=r['timeout'],
                             stdout_tail=r['stdout'][-2000:], stderr_tail=r['stderr'][-2000:]) for r in result['public']])
    (cell / 'checks.json').write_text(json.dumps(seal, indent=2))
    return seal


if __name__ == '__main__':
    try:
        print(json.dumps(check(Path(sys.argv[1]).resolve(), json.loads(Path(sys.argv[2]).read_text()))['oracle']))
    except NoVerdict as exc:
        print('NO_VERDICT: ' + str(exc), file=sys.stderr)
        sys.exit(2)
