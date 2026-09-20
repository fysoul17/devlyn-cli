"""Assess sealed products, actual canonical acceptance, and explicit incomplete rows."""
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
from run import R, H, E, S, W, hashes, module, put


def main():
    registry = json.loads((E / 'REGISTRATION.json').read_text())
    checker = module(H / 'check.py')
    helper = runpy.run_path(str(R / 'config/skills/_shared/task-complete.py'))
    rows = []
    seed = E / 'inputs/root'
    source = 'package/bin/instructions.js'
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
        protected = hashes(seed)
        preserved = all(sealed.get(p) == value for p, value in protected.items() if p != source)
        debris = [p for p in sealed if not p.startswith(('.agents/', '.devlyn/'))
                  and (p.endswith('.pyc') or '__pycache__' in p or sealed[p]['value'].startswith('symlink:'))]
        started = time.monotonic()
        with tempfile.TemporaryDirectory(dir=S, prefix='assess-') as temporary:
            from pathlib import Path
            base = Path(temporary); copy = base / 'work'; shutil.copytree(seed, copy)
            shutil.copyfile(work / source, copy / source)
            added = work / 'tests/test_regression.py'
            if added.is_file(): shutil.copyfile(added, copy / 'tests/test_regression.py')
            public = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                cwd=copy, capture_output=True, text=True, timeout=90)
            external = checker.check(copy / 'package', base)
        result = dict(row, status='SEALED', native=native, changed=changed, new=new, scope=scope,
            preserved=preserved, debris=debris, public=dict(exit_code=public.returncode, stdout=public.stdout, stderr=public.stderr),
            external=external, external_seconds=time.monotonic()-started,
            product_complete=scope and preserved and not debris and public.returncode == 0 and all(c['pass_'] for c in external),
            execution_scope='PENDING_TOOL_AUDIT', scope_minimality='PENDING_DIFF_REVIEW')
        if row['arm'] == 'C':
            states = list((work / '.devlyn/runs').glob('*/pipeline.state.json'))
            try:
                assert len(states) == 1, 'one canonical archive required'
                state = json.loads(states[0].read_text())
                helper['pipeline_acceptance'](work, dict(run_id=state['run_id'],
                    source_sha=state['phases']['cleanup']['post_sha']), list(sealed), S)
                result['pipeline_acceptance'] = 'PASS'
                result['run_id'] = state['run_id']
            except (AssertionError, KeyError, ValueError, OSError, helper['CompletionError']) as exc:
                result['pipeline_acceptance'] = 'FAIL'; result['pipeline_error'] = repr(exc)
        result['mechanical_workflow_complete'] = (result['product_complete'] and native['exit_code'] == 0
            and not native['error'] and native['owned_writers_quiescent']
            and result.get('pipeline_acceptance', 'PASS') == 'PASS')
        assert hashes(work) == sealed, 'Assessment mutated a sealed participant'
        rows.append(result)
    put(E / 'ASSESSMENT.json', rows)
    print(json.dumps([{k: row.get(k) for k in ('draw', 'status', 'product_complete', 'mechanical_workflow_complete')} for row in rows]))


if __name__ == '__main__':
    main()
