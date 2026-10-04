"""Select and materialize the one evaluated snapshot of a finished 0231 cell: locate.py <cell-out>.

Order: an accepted commit validly bound to this task and run; otherwise the newest task-owned linked worktree's tree
at teardown; the anchor only when no task tree was allocated. Every check, oracle row and assessor reads the
materialized <cell-out>/snapshot; the other trees stay in place as audit evidence.
"""
import json
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


def git(repo, *args, check=True):
    done = subprocess.run(['git', *args], cwd=repo, capture_output=True, text=True)
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
    """The receipt's accepted commit if it is bound to this task and an archived run, and descends from the base."""
    acceptance = receipt.get('acceptance') or {}
    sha = acceptance.get('source_sha')
    worktree = host(out, receipt.get('worktree', ''))
    if (receipt.get('allocation') != 'owned' or acceptance.get('task') != receipt.get('task') or not isinstance(sha, str)
            or git(anchor, 'cat-file', '-e', sha + '^{commit}', check=False) is None
            or git(anchor, 'merge-base', '--is-ancestor', allocation_sha, sha, check=False) is None):
        return None
    if acceptance.get('kind') == 'pipeline' and not (worktree and (worktree / '.devlyn/runs' / str(acceptance.get('run_id'))).is_dir()):
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
        sha = accepted(out, anchor, receipt, baseline['allocation_sha'])
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


def materialize(out, selection):
    snapshot = out / 'snapshot'
    if snapshot.exists():
        raise LocatorError('snapshot already materialized')
    if selection['kind'] == 'accepted':
        snapshot.mkdir()
        archive = subprocess.run(['git', 'archive', selection['sha']], cwd=out / 'cell/work', capture_output=True)
        if archive.returncode:
            raise LocatorError('git archive failed: ' + archive.stderr.decode(errors='replace'))
        subprocess.run(['tar', '-x', '-C', str(snapshot)], input=archive.stdout, check=True)
    else:
        shutil.copytree(out / selection['path'], snapshot, symlinks=True,
                        ignore=lambda folder, names: [n for n in names if n in ('.git', '.devlyn')
                                                      and Path(folder) == out / selection['path']])
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
