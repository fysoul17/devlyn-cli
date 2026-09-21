"""Actual producer → candidate CLI integration. No measured product is edited."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import time
import tempfile

REPO = Path(__file__).resolve().parents[3]
E = REPO / '.devlyn/0198'
SCRATCH = REPO / '.git/devlyn-completion/bed944925305d19fa5e49678/scratch'
REL = Path('config/skills/_shared/resolve-bootstrap.py')
PRODUCER = REPO / 'config/skills/_shared/task-complete.py'
ENV = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
ENV.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_TEMPLATE_DIR='', PYTHONDONTWRITEBYTECODE='1')


def command(argv, cwd, **kwargs):
    p = subprocess.run([str(a) for a in argv], cwd=cwd, env=ENV, capture_output=True, text=True, timeout=60, **kwargs)
    return dict(argv=[str(a) for a in argv], exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)


def git(repo, *args):
    row = command(['git', *args], repo)
    assert row['exit_code'] == 0, row
    return row['stdout'].removesuffix('\n')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())


def snapshot(root):
    result = {}
    if not root.exists() and not root.is_symlink():
        return result
    def visit(p):
        info = p.lstat()
        kind = stat.S_IFMT(info.st_mode)
        value = os.readlink(p) if stat.S_ISLNK(kind) else hashlib.sha256(p.read_bytes()).hexdigest() if stat.S_ISREG(kind) else None
        result[str(p.relative_to(root))] = [kind, stat.S_IMODE(info.st_mode), value]
        if stat.S_ISDIR(kind):
            for child in p.iterdir():
                visit(child)
    visit(root)
    return result


def fixture(root, linked=False):
    base = root / 'base'
    base.mkdir()
    git(base, 'init', '-qb', 'main')
    git(base, 'config', 'user.name', 'Fixture')
    git(base, 'config', 'user.email', 'fixture@local')
    (base / 'tracked.txt').write_text('preserve source bytes\n')
    git(base, 'add', 'tracked.txt')
    git(base, 'commit', '-qm', 'fixture')
    git(base, 'remote', 'add', 'origin', 'https://github.com/fysoul17/devlyn-cli.git')
    args = [sys.executable, '-B', PRODUCER, 'allocate', '--repo', base, '--task', 'Actual task description — not a state object', '--branch', 'task/receipt-fixture', '--repository', 'fysoul17/devlyn-cli', '--base', 'main']
    if linked:
        args += ['--worktree', root / 'linked']
    allocation = command(args, base)
    assert allocation['exit_code'] == 0, allocation
    value = json.loads(allocation['stdout'])
    work, receipt = Path(value['worktree']), Path(value['receipt'])
    raw = receipt.read_text()
    data = json.loads(raw)
    assert isinstance(data['task'], str) and data['allocation'] == 'owned' and 'status' not in data
    assert data['id'] == hashlib.sha256(data['branch'].encode()).hexdigest()[:24]
    return work, receipt, data, dict(allocation=allocation, original_receipt=raw)


SUCCESS = ['owned', 'linked', 'absent-root', 'absent-directory', 'absent-receipt', 'detached', 'foreign-branch', 'foreign-worktree', 'foreign-terminal', 'local-producer', 'local-status-unbound', 'local-null', 'status-null', 'no-remote', 'spec', 'verify-only', 'prior-legacy']
BLOCKED = ['interrupted', 'complete', 'abandoned', 'local-bound', 'local-empty-bound', 'flag-bound', 'flag-empty-bound', 'id-mismatch', 'invalid-json', 'duplicate', 'nonfinite', 'array', 'branch-type', 'worktree-type', 'status-type', 'local-type', 'acceptance-type', 'container-link', 'directory-link', 'receipt-link', 'dangling-link', 'container-file', 'directory-file', 'receipt-directory', 'complete-prior', 'interrupted-prior']
CASES = SUCCESS + BLOCKED


def check(product, cases=CASES):
    rows = []
    for name in cases:
        with tempfile.TemporaryDirectory(prefix='0198-case-', dir=SCRATCH) as tmp:
            root = Path(tmp)
            work, receipt, data, evidence = fixture(root, linked=name == 'linked')
            identity = data['id']
            expected = {'receipt_id': identity}
            argv = ['a', 'natural', 'task']
            if name in ('foreign-branch', 'foreign-terminal'):
                data['branch'] = 'other'; expected = None
                if name == 'foreign-terminal': data.update(status='COMPLETE', allocation='allocating')
            elif name == 'foreign-worktree': data['worktree'] = str(root / 'elsewhere'); expected = None
            elif name.startswith('interrupted'): data['allocation'] = 'allocating'
            elif name.startswith('complete'): data['status'] = 'COMPLETE'
            elif name == 'abandoned': data['status'] = 'ABANDONED'
            elif name in ('local-bound', 'local-empty-bound', 'local-status-unbound', 'local-null'):
                data['status'] = 'LOCAL_ONLY'
                if name == 'local-bound': data['acceptance'] = {'kind': 'direct'}
                elif name == 'local-empty-bound': data['acceptance'] = {}
                elif name == 'local-null': data['acceptance'] = None
            elif name in ('flag-bound', 'flag-empty-bound'):
                data.update(local_only=True, acceptance={} if name == 'flag-empty-bound' else {'kind': 'direct'})
            elif name == 'id-mismatch': data['id'] = 'not-the-directory-id'
            elif name == 'branch-type': data['branch'] = 1
            elif name == 'worktree-type': data['worktree'] = None
            elif name == 'status-type': data['status'] = []
            elif name == 'local-type': data['local_only'] = 1
            elif name == 'acceptance-type': data['acceptance'] = []
            elif name == 'status-null': data['status'] = None
            if data != json.loads(evidence['original_receipt']):
                write(receipt, data)
            if name == 'local-producer':
                evidence['local_only'] = command([sys.executable, '-B', PRODUCER, 'complete', '--receipt', receipt, '--local-only'], work)
                assert evidence['local_only']['exit_code'] == 0, evidence
                evidence['local_receipt'] = receipt.read_text()
                actual = json.loads(evidence['local_receipt'])
                assert actual['local_only'] is True and 'status' not in actual and 'acceptance' not in actual
            elif name.startswith('absent-'):
                target = {'absent-root': receipt.parent.parent, 'absent-directory': receipt.parent, 'absent-receipt': receipt}[name]
                shutil.rmtree(target) if target.is_dir() else target.unlink()
                expected = None
            elif name == 'detached':
                git(work, 'checkout', '--detach', '-q'); expected = None
                write(receipt, b'{invalid ignored under detached HEAD')
            elif name == 'no-remote': git(work, 'remote', 'remove', 'origin')
            elif name in ('invalid-json', 'duplicate', 'nonfinite', 'array'):
                write(receipt, {'invalid-json': b'{broken', 'duplicate': ('{"branch":"duplicate",' + json.dumps(data)[1:]).encode(), 'nonfinite': (json.dumps(data)[:-1] + ',"unused":NaN}').encode(), 'array': b'[]'}[name])
            elif name in ('container-link', 'directory-link', 'receipt-link', 'dangling-link'):
                target = receipt.parent.parent if name == 'container-link' else receipt.parent if name == 'directory-link' else receipt
                moved = root / 'redirect'
                target.rename(moved)
                target.symlink_to(root / 'missing' if name == 'dangling-link' else moved, target_is_directory=moved.is_dir())
            elif name in ('container-file', 'directory-file', 'receipt-directory'):
                target = receipt.parent.parent if name == 'container-file' else receipt.parent if name == 'directory-file' else receipt
                shutil.rmtree(target) if target.is_dir() else target.unlink()
                target.mkdir() if name == 'receipt-directory' else target.write_text('not a directory')
            if name in ('spec', 'verify-only'):
                (work / 'spec.md').write_text('# Task\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n{"verification_commands":[{"cmd":"printf ok","stdout_contains":["ok"]}]}\n```\n')
                argv = ['--spec', 'spec.md']
                if name == 'verify-only':
                    (work / 'external.patch').write_text('external bytes\n')
                    argv = ['--verify-only', 'external.patch', *argv]
            if name.endswith('-prior') or name == 'prior-legacy':
                write(work / '.devlyn/pipeline.state.json', {'run_id': 'rs-prior', 'phases': {'final_report': {'verdict': 'PASS', 'completed_at': '2026-09-21T00:00:00Z'}}})
                write(work / '.devlyn/final-report.md', b'prior report\n')
            # Pre-existing lock is explicitly outside the .devlyn no-write contract.
            Path(git(work, 'rev-parse', '--absolute-git-dir'), 'devlyn-bootstrap.lock').touch()
            before = snapshot(work / '.devlyn')
            source_before = snapshot(work / 'tracked.txt')
            redirect_before = snapshot(root / 'redirect')
            receipts_before = snapshot(root / 'base/.git/devlyn-completion')
            index_before = snapshot(Path(git(work, 'rev-parse', '--absolute-git-dir')) / 'index')
            refs_before = git(work, 'show-ref', '--head')
            errors = []
            try:
                invocation = command([sys.executable, '-B', product / REL, *argv], work)
            except subprocess.TimeoutExpired as exc:
                invocation = dict(exit_code=124, stdout=(exc.stdout or b'').decode(errors='replace') if isinstance(exc.stdout, bytes) else exc.stdout or '', stderr=str(exc))
                errors.append('candidate CLI timeout')
            try: response = json.loads(invocation['stdout'])
            except ValueError: response = None
            state_path = work / '.devlyn/pipeline.state.json'
            try:
                state = json.loads(state_path.read_text()) if state_path.exists() else None
            except (ValueError, UnicodeError, OSError) as exc:
                state = None
                errors.append('candidate state unreadable: ' + str(exc))
            try:
                preserved = source_before == snapshot(work / 'tracked.txt') and redirect_before == snapshot(root / 'redirect') and receipts_before == snapshot(root / 'base/.git/devlyn-completion') and index_before == snapshot(Path(git(work, 'rev-parse', '--absolute-git-dir')) / 'index') and refs_before == git(work, 'show-ref', '--head')
            except (OSError, AssertionError) as exc:
                preserved = False
                errors.append('candidate preservation failure: ' + str(exc))
            if name in BLOCKED:
                passed = invocation['exit_code'] != 0 and isinstance(response, dict) and response.get('ok') is False and str(response.get('blocked', '')).startswith('BLOCKED:') and bool(response.get('detail')) and before == snapshot(work / '.devlyn')
            else:
                passed = invocation['exit_code'] == 0 and isinstance(response, dict) and response.get('ok') is True and isinstance(state, dict) and 'task' in state and state['task'] == expected
                if name == 'prior-legacy':
                    archived = work / '.devlyn/runs/rs-prior/pipeline.state.json'
                    try:
                        passed = passed and archived.exists() and 'task' not in json.loads(archived.read_text())
                    except (ValueError, UnicodeError, OSError, TypeError) as exc:
                        passed = False
                        errors.append('candidate archive unreadable: ' + str(exc))
            rows.append(dict(case=name, passed=bool(passed and preserved and not errors), errors=errors, preserved=preserved, expected='BLOCKED' if name in BLOCKED else expected, response=response, state=state, invocation=invocation, producer=evidence))
    return dict(passed=all(r['passed'] for r in rows), passed_checks=sum(r['passed'] for r in rows), total=len(rows), rows=rows)


def regression(product, expects_task=True):
    import ast
    rows = []
    baseline = (E / 'input' / REL).read_text()
    tests = '\n\n'.join(ast.get_source_segment(baseline, node) for node in ast.parse(baseline).body if isinstance(node, ast.FunctionDef) and (node.name == 'self_test' or node.name.endswith('_self_test')))
    if expects_task:
        assert tests.count('        expected = {\n            "version": "3.0",') == 1
        tests = tests.replace('        expected = {\n            "version": "3.0",', '        expected = {\n            "task": None,\n            "version": "3.0",')
    for name, argv in [('baseline-self-tests', [sys.executable, '-B', str(REL), '--self-test']), ('candidate-self-tests', [sys.executable, '-B', str(REL), '--self-test']), ('supplied-and-added-tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'])]:
        with tempfile.TemporaryDirectory(prefix='0198-regression-', dir=SCRATCH) as tmp:
            copied = Path(tmp) / 'product'
            shutil.copytree(product, copied, ignore=shutil.ignore_patterns('.git', '.devlyn', '__pycache__'))
            if name == 'baseline-self-tests':
                path = copied / REL
                code = path.read_text()
                if code.count('if __name__ == "__main__":') != 1:
                    rows.append(dict(case=name, passed=False, error='candidate changed baseline test injection boundary'))
                    continue
                path.write_text(code.replace('if __name__ == "__main__":', tests + '\n\nif __name__ == "__main__":'))
            started = time.monotonic()
            try:
                p = subprocess.run(argv, cwd=copied, capture_output=True, text=True, timeout=300, env=dict(ENV, TMPDIR=tmp))
                rows.append(dict(case=name, seconds=time.monotonic() - started, passed=p.returncode == 0, exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr))
            except subprocess.TimeoutExpired as exc:
                rows.append(dict(case=name, passed=False, error=str(exc)))
    return rows
