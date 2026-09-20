"""External tests use product bytes only; condition/engine labels are not inputs."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile


def check(package, scratch):
    rows = []
    def call(project, name='AGENTS.md'):
        return subprocess.run(['node', '-e', 'require(process.argv[1]).updateInstructions(process.argv[2])',
            str(package / 'bin/instructions.js'), name], cwd=project, capture_output=True, timeout=20)

    def record(label, operation):
        try:
            details = operation()
        except (AssertionError, OSError, ValueError, subprocess.SubprocessError) as exc:
            rows.append(dict(check=label, pass_=False, error=repr(exc)))
        else:
            rows.append(dict(check=label, pass_=True, details=details))

    for name in ('AGENTS.md', 'CLAUDE.md'):
        for component in ('.devlyn', '.devlyn/instructions'):
            for kind in ('outside-link', 'inside-link', 'dangling-link', 'file'):
                for action in ('backup', 'incoming'):
                    def blocked(name=name, component=component, kind=kind, action=action):
                        with tempfile.TemporaryDirectory(dir=scratch) as temp:
                            base = Path(temp); project = base / 'project'; project.mkdir()
                            before = (b'\xef\xbb\xbf# Team \xed\x95\x9c\xea\xb8\x80\r\nKeep!\r\n' if action == 'backup'
                                      else b'<!-- devlyn:instructions:begin broken -->\nlocal edit\n')
                            dest = project / name; dest.write_bytes(before); dest.chmod(0o640)
                            entry = project / component; entry.parent.mkdir(exist_ok=True)
                            target = (project if kind == 'inside-link' else base) / 'target'
                            if kind == 'file':
                                entry.write_bytes(b'keep directory obstruction')
                            else:
                                if kind != 'dangling-link':
                                    target.mkdir(); (target / 'sentinel').write_bytes(b'keep target')
                                entry.symlink_to(target, target_is_directory=True)
                            result = call(project, name)
                            assert result.returncode != 0, result.stdout
                            assert dest.read_bytes() == before
                            assert dest.stat().st_mode & 0o777 == 0o640
                            if kind == 'file':
                                assert entry.read_bytes() == b'keep directory obstruction'
                            else:
                                assert entry.is_symlink() and entry.readlink() == target
                                if kind == 'dangling-link':
                                    assert not target.exists()
                                else:
                                    assert sorted(p.name for p in target.iterdir()) == ['sentinel']
                                    assert (target / 'sentinel').read_bytes() == b'keep target'
                            assert not list(project.glob(name + '.*.tmp'))
                            return dict(diagnostic=result.stderr.decode(errors='replace'), offending_path=str(entry))
                    record(f'{name}/{component}/{kind}/{action}', blocked)

        def ordinary(name=name):
            with tempfile.TemporaryDirectory(dir=scratch) as temp:
                project = Path(temp); dest = project / name
                before = b'\xef\xbb\xbf# My rules\r\nKeep exact bytes\r\n'
                dest.write_bytes(before); dest.chmod(0o664)
                recovery = project / '.devlyn/instructions'; recovery.mkdir(parents=True)
                (recovery / 'unrelated-link').symlink_to(project / 'missing')
                first = call(project, name); assert first.returncode == 0, first.stderr
                installed = dest.read_bytes(); assert installed.startswith(before)
                assert dest.stat().st_mode & 0o777 == 0o664
                backup, = recovery.glob('*.backup'); assert backup.read_bytes() == before
                assert (recovery / '.gitignore').read_bytes() == b'*\n'
                assert (recovery / 'unrelated-link').is_symlink()
                second = call(project, name); assert second.returncode == 0, second.stderr
                assert dest.read_bytes() == installed
                # An exact existing backup can be reused; conflicting bytes must be retained.
                dest.write_bytes(before)
                assert call(project, name).returncode == 0
                backup.write_bytes(b'different backup'); dest.write_bytes(before)
                conflict = call(project, name); assert conflict.returncode != 0
                assert dest.read_bytes() == before and backup.read_bytes() == b'different backup'
                assert b'Instruction recovery file differs' in conflict.stderr
        record(name + '/ordinary-and-collision', ordinary)

        def incoming(name=name):
            with tempfile.TemporaryDirectory(dir=scratch) as temp:
                project = Path(temp); dest = project / name
                before = b'<!-- devlyn:instructions:begin broken -->\nCustom edit\n'
                dest.write_bytes(before)
                result = call(project, name); assert result.returncode != 0
                assert b'needs merge' in result.stderr
                incoming, = (project / '.devlyn/instructions').glob('*.incoming')
                assert b'devlyn:instructions:begin sha256=' in incoming.read_bytes()
                assert dest.read_bytes() == before
        record(name + '/ordinary-incoming', incoming)

        def unused(name=name):
            with tempfile.TemporaryDirectory(dir=scratch) as temp:
                project = Path(temp); dest = project / name
                (project / '.devlyn').write_bytes(b'not a directory, unused')
                result = call(project, name); assert result.returncode == 0, result.stderr
                installed = dest.read_bytes()
                result = call(project, name); assert result.returncode == 0, result.stderr
                assert dest.read_bytes() == installed
                assert (project / '.devlyn').read_bytes() == b'not a directory, unused'
        record(name + '/unused-recovery', unused)

        def legacy(name=name):
            with tempfile.TemporaryDirectory(dir=scratch) as temp:
                project = Path(temp); dest = project / name
                prefix, suffix = b'\xef\xbb\xbf# Team\r\n\r\n', b'\r\n# Keep this suffix\r\n'
                template = (package / name).read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
                before = prefix + template + suffix; dest.write_bytes(before)
                result = call(project, name); assert result.returncode == 0, result.stderr
                after = dest.read_bytes()
                assert after.startswith(prefix) and after.endswith(suffix)
                assert after.count(b'devlyn:instructions:begin') == 1
                backup, = (project / '.devlyn/instructions').glob('*.backup')
                assert backup.read_bytes() == before
        record(name + '/exact-template-migration', legacy)

        def in_place(name=name):
            with tempfile.TemporaryDirectory(dir=scratch) as temp:
                copy = Path(temp) / 'package'; shutil.copytree(package, copy)
                (copy / '.devlyn').write_bytes(b'unused')
                before = (copy / name).read_bytes()
                result = subprocess.run(['node', '-e',
                    'require(process.argv[1]).updateInstructions(process.argv[2])',
                    str(copy / 'bin/instructions.js'), name], cwd=copy, capture_output=True, timeout=20)
                assert result.returncode == 0, result.stderr
                assert (copy / name).read_bytes() == before
                assert (copy / '.devlyn').read_bytes() == b'unused'
        record(name + '/package-in-place', in_place)
    return rows


if __name__ == '__main__':
    result = check(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    print(json.dumps(result, indent=2))
    raise SystemExit(not all(row['pass_'] for row in result))
