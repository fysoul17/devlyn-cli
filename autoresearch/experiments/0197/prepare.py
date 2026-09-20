"""Prepare real source once and calibrate the oracle before native products exist."""
from pathlib import Path
import importlib.util
import json
import shutil

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
E = REPO / '.devlyn/0197'
REL = Path('config/skills/_shared/task-complete.py')
spec = importlib.util.spec_from_file_location('checks', HERE / 'check.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def prepare():
    work = E / 'input'
    work.mkdir()
    shutil.copytree(REPO / REL.parent, work / REL.parent, ignore=shutil.ignore_patterns('__pycache__'))
    (work / 'tests').mkdir()
    shutil.copyfile(HERE / 'test_smoke.py', work / 'tests/test_smoke.py')
    shutil.copyfile(HERE / 'request.md', work / 'spec.md')
    shutil.copyfile(REPO / 'autoresearch/experiments/0179/AGENTS.candidate.md', work / 'AGENTS.md')
    (work / '.gitignore').write_text('.devlyn/\n__pycache__/\n*.pyc\n')
    (work / 'spec.expected.json').write_text(json.dumps({'verification_commands': ['python3 -B -m unittest discover -s tests -v', 'python3 -B config/skills/_shared/task-complete.py --self-test']}, indent=2))
    original = (work / REL).read_text()
    body = (HERE / 'reference.py').read_text()
    reference = original.replace('\ndef main():', '\n' + body + '\n\ndef main():').replace('    allocation = actions.add_parser("allocate")', '    listing = actions.add_parser("history")\n    listing.add_argument("--repo", default=".")\n    allocation = actions.add_parser("allocate")').replace('result = (allocate(args)', 'result = (history(args) if args.action == "history" else allocate(args)')
    controls = {'original': original, 'reference': reference,
        'alternative': reference.replace('return path.lstat().st_size', 'return os.lstat(path).st_size'),
        'mutant-common': reference.replace("common = Path(git(work, 'rev-parse', '--path-format=absolute', '--git-common-dir'))", "common = work / '.git'"),
        'mutant-glob': reference.replace('any(fnmatch.fnmatchcase(p.name, pattern) for pattern in patterns)', 'p.name in patterns'),
        'mutant-scope': reference.replace("if data.get('worktree') == str(work):", 'if True:')}
    rows = []
    for name, code in controls.items():
        if name not in ('original', 'reference'):
            assert code != reference, 'No-op control: ' + name
        candidate = E / 'controls' / name
        shutil.copytree(work, candidate)
        (candidate / REL).write_text(code)
        result = checks.check(candidate, include_regression=False)
        result.update(control=name, expected_pass=name in ('reference', 'alternative'))
        rows.append(result)
        print(json.dumps({k: result[k] for k in ('control', 'passed', 'passed_checks', 'total', 'expected_pass')}), flush=True)
    (E / 'CALIBRATION.json').write_text(json.dumps(rows, indent=2))
    assert all(r['passed'] == r['expected_pass'] for r in rows)


if __name__ == '__main__':
    prepare()
