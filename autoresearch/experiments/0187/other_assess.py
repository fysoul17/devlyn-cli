"""Check sealed review/repair products; reviewer verdicts are not the oracle."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

from other import E, W, hashes, put


def run(argv, work):
    p = subprocess.run(argv, cwd=work, capture_output=True, text=True, timeout=30)
    return {'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def main():
    reg = json.loads((E / 'REGISTRATION.json').read_text())
    for name, digest in reg['sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    rows = []
    for index, (case, arm) in enumerate(reg['order'], 1):
        label = case + '-' + arm
        work = W / ('case-' + str(index))
        result = json.loads((E / (label + '-result.json')).read_text())
        assert hashes(work) == result['sha256'], label
        baseline = hashes(E / 'inputs' / case)
        changed = sorted(name for name in baseline.keys() | result['sha256'].keys()
                         if baseline.get(name) != result['sha256'].get(name))
        row = {'label': label, 'seconds': result['seconds'], 'changed': changed,
               'scope': all(name in ('palette.py', 'tests/test_regression.py') for name in changed)}
        row['functional'] = run([sys.executable, '-B', str(Path(__file__).with_name('intent_check.py')), str(work)], work)
        row['public_and_regression'] = run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], work)
        row['compatibility'] = run([sys.executable, '-B', '-c',
            'from palette import list_commands; '
            'assert all(list_commands(x) == [] for x in ("not-installed", "gemini", "")); print("PASS")'], work)
        row['requirements_complete'] = row['scope'] and all(row[k]['exit_code'] == 0
            for k in ('functional', 'public_and_regression', 'compatibility'))
        row['native_calls'] = []
        for phase in ('review', 'repair', 'recheck'):
            path = E / 'runs' / (label + '-' + phase) / 'receipt.json'
            if path.exists():
                native = json.loads(path.read_text())
                terminal = native['terminal'][-1]
                row['native_calls'].append({'phase': phase, 'seconds': native['seconds'],
                    'exit_code': native['exit_code'], 'is_error': terminal.get('is_error'),
                    'model_usage': terminal['modelUsage'], 'reported_cost_usd': terminal.get('total_cost_usd'),
                    'permission_denials': terminal.get('permission_denials', [])})
        row['native_complete'] = all(call['exit_code'] == 0 and not call['is_error']
                                    and not call['permission_denials'] for call in row['native_calls'])
        assert hashes(work) == result['sha256'], 'assessment changed sealed product'
        rows.append(row)
    put(E / 'ASSESSMENT.json', rows)
    print(json.dumps([{k: row[k] for k in ('label', 'requirements_complete', 'native_complete', 'seconds')} for row in rows]))


if __name__ == '__main__':
    main()
