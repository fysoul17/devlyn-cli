"""External, immutable assessment; participant tests are a separate measure."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def score(case, submission):
    seed = BASE / case / 'seed'
    protected = ['NOTICE.txt', 'test_overlay.py' if case == 'small' else 'test_async_map.py']
    preserved = {name: (submission / name).is_file() and
                 (submission / name).read_bytes() == (seed / name).read_bytes() for name in protected}
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    checks = {}
    commands = {
        'contract': [sys.executable, str(BASE / case / 'oracle.py'), str(submission)],
        'legacy': [sys.executable, '-m', 'unittest', Path(protected[1]).stem],
        'participant_tests': [sys.executable, '-m', 'unittest', 'discover'],
    }
    for name, command in commands.items():
        try:
            result = subprocess.run(command, cwd=submission, env=env,
                                    capture_output=True, text=True, timeout=30)
            checks[name] = {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        except subprocess.TimeoutExpired as error:
            checks[name] = {'exit_code': None, 'error': 'assessment timeout',
                            'stdout': (error.stdout or b'').decode(errors='replace'),
                            'stderr': (error.stderr or b'').decode(errors='replace')}
    return {'case': case, 'protected': preserved, 'checks': checks,
            'mechanical_success': all(preserved.values()) and
            all(checks[name]['exit_code'] == 0 for name in ('contract', 'legacy')),
            'limit': 'Root scope and blind source review still required for complete product success.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=['small', 'hard'])
    parser.add_argument('submission', type=Path)
    args = parser.parse_args()
    print(json.dumps(score(args.case, args.submission.resolve()), indent=2))
