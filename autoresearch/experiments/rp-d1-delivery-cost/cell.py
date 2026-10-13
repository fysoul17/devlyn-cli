"""0251 lifecycle, plus the read-only gh directory and a pre-seal PAT scan."""
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load('cell0251_rpd1', HERE.parent / '0251/cell.py')
auth = load('auth0251_rpd1', HERE.parent / '0251/auth.py')
prepare = load('prepare_rpd1_cell', HERE / 'prepare.py')


def credential_directory(runtime):
    root = auth.directory(runtime['github_auth'])
    for boundary in (Path(runtime['output']).resolve(), Path(runtime['auth']).resolve()):
        if root.is_relative_to(boundary) or boundary.is_relative_to(root):
            raise ValueError('GitHub credential must be disjoint from output and model auth')
    if {p.name for p in root.iterdir()} != {'hosts.yml', 'config.yml'}:
        raise ValueError('GitHub credential requires hosts.yml and config.yml only')
    for path in root.iterdir():
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1):
            raise ValueError('GitHub credential files must be private regular files')
    return root


def credential(runtime):
    root = credential_directory(runtime)
    raw = auth.read_private(root, 'hosts.yml')
    auth.read_private(root, 'config.yml')
    matches = re.findall(rb'^\s*oauth_token:\s*[\"\']?(github_pat_[A-Za-z0-9_]+)[\"\']?\s*$', raw, re.M)
    if len(set(matches)) != 1 or b'github.com:' not in raw:
        raise ValueError('GitHub credential must contain one fine-grained PAT')
    return root, matches[0]


def scan(out, runtime, *, roots=None):
    """Every collected regular file, streamed; symlink text too, without traversal.

    Do not put a hit path/content in a record: either can itself contain the PAT.
    The owner must revoke the PAT in the UI before any future run.
    """
    hit = False

    def search(stream):
        nonlocal hit
        tail = b''
        while chunk := stream.read(1024 * 1024):
            combined = tail + chunk
            hit |= token in combined
            tail = combined[-(len(token) - 1):]

    def unreadable(_):
        raise ValueError('PAT scan encountered an unreadable entry') from None

    reason = None
    try:
        _, token = credential(runtime)
        gitdirs = set()
        for root in roots if roots is not None else (out,):
            root = Path(os.path.abspath(root))
            mode = root.lstat().st_mode
            if stat.S_ISREG(mode):
                with root.open('rb') as stream:
                    search(stream)
                continue
            if not stat.S_ISDIR(mode):
                raise ValueError('PAT scan root is not a regular file or directory')
            for directory, dirs, files in os.walk(root, followlinks=False, onerror=unreadable):
                directory = Path(directory)
                if directory.name == '.git' or (
                        'HEAD' in files and stat.S_ISREG((directory / 'HEAD').lstat().st_mode) and (
                            'objects' in dirs and stat.S_ISDIR((directory / 'objects').lstat().st_mode) or
                            'gitdir' in files and stat.S_ISREG((directory / 'gitdir').lstat().st_mode))):
                    gitdirs.add(directory)
                for name in dirs + files:
                    path = directory / name
                    hit |= token in os.fsencode(path.relative_to(root))
                    mode = path.lstat().st_mode
                    if stat.S_ISLNK(mode):
                        hit |= token in os.fsencode(path.readlink())
                    elif stat.S_ISREG(mode):
                        with path.open('rb') as stream:
                            search(stream)
                    elif not stat.S_ISDIR(mode):
                        raise ValueError('PAT scan encountered a nonregular entry')
        for gitdir in sorted(gitdirs):
            with tempfile.TemporaryFile() as errors, subprocess.Popen(
                    ['git', '--git-dir', str(gitdir), 'cat-file', '--batch-all-objects', '--batch', '--unordered'],
                    stdout=subprocess.PIPE, stderr=errors, env=prepare.github.git_env()) as process:
                search(process.stdout)
                if process.wait() != 0 or errors.tell():
                    raise ValueError('PAT Git object scan failed')
        if hit:
            reason = 'PAT-byte hit: UNKNOWN; owner must revoke PAT immediately; schedule stopped'
    except Exception:
        reason = 'PAT scan failed: UNKNOWN; owner must revoke PAT immediately; schedule stopped'
    if reason:
        try:
            (out / 'pat-scan.json').write_text(json.dumps(dict(status='UNKNOWN', revocation_required=True)))
        finally:
            # Even a failure to write the marker must never expose a scanned path.
            raise ValueError(reason) from None


def run(out, runtime, *, native, check_auth):
    root, _ = credential(runtime)
    plan = json.loads((out / 'plan.json').read_text())
    if ('GH_TOKEN' in plan['env'] or 'GITHUB_TOKEN' in plan['env'] or
            any(plan['env'].get(key) != value for key, value in prepare.GITHUB_ENV.items())):
        raise ValueError('GitHub environment differs from frozen nonsecret contract')
    scan(out, runtime)

    def docker(*argv):
        if argv[0] == 'create':
            args = list(argv)
            index = args.index(plan['image'])
            args[index:index] = ['--mount', f'type=bind,src={root},dst=/run/github,readonly']
            return native.docker(*args)
        return native.docker(*argv)

    # The inherited lifecycle/identity/State-only inspect/tmp custody are unchanged.
    proxy = SimpleNamespace(**(vars(native) | {'docker': docker}))
    return legacy.run(out, runtime, native=proxy, check_auth=check_auth)


def seal(out, runtime, inherited):
    scan(out, runtime)
    return inherited(out)
