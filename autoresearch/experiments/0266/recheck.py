"""Rerun of failed timing rows (DESIGN "Grading"): recheck.py <runtime.json>. Never dispatches models.

For every D3 or D4 slot whose final checks.json has a failed public check or oracle row, that check runs twice more,
serially, on the graded snapshot, exactly as the cell's check.py ran it (its container argv, limits and readers, under
the host check lock), and OUT/timing-recheck.json records both reruns. A row is timing_suspect only when both reruns
pass. A check that fails for a reason that is not a wall-clock deadline fails again; nothing here guesses the reason.
The D oracle evaluates all its rows in one container (0222/check.py), so its two reruns serve every failed row of the
cell, and the synthetic D3.oracle/D4.oracle row passes only when the oracle runs and every row passes.
Resumable: a cell already recorded with both reruns is skipped. Readings keep the inline result.
"""
import fcntl
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CELLS = HERE / 'cells.tsv'
TASKS = ('D3', 'D4')


def load(name):
    """run_cell's resolution: this folder, then 0265, then 0256, then 0233."""
    local = HERE / f'{name}.py'
    source = next((folder / local.name for folder in (HERE, HERE.parent / '0265', HERE.parent / '0256')
                   if (folder / local.name).is_file()), HERE.parent / '0233' / local.name)
    spec = importlib.util.spec_from_file_location(name + '0266r', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load('check')


def failed(checks):
    """Check ids of the inline failures: public:<index> and the oracle row ids as checks.json names them."""
    return ([f'public:{i}' for i, item in enumerate(checks['public']) if item['exit_code'] != 0]
            + [row['id'] for row in checks['oracle'] if row['status'] != 'PASS'])


def public_rerun(runtime, snapshot, task, index):
    record = check.in_image(runtime, snapshot, ['sh', '-c', check.task(task)['public_checks'][index]])
    check.base.last_json(record)  # NoVerdict when the evaluator itself did not start
    return 'PASS' if record['exit_code'] == 0 else 'FAIL'


def oracle_rerun(runtime, snapshot, task):
    """{row id: PASS|FAIL} from one oracle container, or None when the product crashed or hung the oracle."""
    record = check.in_image(runtime, snapshot, ['python3', '-B', '-c', check.base.ORACLE_D, task])
    result = check.base.last_json(record)
    if result is None:
        return None
    if not result['cleanup']:
        raise check.NoVerdict('oracle fixtures were not cleaned')
    return {row['id']: 'PASS' if row['pass'] else 'FAIL' for row in result['checks']}


def locked(runtime, function, *args):
    """The host check lock run_cell holds for its check phase, so a rerun never overlaps a lane's checks."""
    with open(runtime['check_lock'], 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return function(*args)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def recheck_cell(runtime, out, task):
    checks = json.loads((out / 'checks.json').read_text())
    ids = failed(checks)
    snapshot = out / 'snapshot'
    reruns = {check_id: [] for check_id in ids}
    for _ in range(2):
        oracle = None
        if any(not check_id.startswith('public:') for check_id in ids):
            oracle = locked(runtime, oracle_rerun, runtime, snapshot, task)
        for check_id in ids:
            if check_id.startswith('public:'):
                status = locked(runtime, public_rerun, runtime, snapshot, task, int(check_id.split(':', 1)[1]))
            elif oracle is None:
                status = 'FAIL'
            elif check_id == f'{task}.oracle':
                status = 'PASS' if set(oracle.values()) == {'PASS'} else 'FAIL'
            else:
                status = oracle[check_id]
            reruns[check_id].append(status)
    return {check_id: dict(inline='FAIL', reruns=statuses, timing_suspect=statuses == ['PASS', 'PASS'])
            for check_id, statuses in reruns.items()}


def recheck(runtime):
    out_root = Path(runtime['output'])
    path = out_root / 'timing-recheck.json'
    result = json.loads(path.read_text()) if path.is_file() else dict(schema=1, cells={})
    for line in CELLS.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        name, task = line.split()[:2]
        if task not in TASKS or name in result['cells']:
            continue
        verdict = out_root / f'verdict-{name}.json'
        if not verdict.is_file():
            raise SystemExit(f'{name}: no verdict yet')
        out = out_root / name
        if not (out / 'checks.json').is_file():
            print(f'{name}: final attempt has no checks.json; nothing to rerun', file=sys.stderr)
            continue
        if not failed(json.loads((out / 'checks.json').read_text())):
            continue
        result['cells'][name] = recheck_cell(runtime, out, task)
        path.write_text(json.dumps(result, indent=2) + '\n')
    path.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    try:
        print(json.dumps(recheck(json.loads(Path(sys.argv[1]).read_text())), indent=1))
    except check.NoVerdict as exc:
        print('NO_VERDICT: ' + str(exc), file=sys.stderr)
        sys.exit(2)
