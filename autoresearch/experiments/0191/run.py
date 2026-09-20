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
E = R / '.devlyn/0191'
S = R / '.git/devlyn-completion/82aaccd5949d437f761aa13f/scratch'
W = R.parent / '0191-participants'
SOURCE = ('bin/instructions.js', 'bin/instruction-templates.json', 'bin/devlyn.js', 'AGENTS.md', 'CLAUDE.md')


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
        target = seed / 'package' / name; target.parent.mkdir(parents=True, exist_ok=True)
        assert (R / name).read_bytes() == subprocess.check_output(['git', 'show', '981c55e:' + name], cwd=R), name
        shutil.copy2(R / name, target)
    (seed / 'tests').mkdir()
    shutil.copyfile(H / 'test_acceptance.py', seed / 'tests/test_acceptance.py')
    shutil.copyfile(H / 'request.md', seed / 'spec.md')
    (seed / '.gitignore').write_text('.devlyn/\n.agents/\n__pycache__/\n*.pyc\n')
    put(seed / 'spec.expected.json', dict(required_files=['package/bin/instructions.js'],
        forbidden_files=['spec.md', 'spec.expected.json', '.gitignore', 'tests/test_acceptance.py',
                         *['package/' + name for name in SOURCE if name != 'bin/instructions.js']],
        verification_commands=[dict(cmd='/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v',
                                    exit_code=0, timeout_sec=90)]))
    shutil.copyfile(Path.home() / '.codex/models_cache.json', E / 'models_cache.json')


def calibrate():
    seed = E / 'inputs/root'
    # Positive reference is for oracle calibration only, unavailable to participants.
    source = (seed / 'package/bin/instructions.js').read_text()
    old = '  fs.mkdirSync(path.dirname(file), { recursive: true });'
    reference = '''  for (const directory of [path.dirname(path.dirname(file)), path.dirname(file)]) {
    const stat = fs.lstatSync(directory, { throwIfNoEntry: false });
    if (stat && !stat.isDirectory()) {
      throw new Error(`Instruction recovery needs a real directory: ${directory}. Move it aside and rerun installation.`);
    }
    if (!stat) fs.mkdirSync(directory);
  }'''
    assert source.count(old) == 1
    variants = dict(original=source, reference=source.replace(old, reference),
        follows_links=source.replace(old, reference.replace('fs.lstatSync', 'fs.statSync')),
        guards_only_leaf=source.replace(old, reference.replace('[path.dirname(path.dirname(file)), path.dirname(file)]', '[path.dirname(file)]')),
        suppresses_incoming=source.replace(old, reference).replace('    retainFile(incoming, Buffer.from(block));', ''),
        eager_unused_guard=source.replace(old, reference).replace("  const exists = Boolean(stat);",
            "  const unused = fs.lstatSync(path.join(process.cwd(), '.devlyn'), { throwIfNoEntry: false });\n"
            "  if (unused && !unused.isDirectory()) throw new Error('Move .devlyn aside');\n  const exists = Boolean(stat);"),
        allows_inside_links=source.replace(old, reference.replace('stat && !stat.isDirectory()',
            'stat && !stat.isDirectory() && !(stat.isSymbolicLink() && fs.realpathSync(directory).startsWith(process.cwd() + path.sep))')),
        deletes_obstruction=source.replace(old, reference.replace(
            'throw new Error(`Instruction recovery needs a real directory: ${directory}. Move it aside and rerun installation.`);',
            'fs.rmSync(directory, { recursive: true, force: true });')))
    checker = module(H / 'check.py'); results = []
    for name, text in variants.items():
        with tempfile.TemporaryDirectory(dir=S) as temporary:
            base = Path(temporary); package = base / 'package'
            shutil.copytree(seed / 'package', package)
            (package / 'bin/instructions.js').write_text(text)
            rows = checker.check(package, base)
        failed = {row['check'] for row in rows if not row['pass_']}
        static = {row['check'] for row in rows if row['check'].endswith(('/backup', '/incoming'))}
        expected = {
            'original': {p for p in static if '/outside-link/' in p or '/inside-link/' in p},
            'reference': set(),
            'follows_links': {p for p in static if '/outside-link/' in p or '/inside-link/' in p},
            'guards_only_leaf': {p for p in static if p.rsplit('/', 2)[0].endswith('/.devlyn') and ('/outside-link/' in p or '/inside-link/' in p)}
                | {n + '/' + kind for n in ('AGENTS.md', 'CLAUDE.md') for kind in ('ordinary-incoming', 'exact-template-migration')},
            'suppresses_incoming': {n + '/ordinary-incoming' for n in ('AGENTS.md', 'CLAUDE.md')},
            'eager_unused_guard': {n + '/unused-recovery' for n in ('AGENTS.md', 'CLAUDE.md')},
            'allows_inside_links': {p for p in static if '/inside-link/' in p},
            'deletes_obstruction': static,
        }[name]
        assert failed == expected, (name, sorted(failed - expected), sorted(expected - failed))
        results.append(dict(variant=name, checks=rows))
    put(E / 'CALIBRATION.json', results)
    (E / 'reference.js').write_text(variants['reference'])
    print(json.dumps([{r['variant']: sum(c['pass_'] for c in r['checks'])} for r in results]))


def freeze():
    paths = [*H.glob('*'), *list((E / 'inputs').rglob('*')), E / 'models_cache.json',
        E / 'CALIBRATION.json', E / 'reference.js', R / 'AGENTS.md',
        R / '.devlyn/0179/catalog-setting.txt', R / 'autoresearch/experiments/0179/AGENTS.candidate.md',
        R / 'autoresearch/experiments/0183/launch.py', R / 'autoresearch/scripts/comparison-controller.py',
        *list((R / 'config/skills/_shared').rglob('*')), *list((R / 'config/skills/devlyn:resolve').rglob('*'))]
    put(E / 'REGISTRATION.json', dict(version=subprocess.check_output(['codex', '--version'], text=True).strip(),
        order=[dict(draw=f'{i:02}-{arm}', arm=arm, case='root')
        for i, arm in enumerate('ABCCBA', 1)],
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
        sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}))


def run():
    launch = module(H / 'launch.py')
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
