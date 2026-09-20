"""Check copied artifacts while preserving sealed participant workspaces."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from run import E, H, S, W, hashes, module, put


def main():
    registry = json.loads((E / 'REGISTRATION.json').read_text())
    checker = module(H / 'check.py')
    rows = []
    seed, source = E / 'inputs/root', 'package/terminal-claim-check.py'
    for row in registry['order']:
        out, work = E / 'runs' / row['draw'], W / row['draw']
        if not (out / 'sealed.json').exists():
            rows.append(dict(row, status='INCOMPLETE' if out.exists() else 'NOT_RUN'))
            continue
        sealed = json.loads((out / 'sealed.json').read_text())
        assert hashes(work) == sealed, row['draw']
        native = json.loads((out / 'result.json').read_text())
        baseline = json.loads((out / 'input.json').read_text())['baseline']
        changed = subprocess.check_output(['git', 'diff', baseline, '--name-only'], cwd=work, text=True).splitlines()
        new = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=work, text=True).splitlines()
        scope = all(p in (source, 'tests/test_regression.py') for p in changed + new)
        preserved = all(sealed.get(p) == value for p, value in hashes(seed).items() if p != source)
        debris = [p for p in sealed if not p.startswith(('.agents/', '.devlyn/'))
                  and (p.endswith('.pyc') or '__pycache__' in p or sealed[p]['value'].startswith('symlink:'))]
        started = time.monotonic()
        with tempfile.TemporaryDirectory(dir=S, prefix='assess-') as temporary:
            base = Path(temporary); copy = base / 'work'; shutil.copytree(seed, copy)
            shutil.copyfile(work / source, copy / source)
            added = work / 'tests/test_regression.py'
            if added.is_file(): shutil.copyfile(added, copy / 'tests/test_regression.py')
            checks = {}
            for label, argv in (
                ('public', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v']),
                ('self', [sys.executable, '-B', source, '--self-test']),
            ):
                result = subprocess.run(argv, cwd=copy, capture_output=True, text=True, timeout=90)
                checks[label] = dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
            external = checker.check(copy / 'package', base)
        complete = (scope and preserved and not debris and all(c['exit_code'] == 0 for c in checks.values())
                    and all(c['passed'] for c in external))
        rows.append(dict(row, status='SEALED', native=native, changed=changed, new=new, scope=scope,
            preserved=preserved, debris=debris, checks=checks, external=external,
            external_seconds=time.monotonic()-started, product_complete=complete,
            mechanical_workflow_complete=complete and native['exit_code'] == 0 and not native['error']
                and native['owned_writers_quiescent'],
            execution_scope='PENDING_TOOL_AUDIT', scope_minimality='PENDING_DIFF_REVIEW'))
        assert hashes(work) == sealed, 'Assessment mutated a sealed participant'
    put(E / 'ASSESSMENT.json', rows)
    print(json.dumps([{k: row.get(k) for k in ('draw', 'status', 'product_complete', 'mechanical_workflow_complete')} for row in rows]))


if __name__ == '__main__':
    main()
