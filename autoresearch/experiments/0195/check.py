"""External behavioral oracle; run against an untouched participant checkout."""
from pathlib import Path
import copy
import json
import os
import runpy
import subprocess
import sys
import tempfile


def check(package, scratch):
    module = runpy.run_path(str(package / 'terminal-claim-check.py'))
    rows = []
    with tempfile.TemporaryDirectory(dir=scratch) as raw:
        root = Path(raw)
        active = root / '.devlyn/pipeline.state.json'
        active.parent.mkdir()
        base = {'run_id': 'natural-0195', 'phases': {
            'verify': {'started_at': 'start', 'completed_at': 'end', 'verdict': 'PASS'}}}

        def exercise(name, state, expected, reason=None, archived=False):
            original = json.dumps(state).encode()
            path = active
            if archived:
                path = root / '.devlyn/runs/natural-0195/pipeline.state.json'
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original)
            try:
                actual, parsed = module['classify_state_bytes'](root, path, original, archived=archived)
                passed = actual.status == expected and parsed == state and path.read_bytes() == original
                if reason:
                    passed = passed and actual.reason == reason and actual.run_id == state['run_id']
                rows.append(dict(check=name, passed=passed, actual=actual.receipt()))
            except Exception as exc:
                rows.append(dict(check=name, passed=False, error=f'{type(exc).__name__}: {exc}'))
            finally:
                path.unlink()

        for i, verdict in enumerate(([], {}, ['PASS'], {'verdict': 'PASS'}, False, True, 0, 1.5, '', 'UNKNOWN')):
            state = copy.deepcopy(base)
            state['phases']['verify']['verdict'] = verdict
            for archived in (False, True):
                exercise(f'invalid/{i}/{archived}', state, 'MALFORMED', 'verify has invalid verdict', archived)
        for missing in (False, True):
            state = copy.deepcopy(base)
            if missing:
                del state['phases']['verify']['verdict']
            else:
                state['phases']['verify']['verdict'] = None
            exercise(f'null/{missing}', state, 'INCOMPLETE:verify', 'verify completed without verdict')
        for verdict in ('PASS', 'PASS_WITH_ISSUES', 'NEEDS_WORK', 'BLOCKED'):
            state = copy.deepcopy(base)
            state['phases']['verify']['verdict'] = verdict
            exercise(f'valid/{verdict}', state, 'INCOMPLETE:final_report')
            state['phases']['final_report'] = dict(started_at='start', completed_at='end', verdict=verdict)
            exercise(f'archive/{verdict}', state, 'CLEAN', archived=True)
        state = copy.deepcopy(base)
        state['phases']['verify']['verdict'] = []
        state['phases']['plan'] = dict(started_at='start')
        exercise('precedence/open', state, 'INCOMPLETE:plan')
        state['phases']['plan'] = dict(completed_at='end')
        exercise('precedence/lifecycle', state, 'MALFORMED', 'phase plan completed without started_at')
        del state['phases']['plan']
        state['phases']['final_report'] = dict(started_at='start', completed_at='end', verdict={})
        exercise('precedence/final', state, 'MALFORMED', 'final_report completed with null or invalid verdict')

        for i, verdict in enumerate(([], {})):
            state = copy.deepcopy(base)
            state['phases']['verify']['verdict'] = verdict
            raw_state = json.dumps(state).encode()
            active.write_bytes(raw_state)
            env = dict(os.environ)
            env.pop('DEVLYN_RUN_IDS_BEFORE', None)
            proc = subprocess.run([sys.executable, '-B', str(package / 'terminal-claim-check.py'), str(root)],
                                  capture_output=True, env=env, timeout=15)
            try:
                receipt = json.loads(proc.stdout)
            except ValueError:
                receipt = None
            rows.append(dict(check=f'cli/{i}', passed=proc.returncode == 79 and not proc.stderr
                             and receipt == dict(status='MALFORMED', phase=None,
                                 reason='verify has invalid verdict', run_id='natural-0195')
                             and active.read_bytes() == raw_state,
                             exit_code=proc.returncode, stdout=proc.stdout.decode(), stderr=proc.stderr.decode()))
            active.unlink()
        archive = root / '.devlyn/runs/natural-0195/pipeline.state.json'
        archive.write_text(json.dumps(state))
        try:
            result = module['classify'](root, {'natural-0195'})
            rows.append(dict(check='before-run/exclude', passed=result.status == 'NOT_APPLICABLE'))
            result = module['classify'](root)
            rows.append(dict(check='run-set/include', passed=result.status == 'MALFORMED'))
        except Exception as exc:
            rows.append(dict(check='run-set/include', passed=False, error=f'{type(exc).__name__}: {exc}'))
        archive.unlink()
        original = subprocess.run([sys.executable, '-B', str(package / 'terminal-claim-check.py'), '--self-test'],
                                  capture_output=True, timeout=60)
        rows.append(dict(check='original/self-test', passed=original.returncode == 0,
                         stdout=original.stdout.decode(), stderr=original.stderr.decode()))
    return rows


if __name__ == '__main__':
    rows = check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    print(json.dumps(rows, indent=2))
    raise SystemExit(not all(row['passed'] for row in rows))
