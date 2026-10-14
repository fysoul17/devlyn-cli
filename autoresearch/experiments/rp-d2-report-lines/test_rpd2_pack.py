"""Synthetic archives only; registry hashes and local Git blobs are injected."""
import importlib.util
import io
from pathlib import Path
import tarfile

import pytest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('rpd2_test_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(pack, root, monkeypatch):
    source = root / 'registry.tgz'
    before = b'# Instructions\n\n' + pack.OLD + b'\n## End\n'
    after = before.replace(pack.OLD, pack.NEW)
    with tarfile.open(source, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
        for name, data in [('package/package.json', b'{"name":"devlyn-cli","version":"4.2.18"}'),
                           (pack.MEMBER, before), ('package/bin/devlyn.js', b'// fixture\n'),
                           ('package/a-long-name-' + 'z' * 110, b'\x00\xffbytes\n')]:
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o755 if '/bin/' in name else 0o644, 1720000123
            info.uid, info.gid, info.uname, info.gname = 501, 20, 'fixture', 'staff'
            archive.addfile(info, io.BytesIO(data))
        directory = tarfile.TarInfo('package/empty')
        directory.type, directory.mode, directory.mtime = tarfile.DIRTYPE, 0o755, 42
        archive.addfile(directory)
        link = tarfile.TarInfo('package/link')
        link.type, link.linkname, link.mtime = tarfile.SYMTYPE, 'bin/devlyn.js', 55
        archive.addfile(link)
    registration = dict(release=dict(version='4.2.18', **pack.identity(source)))
    real_read = pack.read
    monkeypatch.setattr(pack, 'read', lambda path: registration if Path(path) == pack.PRIOR / 'registration.json' else real_read(path))
    commit = 'a' * 40
    def git(*args):
        if args == ('rev-parse', '--verify', commit + '^{commit}'):
            return (commit + '\n').encode()
        assert args[0] == 'show'
        return before if args[1] == '7516ebc9:' + pack.FILE else after
    monkeypatch.setattr(pack, 'git', git)
    return source, before, after, commit


def test_pack_is_deterministic_copy_and_exact_one_file_diff(tmp_path, monkeypatch):
    p = load('pack')
    source, before, after, commit = fixture(p, tmp_path, monkeypatch)
    first = p.build(source, tmp_path / 'first', commit)
    second = p.build(source, tmp_path / 'second', commit)
    assert first.read_bytes() == second.read_bytes()
    assert (first.parent / 'X.tgz').read_bytes() == source.read_bytes()
    assert (first.parent / 'Y.tgz').read_bytes() == (second.parent / 'Y.tgz').read_bytes()
    assert (first.parent / 'Y.tgz').read_bytes()[4:8] == b'\0' * 4
    arms = p.verify_arms(first)
    for arm in ('X', 'Y'):
        path = first.parent / (arm + '.tgz')
        with tarfile.open(path) as archive:
            archive.extractall(tmp_path / arm, filter='data')
        assert p.tree_manifest(tmp_path / arm / 'package') == p.archive_manifest(path)
        assert p.manifest_digest(p.tree_manifest(tmp_path / arm / 'package')) == arms[arm]['manifest_sha256']
    assert p.content(first.parent / 'Y.tgz') == after
    diff = p.paragraph_diff(before, after).splitlines()
    assert [line[1:] for line in diff if line.startswith('-') and not line.startswith('---')] == p.OLD.decode().splitlines()
    assert [line[1:] for line in diff if line.startswith('+') and not line.startswith('+++')] == p.NEW.decode().splitlines()
    assert arms['Y']['source']['candidate_commit'] == commit


@pytest.mark.parametrize('fault', ['hash', 'integrity', 'control', 'candidate', 'duplicate'])
def test_pack_refuses_invalid_inputs_before_writing(tmp_path, monkeypatch, fault):
    p = load('pack')
    source, before, after, commit = fixture(p, tmp_path, monkeypatch)
    if fault in ('hash', 'integrity'):
        registered = p.read(p.PRIOR / 'registration.json')
        registered['release']['sha256' if fault == 'hash' else 'integrity'] = 'wrong'
    elif fault == 'control':
        monkeypatch.setattr(p, 'git', lambda *args: commit.encode() if args[0] == 'rev-parse' else b'different')
    elif fault == 'candidate':
        original = p.git
        monkeypatch.setattr(p, 'git', lambda *args: after + b'extra change' if args == ('show', commit + ':' + p.FILE) else original(*args))
    else:
        monkeypatch.setattr(p, 'content', lambda _: before + before)
    with pytest.raises(ValueError):
        p.build(source, tmp_path / 'dest', commit)
    assert not (tmp_path / 'dest').exists()


def test_arm_verification_rejects_relabelled_and_changed_artifacts(tmp_path, monkeypatch):
    p = load('pack')
    source, _, _, commit = fixture(p, tmp_path, monkeypatch)
    path = p.build(source, tmp_path / 'arms', commit)
    arms = p.read(path)
    p.write(path, dict(X=arms['Y'], Y=arms['X']))
    with pytest.raises(ValueError, match='identity'):
        p.verify_arms(path)
    p.write(path, arms)
    y = path.parent / 'Y.tgz'
    y.write_bytes(y.read_bytes() + b'drift')
    with pytest.raises(ValueError, match='SHA-256/integrity'):
        p.verify_arms(path)


def test_pair_verification_rejects_other_content_or_metadata_changes(tmp_path, monkeypatch):
    p = load('pack')
    source, _, _, commit = fixture(p, tmp_path, monkeypatch)
    path = p.build(source, tmp_path / 'arms', commit)
    original = path.parent / 'Y.tgz'
    for field in ('mode', 'mtime', 'name', 'bytes', 'order'):
        target = tmp_path / (field + '.tgz')
        with tarfile.open(original) as archive, tarfile.open(target, 'w:gz') as out:
            members = archive.getmembers()
            if field == 'order':
                members.reverse()
            for member in members:
                data = archive.extractfile(member).read() if member.isfile() else None
                if member.name == 'package/bin/devlyn.js':
                    if field in ('mode', 'mtime'):
                        setattr(member, field, getattr(member, field) + 1)
                    elif field == 'name':
                        member.name += '-extra'
                    elif field == 'bytes':
                        data = b'changed bytes'
                        member.size = len(data)
                out.addfile(member, io.BytesIO(data) if data is not None else None)
        with pytest.raises(ValueError):
            p.verify_pair({'X': source, 'Y': target})
