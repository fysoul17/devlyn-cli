"""Configure existing frozen transport; never rewrite historical experiment files."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

R = Path(__file__).resolve().parents[3]
H = Path(__file__).resolve().parent
E = R / '.devlyn/0192'
S = R / '.git/devlyn-completion/568b50d6e8964d26156f3300/scratch'
W = R.parent / '0192-participants'
SOURCE = tuple('config/skills/_shared/' + name for name in ('archive_run.py', 'process-evidence.py', 'invocation-receipt.py', 'platform-support.py', 'resolve-bootstrap.py'))


def module(path):
    spec = importlib.util.spec_from_file_location('loaded_' + path.stem, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


def hashes(root):
    return {str(p.relative_to(root)): dict(mode=p.lstat().st_mode & 0o777,
                value='symlink:' + str(p.readlink()) if p.is_symlink() else hashlib.sha256(p.read_bytes()).hexdigest())
            for p in root.rglob('*') if (p.is_symlink() or p.is_file()) and '.git' not in p.relative_to(root).parts}


def prepare():
    seed = E / 'inputs/root'; seed.mkdir(parents=True)
    for name in SOURCE:
        target = seed / 'package' / Path(name).name; target.parent.mkdir(parents=True, exist_ok=True)
        assert (R / name).read_bytes() == subprocess.check_output(['git', 'show', 'bcbe4e7:' + name], cwd=R), name
        shutil.copy2(R / name, target)
    (seed / 'tests').mkdir()
    shutil.copyfile(H / 'test_acceptance.py', seed / 'tests/test_acceptance.py')
    shutil.copyfile(H / 'request.md', seed / 'spec.md')
    (seed / '.gitignore').write_text('.devlyn/\n.agents/\n__pycache__/\n*.pyc\n')
    put(seed / 'spec.expected.json', dict(required_files=['package/archive_run.py'],
        forbidden_files=['spec.md', 'spec.expected.json', '.gitignore', 'tests/test_acceptance.py',
                         *['package/' + Path(name).name for name in SOURCE if not name.endswith('/archive_run.py')]],
        verification_commands=[dict(cmd='/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v',
                                    exit_code=0, timeout_sec=90)]))
    shutil.copyfile(Path.home() / '.codex/models_cache.json', E / 'models_cache.json')


def calibrate():
    seed = E / 'inputs/root'
    source = (seed / 'package/archive_run.py').read_text()
    old = '            shutil.move(str(source), str(target))\n            completed.append((source, target))'
    new = """            try:
                shutil.move(str(source), str(target))
            except OSError:
                target.unlink(missing_ok=True)
                raise
            completed.append((source, target))"""
    assert source.count(old) == 1
    positive = source.replace(old, new)
    variants = dict(original=source, reference=positive,
        rename_only=positive.replace('shutil.move(str(source), str(target))', '__import__("os").rename(source, target)'),
        swallows_error=positive.replace('                raise\n            completed', '                return 0\n            completed'),
        no_prior_rollback=positive.replace('reversed(completed)', '[]'),
        clobbers_collision=positive.replace('if target.exists() or target.is_symlink():\n            raise ArchiveError', 'if False:\n            raise ArchiveError'))
    checker = module(H / 'check.py'); results = []
    for name, content in variants.items():
        with tempfile.TemporaryDirectory(dir=S) as temporary:
            base = Path(temporary); package = base / 'package'
            shutil.copytree(seed / 'package', package)
            (package / 'archive_run.py').write_text(content)
            rows = checker.check(package, base)
        failed = {row['check'] for row in rows if not row['pass_']}
        expected = {
            'original': {r['check'] for r in rows if r['check'].startswith(('copy/', 'metadata/', 'unlink/'))},
            'reference': set(),
            'rename_only': {'cross-filesystem'} | {r['check'] for r in rows if r['check'].startswith(('copy/', 'metadata/', 'unlink/'))},
            'swallows_error': {r['check'] for r in rows if r['check'].startswith(('copy/', 'metadata/', 'unlink/'))},
            'no_prior_rollback': {r['check'] for r in rows if r['check'].startswith(('copy/', 'metadata/', 'unlink/')) and '/a.log.md/' not in r['check']},
            'clobbers_collision': {'collision', 'link-collision', 'existing-selftests'},
        }[name]
        for row in rows:
            if row['pass_']: continue
            expected_reason = {
                'original': 'original bytes/modes or unrelated/partial output changed',
                'reference': '',
                'rename_only': 'simulated cross-device' if row['check'] == 'cross-filesystem' else 'required failure not reached',
                'swallows_error': 'original error not propagated',
                'no_prior_rollback': 'original bytes/modes or unrelated/partial output changed',
                'clobbers_collision': 'collision archive violation was accepted' if row['check'] == 'existing-selftests' else 'invalid input accepted',
            }[name]
            assert expected_reason in row['error'], (name, row)
        results.append(dict(variant=name, checks=rows))
        if failed != expected:
            put(E / ('CALIBRATION-FAIL-' + name + '.json'), results)
            raise AssertionError((name, sorted(failed - expected), sorted(expected - failed)))
    put(E / 'CALIBRATION.json', results)
    (E / 'reference.py').write_text(positive)
    print(json.dumps([{r['variant']: sum(c['pass_'] for c in r['checks'])} for r in results]))


def freeze():
    paths = [*H.glob('*'), *list((E / 'inputs').rglob('*')), E / 'models_cache.json',
        E / 'CALIBRATION.json', E / 'reference.py', E / 'REPRODUCTION.json', R / 'AGENTS.md',
        R / '.devlyn/0179/catalog-setting.txt', R / 'autoresearch/experiments/0179/AGENTS.candidate.md',
        R / 'autoresearch/experiments/0191/launch.py', R / 'autoresearch/scripts/comparison-controller.py',
        *list((R / 'config/skills/_shared').rglob('*')), *list((R / 'config/skills/devlyn:resolve').rglob('*'))]
    put(E / 'REGISTRATION.json', dict(version=subprocess.check_output(['codex', '--version'], text=True).strip(),
        order=[dict(draw=f'{i:02}-{arm}', arm=arm, case='root')
        for i, arm in enumerate('ABCCBA', 1)],
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
        sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}))


def run():
    launch = module(R / 'autoresearch/experiments/0191/launch.py')
    launch.EVIDENCE, launch.SCRATCH, launch.WORKS = E, S, W
    registry = json.loads((E / 'REGISTRATION.json').read_text())
    for row in registry['order']:
        out = E / 'runs' / row['draw']
        if out.exists():
            raise RuntimeError('Existing draw; do not silently resume or reroll: ' + row['draw'])
        previous = dict(os.environ)
        try:
            assert subprocess.check_output(['codex', '--version'], text=True).strip() == registry['version']
            os.environ['TMPDIR'] = str(W / row['draw'])
            sys.argv = ['launch.py', row['draw'], row['arm'], row['case']]
            launch.main()
        finally:
            os.environ.clear(); os.environ.update(previous)
        put(out / 'sealed.json', hashes(W / row['draw']))
        result = json.loads((out / 'result.json').read_text())
        assert not result['error'] and result['owned_writers_quiescent'], result
        events = [json.loads(line) for line in (out / 'stdout').read_text().splitlines() if line.strip()]
        if result['exit_code'] == 124:
            continue  # The registered native deadline is a scored workflow failure, not a reroll.
        assert any(e.get('type') == 'turn.completed' for e in events), 'Missing native completion; inspect terminal error'
        if row['arm'] == 'C':
            assert list((W / row['draw'] / '.devlyn/runs').glob('*/pipeline.state.json')), 'Full archive missing; stop'


if __name__ == '__main__':
    {'prepare': prepare, 'calibrate': calibrate, 'freeze': freeze, 'run': run}[sys.argv[1]]()
