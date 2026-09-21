"""Replay exposed 0198 branch witnesses; terminal status is a fixture mutation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys
import tempfile

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('checks0198', REPO / 'autoresearch/experiments/0198/check.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def check(product, scratch):
    for case in ('normal', 'trailing-nbsp', 'branch-tag-collision'):
        for terminal in (False, True):
            with tempfile.TemporaryDirectory(prefix='0204-witness-', dir=scratch) as tmp:
                work = Path(tmp) / 'repo'
                work.mkdir()
                c.git(work, 'init', '-qb', 'main')
                c.git(work, 'config', 'user.name', 'Fixture')
                c.git(work, 'config', 'user.email', 'fixture@local')
                (work / 'source.txt').write_bytes(b'keep source\n')
                c.git(work, 'add', 'source.txt')
                c.git(work, 'commit', '-qm', 'fixture')
                c.git(work, 'remote', 'add', 'origin', 'https://github.com/fysoul17/devlyn-cli.git')
                branch = 'task/x' + ('\u00a0' if case == 'trailing-nbsp' else '')
                c.git(work, 'check-ref-format', 'refs/heads/' + branch)
                allocation = c.command([sys.executable, '-B', c.PRODUCER, 'allocate',
                    '--repo', work, '--task', 'Actual receipt for branch witness',
                    '--branch', branch, '--repository', 'fysoul17/devlyn-cli', '--base', 'main'], work)
                if allocation['exit_code']:
                    raise RuntimeError(allocation)
                receipt = Path(json.loads(allocation['stdout'])['receipt'])
                original_receipt = receipt.read_text()
                data = json.loads(original_receipt)
                if data['branch'] != branch or data['id'] != hashlib.sha256(branch.encode()).hexdigest()[:24]:
                    raise RuntimeError('allocator did not preserve exact branch')
                if terminal:
                    data['status'] = 'COMPLETE'
                    c.write(receipt, data)
                if case == 'branch-tag-collision':
                    c.git(work, 'tag', branch)
                full = c.git(work, 'symbolic-ref', 'HEAD')
                short = c.git(work, 'symbolic-ref', '--short', 'HEAD')
                if full != 'refs/heads/' + branch:
                    raise RuntimeError('witness HEAD does not match the allocated branch')
                (work / '.git/devlyn-bootstrap.lock').touch()
                before = c.snapshot(work)
                run = c.command([sys.executable, '-B', product / c.REL, 'receipt', 'witness'], work)
                after = c.snapshot(work)
                try:
                    output = json.loads(run['stdout'])
                    output_error = None if isinstance(output, dict) else 'CLI output is not an object'
                except ValueError as exc:
                    output, output_error = None, str(exc)
                state_path = work / '.devlyn/pipeline.state.json'
                try:
                    state = json.loads(state_path.read_text()) if state_path.exists() else None
                    state_error = None
                except ValueError as exc:
                    state, state_error = None, str(exc)
                kept = {k: v for k, v in after.items() if k != '.devlyn' and not k.startswith('.devlyn/')} == before
                passed = (run['exit_code'] != 0 and isinstance(output, dict) and output.get('ok') is False and before == after) if terminal else (
                    run['exit_code'] == 0 and isinstance(state, dict) and state.get('task') == {'receipt_id': data['id']} and kept)
                yield dict(case=case, terminal=terminal, passed=passed and not output_error and not state_error,
                    preserved=kept, branch=branch, full_ref=full, short_ref=short,
                    allocation=allocation, producer_receipt=original_receipt,
                    evaluated_receipt=receipt.read_text(), invocation=run, state=state,
                    output_error=output_error, state_error=state_error)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: witnesses.py <product> <owned-scratch> <new-result.json>')
    product, scratch, output = map(Path, sys.argv[1:])
    # Reserve before execution; interrupted evidence cannot be silently rerolled.
    with output.open('x') as stream:
        rows = []
        try:
            for row in check(product.resolve(), scratch.resolve()):
                rows.append(row)
        finally:
            json.dump(dict(product=str(product.resolve()),
                source_sha256=c.snapshot(product / 'config'), rows=rows), stream, indent=2)
            stream.write('\n')
    print(json.dumps({row['case'] + ('-terminal' if row['terminal'] else '-owned'): row['passed'] for row in rows}))
    raise SystemExit(0 if all(row['passed'] for row in rows) else 1)
