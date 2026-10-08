"""Assemble the 0235 control trees: control.py <sources> <cache> <out>. Never dispatches models.

<out>/public                    participant /control: public tools only
<out>/oracle                    evaluator-only files, mounted over /control/autoresearch in check containers
<out>/packages/<arm>/package    each installing arm's package (B, R), mounted only into its own installer
"""
import hashlib
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
# Source commit -> sha256 from the history-aware 0232 pack procedure.
ARMS = {'B': ('dd4957775337e597f39838fa73acd5c7ec4a5699', '6f03f5ac2895eaccc22ff12d1644a0fc623baca1eec7d00e877ce3254d33352d'),
        'R': ('59ed8a3339316d68290afcf5b74cae0defb84dcf', '90f041bf3f650ca3f028ba6288b4c38bd29a198dd5f76a29163e3e1ce1eb89f7')}
ORACLE = [name for name in base.TRACKED if name.startswith('autoresearch/experiments/')] + [
    'autoresearch/experiments/0233/oracle.js']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pack_env(temp):
    """Use the Node 20/npm 10 toolchain that produced the frozen pack bytes, even when cwd changes PATH order."""
    for directory in os.environ.get('PATH', '').split(os.pathsep):
        node, npm = Path(directory) / 'node', Path(directory) / 'npm'
        if not (node.is_file() and npm.is_file()):
            continue
        env = {**os.environ, 'PATH': directory + os.pathsep + os.environ['PATH'],
                'npm_config_cache': str(Path(temp) / 'npm-cache')}
        try:
            node_version = subprocess.run([str(node), '--version'], env=env, capture_output=True, text=True, check=True).stdout.strip()
            npm_version = subprocess.run([str(npm), '--version'], env=env, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            continue
        if node_version.startswith('v20.') and npm_version.startswith('10.'):
            return env
    raise RuntimeError('0235 packing requires the registered Node 20/npm 10 toolchain on PATH')


def pack(cache, arm):
    """The publish procedure (publish.yml) at the arm's commit, identical for every arm: a clone with its history,
    `scripts/update-instruction-templates.js` (it rebuilds the migration fingerprints from first-parent history),
    then `npm pack`."""
    commit, pinned = ARMS[arm]
    path = cache / f'{arm}.tgz'
    if not path.exists():
        with tempfile.TemporaryDirectory() as temp:
            env = pack_env(temp)
            clone = Path(temp) / 'repo'
            subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(REPO), str(clone)], check=True)
            subprocess.run(['git', '-C', str(clone), 'checkout', '-q', '--detach', commit], check=True)
            subprocess.run(['node', 'scripts/update-instruction-templates.js'], cwd=clone, check=True, env=env)
            name = subprocess.run(['npm', 'pack', '--silent', '--ignore-scripts', '--pack-destination', str(cache)],
                                  cwd=clone, check=True, capture_output=True, text=True, env=env).stdout.split()[-1]
            (cache / name).rename(path)
    if digest(path) != pinned:
        raise ValueError(f'{arm}.tgz: sha256 mismatch')
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
        tgz = pack(cache, arm)
        with tarfile.open(tgz) as archive:
            archive.extractall(out / 'packages' / arm, filter='data')
        packages[arm] = dict(commit=ARMS[arm][0], sha256=digest(tgz), files=members(tgz))
    record = dict(packages=packages, manifests={name: manifest(out / name) for name in ('public', 'oracle', 'packages')})
    (out.parent / (out.name + '.manifest.json')).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    print(hashlib.sha256(json.dumps(record['manifests'], sort_keys=True).encode()).hexdigest())


if __name__ == '__main__':
    build(*(Path(arg).resolve() for arg in sys.argv[1:4]))
