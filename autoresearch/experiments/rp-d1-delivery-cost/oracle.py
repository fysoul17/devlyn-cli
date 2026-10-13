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

    def rejects(args, error):
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                f(*args)
            except error as exc:
                return not isinstance(exc, SystemExit) or exc.code == 2
        return False

    if task == 'BV':
        f = module.is_expired
        moment = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        checks = {
            'boundary': lambda: all(f(value, value) is True for value in (-5, 0, 10, 1.5)),
            'before-after': lambda: f(9, 10) is False and f(11, 10) is True and f(-11, -10) is False,
            'datetime': lambda: (f(moment, moment) is True and
                f(moment - datetime.timedelta(microseconds=1), moment) is False and
                f(moment + datetime.timedelta(microseconds=1), moment) is True),
            'errors': lambda: all(rejects(args, TypeError) for args in ((None, 0), (0, None), (0, '0'))),
        }
    else:
        f = module.parse_limit
        checks = {
            'default': lambda: f([]) == 10,
            'zero': lambda: f(['--limit', '0']) == 0 and f(['--limit=0']) == 0,
            'positive': lambda: all(f(['--limit', str(n)]) == n for n in (1, 10, 23)),
            'errors': lambda: all(rejects((args,), SystemExit) for args in (
                ['--limit', '-1'], ['--limit', 'bad'], ['--limit', '1.5'], ['--limit'], ['--unknown'])),
        }
    for name, probe in checks.items():
        try:
            results[name] = dict(id=name, status='PASS' if probe() else 'FAIL')
        except (Exception, SystemExit):
            results[name] = dict(id=name, status='FAIL', reason='participant raised during check')
    regression = work / 'tests/test_regression.py'
    results['regression'] = dict(id='regression', status='FAIL')
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
        results['regression']['status'] = 'PASS' if codes == [0, 1] else 'FAIL'
    return dict(schema='rp-d1-oracle-v1', rows=[results[name] for name in ROWS[task]])


if __name__ == '__main__':
    try:
        print(json.dumps(check(sys.argv[1], Path(sys.argv[2]))))
    except Exception as exc:
        print(json.dumps(dict(status='UNKNOWN', reason=type(exc).__name__)))
        raise SystemExit(2)
