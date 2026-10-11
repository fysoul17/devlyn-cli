"""0238 F23 supplement: exact historical d25 precision/offset inputs, never an owner prompt.

Usage: python3 f23_precision.py SNAPSHOT [--node NODE]
Exit 0: both rows pass; 1: observed product failure; 2: apparatus STOP.
Copies the product into disposable storage; never edits the supplied snapshot.
The original 0234 request and two oracle rows remain unchanged and required.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


BASE = [('a-later', '2027-01-01T00:00:00.0002Z'),
        ('z-earlier', '2027-01-01T00:00:00.0001Z')]
CASES = [
    ('submillisecond-order', 1, BASE, ['z-earlier']),
    ('offset-equivalence', 2,
     BASE + [('b-equivalent', '2027-01-01T01:00:00.000100+01:00')],
     ['b-equivalent', 'z-earlier']),
]


def wave(quantity, orders):
    return dict(warehouses=[dict(id='w', distance=0, lots=[
        dict(sku='s', lot='l', qty=quantity, expires='2028-01-01')])],
        orders=[dict(id=name, priority=1, submitted_at=stamp, lines=[
            dict(sku='s', qty=1, single_warehouse=False)]) for name, stamp in orders])


def expected(accepted):
    return dict(accepted=[dict(id=name, allocations=[
        dict(sku='s', warehouse='w', lot='l', qty=1)]) for name in accepted],
        rejected=[dict(id='a-later', reason='insufficient_stock')])


def issues(raw, accepted):
    """Grade only explicit output obligations; exhausted lots may be omitted or kept."""
    errors = []
    if raw['exit_code'] != 0:
        errors.append('successful valid input must exit 0')
    if raw['stderr'] != '':
        errors.append('successful valid input must have empty stderr')
    try:
        value = json.loads(raw['stdout'])
    except ValueError:
        return errors + ['stdout is not exactly one parseable JSON value']
    if not isinstance(value, dict) or set(value) != {'accepted', 'rejected', 'remaining'}:
        return errors + ['output must have exactly accepted, rejected, remaining']
    want = expected(accepted)
    if value['accepted'] != want['accepted']:
        errors.append('accepted order/allocation schema or stock allocation differs')
    elif any(type(allocation['qty']) not in (int, float)
             for row in value['accepted'] for allocation in row['allocations']):
        errors.append('allocation quantity must be numeric, not boolean')
    if value['rejected'] != want['rejected']:
        errors.append('rejected order/reason/schema differs')
    remaining = value['remaining']
    zero = dict(warehouse='w', sku='s', lot='l', qty=0, expires='2028-01-01')
    # The exact accepted allocations consume all input stock. As in 0234's
    # remainingMatches, exhausted rows are optional; duplicate/unknown rows are not.
    if remaining != [] and remaining != [zero]:
        errors.append('remaining stock/schema differs (zero row optional)')
    elif remaining and type(remaining[0]['qty']) not in (int, float):
        errors.append('remaining quantity must be numeric, not boolean')
    return errors


def evaluate(source, node='node'):
    source = Path(source).resolve()
    cli = source / 'bin/cli.js'
    result = dict(schema='0238-f23-precision-v1', source=str(source), rows=[])
    if not cli.is_file():
        return dict(result, status='STOP', error='snapshot has no bin/cli.js')
    result['cli_sha256'] = hashlib.sha256(cli.read_bytes()).hexdigest()
    try:
        with tempfile.TemporaryDirectory(prefix='0238-f23-precision-') as temp:
            work = Path(temp) / 'work'
            shutil.copytree(source, work, ignore=shutil.ignore_patterns('.git', 'node_modules'))
            if (source / 'node_modules').is_dir():
                (work / 'node_modules').symlink_to(source / 'node_modules', target_is_directory=True)
            for row_id, quantity, orders, accepted in CASES:
                payload = wave(quantity, orders)
                input_path = Path(temp) / (row_id + '.json')
                input_path.write_text(json.dumps(payload), encoding='utf-8')
                # Same 30-second local child bound as 0234/calibrate.py.
                command = [node, str(work / 'bin/cli.js'), 'fulfill-wave', '--input', str(input_path)]
                try:
                    run = subprocess.run(command, cwd=work, capture_output=True,
                                         text=True, timeout=30)
                except subprocess.TimeoutExpired as exc:
                    def text(value):
                        return value.decode(errors='replace') if isinstance(value, bytes) else value or ''
                    result['rows'].append(dict(id=row_id, status='STOP', input=payload,
                        error='child exceeded existing 30-second calibration bound',
                        raw=dict(exit_code=None, stdout=text(exc.stdout), stderr=text(exc.stderr))))
                    break
                raw = dict(exit_code=run.returncode, stdout=run.stdout, stderr=run.stderr)
                errors = issues(raw, accepted)
                result['rows'].append(dict(id=row_id, status='FAIL' if errors else 'PASS',
                    input=payload, expected=expected(accepted), errors=errors, raw=raw))
    except (OSError, UnicodeError) as exc:
        return dict(result, status='STOP', error=f'{type(exc).__name__}: {exc}')
    statuses = {row['status'] for row in result['rows']}
    result['status'] = 'STOP' if 'STOP' in statuses else 'FAIL' if 'FAIL' in statuses else 'PASS'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--node', default='node')
    args = parser.parse_args()
    result = evaluate(args.snapshot, args.node)
    print(json.dumps(result, ensure_ascii=False))
    return {'PASS': 0, 'FAIL': 1, 'STOP': 2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
