"""Assemble the 0256 control trees: control.py <sources> <cache> <out>. Never dispatches models.

<out>/public                    participant /control: public tools only
<out>/oracle                    evaluator-only files, mounted over /control/autoresearch in check containers
<out>/packages/B/package        published package, mounted only into B's installer; A has none
"""
import hashlib
import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('control0222', HERE.parent / '0222/control.py')
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
ARMS = ('B',)
PACKAGE_URL = 'https://registry.npmjs.org/devlyn-cli/-/devlyn-cli-4.2.24.tgz'
INTEGRITY = 'sha512-bciFYsU0mRJLH9DunMRENLMOR4wjLygdKb9Ub9e/Vu8u9A20Noc/k1UskrRq+7vlCdG983ky9ObBydxq1ufhTQ=='
ORACLE = [name for name in base.TRACKED if name.startswith('autoresearch/experiments/')] + [
    'autoresearch/experiments/0233/oracle.js']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(cache):
    """Read the frozen npm tarball or fetch it once; cached corruption is always fatal."""
    import urllib.request
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / 'B.tgz'
    if path.exists():
        data = path.read_bytes()
    else:
        with urllib.request.urlopen(PACKAGE_URL, timeout=60) as response:
            data = response.read()
    expected = base64.b64decode(INTEGRITY.removeprefix('sha512-'))
    if hashlib.sha512(data).digest() != expected:
        raise ValueError('B.tgz: npm integrity mismatch')
    if not path.exists():
        path.write_bytes(data)
    return path


def members(path):
    with tarfile.open(path) as archive:
        return {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest()
                for m in archive.getmembers() if m.isfile()}


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
                        '--target', temp, str(sources / 'click')], check=True,
                       env={**os.environ, 'PIP_CACHE_DIR': str(Path(temp) / 'pip-cache')})
        (info,) = Path(temp).glob('click-*.dist-info')
        shutil.copytree(info, public / 'python' / info.name)
    packages = {}
    for arm in ARMS:
        tgz = fetch(cache)
        with tarfile.open(tgz) as archive:
            archive.extractall(out / 'packages' / arm, filter='data')
        packages[arm] = dict(url=PACKAGE_URL, integrity=INTEGRITY, sha256=digest(tgz), files=members(tgz))
    record = dict(packages=packages, manifests={name: manifest(out / name) for name in ('public', 'oracle', 'packages')})
    (out.parent / (out.name + '.manifest.json')).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    print(hashlib.sha256(json.dumps(record['manifests'], sort_keys=True).encode()).hexdigest())


if __name__ == '__main__':
    build(*(Path(arg).resolve() for arg in sys.argv[1:4]))
