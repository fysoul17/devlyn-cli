"""Model-free calibration through check.evaluate: calibrate.py <runtime.json> <out-dir> [repeats]. Never dispatches models.

Expectations are fixed from prior evidence before running: 0207 reference/mutant rules for D3/D4, and the
recorded 0185 replay outcomes (.devlyn/0185/REPLAY-RESULTS.json, ADDITIONAL-REPLAY-RESULTS.json).
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load('check0222', HERE / 'check.py')
mutants = load('calibrate0207', HERE.parent / '0207/calibrate.py')
PARTICIPANTS = Path('/Users/aipalm/.local/share/nx01/0185-participants')
# product: (source path, sha256, rows that must FAIL, rows that must be NOT_TRIGGERED); other rows PASS.
I0185 = {
    'install-1-A': (PARTICIPANTS / 'install-1-A/bin/devlyn.js', '7fda1a901071', {'release', 'terminal-alias'}, set()),
    'install-1-B': (PARTICIPANTS / 'install-1-B/bin/devlyn.js', 'fdcac1b6d347', {'release', 'terminal-alias'}, set()),
    'install-2-A': (PARTICIPANTS / 'install-2-A/bin/devlyn.js', '337e167a09e8', {'release', 'terminal-alias'}, set()),
    'install-2-B': (PARTICIPANTS / 'install-2-B/bin/devlyn.js', '6c7d3bb5c63b', {'release', 'terminal-alias'}, set()),
    'install-1-C': (PARTICIPANTS / 'install-1-C/bin/devlyn.js', 'c56eb6d8fbe0', {'absence-lock'}, set()),
    'install-2-C': (PARTICIPANTS / 'install-2-C/bin/devlyn.js', 'bf0aa17acae7', set(), set()),
    'reference': (REPO / '.devlyn/0185/source/reference.js', None, {'release', 'terminal-alias'}, {'absence-lock'}),
}


def variants(task, sources):
    """Yield (name, tree, judge) where judge(result) -> expected."""
    if task in ('D3', 'D4'):
        source = sources / check.task(task)['source']
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
        if head != check.task(task)['base_sha'] or subprocess.check_output(['git', 'status', '--porcelain'], cwd=source):
            raise ValueError(task + ' source is not the clean registered base')
        options = [('baseline', None), ('reference', None)] + [(m[0], m) for m in mutants.MUTANTS[task]]
        for name, mutant in options:
            with tempfile.TemporaryDirectory(prefix=task + '-') as temp:
                tree = Path(temp) / 'work'
                shutil.copytree(source, tree, symlinks=True, ignore=shutil.ignore_patterns('.git'))
                if name != 'baseline':
                    mutants.reference(tree, task)
                if mutant:
                    _, _, path, old, new, *count = mutant
                    mutants.replace(tree, path, old, new, count[0] if count else 1)

                def judge(result, name=name, mutant=mutant):
                    failed = {r['id'] for r in result['rows'] if r['status'] != 'PASS'}
                    # The last public check is the format gate; the 0207 reference predates it (disclosed miss).
                    public = all(p['exit_code'] == 0 for p in result['public'][:-1])
                    return (bool(failed) and public if name == 'baseline' else
                            not failed and public if name == 'reference' else mutant[1] in failed)
                yield name, tree, judge
        return
    inputs = REPO / check.task('I0185')['source_dir']
    for name, (product, prefix, fail, untriggered) in [('original', (None, None, None, None)), *I0185.items()]:
        with tempfile.TemporaryDirectory(prefix='I0185-') as temp:
            tree = Path(temp) / 'work'
            shutil.copytree(inputs, tree)
            if product:
                if prefix and not hashlib.sha256(product.read_bytes()).hexdigest().startswith(prefix):
                    raise ValueError('sealed 0185 product changed: ' + name)
                shutil.copyfile(product, tree / 'bin/devlyn.js')

            def judge(result, fail=fail, untriggered=untriggered):
                rows = {r['id']: r['status'] for r in result['rows']}
                public = all(p['exit_code'] == 0 for p in result['public'])
                if fail is None:  # the untouched original must be rejected
                    return rows['heldout'] == 'FAIL' or not public
                return public and all(status == ('FAIL' if key in fail else 'NOT_TRIGGERED' if key in untriggered
                                                 else 'PASS') for key, status in rows.items())
            yield name, tree, judge


def main(runtime_path, out, repeats=1):
    runtime = json.loads(Path(runtime_path).read_text())
    out.mkdir(parents=True, exist_ok=False)
    summary = []
    for repeat in range(repeats):
        for task in ('D3', 'D4', 'I0185'):
            for name, tree, judge in variants(task, Path(runtime['sources'])):
                result = check.evaluate(tree, task, runtime)
                load_avg = os.getloadavg()[0] if platform.system() != 'Windows' else None
                row = dict(repeat=repeat, task=task, variant=name, expected=judge(result), load=load_avg,
                           rows=result['rows'], public=[p['exit_code'] for p in result['public']])
                (out / f'{repeat}-{task}-{name}.json').write_text(json.dumps(result, indent=2))
                summary.append(row)
                print(json.dumps(row), flush=True)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))
    return 0 if all(r['expected'] for r in summary) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], Path(sys.argv[2]).resolve(), int(sys.argv[3]) if len(sys.argv) > 3 else 1))
