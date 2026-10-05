"""Select and materialize the one evaluated snapshot of a finished 0232 cell: locate.py <cell-out>.

F, exactly as 0231: an accepted commit validly bound to this task and run; otherwise the newest task-owned linked
worktree's tree at teardown; the anchor only when no task tree was allocated. A and I are native: the anchor, the
session's working directory, when its product changed, otherwise the one linked worktree whose product changed;
changed products in more than one worktree are a STOP. Every check, oracle row and assessor reads the materialized
<cell-out>/snapshot; the other trees stay in place as audit evidence.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

_spec = importlib.util.spec_from_file_location('packet0222l', Path(__file__).resolve().parent.parent / '0222/packet.py')
packet = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(packet)
WRITABLE = {'/cell': 'cell', '/tmp': 'tmp', '/home/participant': 'home'}


class LocatorError(RuntimeError):
    """An apparatus defect: the snapshot cannot be selected or materialized."""


def host(out, path):
    for prefix, name in WRITABLE.items():
        if path == prefix or path.startswith(prefix + '/'):
            return out / name / path[len(prefix):].lstrip('/')
    return None


# Host Git never runs participant-configured commands: no fsmonitor, untracked cache or hooks, no user or system
# config, no optional locks, no lazy fetch; it reads objects as committed (no replacement refs); and it uses only
# commands that execute nothing (no status, no filters; final_tree's add runs with every filter blanked).
SAFE = ('-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false', '-c', 'core.hooksPath=/dev/null')
ENV = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0',
       'GIT_NO_LAZY_FETCH': '1', 'GIT_NO_REPLACE_OBJECTS': '1'}


def raw_tree(command, commit, dest):
    """Write a commit's tracked tree into dest from its raw objects (ls-tree + cat-file): no export attributes, filters or
    conversions, so what is compared is exactly what the commit records. command is the Git prefix to use."""
    listing = subprocess.run([*command, 'ls-tree', '-r', '-z', '--full-tree', commit], capture_output=True, env=ENV)
    if listing.returncode:
        raise LocatorError('git ls-tree failed: ' + listing.stderr.decode(errors='replace'))
    for entry in filter(None, listing.stdout.split(b'\0')):
        meta, path = entry.split(b'\t', 1)
        mode, kind, sha = meta.decode().split()
        if kind != 'blob':
            raise LocatorError(f'unsupported tree entry {kind} at {path.decode(errors="replace")}')
        blob = subprocess.run([*command, 'cat-file', 'blob', sha], capture_output=True, env=ENV)
        if blob.returncode:
            raise LocatorError('git cat-file failed: ' + blob.stderr.decode(errors='replace'))
        target = dest / path.decode()
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == '120000':
            target.symlink_to(blob.stdout.decode())
        else:
            target.write_bytes(blob.stdout)
            target.chmod(0o755 if mode == '100755' else 0o644)
    return dest


def git(repo, *args, check=True):
    done = subprocess.run(['git', *SAFE, *args], cwd=repo, capture_output=True, text=True, env=ENV)
    if check and done.returncode:
        raise LocatorError(f'git {" ".join(args)}: {done.stderr.strip()}')
    return done.stdout.strip() if done.returncode == 0 else None


def receipts(anchor):
    """Allocation receipts under the common Git directory, oldest first."""
    found = []
    for path in sorted((anchor / '.git/devlyn-completion').glob('*/receipt.json'), key=lambda p: p.stat().st_mtime):
        try:
            found.append((path, json.loads(path.read_text())))
        except ValueError as exc:
            raise LocatorError(f'unreadable receipt {path}: {exc}') from exc
    return found


def run_record(out, receipt_path, worktree, relative):
    """A file of the accepted run: in its worktree, or in the receipt's custody once cleanup removed the tree."""
    for root in ((worktree,) if worktree else ()) + (receipt_path.parent / 'custody',):
        if (root / relative).is_file():
            return root / relative
    return None


def accepted(out, anchor, receipt_path, receipt, allocation_sha):
    """The receipt's accepted commit, if bound to this task and to an archived run that sealed exactly that commit."""
    acceptance = receipt.get('acceptance') or {}
    sha, run_id = acceptance.get('source_sha'), acceptance.get('run_id')
    if (receipt.get('allocation') != 'owned' or acceptance.get('task') != receipt.get('task') or not isinstance(sha, str)
            or acceptance.get('kind') != 'pipeline' or not isinstance(run_id, str)
            or git(anchor, 'cat-file', '-e', sha + '^{commit}', check=False) is None
            or git(anchor, 'merge-base', '--is-ancestor', allocation_sha, sha, check=False) is None):
        return None
    worktree = host(out, receipt.get('worktree', ''))
    state = run_record(out, receipt_path, worktree, f'.devlyn/runs/{run_id}/pipeline.state.json')
    seal = run_record(out, receipt_path, worktree, f'.devlyn/runs/{run_id}/source-seal.json')
    try:
        if (not state or not seal or json.loads(state.read_text()).get('run_id') != run_id
                or (json.loads(seal.read_text()).get('seal') or {}).get('head') != sha):
            return None
    except ValueError:
        return None
    return sha


def native(out, baseline):
    """A and I: the anchor when its product differs from the allocation, else the one preserved linked worktree
    whose product does, else the unchanged anchor. Never a silent choice between changed worktrees."""
    anchor = out / 'cell/work'
    links = (host(out, (d / 'gitdir').read_text().strip()) for d in sorted((anchor / '.git/worktrees').glob('*')))
    trees = [anchor, *(link.parent for link in links if link and link.parent.is_dir())]
    with tempfile.TemporaryDirectory() as temp:
        changed = [t for i, t in enumerate(trees) if packet.tree(copy_tree(out, t, Path(temp) / str(i))) != baseline['files']]
    names = [str(t.relative_to(out)) for t in changed]
    if anchor in changed or not changed:
        return dict(kind='anchor', path='cell/work', changed=names, candidates=[])
    if len(changed) > 1:
        raise LocatorError('a native run changed more than one linked worktree: ' + ', '.join(names))
    return dict(kind='worktree', path=names[0], changed=names, candidates=[])


def select(out, baseline):
    if baseline['arm'] != 'F':
        return native(out, baseline)
    anchor = out / 'cell/work'
    found = receipts(anchor)
    candidates = []
    for path, receipt in found:
        candidates.append(dict(receipt=str(path.relative_to(out)), allocation=receipt.get('allocation'),
                               worktree=receipt.get('worktree'), local_only=bool(receipt.get('local_only')),
                               acceptance=bool(receipt.get('acceptance'))))
    for path, receipt in reversed(found):
        sha = accepted(out, anchor, path, receipt, baseline['allocation_sha'])
        if sha:
            return dict(kind='accepted', sha=sha, receipt=str(path.relative_to(out)), candidates=candidates)
    for path, receipt in reversed(found):
        worktree = host(out, receipt.get('worktree', ''))
        if receipt.get('allocation') == 'owned' and worktree and worktree.is_dir():
            return dict(kind='worktree', path=str(worktree.relative_to(out)), receipt=str(path.relative_to(out)),
                        candidates=candidates)
    if any(r.get('allocation') == 'owned' for _, r in found):
        raise LocatorError('an owned allocation names no preserved worktree')
    return dict(kind='anchor', path='cell/work', candidates=candidates)


def command(out, folder):
    """The host Git prefix for the anchor or a linked worktree, whose Git links record container paths."""
    anchor = out / 'cell/work'
    if folder == anchor:
        return ['git', *SAFE, '-C', str(folder)]
    gitdir = next((d for d in (anchor / '.git/worktrees').iterdir()
                   if host(out, (d / 'gitdir').read_text().strip()) == folder / '.git'), None)
    if gitdir is None:
        raise LocatorError(f'no registered worktree for {folder}')
    return ['git', *SAFE, '--git-dir', str(gitdir), '--work-tree', str(folder)]


def cell_env(out):
    """Host Git reading the cell home, as the container does, never the host user's ignore files."""
    return {k: v for k, v in ENV.items() if k != 'XDG_CONFIG_HOME'} | dict(HOME=str(out / 'home'))


def gitlinks(listing):
    """The paths of the commit entries (gitlinks) in a NUL-separated recursive ls-tree listing."""
    return [entry.split('\t', 1)[1] for entry in listing.split('\0') if entry.split(' ')[1:2] == ['commit']]


def tree_files(out, folder):
    """Tracked and untracked files Git does not ignore in the anchor or a linked worktree (Git's own view of the
    product), read from the host with the cell home."""
    listed = subprocess.run([*command(out, folder), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            capture_output=True, text=True, env=cell_env(out))
    if listed.returncode:
        raise LocatorError('git ls-files failed: ' + listed.stderr.strip())
    return sorted({n for n in listed.stdout.split('\0') if n and n.split('/')[0] != '.devlyn'})


def copy_tree(out, folder, dest):
    """Copy Git's view of a tree's product (tree_files) into dest; returns dest. A directory entry (a nested
    repository) is copied as a tree with its symlinks kept; any copy failure is a locator defect."""
    dest.mkdir(exist_ok=True)
    try:
        for name in tree_files(out, folder):
            source, target = folder / name, dest / name
            if not source.is_symlink() and not source.exists():
                continue  # a tracked file the product deleted: absent from the snapshot
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                target.symlink_to(source.readlink())
            elif source.is_dir():
                shutil.copytree(source, target, symlinks=True)
            else:
                shutil.copy2(source, target)
    except OSError as exc:
        raise LocatorError(f'copying {folder.relative_to(out)} failed: {exc}') from exc
    return dest


def final_tree(out, folder):
    """The review launcher's tree of a run location's whole working-tree state, by its algorithm (HEAD read into a
    temporary index, `add -A -- .`, write-tree) on the host with the cell home. The index and every new object stay in
    a temporary directory, so no evidence is written. No participant command runs: every filter key the repository
    configures is blanked, and a tracked submodule is refused because adding it would run `git status` inside it. A
    nested repository the add records as a gitlink is refused too: the tree would hold only its commit, while the
    snapshot copies its live files."""
    prefix = command(out, folder)
    env = cell_env(out)
    listing = subprocess.run([*prefix, 'ls-tree', '-r', '-z', '--full-tree', 'HEAD'], capture_output=True, text=True, env=env)
    filters = subprocess.run([*prefix, 'config', '-z', '--get-regexp', r'^filter\.'], capture_output=True, text=True, env=env)
    if listing.returncode or filters.returncode not in (0, 1):  # config exits 1 when nothing matches
        raise LocatorError(f'git in {folder.relative_to(out)}: {(listing.stderr + filters.stderr).strip()}')
    if submodules := gitlinks(listing.stdout):
        raise LocatorError('the run location tracks a submodule: ' + ', '.join(submodules))
    keys = [entry.split('\n', 1)[0] for entry in filters.stdout.split('\0') if entry]
    with tempfile.TemporaryDirectory() as temp:
        (Path(temp) / 'objects').mkdir()
        env.update(GIT_INDEX_FILE=f'{temp}/index', GIT_OBJECT_DIRECTORY=f'{temp}/objects',
                   GIT_ALTERNATE_OBJECT_DIRECTORIES=str(out / 'cell/work/.git/objects'), GIT_CONFIG_COUNT=str(len(keys)))
        for i, key in enumerate(keys):
            env[f'GIT_CONFIG_KEY_{i}'], env[f'GIT_CONFIG_VALUE_{i}'] = key, 'false' if key.endswith('.required') else ''
        for args in (('read-tree', 'HEAD'), ('add', '-A', '--', '.'), ('write-tree',)):
            done = subprocess.run([*prefix, *args], cwd=folder, capture_output=True, text=True, env=env)
            if done.returncode:
                raise LocatorError(f'git {" ".join(args)} in {folder.relative_to(out)}: {done.stderr.strip()}')
        tree = done.stdout.strip()
        listing = subprocess.run([*prefix, 'ls-tree', '-r', '-z', tree], capture_output=True, text=True, env=env)
        if listing.returncode:
            raise LocatorError(f'git ls-tree in {folder.relative_to(out)}: {listing.stderr.strip()}')
    if nested := gitlinks(listing.stdout):
        raise LocatorError('the run location holds a nested repository recorded only by its commit: ' + ', '.join(nested))
    return tree


def materialize(out, selection):
    snapshot = out / 'snapshot'
    if snapshot.exists():
        raise LocatorError('snapshot already materialized')
    snapshot.mkdir()
    if selection['kind'] == 'accepted':
        return raw_tree(['git', *SAFE, '-C', str(out / 'cell/work')], selection['sha'], snapshot)
    return copy_tree(out, out / selection['path'], snapshot)


def locate(out):
    baseline = json.loads((out / 'baseline.json').read_text())
    selection = select(out, baseline)
    materialize(out, selection)
    (out / 'snapshot.json').write_text(json.dumps(selection, indent=2))
    return selection


if __name__ == '__main__':
    try:
        print(json.dumps(locate(Path(sys.argv[1]).resolve())))
    except LocatorError as exc:
        print('LOCATOR_STOP: ' + str(exc), file=sys.stderr)
        sys.exit(2)
