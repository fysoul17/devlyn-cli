"""Bring the 0266 runtime root to "ready for SMOKE": setup_runtime.py [--root DIR] [--codex-auth PATH].

Never dispatches models. Idempotent: each step prints one line with what it found or did, keeps what already matches its pin and refuses on
anything that differs. It never reads a credential and never writes into the auth folders. --codex-auth names the
Codex login the run uses (DESIGN Operations "Codex login"), an absolute path to an existing regular file, written as
`codex_auth` into the three runtime files; without it the field keeps what the runtime files hold (null when new: cells
would use the host's default login).

The login is named late (README): everything else, the instruction seal and the witness and probe controls are prepared
without it, because none of them reads a login or the runtime's `codex_auth`. Naming it afterwards (the same command
with --codex-auth) finds every other step present and rewrites `codex_auth` alone, once, while it is null and before
any cell has started (no <output>/*/run/started.json); naming another login later refuses.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = Path.home() / '.local/share/nx01/0266-live'
ARCHIVE = Path.home() / '.local/share/nx01/archive/reports-0256-0260/0257'  # 0257 prompts carry the issue snapshots
HOST_MODELS_CACHE = Path.home() / '.codex/models_cache.json'
OVERRIDE = HERE.parent / '0256/tasks-override.json'
REMOTE = 'https://github.com/{}'
SOURCES = {t['source']: (t['repository'], t['base_sha'], t['tree_sha'])
           for t in json.loads((HERE.parent / '0233/tasks.json').read_text())['tasks'] if t['id'] in ('D3', 'D4')}
FOLDERS = {'sources': None, 'cache': None, 'scratch': 0o700, 'output': None,
           'auth-smoke': 0o700, 'auth-claude': 0o700, 'auth-codex': 0o700}
IMAGE = 'devlyn-0265'
VERSIONS = ['2.1.322 (Claude Code)', 'codex-cli 0.164.0']  # `claude --version`, `codex --version` in the image
CODEX_VERSION = '0.164.0'
LANES = {'smoke': None, 'claude': 'claude', 'codex': 'codex'}
RENEWAL = ['claude', '-p', '--tools', '', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', 'OK']
CAPS = {'five_hour': 95, 'seven_day': 95}
CALLER = '\nCALLER CONTRACT\n'

_spec = importlib.util.spec_from_file_location('control0266', HERE / 'control.py')
control = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(control)


class Refused(RuntimeError):
    pass


def say(step, text):
    print(f'{step}: {text}', flush=True)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def sh(*argv, stream=False):
    """Run a command; a nonzero exit refuses with its last stderr line."""
    done = subprocess.run(argv, capture_output=not stream, text=True)
    if done.returncode:
        tail = (done.stderr or '').strip().splitlines()[-1:] if not stream else []
        raise Refused(f'{" ".join(argv[:3])} exited {done.returncode}' + (f': {tail[0]}' if tail else ''))
    return (done.stdout or '').strip()


def folders(root):
    made = []
    for name, mode in FOLDERS.items():
        path = root / name
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise Refused(f'{path} is not a directory')
        if not path.exists():
            path.mkdir(parents=True)
            if mode is not None:
                path.chmod(mode)
            made.append(name)
        elif mode is not None and stat.S_IMODE(path.stat().st_mode) != mode:
            raise Refused(f'{path} has mode {stat.S_IMODE(path.stat().st_mode):o}, expected {mode:o}')
    say('folders', 'created ' + ' '.join(made) if made else 'present')


def clones(root):
    for name, (repository, commit, tree) in SOURCES.items():
        path = root / 'sources' / name
        action = 'present'
        if not path.exists():
            sh('git', 'clone', '--quiet', REMOTE.format(repository), str(path))
            sh('git', '-C', str(path), 'checkout', '--quiet', '--detach', commit)
            action = 'cloned'
        found = subprocess.run(['git', '-C', str(path), 'rev-parse', f'{commit}^{{tree}}', 'HEAD'],
                               capture_output=True, text=True).stdout.split()
        if found != [tree, commit]:
            raise Refused(f'{path}: expected HEAD {commit} with tree {tree}, found {found}')
        if sh('git', '--no-optional-locks', '-C', str(path), 'status', '--porcelain', '--untracked-files=all'):
            raise Refused(f'{path}: working tree is not clean')
        say('sources', f'{name} {action}: HEAD {commit}, tree {tree}')


def restore(prompt_text):
    """The issue snapshot is the UTF-8 bytes of the caller contract's original_context (0257/prepare.py)."""
    index = prompt_text.index(CALLER)
    return json.loads(prompt_text[index + len(CALLER):])['original_context'].encode('utf-8')


def issues(root, archive=ARCHIVE):
    override = json.loads(OVERRIDE.read_text())
    for task in ('D3', 'D4'):
        expected = override[task]['issue_snapshot_sha256']
        path = root / 'sources' / f'{task}-issue.json'
        if path.exists():
            if sha256(path.read_bytes()) != expected:
                raise Refused(f'{path}: sha256 differs from {OVERRIDE.name} {expected}')
            say('issue', f'{task} present, sha256 {expected}')
            continue
        prompt = next(iter(sorted(Path(archive).glob(f'*-{task}-*/prompt.txt'))), None)
        if prompt is None:
            raise Refused(f'no archived {task} prompt under {archive}')
        data = restore(prompt.read_text(encoding='utf-8'))
        if sha256(data) != expected:
            raise Refused(f'{prompt}: restored {task} snapshot sha256 {sha256(data)}, expected {expected}')
        with path.open('xb') as stream:
            stream.write(data)
        say('issue', f'{task} restored from {prompt}, sha256 {expected}')


def package(root):
    path = root / 'cache/B.tgz'
    action = 'present' if path.exists() else 'downloaded'
    try:
        control.fetch(root / 'cache')
    except ValueError as exc:
        raise Refused(str(exc)) from None
    say('package', f'B.tgz {action}, {control.INTEGRITY}, sha256 {sha256(path.read_bytes())}')


def image_id():
    done = subprocess.run(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def tarball_id(path):
    """The config digest `docker save` recorded, i.e. the saved image's ID."""
    try:
        with tarfile.open(path) as archive:
            (entry,) = json.load(archive.extractfile('manifest.json'))
    except (OSError, KeyError, ValueError, tarfile.TarError) as exc:
        raise Refused(f'{path} is not a readable image tarball: {exc}') from None
    return 'sha256:' + Path(entry['Config']).name.removesuffix('.json')


def image(root):
    tarball = root / 'image.tar'
    found, action = image_id(), 'present'
    if found is None and tarball.exists():
        sh('docker', 'load', '-i', str(tarball))
        found, action = image_id(), 'loaded from image.tar'
    elif found is None:
        sh('bash', str(HERE.parent / '0265/build.sh'), str(root / 'cache/image'), str(root / 'sources'), stream=True)
        found, action = image_id(), 'built'
    if found is None:
        raise Refused(f'no image {IMAGE} after {action}')
    versions = sh('docker', 'run', '--rm', '--network', 'none', found, 'sh', '-c', 'claude --version; codex --version')
    if versions.splitlines() != VERSIONS:
        raise Refused(f'{IMAGE} {found} reports {versions.splitlines()}, expected {VERSIONS}')
    if not tarball.exists():
        partial = tarball.with_name(tarball.name + '.partial')
        sh('docker', 'save', '-o', str(partial), found)
        os.replace(partial, tarball)
        action += ', saved image.tar'
    if tarball_id(tarball) != found:
        raise Refused(f'{tarball} holds {tarball_id(tarball)}, not {IMAGE} {found}')
    say('image', f'{action}: {found}, image.tar {tarball.stat().st_size} bytes')
    return found


def control_tree(root, image):
    out, manifest_path = root / 'control', root / 'control.manifest.json'
    action = 'present'
    if not out.exists():
        if manifest_path.exists():
            raise Refused(f'{manifest_path} exists without its tree')
        try:
            control.build(root / 'sources', root / 'cache', out, image)
        except ValueError as exc:
            shutil.rmtree(out, ignore_errors=True)
            manifest_path.unlink(missing_ok=True)
            raise Refused(str(exc)) from None
        except BaseException:
            shutil.rmtree(out, ignore_errors=True)
            manifest_path.unlink(missing_ok=True)
            raise
        action = 'built'
    if not manifest_path.is_file():
        raise Refused(f'{out} exists without {manifest_path.name}')
    record = json.loads(manifest_path.read_text())
    entry = record['packages']['B']
    if (entry['url'], entry['integrity'], entry['sha256']) != (
            control.PACKAGE_URL, control.INTEGRITY, sha256((root / 'cache/B.tgz').read_bytes())):
        raise Refused(f'{manifest_path}: package B is not {control.PACKAGE_URL}')
    for name in ('public', 'oracle', 'packages'):
        if control.manifest(out / name) != record['manifests'][name]:
            raise Refused(f'{out / name} differs from {manifest_path.name}')
    manifests = sha256(json.dumps(record['manifests'], sort_keys=True).encode())
    say('control', f'{action}: manifest sha256 {sha256(manifest_path.read_bytes())}, manifests digest {manifests}')
    packages(out / 'packages', record['packages'])


def packages(folder, recorded):
    """DESIGN "Arms": each package's tree and release digest against its pin and its record, and each C package's
    qualification comparison with B (control.compare), whose frozen files and fields are printed."""
    if sorted(recorded) != sorted(control.PACKAGES):
        raise Refused(f'control manifest packages {sorted(recorded)}, expected {sorted(control.PACKAGES)}')
    for name, (tree, release_digest) in control.PINS.items():
        found = control.tree_sha256(folder / name / 'package')
        declared = control.release(folder / name / 'package')['digest']['value']
        if {found, recorded[name]['tree_sha256']} != {tree} or {declared, recorded[name]['release_digest']} != {
                release_digest}:
            raise Refused(f'package {name}: tree {found}, release {declared}; pinned {tree}, {release_digest}')
        if name == 'B':
            say('package', f'B tree {tree}, release {release_digest}')
            continue
        try:
            comparison = control.compare(folder / 'B/package', folder / name / 'package', name)
        except ValueError as exc:
            raise Refused(str(exc)) from None
        if comparison != recorded[name]['comparison']:
            raise Refused(f'package {name}: comparison differs from its record')
        say('package', f'{name} tree {tree}, release {release_digest}; differs from B in exactly '
                       f'{len(comparison["files"])} files {comparison["files"]} and {len(comparison["fields"])} '
                       f'derived fields {comparison["fields"]}')


def client_version(path):
    try:
        return json.loads(Path(path).read_text()).get('client_version')
    except (OSError, ValueError, AttributeError):
        return None


def models_cache(root, host=HOST_MODELS_CACHE):
    target = root / 'models_cache.json'
    action = 'present'
    if not target.exists():
        if client_version(host) != CODEX_VERSION:
            # 0256/models_cache.py needs a Codex login copy in an auth folder, which this script never writes.
            raise Refused(f'{host} is not a Codex {CODEX_VERSION} models cache: generate {target} with '
                          '0256/models_cache.py once the driver has snapshotted auth-smoke/codex.json')
        partial = target.with_name(target.name + '.partial')
        shutil.copyfile(host, partial)
        os.replace(partial, target)
        action = f'copied from {host}'
    if client_version(target) != CODEX_VERSION:
        raise Refused(f'{target}: client_version {client_version(target)}, expected {CODEX_VERSION}')
    say('models_cache', f'{action}: client_version {CODEX_VERSION}, sha256 {sha256(target.read_bytes())}')


def runtime_record(root, image, lane_file, lane, codex_auth=None):
    return dict(output=str(root / 'output'), control=str(root / 'control'), sources=str(root / 'sources'),
                scratch=str(root / 'scratch'), image=image, image_tarball=str(root / 'image.tar'),
                models_cache=str(root / 'models_cache.json'), auth=str(root / f'auth-{lane_file}'),
                renewal_command=RENEWAL, tasks_override=str(OVERRIDE.resolve()), caps=CAPS,
                codex_auth=codex_auth,  # the Codex login run_cell.snapshot_auth copies; null: the host default
                lane=lane, renewal_lock=str(root / 'renewal.lock'), check_lock=str(root / 'check.lock'))


def codex_auth_path(path):
    """--codex-auth: an absolute path to an existing regular file, by its metadata only (never opened)."""
    if path is not None and not (os.path.isabs(path) and Path(path).is_file()):
        raise Refused(f'--codex-auth {path} is not an absolute path to an existing regular file')
    return path


def runtime_files(root, image, codex_auth=None):
    started = sorted((root / 'output').glob('*/run/started.json'))
    for lane_file, lane in LANES.items():
        path = root / f'runtime-{lane_file}.json'
        record = runtime_record(root, image, lane_file, lane, codex_auth)
        if path.exists():
            found = json.loads(path.read_text())
            if codex_auth is None:  # not named in this call: keep what the runtime holds
                record['codex_auth'] = found.get('codex_auth')
            if dict(found, codex_auth=None) != dict(record, codex_auth=None):
                raise Refused(f'{path} differs from the expected runtime')
            if found.get('codex_auth') == record['codex_auth']:
                say('runtime', f'{path.name} present')
                continue
            if found.get('codex_auth') is not None:
                raise Refused(f'{path} already names the Codex login {found["codex_auth"]}')
            if started:
                raise Refused(f'{path}: a cell has started ({started[0].parent.parent.name}); the Codex login is '
                              'named before SMOKE')
            partial = path.with_name(path.name + '.partial')
            partial.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
            os.replace(partial, path)
            say('runtime', f'{path.name}: codex_auth named {codex_auth}')
        else:
            with path.open('x') as stream:
                stream.write(json.dumps(record, indent=2, sort_keys=True) + '\n')
            say('runtime', f'{path.name} written')


def setup(root, archive=ARCHIVE, host_cache=HOST_MODELS_CACHE, codex_auth=None):
    root = Path(root).expanduser().resolve()
    codex_auth = codex_auth_path(codex_auth)  # before any step: a wrong path refuses with nothing done
    folders(root)
    clones(root)
    issues(root, archive)
    package(root)
    found = image(root)
    control_tree(root, found)
    models_cache(root, host_cache)
    runtime_files(root, found, codex_auth)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', default=str(ROOT))
    parser.add_argument('--codex-auth', help="absolute path to the Codex login's auth.json the run uses")
    try:
        args = parser.parse_args()
        setup(args.root, codex_auth=args.codex_auth)
    except Refused as exc:
        print(f'REFUSED: {exc}', file=sys.stderr)
        sys.exit(1)
