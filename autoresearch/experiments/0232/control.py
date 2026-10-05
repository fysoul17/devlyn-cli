"""Assemble the 0232 control trees: control.py <sources> <cache> <out>. Never dispatches models.

<out>/public                    participant /control: public tools only
<out>/oracle                    evaluator-only files, mounted over /control/autoresearch in check containers
<out>/packages/<arm>/package    each installing arm's package (I, F), mounted only into its own installer; A has none
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('control0222', HERE.parent / '0222/control.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
# Source commit -> sha256 of its `npm pack`. F is 0231's control package at the digest its 0231 build recorded
# (0231-live/control.manifest.json), which is also the published 4.1.0 tarball's. I is candidate/0232-rung1.
ARMS = {'F': ('4056ebe24cba16c03bc447a8fbd4bb92cbf21edb', '48d21558e717a8b833b619d7ea696d07512cb78b6f29d13b0ccfb063ac263806'),
        'I': (None, None)}  # PLACEHOLDER: the rung-1 commit and its pack's sha256 are filled at FREEZE
PUBLISHED = ('https://registry.npmjs.org/devlyn-cli/-/devlyn-cli-4.1.0.tgz', None)
ORACLE = [name for name in base.TRACKED if name.startswith('autoresearch/experiments/')]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pack(cache, arm):
    """The publish procedure (publish.yml) at the arm's commit, identical for every arm: a clone with its history,
    `scripts/update-instruction-templates.js` (it rebuilds the migration fingerprints from first-parent history),
    then `npm pack`."""
    commit, pinned = ARMS[arm]
    if commit is None:
        raise ValueError(f'{arm}: its commit is a placeholder until FREEZE')
    path = cache / f'{arm}.tgz'
    if not path.exists():
        with tempfile.TemporaryDirectory() as temp:
            clone = Path(temp) / 'repo'
            subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(REPO), str(clone)], check=True)
            subprocess.run(['git', '-C', str(clone), 'checkout', '-q', '--detach', commit], check=True)
            subprocess.run(['node', 'scripts/update-instruction-templates.js'], cwd=clone, check=True)
            name = subprocess.run(['npm', 'pack', '--silent', '--ignore-scripts', '--pack-destination', str(cache)],
                                  cwd=clone, check=True, capture_output=True, text=True).stdout.split()[-1]
            (cache / name).rename(path)
    if pinned and digest(path) != pinned:
        raise ValueError(f'{arm}.tgz: sha256 mismatch')
    return path


def members(path):
    with tarfile.open(path) as archive:
        return {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                for m in archive.getmembers() if m.isfile()}


def published_check(cache, control_tgz):
    """Whether F's pack equals the published 4.1.0 tarball, file for file: evidence that `pack` reproduces the
    publish procedure."""
    url, _ = PUBLISHED
    path = cache / 'published-4.1.0.tgz'
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    ours, theirs = members(control_tgz), members(path)
    differ = sorted(n for n in ours.keys() | theirs.keys() if ours.get(n) != theirs.get(n))
    return dict(published_sha256=digest(path), control_sha256=digest(control_tgz), equal=not differ, differ=differ)


def manifest(tree):
    return {str(p.relative_to(tree)): digest(p) for p in sorted(tree.rglob('*')) if p.is_file()}


def build(sources, cache, out):
    out.mkdir(parents=False, exist_ok=False)
    public, oracle = out / 'public', out / 'oracle'
    for name in ORACLE:
        target = oracle / Path(name).relative_to('autoresearch')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    public.mkdir()
    (public / 'autoresearch').mkdir()  # the check containers' mount point for the oracle tree
    with tarfile.open(base.fetch(cache, 'prettier.tgz')) as archive:
        archive.extractall(public / '.prettier', filter='data')
    (public / '.prettier/package').rename(public / 'prettier')
    (public / '.prettier').rmdir()
    with zipfile.ZipFile(base.fetch(cache, 'ruff.whl')) as wheel:
        (public / 'ruff').write_bytes(wheel.read('ruff-0.15.9.data/scripts/ruff'))
    (public / 'ruff').chmod(0o755)
    # Click's tests read its installed metadata. Only the metadata is provided: an installed copy of the code would
    # silently replace the cell's own source whenever `src` is not first on the path.
    with tempfile.TemporaryDirectory() as temp:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--no-deps', '--no-compile',
                        '--target', temp, str(sources / 'click')], check=True)
        (info,) = Path(temp).glob('click-*.dist-info')
        shutil.copytree(info, public / 'python' / info.name)
    packages = {}
    for arm in ARMS:
        tgz = pack(cache, arm)
        with tarfile.open(tgz) as archive:
            archive.extractall(out / 'packages' / arm, filter='data')
        packages[arm] = dict(commit=ARMS[arm][0], sha256=digest(tgz), files=members(tgz))
    record = dict(packages=packages, published=published_check(cache, cache / 'F.tgz'),
                  manifests={name: manifest(out / name) for name in ('public', 'oracle', 'packages')})
    (out.parent / (out.name + '.manifest.json')).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    print(hashlib.sha256(json.dumps(record['manifests'], sort_keys=True).encode()).hexdigest())


if __name__ == '__main__':
    build(*(Path(arg).resolve() for arg in sys.argv[1:4]))
