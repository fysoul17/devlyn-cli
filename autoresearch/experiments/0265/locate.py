"""Select one 0265 submitted source: unique accepted receipt, else unique changed product tree.

0233's locate with two changes for 4.3.30's delivery helper (DESIGN Q4): a receipt binds an accepted commit by either
kind the helper binds, `direct` or `loop` (ACCEPTED; 4.3.30 retired `pipeline`), and changed trees that are the same
in Git's view at every path (same_result) are one result (4.3.30 keeps the edits in the anchor while a delivery is
pending or refused), graded once with the others recorded as duplicates. All other trees remain for audit; changed
trees that differ, or two accepted receipts, STOP before grading.
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
# commands that execute nothing (no status or filters).
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


def accepted(out, anchor, receipt, allocation_sha):
    """The receipt's accepted commit, if bound to this task: a `direct` acceptance, or a `loop` one whose verdict is
    ACCEPTED (4.3.30 task-complete.py bind_acceptance; a FAILED loop result is never a product)."""
    acceptance = receipt.get('acceptance') or {}
    sha = acceptance.get('source_sha')
    if (receipt.get('allocation') != 'owned' or receipt.get('baseline') != allocation_sha
            or host(out, receipt.get('anchor', '')) != anchor
            or acceptance.get('task') != receipt.get('task') or not isinstance(sha, str)
            or acceptance.get('kind') not in ('direct', 'loop')
            or acceptance['kind'] == 'loop' and acceptance.get('verdict') != 'ACCEPTED'
            or receipt.get('source_sha') != sha
            or git(anchor, 'cat-file', '-e', sha + '^{commit}', check=False) is None
            or git(anchor, 'merge-base', '--is-ancestor', allocation_sha, sha, check=False) is None):
        return None
    return sha


def same_result(entries):
    """packet.tree() entries as Git sees a tree (DESIGN Q4, O2): each path's type (a symbolic link and its target, or a
    regular file and its bytes; a directory by the paths under it), and a regular file's executable bit. Other
    permission bits are dropped, as Git drops them (0644 and 0664 are one mode, 0755 another)."""
    def mode(value):
        digest, bits = value.split(':')
        return f'{digest}:{"755" if int(bits, 8) & 0o100 else "644"}'
    return json.dumps({name: value if value.startswith('link:') else mode(value) for name, value in entries.items()},
                      sort_keys=True)


def native(out, baseline):
    """Select the one changed product tree, or the unchanged anchor. Changed trees that are the same result at every
    path (same_result) are one result: the first (the anchor when it is one of them) is selected and the others are
    its duplicates. Changed trees that differ are rejected."""
    anchor = out / 'cell/work'
    links = (host(out, (d / 'gitdir').read_text().strip()) for d in sorted((anchor / '.git/worktrees').glob('*')))
    trees = [anchor, *(link.parent for link in links if link and link.parent.is_dir())]
    with tempfile.TemporaryDirectory() as temp:
        entries = [packet.tree(copy_tree(out, t, Path(temp) / str(i))) for i, t in enumerate(trees)]
    changed = [(t, e) for t, e in zip(trees, entries) if e != baseline['files']]
    names = [str(t.relative_to(out)) for t, _ in changed]
    contents = {same_result(e) for _, e in changed}
    if len(contents) > 1:
        raise LocatorError('more than one changed product tree: ' + ', '.join(names))
    if not changed or changed[0][0] == anchor:
        return dict(kind='anchor', path='cell/work', changed=names, duplicates=names[1:], candidates=[])
    return dict(kind='worktree', path=names[0], changed=names, duplicates=names[1:], candidates=[])


def select(out, baseline):
    anchor = out / 'cell/work'
    found = receipts(anchor)
    candidates = []
    for path, receipt in found:
        candidates.append(dict(receipt=str(path.relative_to(out)), allocation=receipt.get('allocation'),
                               worktree=receipt.get('worktree'), local_only=bool(receipt.get('local_only')),
                               acceptance=bool(receipt.get('acceptance'))))
    bound = [(path, sha) for path, receipt in found
             if (sha := accepted(out, anchor, receipt, baseline['allocation_sha']))]
    if len(bound) > 1:
        raise LocatorError('more than one accepted receipt: ' + ', '.join(str(p.relative_to(out)) for p, _ in bound))
    if bound:
        path, sha = bound[0]
        return dict(kind='accepted', rule='receipt', sha=sha, receipt=str(path.relative_to(out)), candidates=candidates)
    selection = native(out, baseline)
    selection['rule'] = 'changed-product' if selection['changed'] else 'unchanged-anchor'
    selection['candidates'] = candidates
    return selection


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
