"""Select and materialize the one evaluated snapshot of a finished 0231 cell: locate.py <cell-out>.

Order: an accepted commit validly bound to this task and run; otherwise the newest task-owned linked worktree's tree
at teardown; the anchor only when no task tree was allocated. Every check, oracle row and assessor reads the
materialized <cell-out>/snapshot; the other trees stay in place as audit evidence.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

WRITABLE = {'/cell': 'cell', '/tmp': 'tmp', '/home/participant': 'home'}


class LocatorError(RuntimeError):
    """An apparatus defect: the snapshot cannot be selected or materialized."""


def host(out, path):
    for prefix, name in WRITABLE.items():
        if path == prefix or path.startswith(prefix + '/'):
            return out / name / path[len(prefix):].lstrip('/')
    return None


# Host Git never runs participant-configured commands: no fsmonitor, untracked cache or hooks, no user or system
# config, no optional locks; and only commands that execute nothing (no status, no filters).
SAFE = ('-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false', '-c', 'core.hooksPath=/dev/null')
ENV = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_OPTIONAL_LOCKS': '0'}


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


def select(out, baseline):
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


def tree_files(out, folder):
    """Tracked and untracked files Git does not ignore in the anchor or a linked worktree (Git's own view of the
    product), read from the host even though linked worktrees record container paths."""
    anchor = out / 'cell/work'
    if folder == anchor:
        command = ['git', *SAFE, '-C', str(folder)]
    else:
        gitdir = next((d for d in (anchor / '.git/worktrees').iterdir()
                       if host(out, (d / 'gitdir').read_text().strip()) == folder / '.git'), None)
        if gitdir is None:
            raise LocatorError(f'no registered worktree for {folder}')
        command = ['git', *SAFE, '--git-dir', str(gitdir), '--work-tree', str(folder)]
    listed = subprocess.run([*command, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                            capture_output=True, text=True, env=ENV)
    if listed.returncode:
        raise LocatorError('git ls-files failed: ' + listed.stderr.strip())
    return sorted({n for n in listed.stdout.split('\0') if n and n.split('/')[0] != '.devlyn'})


def materialize(out, selection):
    snapshot = out / 'snapshot'
    if snapshot.exists():
        raise LocatorError('snapshot already materialized')
    snapshot.mkdir()
    if selection['kind'] == 'accepted':
        archive = subprocess.run(['git', *SAFE, 'archive', selection['sha']], cwd=out / 'cell/work', capture_output=True, env=ENV)
        if archive.returncode:
            raise LocatorError('git archive failed: ' + archive.stderr.decode(errors='replace'))
        subprocess.run(['tar', '-x', '-C', str(snapshot)], input=archive.stdout, check=True)
        return snapshot
    folder = out / selection['path']
    for name in tree_files(out, folder):
        source, target = folder / name, snapshot / name
        if not source.is_symlink() and not source.exists():
            continue  # a tracked file the product deleted: absent from the snapshot
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            target.symlink_to(source.readlink())
        else:
            shutil.copy2(source, target)
    return snapshot


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
