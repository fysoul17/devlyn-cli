"""Assemble the read-only /control tree: control.py <sources> <cache> <out>. Never dispatches models."""
import hashlib
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
PINNED = {  # name: (url, sha256)
    'prettier.tgz': ('https://registry.npmjs.org/prettier/-/prettier-3.8.3.tgz',
                     'c8a850e71b7366f1bac1885e05b2f929d47168009f3b6914413902ca8b980fde'),
    'ruff.whl': ('https://files.pythonhosted.org/packages/py3/r/ruff/'
                 'ruff-0.15.9-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl',
                 '9439a342adb8725f32f92732e2bafb6d5246bd7a5021101166b223d312e8fc59'),
    'devlyn-cli.tgz': ('https://registry.npmjs.org/devlyn-cli/-/devlyn-cli-3.2.1.tgz',
                       '17e57582213e52ca1fbf7b5de181c3112b44703aca4f181e0120e7884a773c5b'),
}
# B': `npm pack` of the Session 5 merge (PR #114), pinned like a download; packing is byte-reproducible.
CANDIDATE = ('79532e9738b67abfd40e51dc7d613f507c0c78d1',
             '433cb672fa63f3e9450bf4686427fd451d752849d640a79312c5ae6251e2b245')
TRACKED = ['autoresearch/experiments/0206/tasks.json', 'autoresearch/experiments/0207/calibrate.py',
           'autoresearch/experiments/0207/commander.mjs', 'autoresearch/experiments/0207/click_checks.py',
           'autoresearch/experiments/0211/packet.py', 'autoresearch/experiments/0185/support.js',
           'autoresearch/experiments/0185/acceptance.js', 'autoresearch/experiments/0185/heldout.js',
           'autoresearch/experiments/0222/tasks.json', 'autoresearch/experiments/0222/packet.py',
           'autoresearch/experiments/0222/oracle/replay.js',
           'autoresearch/experiments/0222/oracle/replay-terminal.js',
           'autoresearch/experiments/0222/oracle/replay-absence.js']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(cache, name):
    url, sha = PINNED[name]
    path = cache / name
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    if digest(path) != sha:
        raise ValueError(f'{name}: sha256 mismatch')
    return path


def pack(cache):
    commit, sha = CANDIDATE
    path = cache / 'devlyn-intent.tgz'
    if not path.exists():
        with tempfile.TemporaryDirectory() as temp:
            archive = subprocess.run(['git', 'archive', commit], cwd=REPO, check=True, capture_output=True).stdout
            subprocess.run(['tar', '-x', '-C', temp], input=archive, check=True)  # the repo has absolute symlinks
            name = subprocess.run(['npm', 'pack', '--silent', '--ignore-scripts', '--pack-destination', str(cache)],
                                  cwd=temp, check=True, capture_output=True, text=True).stdout.split()[-1]
            (cache / name).rename(path)
    if digest(path) != sha:
        raise ValueError('devlyn-intent.tgz: sha256 mismatch')
    return path


def build(sources, cache, out):
    out.mkdir(parents=False, exist_ok=False)
    for name in TRACKED:
        (out / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, out / name)
    for name in ('run-bounded.py', 'platform-support.py'):
        shutil.copyfile(REPO / 'config/skills/_shared' / name, out / name)
    shutil.copyfile(HERE / 'review.py', out / 'review.py')
    with tarfile.open(fetch(cache, 'prettier.tgz')) as archive:
        archive.extractall(out / '.prettier', filter='data')
    (out / '.prettier/package').rename(out / 'prettier')
    (out / '.prettier').rmdir()
    with zipfile.ZipFile(fetch(cache, 'ruff.whl')) as wheel:
        (out / 'ruff').write_bytes(wheel.read('ruff-0.15.9.data/scripts/ruff'))
    (out / 'ruff').chmod(0o755)
    with tarfile.open(fetch(cache, 'devlyn-cli.tgz')) as archive:
        archive.extractall(out / 'devlyn-cli', filter='data')
    with tarfile.open(pack(cache)) as archive:
        archive.extractall(out / 'devlyn-intent', filter='data')
    # Click's tests read installed metadata; /work/src still shadows the code.
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet', '--no-deps', '--no-compile',
                    '--target', str(out / 'python'), str(sources / 'click')], check=True)
    for cache_dir in list((out / 'python').rglob('__pycache__')):
        shutil.rmtree(cache_dir)
    manifest = {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out.parent / (out.name + '.manifest.json')).write_text(json.dumps(manifest, indent=1) + '\n')
    print(hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest())


if __name__ == '__main__':
    build(*(Path(arg).resolve() for arg in sys.argv[1:4]))
