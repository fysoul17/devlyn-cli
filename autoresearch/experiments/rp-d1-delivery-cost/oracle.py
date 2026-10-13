"""Independent hidden checks, including a regression replay on original source."""
import contextlib
import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
IMPLEMENTATION = {'BV': 'src/expiry/__init__.py', 'Z0': 'src/limitcli/__init__.py'}
ROWS = {'BV': ['boundary', 'before-after', 'datetime', 'errors', 'regression'],
        'Z0': ['default', 'zero', 'positive', 'errors', 'regression']}


def check(task, work):
    implementation = IMPLEMENTATION[task]
    spec = importlib.util.spec_from_file_location('subject', work / implementation)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    results = {}
    if task == 'BV':
        f = module.is_expired
        results['boundary'] = all(f(value, value) is True for value in (-5, 0, 10, 1.5))
        results['before-after'] = f(9, 10) is False and f(11, 10) is True and f(-11, -10) is False
        moment = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        results['datetime'] = (f(moment, moment) is True and
            f(moment - datetime.timedelta(microseconds=1), moment) is False and
            f(moment + datetime.timedelta(microseconds=1), moment) is True)
        cases = [(None, 0), (0, None), (0, '0')]
        errors = []
        for args in cases:
            try:
                f(*args)
            except TypeError:
                errors.append(True)
            else:
                errors.append(False)
        results['errors'] = all(errors)
    else:
        f = module.parse_limit
        results['default'] = f([]) == 10
        results['zero'] = f(['--limit', '0']) == 0 and f(['--limit=0']) == 0
        results['positive'] = all(f(['--limit', str(n)]) == n for n in (1, 10, 23))
        errors = []
        for args in (['--limit', '-1'], ['--limit', 'bad'], ['--limit', '1.5'], ['--limit'], ['--unknown']):
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    f(args)
                except SystemExit as exc:
                    errors.append(exc.code == 2)
                else:
                    errors.append(False)
        results['errors'] = all(errors)
    regression = work / 'tests/test_regression.py'
    results['regression'] = False
    if regression.is_file() and not regression.is_symlink():
        codes = []
        with tempfile.TemporaryDirectory(prefix='rp-d1-regression-') as temporary:
            for label in ('candidate', 'original'):
                dest = Path(temporary) / label
                shutil.copytree(HERE / 'fixtures' / task, dest)
                shutil.copy2(regression, dest / 'tests/test_regression.py')
                if label == 'candidate':
                    shutil.copy2(work / implementation, dest / implementation)
                env = {k: v for k, v in os.environ.items() if not k.startswith(('PYTHON', 'PYTEST'))}
                env.update(PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONPATH=str(dest / 'src'))
                result = subprocess.run([sys.executable, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                                         'tests/test_regression.py'], cwd=dest, capture_output=True, text=True,
                                        timeout=600, env=env)
                if result.returncode not in (0, 1, 5):
                    raise ValueError('regression replay did not produce a test verdict')
                codes.append(result.returncode)
        results['regression'] = codes == [0, 1]
    return dict(schema='rp-d1-oracle-v1', rows=[dict(id=name, status='PASS' if results[name] else 'FAIL')
                                            for name in ROWS[task]])


if __name__ == '__main__':
    try:
        print(json.dumps(check(sys.argv[1], Path(sys.argv[2]))))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        print(json.dumps(dict(status='UNKNOWN', reason=type(exc).__name__)))
        raise SystemExit(2)
