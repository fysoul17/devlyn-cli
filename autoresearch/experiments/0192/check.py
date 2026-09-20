"""Arm-blind external behavior checks. No participant instruction inspection."""
from pathlib import Path
import contextlib
import errno
import hashlib
import json
import os
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch


def snapshot(root):
    return {str(p.relative_to(root)): (('link', os.readlink(p)) if p.is_symlink()
            else ('file', p.read_bytes().hex(), stat.S_IMODE(p.stat().st_mode)))
            for p in root.rglob('*') if p.is_symlink() or p.is_file()}


def fixture(base):
    base = base.resolve()
    d = base / '.devlyn'; d.mkdir()
    state = {'run_id': 'trial', 'phases': {}, 'process_evidence': None}
    files = {'a.log.md': b'alpha\r\n', 'final-report.md': b'report\n',
             'probes/P1.py': b'print(1)\n', 'z.log.md': b'omega\n'}
    state['phases']['final_report'] = dict(output_sha256=hashlib.sha256(files['final-report.md']).hexdigest(),
        artifacts={'log_file': '.devlyn/final-report.md'})
    # Real judge-role state bindings exercise dynamic paths without external processes.
    binding = b'{"role":"primary"}\n'; stream = b'judge raw\n'
    files.update({'review-role.json': binding, 'review-stream.txt': stream})
    artifact = lambda name, raw: dict(path='.devlyn/' + name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    state['phases']['verify'] = dict(role_evidence={'primary': dict(artifact('review-role.json', binding),
        artifacts=[artifact('review-stream.txt', stream)])})
    files['pipeline.state.json'] = json.dumps(state).encode()
    for i, (name, raw) in enumerate(files.items()):
        p = d / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw); p.chmod(0o640 if i % 2 else 0o600)
    (d / 'unrelated.data').write_bytes(b'keep root')
    target = d / 'runs/trial'; target.mkdir(parents=True)
    (target / 'unrelated.data').write_bytes(b'keep destination')
    return d, target, files


def check(package, parent):
    m = runpy.run_path(str(package / 'archive_run.py'))
    rows = []
    def case(name, action):
        with tempfile.TemporaryDirectory(dir=parent) as temporary:
            try:
                detail = action(Path(temporary))
                rows.append(dict(check=name, pass_=True, detail=detail))
            except Exception as exc:
                rows.append(dict(check=name, pass_=False, error=repr(exc)))
    def success(base, cross=False):
        d, target, files = fixture(base); before = snapshot(d)
        with patch.object(os, 'rename', side_effect=OSError(errno.EXDEV, 'simulated cross-device')) if cross else contextlib.nullcontext():
            count = m['move_artifacts'](d, target)
        assert count == len(files), count
        after = snapshot(d)
        expected = {('runs/trial/' + n if n in files else n): v for n, v in before.items()}
        assert after == expected, (after.keys(), expected.keys())
        assert not (d / 'probes').exists()
        return dict(moved=count)
    case('same-filesystem', success)
    case('cross-filesystem', lambda b: success(b, True))
    def failure(base, boundary, selected, cross):
        d, target, files = fixture(base); before = snapshot(d)
        original_copy, original_stat, original_unlink = shutil.copyfile, shutil.copystat, os.unlink
        fired = []
        marker = OSError(errno.ENOSPC if boundary != 'unlink' else errno.EACCES, '0192 controlled ' + boundary)
        def selected_source(src):
            return Path(src) == d / selected
        def copy(src, dst, *args, **kwargs):
            if boundary == 'copy' and selected_source(src) and not fired:
                fired.append(str(src)); Path(dst).write_bytes(b'partial-copy'); raise marker
            return original_copy(src, dst, *args, **kwargs)
        def metadata(src, dst, *args, **kwargs):
            if boundary == 'metadata' and selected_source(src) and not fired:
                fired.append(str(src)); raise marker
            return original_stat(src, dst, *args, **kwargs)
        def unlink(src, *args, **kwargs):
            if boundary == 'unlink' and selected_source(src) and not fired:
                fired.append(str(src)); raise marker
            return original_unlink(src, *args, **kwargs)
        original_rename = os.rename
        def rename(src, dst, *args, **kwargs):
            # Cross both forward and rollback transfers when selected, rather than
            # silently making the rollback a same-filesystem special case.
            if cross or Path(src) == d / selected:
                raise OSError(errno.EXDEV, 'simulated cross-device')
            return original_rename(src, dst, *args, **kwargs)
        caught = None
        with patch.object(os, 'rename', side_effect=rename), patch.object(shutil, 'copyfile', side_effect=copy), \
             patch.object(shutil, 'copystat', side_effect=metadata), patch.object(os, 'unlink', side_effect=unlink):
            try: m['move_artifacts'](d, target)
            except OSError as exc: caught = exc
        assert fired, 'required failure not reached'
        assert caught is marker, ('original error not propagated', repr(caught))
        assert snapshot(d) == before, 'original bytes/modes or unrelated/partial output changed'
        assert m['move_artifacts'](d, target) == len(files), 'retry failed'
        expected = {('runs/trial/' + n if n in files else n): v for n, v in before.items()}
        assert snapshot(d) == expected, 'retry layout/bytes/modes changed'
        assert not (d / 'probes').exists()
        return dict(triggered=fired, error=str(caught))
    for boundary in ('copy', 'metadata', 'unlink'):
        for selected in ('a.log.md', 'pipeline.state.json', 'probes/P1.py', 'review-stream.txt'):
            for cross in (False, True):
                case(f'{boundary}/{selected}/all-cross={cross}', lambda b, a=boundary, s=selected, c=cross: failure(b,a,s,c))
    def refuse(base, kind):
        d, target, files = fixture(base)
        if kind == 'collision': (target / 'z.log.md').write_bytes(b'occupied')
        elif kind == 'link-collision': (target / 'z.log.md').symlink_to(base / 'absent')
        elif kind == 'report': (d / 'final-report.md').write_bytes(b'altered')
        elif kind == 'evidence': (d / 'review-stream.txt').write_bytes(b'altered')
        elif kind == 'json': (d / 'pipeline.state.json').write_text('{"run_id":"trial","run_id":"trial"}')
        before = snapshot(d)
        try: m['move_artifacts'](d, target)
        except m['ArchiveError']: pass
        else: raise AssertionError('invalid input accepted')
        assert snapshot(d) == before, 'refusal mutated input'
    for kind in ('collision', 'link-collision', 'report', 'evidence', 'json'):
        case(kind, lambda b, k=kind: refuse(b,k))
    def cli(base, invalid=False):
        d, target, files = fixture(base)
        if invalid: (d / 'pipeline.state.json').write_bytes(b'{broken')
        before = snapshot(d)
        result = subprocess.run([sys.executable, '-B', str(package / 'archive_run.py'), '--devlyn-dir', str(d)],
            cwd=base, capture_output=True, text=True, timeout=30)
        if invalid:
            assert result.returncode == 1 and 'archive blocked' in result.stderr and 'Traceback' not in result.stderr
            assert snapshot(d) == before
        else:
            assert result.returncode == 0 and f'files={len(files)}' in result.stdout, result.stderr
            expected = {('runs/trial/' + n if n in files else n): v for n, v in before.items()}
            assert snapshot(d) == expected
    case('cli-success', cli)
    case('cli-invalid', lambda b: cli(b, True))
    def selftest(base):
        result = subprocess.run([sys.executable, '-B', str(package / 'archive_run.py'), '--self-test'],
            cwd=base, env=dict(os.environ, TMPDIR=str(base)), capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr
        return dict(exit_code=result.returncode)
    case('existing-selftests', selftest)
    return rows
