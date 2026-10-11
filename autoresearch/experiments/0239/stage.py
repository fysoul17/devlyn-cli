"""One-shot offline staging of the registered 0239 packages, tasks and control."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}


def stage(dest, packs, template):
    old = read(template)
    metadata = read(packs / 'packages.json')
    if set(metadata['packages']) != {'B', 'C'}:
        raise ValueError('expected exactly B and C')
    for arm, package in metadata['packages'].items():
        if sha(packs / (arm + '.tgz')) != package['sha256']:
            raise ValueError('package archive changed: ' + arm)
    tasks = read(HERE / 'tasks-foreground-smoke-draft.json')
    prior = read(HERE.parent / '0237/tasks-confirmation-max.json')
    task = next(t for t in prior['tasks'] if t['id'] == 'CF-CONFIG')
    task.update(id='CFG-LIFE', domain='child-lifetime-development', stratum='exposed-development',
                eq3_dir='autoresearch/experiments/0239/fixtures/CFG-LIFE')
    # New oracle names are bound by the prospectively predicted control output.
    rows = read(HERE / 'fixtures/CFG-LIFE/controls/pinned-run-1/gold-oracle.json')
    task['oracle'] = [row['id'] for row in json.loads(rows['stdout'])['manifestations']]
    if task['request'] != (HERE / 'fixtures/CFG-LIFE/goal.md').read_text().strip():
        raise ValueError('ordinary goal differs from original task')
    tasks['tasks'].append(task)
    dest.mkdir(parents=True, exist_ok=False, mode=0o700)
    control = dest / 'control'
    control.mkdir()
    for name in ('public', 'oracle'):
        shutil.copytree(Path(old['control']) / name, control / name, symlinks=True)
    oracle = control / 'oracle/eq3/CFG-LIFE/oracle.py'
    oracle.parent.mkdir(parents=True)
    shutil.copyfile(HERE / 'fixtures/CFG-LIFE/hidden/oracle.py', oracle)
    for arm, package in metadata['packages'].items():
        target = control / 'packages' / arm
        target.mkdir(parents=True)
        with tarfile.open(packs / (arm + '.tgz')) as archive:
            payload = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                       for m in archive if m.isfile()}
            if payload != package['files']:
                raise ValueError('package payload changed: ' + arm)
            archive.extractall(target, filter='data')
        if tree(target) != package['files']:
            raise ValueError('extracted package differs: ' + arm)
    write(dest / 'control.manifest.json', {'manifests': {
        name: tree(control / name) for name in ('public', 'oracle', 'packages')}})
    write(dest / 'tasks.json', tasks)
    shutil.copyfile(packs / 'packages.json', dest / 'packages.json')
    runtime = {**old, 'control': str(control), 'output': str(dest / 'out-smoke'),
               'tasks_file': str(dest / 'tasks.json'), 'source_root': str(REPO),
               'scratch': str(dest / 'scratch'), 'phase': 'smoke', 'boot_catalogs': {}}
    write(dest / 'runtime-smoke.json', runtime)
    write(dest / 'staging.json', {'stage_sha256': sha(Path(__file__)),
        'template_sha256': sha(template), 'files': {
            name: sha(dest / name) for name in ('tasks.json', 'packages.json',
                                               'control.manifest.json', 'runtime-smoke.json')}})
    return runtime


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--packs', type=Path, required=True)
    parser.add_argument('--template', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(stage(args.destination.resolve(), args.packs.resolve(), args.template.resolve())))
