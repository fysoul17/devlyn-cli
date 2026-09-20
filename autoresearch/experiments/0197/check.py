"""Arm-blind actual-CLI checks. Fixtures are disposable; products are never edited."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[3]
SCRATCH = REPO / '.git/devlyn-completion/6679a50a1aea2765d110b7d3/scratch'
REL = Path('config/skills/_shared/task-complete.py')
ENV = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_TEMPLATE_DIR='', PYTHONDONTWRITEBYTECODE='1')
KEYS = ('runs', 'task_evidence', 'programs', 'pending_reconcile', 'unowned_artifacts')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())


def snapshot(root):
    rows = {}
    def visit(p):
        s = p.lstat()
        kind = stat.S_IFMT(s.st_mode)
        try:
            value = os.readlink(p) if stat.S_ISLNK(s.st_mode) else hashlib.sha256(p.read_bytes()).hexdigest() if stat.S_ISREG(s.st_mode) else None
        except PermissionError:
            value = 'UNREADABLE'
        rows[str(p.relative_to(root))] = [kind, stat.S_IMODE(s.st_mode), value, s.st_mtime_ns]
        if stat.S_ISDIR(s.st_mode):
            try:
                children = list(p.iterdir())
            except PermissionError:
                rows[str(p.relative_to(root))].append('UNREADABLE')
                children = []
            for child in children:
                visit(child)
    visit(root)
    return rows


def bytes_under(path):
    mode = path.lstat().st_mode
    if stat.S_ISREG(mode):
        return path.stat().st_size
    if stat.S_ISDIR(mode):
        return sum(bytes_under(p) for p in path.iterdir())
    return 0


def entry(repo, path):
    return dict(path=path.relative_to(repo).as_posix(), logical_bytes=bytes_under(path))


def fixture(root, linked=False):
    base = root / 'base'
    base.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(base)], check=True, env=ENV)
    subprocess.run(['git', '-C', str(base), '-c', 'user.name=Fixture', '-c', 'user.email=f@local', 'commit', '--allow-empty', '-qm', 'fixture'], check=True, env=ENV)
    repo = base
    if linked:
        repo = root / 'linked'
        subprocess.run(['git', '-C', str(base), 'worktree', 'add', '-qb', 'linked', str(repo)], check=True, capture_output=True, env=ENV)
    common = base / '.git'
    receipts = common / 'devlyn-completion'
    d = repo / '.devlyn'
    return repo, common, receipts, d


def populated(repo, receipts, d):
    for name, task in [('rs-a', {'receipt_id': 'a'}), ('rs-b', {'receipt_id': 'a'}), ('rs-u', None), ('rs-m', {'receipt_id': 'missing'})]:
        write(d / 'runs' / name / 'pipeline.state.json', {'task': task})
        write(d / 'runs' / name / 'payload.bin', b'12345')
    write(d / 'runs/rs-legacy/pipeline.state.json', {})
    write(d / 'runs/rs-null/pipeline.state.json', {'task': {}})
    write(d / 'runs/terminal_active/blob', b'ignored')
    write(d / 'runs/run_daemon/blob', b'ignored')
    write(receipts / 'a/receipt.json', {'status': 'COMPLETE', 'worktree': str(repo.resolve()), 'files': {'.devlyn/bound/check.txt': {}}, 'reconcile': {'status': 'DONE'}})
    write(receipts / 'b/receipt.json', {'status': 'PR', 'worktree': str(repo.parent / 'elsewhere'), 'files': {'.devlyn/foreign/check.txt': {}}, 'reconcile': {'status': 'PENDING', 'reason': 'PR open'}})
    write(d / 'bound/check.txt', b'accepted')
    write(d / 'foreign/check.txt', b'not ours')
    write(d / 'task-evidence/a/x', b'abc')
    write(d / 'programs/p/x', b'1234567')
    write(d / 'notes/data', b'123456789')
    write(d / 'verify.primary.findings.jsonl', b'{}\n')
    write(d / 'engines.json', {})
    groups = []
    for identity, names, status in [(None, ['rs-legacy', 'rs-null', 'rs-u'], 'untasked'), ('a', ['rs-a', 'rs-b'], 'COMPLETE'), ('missing', ['rs-m'], 'receipt-missing')]:
        items = [entry(repo, d / 'runs' / name) for name in names]
        groups.append(dict(receipt_id=identity, status=status, runs=items, logical_bytes=sum(x['logical_bytes'] for x in items)))
    return dict(runs=groups, task_evidence=[entry(repo, d / 'task-evidence/a')], programs=[entry(repo, d / 'programs/p')],
        pending_reconcile=[dict(receipt_id='b', path='devlyn-completion/b/receipt.json', reason='PR open', logical_bytes=(receipts / 'b/receipt.json').stat().st_size)],
        unowned_artifacts=[entry(repo, d / 'foreign'), entry(repo, d / 'notes')])


def regression(product):
    rows = []
    for name, argv in [('existing-self-test', [sys.executable, '-B', str(product / REL), '--self-test']), ('supplied-and-added-tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'])]:
        with tempfile.TemporaryDirectory(prefix='0197-regression-', dir=SCRATCH) as tmp:
            copy = Path(tmp) / 'product'
            shutil.copytree(product, copy, ignore=shutil.ignore_patterns('.git', '.devlyn', '__pycache__'))
            argv = [part.replace(str(product), str(copy)) for part in argv]
            env = dict(ENV, TMPDIR=tmp)
            try:
                proc = subprocess.run(argv, cwd=copy, capture_output=True, text=True, timeout=300, env=env)
                rows.append(dict(case=name, tier='regression', passed=proc.returncode == 0, exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr))
            except subprocess.TimeoutExpired as exc:
                rows.append(dict(case=name, tier='regression', passed=False, error=str(exc)))
    return rows


def check(product, include_regression=True):
    rows = []
    cases = ['empty', 'normal', 'linked', 'bytes-links', 'null-status', 'unsafe-id', 'invalid-state', 'duplicate-json', 'nonfinite-json', 'missing-state', 'bad-receipt', 'bad-task-type', 'bad-reconcile-type', 'bad-files-type', 'redirect-root', 'redirect-container', 'redirect-run', 'redirect-receipts', 'redirect-receipt', 'redirect-json', 'file-container', 'unsafe-files', 'receipt-duplicate', 'receipt-nonfinite', 'receipt-syntax', 'receipt-array', 'receipt-json-link', 'id-empty', 'id-dot', 'id-backslash', 'id-number', 'id-nul', 'pending-no-devlyn', 'pending-sort', 'checkout-alias', 'layout-run-file', 'layout-receipt-file', 'layout-missing-receipt', 'dangling-entries', 'unreadable-state', 'unreadable-dir']
    for name in cases:
        with tempfile.TemporaryDirectory(prefix='0197-check-', dir=SCRATCH) as tmp:
            root = Path(tmp)
            repo, common, receipts, d = fixture(root, linked=name == 'linked')
            expected = {k: [] for k in KEYS} if name == 'empty' else populated(repo, receipts, d)
            failure = name not in ('empty', 'normal', 'linked', 'bytes-links', 'null-status', 'unsafe-files', 'pending-no-devlyn', 'pending-sort', 'checkout-alias', 'layout-run-file', 'layout-receipt-file', 'layout-missing-receipt', 'dangling-entries')
            invocation_repo = repo
            if name == 'unsafe-files':
                path = receipts / 'a/receipt.json'
                data = json.loads(path.read_text())
                data['files'].update({'.devlyn/../.devlyn/notes/x': {}, '/.devlyn/notes/x': {}, 'elsewhere/notes/x': {}})
                write(path, data)
            elif name.startswith('receipt-'):
                path = receipts / 'a/receipt.json'
                if name == 'receipt-json-link':
                    outside = root / 'receipt-target'
                    path.rename(outside)
                    path.symlink_to(outside)
                else:
                    write(path, {'receipt-duplicate': b'{"status":null,"status":"COMPLETE"}', 'receipt-nonfinite': b'{"other":NaN}', 'receipt-syntax': b'{', 'receipt-array': b'[]'}[name])
            elif name.startswith('id-'):
                identity = {'id-empty': '', 'id-dot': '.', 'id-backslash': 'a\\b', 'id-number': 42, 'id-nul': 'a\x00b'}[name]
                write(d / 'runs/rs-a/pipeline.state.json', {'task': {'receipt_id': identity}})
            elif name == 'pending-no-devlyn':
                shutil.rmtree(d)
                expected = {**{k: [] for k in KEYS}, 'pending_reconcile': expected['pending_reconcile']}
            elif name == 'pending-sort':
                for identity in ('z', 'aa'):
                    path = receipts / identity / 'receipt.json'
                    write(path, {'reconcile': {'status': 'PENDING'}})
                    expected['pending_reconcile'].append(dict(receipt_id=identity, path=path.relative_to(common).as_posix(), reason=None, logical_bytes=path.stat().st_size))
                expected['pending_reconcile'].sort(key=lambda x: x['receipt_id'])
            elif name == 'checkout-alias':
                invocation_repo = root / 'alias'
                invocation_repo.symlink_to(repo, target_is_directory=True)
            elif name == 'layout-run-file':
                write(d / 'runs/rs-file', b'not a directory')
            elif name == 'layout-receipt-file':
                write(receipts / 'stray-file', b'not a directory')
            elif name == 'layout-missing-receipt':
                (receipts / 'no-receipt').mkdir()
            elif name == 'dangling-entries':
                for parent in (d, d / 'programs', d / 'task-evidence'):
                    (parent / 'broken').symlink_to(root / 'absent')
                expected['programs'].insert(0, entry(repo, d / 'programs/broken'))
                expected['task_evidence'].append(entry(repo, d / 'task-evidence/broken'))
                expected['unowned_artifacts'].insert(0, entry(repo, d / 'broken'))
            elif name == 'unreadable-state':
                (d / 'runs/rs-a/pipeline.state.json').chmod(0)
            elif name == 'unreadable-dir':
                (d / 'programs/p').chmod(0)
            elif name == 'bytes-links':
                p = d / 'programs/p'
                os.link(p / 'x', p / 'hardlink')
                (p / 'outside').symlink_to(root / 'base/.git', target_is_directory=True)
                os.mkfifo(p / 'pipe')
                (d / 'task-evidence/symlink').symlink_to(p, target_is_directory=True)
                expected['programs'] = [entry(repo, p)]
                expected['task_evidence'].append(entry(repo, d / 'task-evidence/symlink'))
            elif name == 'null-status':
                write(receipts / 'a/receipt.json', {'files': {'.devlyn/bound/check.txt': {}}, 'worktree': str(repo.resolve())})
                expected['runs'][1]['status'] = None
            elif name == 'unsafe-id':
                write(d / 'runs/rs-a/pipeline.state.json', {'task': {'receipt_id': '../a'}})
            elif name in ('invalid-state', 'duplicate-json', 'nonfinite-json', 'bad-task-type'):
                write(d / 'runs/rs-a/pipeline.state.json', {'invalid-state': b'[]', 'duplicate-json': b'{"task":null,"task":{}}', 'nonfinite-json': b'{"other":NaN}', 'bad-task-type': b'{"task":[]}' }[name])
            elif name == 'missing-state':
                (d / 'runs/rs-a/pipeline.state.json').unlink()
            elif name in ('bad-receipt', 'bad-reconcile-type', 'bad-files-type'):
                write(receipts / 'a/receipt.json', {'bad-receipt': b'{"status":42}', 'bad-reconcile-type': b'{"reconcile":[]}', 'bad-files-type': b'{"files":[]}' }[name])
            elif name.startswith('redirect-'):
                target = {'redirect-root': d, 'redirect-container': d / 'programs', 'redirect-run': d / 'runs/rs-a', 'redirect-receipts': receipts, 'redirect-receipt': receipts / 'a', 'redirect-json': d / 'runs/rs-a/pipeline.state.json'}[name]
                outside = root / 'redirected'
                target.rename(outside)
                target.symlink_to(outside, target_is_directory=outside.is_dir())
            elif name == 'file-container':
                shutil.rmtree(d / 'programs')
                write(d / 'programs', b'not directory')
            before = snapshot(root)
            try:
                proc = subprocess.run([sys.executable, '-B', str(product / REL), 'history', '--repo', str(invocation_repo)], cwd=product, capture_output=True, text=True, timeout=20, env=ENV)
                try:
                    actual = json.loads(proc.stdout)
                except ValueError:
                    actual = None
                after = snapshot(root)
                changes = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
                unchanged = not changes
                passed = (proc.returncode != 0 and isinstance(actual, dict) and actual.get('status') == 'BLOCKED' and isinstance(actual.get('reason'), str) and bool(actual['reason'])) if failure else proc.returncode == 0 and actual == expected
                rows.append(dict(case=name, tier='error' if failure else 'success', passed=bool(passed and unchanged), unchanged=unchanged, changed_paths=changes, exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, expected='BLOCKED' if failure else expected))
            except subprocess.TimeoutExpired as exc:
                rows.append(dict(case=name, passed=False, error=str(exc)))
    if include_regression:
        rows.extend(regression(product))
    normal_pass = next(r['passed'] for r in rows if r['case'] == 'normal')
    return dict(error_tier_eligible=normal_pass, success_passed=sum(r['passed'] for r in rows if r.get('tier') == 'success'), success_total=sum(r.get('tier') == 'success' for r in rows), passed=all(r['passed'] for r in rows), passed_checks=sum(r['passed'] for r in rows), total=len(rows), checks=rows)


if __name__ == '__main__':
    print(json.dumps(check(Path(sys.argv[1]).resolve()), indent=2))
