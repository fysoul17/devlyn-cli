"""Seal first, then independently check artifacts; no participant repair feedback."""
from pathlib import Path
import hashlib
import importlib.util
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import time

R = Path(__file__).resolve().parents[3]
H = Path(__file__).resolve().parent
E = R / '.devlyn/0187'
W = R.parent / '0187-participants'
S = R / '.git/devlyn-completion/2e0e0a6ae08ba22e8451fd57/scratch'


def put(path, value):
    with path.open('x') as output:
        json.dump(value, output, indent=2)


def command(argv, cwd):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=90)
    return {'exit_code': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}


def main():
    registry = json.loads((E / 'REGISTRATION.json').read_text())
    for path, digest in registry['sha256'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    for row in registry['order']:
        assert (E / 'runs' / row['draw'] / 'result.json').exists(), row
    seals = {row['draw']: files(W / row['draw']) for row in registry['order']}
    put(E / 'SEALED-OUTPUTS.json', seals)
    helper = runpy.run_path(str(R / 'config/skills/_shared/task-complete.py'))
    rows = []
    for row in registry['order']:
        work = W / row['draw']
        out = E / 'runs' / row['draw']
        source = 'duration.py' if row['case'] == 'root' else 'stream.py'
        native = json.loads((out / 'result.json').read_text())
        baseline = json.loads((out / 'input.json').read_text())['baseline']
        changed = subprocess.check_output(['git', 'diff', baseline, '--name-only'], cwd=work, text=True).splitlines()
        new = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=work, text=True).splitlines()
        scope = all(p in (source, 'tests/test_regression.py') for p in changed + new)
        seed = E / 'inputs' / row['case']
        preserved = all((work / rel).is_file() and (work / rel).read_bytes() == p.read_bytes()
                        for p in seed.rglob('*') if p.is_file()
                        for rel in [p.relative_to(seed)] if str(rel) != source)
        debris = [p for p in seals[row['draw']] if not any(x in Path(p).parts for x in ('.devlyn', '.agents'))
                  and (p.endswith('.pyc') or '__pycache__' in Path(p).parts)]
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix='0187-score-', dir=S) as tmp:
            copy = Path(tmp) / 'work'
            shutil.copytree(seed, copy)
            shutil.copyfile(work / source, copy / source)
            public = command([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], copy)
            hidden = command([sys.executable, '-B', str(H / 'heldout.py'), str(copy), row['case']], copy)
        result = {**row, 'native': native, 'changed': changed, 'new': new, 'scope': scope,
                  'preserved': preserved, 'debris': debris, 'public': public, 'hidden': hidden,
                  'external_check_seconds': time.monotonic()-started}
        result['product_complete'] = scope and preserved and not debris and public['exit_code'] == hidden['exit_code'] == 0
        if row['arm'] == 'C':
            states = list((work / '.devlyn/runs').glob('*/pipeline.state.json'))
            result['archives'] = [str(p) for p in states]
            try:
                assert len(states) == 1, 'exactly one terminal archive required'
                state = json.loads(states[0].read_text())
                acceptance = {'run_id': state['run_id'], 'source_sha': state['phases']['cleanup']['post_sha']}
                helper['pipeline_acceptance'](work, acceptance, list(seals[row['draw']]), S)
                result['pipeline_acceptance'] = 'PASS'
                result['phases'] = {k: {'verdict': v.get('verdict'), 'round': v.get('round')}
                                    for k, v in state['phases'].items()}
            except (AssertionError, KeyError, ValueError, OSError, helper['CompletionError']) as error:
                result['pipeline_acceptance'] = 'FAIL'
                result['pipeline_error'] = repr(error)
        result['workflow_complete'] = (result['product_complete'] and native['exit_code'] == 0
                                       and not native['error'] and native['owned_writers_quiescent']
                                       and result.get('pipeline_acceptance', 'PASS') == 'PASS')
        rows.append(result)
    assert all(files(W / row['draw']) == seals[row['draw']] for row in registry['order'])
    put(E / 'ASSESSMENT.json', rows)
    spec = importlib.util.spec_from_file_location('telemetry0187', R / 'autoresearch/experiments/0183/telemetry.py')
    telemetry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(telemetry)
    telemetry.EVIDENCE, telemetry.WORKS = E, W
    put(E / 'TELEMETRY.json', [telemetry.collect(row['draw']) for row in rows])
    print(json.dumps([{k: row[k] for k in ('draw', 'product_complete', 'workflow_complete')} for row in rows]))


if __name__ == '__main__':
    main()
