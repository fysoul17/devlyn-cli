"""Offline fixture controls; writes a new output directory, never old evidence."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    prediction_path = HERE / 'prediction.json'
    prediction = json.loads(prediction_path.read_text(encoding='utf-8'))
    summary = {
        'started_at': datetime.now(timezone.utc).isoformat(),
        'python': sys.version,
        'platform': platform.platform(),
        'prediction_sha256': hashlib.sha256(prediction_path.read_bytes()).hexdigest(),
        'cases': [],
    }
    problems = []
    for name, expected in prediction['expectations'].items():
        with tempfile.TemporaryDirectory(prefix='cfg-life-control-') as temporary:
            work = Path(temporary) / 'work'
            shutil.copytree(HERE / ('visible' if name == 'baseline' else 'gold'), work)
            if name not in ('baseline', 'gold'):
                shutil.copytree(HERE / 'hidden/alternatives' / name, work, dirs_exist_ok=True)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            result = {'case': name}
            commands = {
                'public': [sys.executable, '-B', 'checks/run_checks.py'],
                'oracle': [sys.executable, '-B', str(HERE / 'hidden/oracle.py'), str(work)],
            }
            if name == 'sharing':
                commands['sharing-probe'] = [sys.executable, '-B', '-c',
                    'from beacon.merge import merge; base={"kept": [1]}; '
                    'later={"new": [2]}; result=merge(base,later); '
                    'assert result["kept"] is base["kept"]; '
                    'assert result["new"] is later["new"]; '
                    'assert base=={"kept":[1]} and later=={"new":[2]}; '
                    'print("internal input lists shared; merge did not mutate inputs")']
            for phase, command in commands.items():
                completed = subprocess.run(command, cwd=work, env=env,
                    capture_output=True, text=True, encoding='utf-8', timeout=30)
                raw = {'command': command, 'cwd': str(work),
                    'returncode': completed.returncode,
                    'stdout': completed.stdout, 'stderr': completed.stderr}
                (output / f'{name}-{phase}.json').write_text(
                    json.dumps(raw, indent=2) + '\n', encoding='utf-8')
                result[f'{phase}_exit'] = completed.returncode
                if completed.returncode != 0:
                    problems.append(f'{name}/{phase}: unexpected exit {completed.returncode}')
                if phase == 'oracle':
                    rows = json.loads(completed.stdout)['manifestations']
                    ids = [row['id'] for row in rows]
                    if len(ids) != len(set(ids)) or any(type(row['passed']) is not bool for row in rows):
                        raise ValueError('ambiguous oracle rows')
                    passed = [row['id'] for row in rows if row['passed']]
                    failed = [row['id'] for row in rows if not row['passed']]
                    result.update(oracle_passed=len(passed), oracle_total=len(rows),
                                  passed=passed, failed=failed)
                    for key in ('oracle_passed', 'oracle_total'):
                        if key in expected and result[key] != expected[key]:
                            problems.append(f'{name}/{key}: {result[key]} != {expected[key]}')
                    for row_id in expected.get('must_fail', []) + expected.get('fails_include', []):
                        if row_id not in failed:
                            problems.append(f'{name}: expected failure missing: {row_id}')
            if result['public_exit'] != expected['public_exit']:
                problems.append(f'{name}: unexpected public result')
            summary['cases'].append(result)
    summary.update(finished_at=datetime.now(timezone.utc).isoformat(),
                   predictions_match=not problems, problems=problems)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0 if not problems else 1


if __name__ == '__main__':
    raise SystemExit(main())
